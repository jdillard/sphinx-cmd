#!/usr/bin/env python3
"""
Command to delete unused .rst files and their unique assets.
"""

import os
import re
from collections import defaultdict
from pathlib import Path

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


def extract_assets(
    file_path,
    visited=None,
    cli_directives=None,
    context_path=None,
    verbose=False,
    base_dir=None,
):
    """Extract asset references from an .rst file, recursively parsing includes."""
    if visited is None:
        visited = set()

    # Use the directory of the original file as base for relative path resolution
    if base_dir is None:
        base_dir = os.path.dirname(file_path)

    # Avoid circular includes
    abs_path = os.path.abspath(file_path)
    if abs_path in visited:
        return {}
    visited.add(abs_path)

    if verbose:
        print(f"Processing file: {file_path}")

    asset_directives = {}
    directive_patterns = get_directive_patterns(cli_directives, context_path)

    # If file doesn't exist, skip it
    if not os.path.exists(file_path):
        if verbose:
            print(f"Skipping non-existent file: {file_path}")
        return asset_directives

    try:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
            for directive, pattern in directive_patterns.items():
                for match in pattern.findall(content):
                    asset_path = match.strip()
                    if directive == "include":
                        # Include paths are resolved relative to the current file
                        asset_full_path = os.path.normpath(
                            os.path.join(os.path.dirname(file_path), asset_path)
                        )
                    else:
                        # Non-include assets are resolved relative to the base directory
                        asset_full_path = os.path.normpath(
                            os.path.join(base_dir, asset_path)
                        )
                    asset_abs_path = os.path.abspath(asset_full_path)

                    if verbose:
                        print(f"Found {directive}: {asset_path}")
                        print(f"  Absolute path: {asset_abs_path}")

                    if directive == "include":
                        if verbose:
                            print(f"Parsing include: {asset_full_path}")
                        # Recursively extract assets from included files,
                        # preserving base_dir
                        included_assets = extract_assets(
                            asset_full_path,
                            visited,
                            cli_directives,
                            context_path,
                            verbose,
                            base_dir,
                        )
                        asset_directives.update(included_assets)

                    asset_directives[asset_full_path] = directive
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return asset_directives


def build_asset_index(rst_files, cli_directives=None, context_path=None, verbose=False):
    """Build an index of assets and which files reference them."""
    asset_to_files = defaultdict(set)
    file_to_assets = {}
    asset_directive_map = {}

    if verbose:
        print(f"Building asset index for {len(rst_files)} RST files...")

    for rst in rst_files:
        asset_directives = extract_assets(
            rst,
            cli_directives=cli_directives,
            context_path=context_path,
            verbose=verbose,
        )
        file_to_assets[rst] = set(asset_directives.keys())
        for asset, directive in asset_directives.items():
            asset_to_files[asset].add(rst)
            asset_directive_map[asset] = directive

    if verbose:
        print(f"Found {len(asset_to_files)} unique assets across all files")

    return asset_to_files, file_to_assets, asset_directive_map


def get_transitive_includes(
    file_path,
    visited=None,
    cli_directives=None,
    context_path=None,
    verbose=False,
    base_dir=None,
):
    """Get all files included transitively from a file."""
    if visited is None:
        visited = set()

    # Use the directory of the original file as base for relative path resolution
    if base_dir is None:
        base_dir = os.path.dirname(file_path)

    # Avoid circular includes
    abs_path = os.path.abspath(file_path)
    if abs_path in visited:
        return set()
    visited.add(abs_path)

    if verbose:
        print(f"Checking for includes in: {file_path}")

    includes = set()

    if not os.path.exists(file_path):
        if verbose:
            print(f"Skipping non-existent file: {file_path}")
        return includes

    directive_patterns = get_directive_patterns(cli_directives, context_path)

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
                    if verbose:
                        print(f"Found include: {include_path}")

                    # Recursively get includes from the included file,
                    # preserving base_dir
                    includes.update(
                        get_transitive_includes(
                            include_full_path,
                            visited,
                            cli_directives,
                            context_path,
                            verbose,
                            base_dir,
                        )
                    )
    except Exception as e:
        print(f"Warning: Could not read {file_path}: {e}")

    return includes


