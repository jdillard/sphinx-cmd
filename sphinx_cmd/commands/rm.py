#!/usr/bin/env python3
"""
Command to delete unused .rst files and their unique assets.
"""

import os
import re
from collections import defaultdict

# Regex patterns for reStructuredText directives
DIRECTIVE_PATTERNS = {
    "image": re.compile(r"^\s*\.\.\s+image::\s+(.+)$", re.MULTILINE),
    "figure": re.compile(r"^\s*\.\.\s+figure::\s+(.+)$", re.MULTILINE),
    "include": re.compile(r"^\s*\.\.\s+include::\s+(.+)$", re.MULTILINE),
}


def find_rst_files(path):
    """Find all .rst files in the given path."""
    if os.path.isfile(path) and path.endswith(".rst"):
        return [path]
    rst_files = []
    for root, _, files in os.walk(path):
        for file in files:
            if file.endswith(".rst"):
                rst_files.append(os.path.join(root, file))
    return rst_files


def extract_assets(file_path, processed_includes=None):
    """
    Extract asset references from an .rst file, but don't recursively process includes.

    This function extracts direct assets only to avoid recursion issues.
    The recursive processing happens in a separate phase using the index.

    Args:
        file_path: Path to the RST file
        processed_includes: Not used here, kept for compatibility

    Returns:
        Dictionary mapping asset paths to their directive types
    """
    # Simple implementation that just extracts direct assets
    asset_directives = {}

    if not os.path.exists(file_path) or not os.path.isfile(file_path):
        return {}

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()

            # Process all directive types
            for directive, pattern in DIRECTIVE_PATTERNS.items():
                for match in pattern.findall(content):
                    asset_path = match.strip()
                    asset_full_path = os.path.normpath(
                        os.path.join(os.path.dirname(file_path), asset_path)
                    )
                    # Store the directive type
                    asset_directives[asset_full_path] = directive
    except Exception:
        # Handle any file reading errors silently
        pass

    return asset_directives


def build_asset_index(rst_files):
    """
    Build an index of assets and which files reference them,
    handling include directives properly.
    """
    asset_to_files = defaultdict(set)
    file_to_assets = {}
    asset_directive_map = {}
    include_graph = defaultdict(list)  # Track which files are included by others

    # First pass: collect direct assets from each rst file
    # and build the include graph
    for rst in rst_files:
        try:
            asset_directives = extract_assets(rst)
            direct_assets = set()

            # Process each asset
            for asset, directive in asset_directives.items():
                asset_directive_map[asset] = directive
                direct_assets.add(asset)

                # If this is an include directive, record it in the include graph
                if directive == "include" and os.path.exists(asset):
                    include_graph[rst].append(asset)

            file_to_assets[rst] = direct_assets

        except Exception:
            file_to_assets[rst] = set()

    # Second pass: process include relationships to propagate assets
    # Non-recursive implementation to avoid recursion depth issues
    processed = set()

    def process_includes(file_path):
        """Process includes for a file and return all transitive assets."""
        if file_path in processed:
            return file_to_assets.get(file_path, set())

        processed.add(file_path)
        all_assets = set(file_to_assets.get(file_path, set()))

        # Process each included file
        for included_file in include_graph.get(file_path, []):
            # For each included file, add its assets to the current file
            if included_file not in processed:
                included_assets = process_includes(included_file)
                all_assets.update(included_assets)

        # Update the file's full asset list
        file_to_assets[file_path] = all_assets
        return all_assets

    # Process all root files (those that aren't included by others)
    for rst in rst_files:
        process_includes(rst)

    # Third pass: build the reverse index of which files reference each asset
    for rst_file, assets in file_to_assets.items():
        for asset in assets:
            asset_to_files[asset].add(rst_file)

    return asset_to_files, file_to_assets, asset_directive_map


