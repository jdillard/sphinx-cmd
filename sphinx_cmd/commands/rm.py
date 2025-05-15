#!/usr/bin/env python3
"""
Command to delete unused .rst files and their unique assets.
"""

import os
from collections import defaultdict

from sphinx_cmd.config import get_directive_patterns


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


def extract_assets(file_path, visited=None, cli_directives=None):
    """Extract asset references from an .rst file, recursively parsing includes."""
    if visited is None:
        visited = set()

    # Avoid circular includes
    abs_path = os.path.abspath(file_path)
    if abs_path in visited:
        return {}
    visited.add(abs_path)

    asset_directives = {}
    directive_patterns = get_directive_patterns(cli_directives)

    # If file doesn't exist, skip it
    if not os.path.exists(file_path):
        return asset_directives

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            for directive, pattern in directive_patterns.items():
                for match in pattern.findall(content):
                    asset_path = match.strip()
                    asset_full_path = os.path.normpath(
                        os.path.join(os.path.dirname(file_path), asset_path)
                    )

                    if directive == "include":
                        # Recursively extract assets from included files
                        included_assets = extract_assets(
                            asset_full_path, visited.copy()
                        )
                        asset_directives.update(included_assets)

                    asset_directives[asset_full_path] = directive
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return asset_directives


def build_asset_index(rst_files, cli_directives=None):
    """Build an index of assets and which files reference them."""
    asset_to_files = defaultdict(set)
    file_to_assets = {}
    asset_directive_map = {}

    for rst in rst_files:
        asset_directives = extract_assets(rst, cli_directives=cli_directives)
        file_to_assets[rst] = set(asset_directives.keys())
        for asset, directive in asset_directives.items():
            asset_to_files[asset].add(rst)
            asset_directive_map[asset] = directive
    return asset_to_files, file_to_assets, asset_directive_map


def get_transitive_includes(file_path, visited=None, cli_directives=None):
    """Get all files included transitively from a file."""
    if visited is None:
        visited = set()

    # Avoid circular includes
    abs_path = os.path.abspath(file_path)
    if abs_path in visited:
        return set()
    visited.add(abs_path)

    includes = set()

    if not os.path.exists(file_path):
        return includes

    directive_patterns = get_directive_patterns(cli_directives)

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            # Only process include directive
            if "include" in directive_patterns:
                pattern = directive_patterns["include"]
                for match in pattern.findall(content):
                    include_path = match.strip()
                    include_full_path = os.path.normpath(
                        os.path.join(os.path.dirname(file_path), include_path)
                    )
                    includes.add(include_full_path)
                    # Recursively get includes from the included file
                    includes.update(
                        get_transitive_includes(
                            include_full_path, visited.copy(), cli_directives
                        )
                    )
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return includes


def delete_unused_assets_and_pages(
    asset_to_files, file_to_assets, asset_directive_map, dry_run=False
):
    """Delete files and their unique assets if not used elsewhere."""
    deleted_pages = []
    deleted_assets = []
    affected_dirs = set()

    # Track which files have been processed to avoid duplicates
    processed_files = set()

    for rst_file, assets in file_to_assets.items():
        # Skip if already processed (can happen with transitive includes)
        if rst_file in processed_files:
            continue

        unused_assets = [a for a in assets if len(asset_to_files[a]) == 1]
        if len(unused_assets) == len(assets):  # All assets are unique to this file
            # Get all files transitively included by this file
            included_files = get_transitive_includes(rst_file)

            # Process the main file and all its includes
            for file_to_process in [rst_file] + list(included_files):
                if (
                    file_to_process in processed_files
                    or file_to_process not in file_to_assets
                ):
                    continue

                processed_files.add(file_to_process)
                file_assets = file_to_assets.get(file_to_process, set())
                file_unused_assets = [
                    a for a in file_assets if len(asset_to_files[a]) == 1
                ]

                # Delete unused assets for this file
                for asset in file_unused_assets:
                    directive = asset_directive_map.get(asset, "asset")
                    if os.path.exists(asset) and asset not in deleted_assets:
                        if dry_run:
                            origin = (
                                " (from include)" if file_to_process != rst_file else ""
                            )
                            print(
                                f"[dry-run] Would delete {directive}: {asset}{origin}"
                            )
                        else:
                            affected_dirs.add(os.path.dirname(asset))
                            os.remove(asset)
                            deleted_assets.append(asset)

                # Delete the file if it exists and isn't the main rst file being checked
                if file_to_process != rst_file and os.path.exists(file_to_process):
                    if dry_run:
                        print(
                            f"[dry-run] Would delete included file: {file_to_process}"
                        )
                    else:
                        affected_dirs.add(os.path.dirname(file_to_process))
                        os.remove(file_to_process)
                        deleted_pages.append(file_to_process)

            # Finally, delete the main rst file
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
    rst_files = find_rst_files(args.path)
    asset_to_files, file_to_assets, asset_directive_map = build_asset_index(
        rst_files, cli_directives=args.directives
    )
    deleted_pages, deleted_assets, affected_dirs = delete_unused_assets_and_pages(
        asset_to_files, file_to_assets, asset_directive_map, args.dry_run
    )

    deleted_dirs = []
    if affected_dirs:
        deleted_dirs = remove_empty_dirs(affected_dirs, original_path, args.dry_run)

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