# Toctree pattern similar to mv.py
TOCTREE_PATTERN = re.compile(
    r"^\s*\.\.\s+toctree::(.*?)(?=^\S|\Z)", re.DOTALL | re.MULTILINE
)


def find_toctree_references(rst_files, removed_files, verbose=False):
    """Find which files contain toctree references to files being removed."""
    toctree_references = {}

    if verbose:
        print(
            f"Checking for toctree references to removed files "
            f"in {len(rst_files)} files..."
        )

    # Convert removed files to Path objects for proper comparison
    removed_paths = {Path(f).resolve() for f in removed_files}
    removed_stems = {Path(f).stem for f in removed_files}

    for rst_file in rst_files:
        if rst_file in removed_files:
            continue  # Skip files that are being removed

        if not os.path.exists(rst_file):
            continue

        try:
            with open(rst_file, "r", encoding="utf-8") as f:
                content = f.read()

            # Find toctree entries
            toctree_matches = TOCTREE_PATTERN.findall(content)
            for toctree_content in toctree_matches:
                # Extract file references from toctree
                lines = toctree_content.split("\n")
                matching_entries = []
                rst_file_path = Path(rst_file)

                for line in lines:
                    line = line.strip()
                    if line and not line.startswith(":"):  # Skip options
                        ref_file = line.split()[0] if line.split() else ""
                        if ref_file:
                            ref_path = Path(ref_file)

                            # Check for matches using multiple strategies
                            is_match = False

                            # Strategy 1: Try to resolve the reference relative
                            # to the toctree file
                            try:
                                resolved_ref = (
                                    (rst_file_path.parent / ref_path)
                                    .with_suffix(".rst")
                                    .resolve()
                                )
                                if resolved_ref in removed_paths:
                                    is_match = True
                            except:
                                pass

                            # Strategy 2: Check if reference with .rst extension
                            # matches any removed file
                            if not is_match:
                                ref_with_rst = ref_path.with_suffix(".rst").resolve()
                                if ref_with_rst in removed_paths:
                                    is_match = True

                            # Strategy 3: Check direct path match
                            # (for absolute or root-relative paths)
                            if not is_match:
                                try:
                                    # If the reference starts with '/', treat it as
                                    # relative to the directory containing the toctree
                                    if str(ref_path).startswith("/"):
                                        # Remove leading slash and resolve relative
                                        # to the directory containing the toctree file
                                        rel_ref_path = Path(str(ref_path)[1:])
                                        resolved_ref = (
                                            (rst_file_path.parent / rel_ref_path)
                                            .with_suffix(".rst")
                                            .resolve()
                                        )
                                        if resolved_ref in removed_paths:
                                            is_match = True
                                        # Also check without adding .rst extension
                                        # in case it's already there
                                        resolved_ref_no_ext = (
                                            rst_file_path.parent / rel_ref_path
                                        ).resolve()
                                        if resolved_ref_no_ext in removed_paths:
                                            is_match = True
                                    else:
                                        # Regular path resolution for non-absolute paths
                                        if (
                                            ref_path.resolve() in removed_paths
                                            or Path(str(ref_path) + ".rst").resolve()
                                            in removed_paths
                                        ):
                                            is_match = True
                                except:
                                    pass

                            # Strategy 4: Only fall back to stem matching if the
                            # previous strategies failed to resolve paths
                            # This should only happen when files don't exist
                            # or paths are broken
                            if not is_match and ref_path.stem in removed_stems:
                                # Only use stem matching if we couldn't resolve the path
                                # in previous strategies. Check if the reference file
                                # actually exists at the resolved location
                                try:
                                    expected_location = (
                                        rst_file_path.parent / ref_path
                                    ).with_suffix(".rst")
                                    if not expected_location.exists():
                                        # File doesn't exist where it should, so stem
                                        # matching might be appropriate
                                        for removed_path in removed_paths:
                                            if (
                                                ref_path.stem == removed_path.stem
                                                and len(ref_path.parts)
                                                == 1  # Only simple filename references
                                                and str(ref_path) == removed_path.stem
                                            ):  # Exact stem match only
                                                is_match = True
                                                break
                                except:
                                    # If we can't even check if the file exists,
                                    # skip stem matching entirely
                                    pass

                            if is_match:
                                matching_entries.append(ref_file)
                                if verbose:
                                    print(
                                        f"Found toctree reference to "
                                        f"'{ref_file}' in {rst_file}"
                                    )

                if matching_entries:
                    if rst_file not in toctree_references:
                        toctree_references[rst_file] = []
                    toctree_references[rst_file].extend(matching_entries)

        except Exception as e:
            print(f"Warning: Could not read {rst_file}: {e}")

    return toctree_references