def delete_unused_assets_and_pages(
    asset_to_files, file_to_assets, asset_directive_map, dry_run=False
):
    """Delete files and their unique assets if not used elsewhere."""
    deleted_pages = []
    deleted_assets = []
    affected_dirs = set()

    for rst_file, assets in file_to_assets.items():
        if not assets:  # Skip files with no assets
            continue

        # Check if all assets are unique to this file
        all_unique = True
        for asset in assets:
            if len(asset_to_files[asset]) > 1:
                all_unique = False
                break

        if all_unique:  # All assets are unique to this file
            # First remove the assets
            for asset in assets:
                directive = asset_directive_map.get(asset, "asset")
                if os.path.exists(asset):
                    if dry_run:
                        print(f"[dry-run] Would delete {directive}: {asset}")
                    else:
                        affected_dirs.add(os.path.dirname(asset))
                        os.remove(asset)
                        deleted_assets.append(asset)

            # Then remove the RST file itself
            if os.path.exists(rst_file):
                if dry_run:
                    print(f"[dry-run] Would delete page: {rst_file}")
                else:
                    affected_dirs.add(os.path.dirname(rst_file))
                    os.remove(rst_file)
                    deleted_pages.append(rst_file)

    return deleted_pages, deleted_assets, affected_dirs


def remove_empty_dirs(dirs, original_path, dry_run=False):
    """Remove empty directories, bottom-up."""
    deleted_dirs = []

    # Add parent directories to the affected dirs set
    all_dirs = set(dirs)
    for dir_path in dirs:
        # Add all parent directories up to but not including the original path
        parent = os.path.dirname(dir_path)
        while parent and os.path.exists(parent) and parent != original_path:
            all_dirs.add(parent)
            parent = os.path.dirname(parent)

    # Sort by path depth (deepest first)
    sorted_dirs = sorted(all_dirs, key=lambda d: d.count(os.sep), reverse=True)

    # Process directories from deepest to shallowest
    for dir_path in sorted_dirs:
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            continue

        # Check if directory is empty
        if not os.listdir(dir_path):
            if dry_run:
                print(f"[dry-run] Would delete empty directory: {dir_path}")
            else:
                os.rmdir(dir_path)
                deleted_dirs.append(dir_path)

    # Check if the original path (if it's a directory) is now empty and should
    # be removed
    if os.path.isdir(original_path) and not os.listdir(original_path):
        if dry_run:
            print(f"[dry-run] Would delete empty directory: {original_path}")
        else:
            os.rmdir(original_path)
            deleted_dirs.append(original_path)

    return deleted_dirs


def execute(args):
    """Execute the rm command."""
    original_path = os.path.abspath(args.path)

    # Find RST files to process
    rst_files = find_rst_files(args.path)

    # If no RST files found, exit early
    if not rst_files:
        print(f"No RST files found in {args.path}")
        return

    # Build asset relationships
    asset_to_files, file_to_assets, asset_directive_map = build_asset_index(rst_files)

    # Delete unused files and assets
    deleted_pages, deleted_assets, affected_dirs = delete_unused_assets_and_pages(
        asset_to_files, file_to_assets, asset_directive_map, args.dry_run
    )

    # Remove empty directories
    deleted_dirs = []
    if affected_dirs:
        deleted_dirs = remove_empty_dirs(affected_dirs, original_path, args.dry_run)

    # Print summary if not in dry-run mode
    if not args.dry_run:
        print(f"\nDeleted {len(deleted_assets)} unused asset(s):")
        for a in deleted_assets:
            directive = asset_directive_map.get(a, "asset")
            print(f"  - ({directive}) {a}")

        print(f"\nDeleted {len(deleted_pages)} RST page(s):")
        for p in deleted_pages:
            print(f"  - {p}")

        if deleted_dirs:
            print(f"\nDeleted {len(deleted_dirs)} empty directory/directories:")
            for d in deleted_dirs:
                print(f"  - {d}")
