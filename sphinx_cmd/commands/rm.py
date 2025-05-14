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


def extract_assets(file_path):
    """Extract asset references from an .rst file."""
    asset_directives = {}
    with open(file_path, encoding="utf-8") as f:
        content = f.read()
        for directive, pattern in DIRECTIVE_PATTERNS.items():
            for match in pattern.findall(content):
                asset_path = match.strip()
                asset_full_path = os.path.normpath(
                    os.path.join(os.path.dirname(file_path), asset_path)
                )
                asset_directives[asset_full_path] = directive
    return asset_directives


def build_asset_index(rst_files):
    """Build an index of assets and which files reference them."""
    asset_to_files = defaultdict(set)
    file_to_assets = {}
    asset_directive_map = {}

    for rst in rst_files:
        asset_directives = extract_assets(rst)
        file_to_assets[rst] = set(asset_directives.keys())
        for asset, directive in asset_directives.items():
            asset_to_files[asset].add(rst)
            asset_directive_map[asset] = directive
    return asset_to_files, file_to_assets, asset_directive_map


def delete_unused_assets_and_pages(
    asset_to_files, file_to_assets, asset_directive_map, dry_run=False
):
    """Delete files and their unique assets if not used elsewhere."""
    deleted_pages = []
    deleted_assets = []
    affected_dirs = set()

    for rst_file, assets in file_to_assets.items():
        unused_assets = [a for a in assets if len(asset_to_files[a]) == 1]
        if len(unused_assets) == len(assets):  # All assets are unique to this file
            for asset in unused_assets:
                directive = asset_directive_map.get(asset, "asset")
                if os.path.exists(asset):
                    if dry_run:
                        print(f"[dry-run] Would delete {directive}: {asset}")
                    else:
                        affected_dirs.add(os.path.dirname(asset))
                        os.remove(asset)
                        deleted_assets.append(asset)
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
    asset_to_files, file_to_assets, asset_directive_map = build_asset_index(rst_files)
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