def remove_toctree_entries(file_path, entries_to_remove, dry_run=False, verbose=False):
    """Remove specific entries from toctree directives in a file."""
    if not os.path.exists(file_path):
        return False

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Process each toctree directive
        def replace_toctree(match):
            toctree_content = match.group(1)
            lines = toctree_content.split("\n")
            new_lines = []

            for line in lines:
                stripped = line.strip()
                if stripped and not stripped.startswith(":"):  # Skip options
                    ref_file = stripped.split()[0] if stripped.split() else ""
                    if ref_file not in entries_to_remove:
                        new_lines.append(line)
                    elif verbose:
                        print(f"  Removing toctree entry: {ref_file}")
                else:
                    new_lines.append(line)

            return ".. toctree::" + "\n".join(new_lines)

        new_content = TOCTREE_PATTERN.sub(replace_toctree, content)

        if new_content != original_content:
            if dry_run:
                print(f"[dry-run] Would update toctree entries in: {file_path}")
            else:
                with open(file_path, "w", encoding="utf-8") as f:
                    f.write(new_content)
                if verbose:
                    print(f"Updated toctree entries in: {file_path}")
            return True
        else:
            if verbose:
                print(f"No toctree changes needed in: {file_path}")
            return False

    except Exception as e:
        print(f"Error updating toctree entries in {file_path}: {e}")
        return False


def delete_unused_assets_and_pages(
    asset_to_files,
    file_to_assets,
    asset_directive_map,
    dry_run=False,
    context_path=None,
    verbose=False,
):
    """
    Delete files and their unique assets if not used elsewhere.

    If context_path is provided, only files within that context will be removed
    for safety reasons.
    """
    deleted_pages = []
    deleted_assets = []
    affected_dirs = set()
    would_delete_something = False  # Flag to track if anything would be deleted

    # Track which files have been processed to avoid duplicates
    processed_files = set()

    if verbose:
        print("Analyzing files and assets for removal...")

    for rst_file, assets in file_to_assets.items():
        # Skip if already processed (can happen with transitive includes)
        if rst_file in processed_files:
            if verbose:
                print(f"Skipping already processed file: {rst_file}")
            continue

        unused_assets = [a for a in assets if len(asset_to_files[a]) == 1]

        if verbose:
            print(
                f"File: {rst_file} has {len(assets)} assets, {len(unused_assets)}"
                " are unique"
            )

        if len(unused_assets) == len(assets):  # All assets are unique to this file
            if verbose:
                print(f"File {rst_file} has no shared assets, processing for removal")

            # Get all files transitively included by this file
            included_files = get_transitive_includes(rst_file, verbose=verbose)

            if verbose and included_files:
                print(f"Found {len(included_files)} transitively included files")

            # Process the main file and all its includes
            for file_to_process in [rst_file] + list(included_files):
                if (
                    file_to_process in processed_files
                    or file_to_process not in file_to_assets
                ):
                    if verbose and file_to_process in processed_files:
                        print(f"Skipping already processed include: {file_to_process}")
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
                        # Check if asset is within context path if context is provided
                        is_in_context = True
                        if context_path:
                            asset_abs_path = os.path.abspath(asset)
                            context_abs_path = os.path.abspath(context_path)
                            # Check if the asset path starts with the context path
                            is_in_context = asset_abs_path.startswith(context_abs_path)

                        if not is_in_context:
                            if dry_run:
                                print(
                                    f"[dry-run] Skipping {directive} (outside context):"
                                    f" {asset}"
                                )
                            elif verbose:
                                print(f"Skipping asset (outside context): {asset}")
                            continue

                        if dry_run:
                            origin = (
                                " (from include)" if file_to_process != rst_file else ""
                            )
                            print(
                                f"[dry-run] Would delete {directive}: {asset}{origin}"
                            )
                            would_delete_something = True
                        else:
                            if verbose:
                                print(f"Removing asset: {asset}")
                            affected_dirs.add(os.path.dirname(asset))
                            os.remove(asset)
                            deleted_assets.append(asset)

                # Delete the file if it exists and isn't the main rst file being checked
                if file_to_process != rst_file and os.path.exists(file_to_process):
                    # Check if file is within context path if context is provided
                    is_in_context = True
                    if context_path:
                        file_abs_path = os.path.abspath(file_to_process)
                        context_abs_path = os.path.abspath(context_path)
                        # Check if the file path starts with the context path
                        is_in_context = file_abs_path.startswith(context_abs_path)

                    if not is_in_context:
                        if dry_run:
                            print(
                                f"[dry-run] Skipping included file (outside context):"
                                f" {file_to_process}"
                            )
                        elif verbose:
                            print(
                                "Skipping included file (outside context):"
                                f" {file_to_process}"
                            )
                        continue

                    if dry_run:
                        print(
                            f"[dry-run] Would delete included file: {file_to_process}"
                        )
                        would_delete_something = True
                    else:
                        if verbose:
                            print(f"Removing included file: {file_to_process}")
                        affected_dirs.add(os.path.dirname(file_to_process))
                        os.remove(file_to_process)
                        deleted_pages.append(file_to_process)

            # Finally, delete the main rst file
            if os.path.exists(rst_file):
                # Check if file is within context path if context is provided
                is_in_context = True
                if context_path:
                    file_abs_path = os.path.abspath(rst_file)
                    context_abs_path = os.path.abspath(context_path)
                    # Check if the file path starts with the context path
                    is_in_context = file_abs_path.startswith(context_abs_path)

                if not is_in_context:
                    if dry_run:
                        print(f"[dry-run] Skipping page (outside context): {rst_file}")
                    elif verbose:
                        print(f"Skipping page (outside context): {rst_file}")
                    continue

                if dry_run:
                    print(f"[dry-run] Would delete page: {rst_file}")
                    would_delete_something = True
                else:
                    if verbose:
                        print(f"Removing page: {rst_file}")
                    affected_dirs.add(os.path.dirname(rst_file))
                    os.remove(rst_file)
                    deleted_pages.append(rst_file)

    return deleted_pages, deleted_assets, affected_dirs, would_delete_something


def remove_empty_dirs(dirs, original_path, dry_run=False, verbose=False):
    """Remove empty directories, bottom-up."""
    deleted_dirs = []

    if verbose:
        print(f"Checking for empty directories in {len(dirs)} affected paths...")

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

    if verbose:
        print(f"Scanning {len(sorted_dirs)} directories for emptiness...")

    # Process directories from deepest to shallowest
    for dir_path in sorted_dirs:
        if not os.path.exists(dir_path) or not os.path.isdir(dir_path):
            if verbose:
                print(f"Skipping non-existent or non-directory path: {dir_path}")
            continue

        # Check if directory is empty
        if not os.listdir(dir_path):
            if dry_run:
                print(f"[dry-run] Would delete empty directory: {dir_path}")
            else:
                if verbose:
                    print(f"Removing empty directory: {dir_path}")
                os.rmdir(dir_path)
                deleted_dirs.append(dir_path)
        elif verbose:
            print(f"Directory not empty, skipping: {dir_path}")

    # Check if the original path (if it's a directory) is now empty and should
    # be removed
    if os.path.isdir(original_path) and not os.listdir(original_path):
        if dry_run:
            print(f"[dry-run] Would delete empty directory: {original_path}")
        else:
            if verbose:
                print(f"Removing empty original directory: {original_path}")
            os.rmdir(original_path)
            deleted_dirs.append(original_path)

    return deleted_dirs


def execute(args):
    """Execute the rm command."""
    original_path = os.path.abspath(args.path)

    # Get global options
    context_path = getattr(args, "context", None)
    dry_run = getattr(args, "dry_run", False)
    directives = getattr(args, "directives", None)
    verbose = getattr(args, "verbose", False)

    if verbose:
        print(f"Starting sphinx-cmd rm operation on path: {original_path}")
        print(f"Options: dry-run={dry_run}, directives={directives}")

    rst_files = find_rst_files(args.path)

    if verbose:
        print(f"Found {len(rst_files)} RST files to analyze")

    # Display context information
    if context_path:
        context_abs_path = os.path.abspath(context_path)
        print(f"Context path: {context_abs_path}")
        print("Safety mode: Only files within the context path will be removed")
    else:
        print("Context path not set - all unused files will be removed")

    asset_to_files, file_to_assets, asset_directive_map = build_asset_index(
        rst_files, cli_directives=directives, context_path=context_path, verbose=verbose
    )

    deleted_pages, deleted_assets, affected_dirs, would_delete_something = (
        delete_unused_assets_and_pages(
            asset_to_files,
            file_to_assets,
            asset_directive_map,
            dry_run,
            context_path,
            verbose,
        )
    )

    # Handle toctree updates (default behavior)
    toctree_updates = 0
    updated_toctree_files = []
    if deleted_pages or would_delete_something:
        # Get list of files to be deleted (or would be deleted in dry-run)
        files_to_remove = deleted_pages if not dry_run else []

        # In dry-run mode, we need to determine which files would be deleted
        if dry_run and would_delete_something:
            files_to_remove = []
            for rst_file, assets in file_to_assets.items():
                unused_assets = [a for a in assets if len(asset_to_files[a]) == 1]
                if len(unused_assets) == len(
                    assets
                ):  # All assets are unique to this file
                    # Check context constraints like in delete_unused_assets_and_pages
                    is_in_context = True
                    if context_path:
                        file_abs_path = os.path.abspath(rst_file)
                        context_abs_path = os.path.abspath(context_path)
                        is_in_context = file_abs_path.startswith(context_abs_path)
                    if is_in_context:
                        files_to_remove.append(rst_file)

        if files_to_remove:
            if verbose:
                print(
                    f"Checking for toctree references to "
                    f"{len(files_to_remove)} removed files..."
                )

            # Find all RST files that might contain toctrees
            all_rst_files = find_rst_files(context_path if context_path else ".")

            # Find toctree references to files being removed
            toctree_references = find_toctree_references(
                all_rst_files, files_to_remove, verbose
            )

            if toctree_references:
                print(
                    f"\nFound toctree references in {len(toctree_references)} file(s):"
                )

                for file_path, entries in toctree_references.items():
                    print(f"  - {file_path}: {', '.join(entries)}")

                    # Remove the toctree entries
                    if remove_toctree_entries(file_path, entries, dry_run, verbose):
                        toctree_updates += 1
                        updated_toctree_files.append(file_path)
            else:
                if verbose:
                    print("No toctree references found to removed files.")
    else:
        if verbose:
            print("No files removed, skipping toctree updates.")

    deleted_dirs = []
    if affected_dirs:
        deleted_dirs = remove_empty_dirs(affected_dirs, original_path, dry_run, verbose)

    if dry_run:
        # In dry-run mode, show a summary of what would be deleted
        if not would_delete_something:
            print("\n[dry-run] No unused files found, nothing would be deleted.")
        if toctree_updates > 0:
            print(
                f"[dry-run] Would update toctree entries in {toctree_updates} file(s):"
            )
            for file_path in updated_toctree_files:
                print(f"  - {file_path}")
    else:
        # Not in dry-run mode, report what was actually deleted
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

        if toctree_updates > 0:
            print(f"\nUpdated toctree entries in {toctree_updates} file(s):")
            for file_path in updated_toctree_files:
                print(f"  - {file_path}")

    if verbose:
        print("Operation completed successfully")
