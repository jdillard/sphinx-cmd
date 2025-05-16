#!/usr/bin/env python3
"""
Command to move/rename .rst files and update all references.
"""

import re
import shutil
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

# Regex patterns for different types of references in reStructuredText
REFERENCE_PATTERNS = {
    "toctree": re.compile(r"^\s*(\S+)\s*$", re.MULTILINE),
    "include": re.compile(r"^\s*\.\.\s+include::\s+(.+)$", re.MULTILINE),
    "literalinclude": re.compile(r"^\s*\.\.\s+literalinclude::\s+(.+)$", re.MULTILINE),
    "code-block": re.compile(
        r"^\s*\.\.\s+code-block::\s+\w+\s*\n\s*:name:\s+(.+)$", re.MULTILINE
    ),
    "reference": re.compile(r":doc:`([^`]+)`", re.MULTILINE),
    "internal_link": re.compile(r"`([^<>`]+)\s+<([^>]+)>`__?", re.MULTILINE),
}

# Patterns that appear in toctree contexts
TOCTREE_PATTERN = re.compile(
    r"^\s*\.\.\s+toctree::(.*?)(?=^\S|\Z)", re.DOTALL | re.MULTILINE
)


def find_all_rst_files(root_path: str) -> List[str]:
    """Find all .rst files in the given directory tree."""
    rst_files = []
    root = Path(root_path)

    if root.is_file() and root.suffix == ".rst":
        return [str(root)]

    for file_path in root.rglob("*.rst"):
        rst_files.append(str(file_path))

    return rst_files


def extract_references(
    file_path: str, context_path: Optional[str] = None, verbose: bool = False
) -> Dict[str, List[str]]:
    """Extract all file references from an .rst file."""
    references = defaultdict(list)

    if verbose:
        print(f"Extracting references from: {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find toctree entries
    toctree_matches = TOCTREE_PATTERN.findall(content)
    for toctree_content in toctree_matches:
        if verbose:
            print(f"Found toctree directive in {file_path}")

        # Extract file references from toctree
        lines = toctree_content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith(":"):  # Skip options
                # Handle both relative and absolute paths
                ref_file = line.split()[0] if line.split() else ""
                if ref_file:
                    references["toctree"].append(ref_file)
                    if verbose:
                        print(f"Found toctree entry: {ref_file}")

    # Find other types of references
    for ref_type, pattern in REFERENCE_PATTERNS.items():
        if ref_type == "toctree":
            continue  # Already handled above

        for match in pattern.findall(content):
            if isinstance(match, tuple):
                # For patterns with multiple groups, take the relevant one
                ref_path = match[1] if ref_type == "internal_link" else match[0]
            else:
                ref_path = match
            references[ref_type].append(ref_path)

            if verbose:
                print(f"Found {ref_type} reference: {ref_path}")
                # For references that could be image files or other assets, show absolute path
                if ref_type in ["image", "figure", "include"]:
                    ref_full_path = Path(file_path).parent / ref_path
                    ref_abs_path = ref_full_path.resolve()
                    print(f"  Absolute path: {ref_abs_path}")

    if verbose and not references:
        print(f"No references found in {file_path}")

    return dict(references)


def find_files_referencing(
    target_file: str,
    all_files: List[str],
    context_path: Optional[str] = None,
    verbose: bool = False,
) -> List[Tuple[str, str]]:
    """Find all files that reference the target file."""
    referencing_files = []
    target_path = Path(target_file)
    target_stem = target_path.stem  # filename without extension

    if verbose:
        print(f"Searching for references to {target_file} (stem: {target_stem})")
        print(f"Checking {len(all_files)} files for references...")

    for file_path in all_files:
        if file_path == target_file:
            if verbose:
                print(f"Skipping the target file itself: {file_path}")
            continue

        try:
            # Extract references using context from conf.py if provided
            references = extract_references(
                file_path, context_path=context_path, verbose=verbose
            )

            for ref_type, ref_list in references.items():
                for ref in ref_list:
                    # Normalize the reference path
                    ref_path = Path(ref)

                    # Check if this reference matches our target file
                    if (
                        ref_path.stem == target_stem
                        or ref == target_stem
                        or str(ref_path.with_suffix(".rst")) == target_file
                    ):
                        referencing_files.append((file_path, ref_type))
                        if verbose:
                            print(f"Found reference in {file_path} ({ref_type}): {ref}")
                            # For references that could be image files or other assets, show absolute path
                            if ref_type in ["image", "figure", "include"]:
                                ref_full_path = Path(file_path).parent / ref
                                ref_abs_path = ref_full_path.resolve()
                                print(f"  Absolute path: {ref_abs_path}")
                        break
        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    if verbose:
        print(f"Found {len(referencing_files)} files referencing {target_file}")

    return referencing_files


def update_references_in_file(
    file_path: str, old_ref: str, new_ref: str, verbose: bool = False
) -> bool:
    """Update references to the moved file in a single file."""
    old_path = Path(old_ref)
    new_path = Path(new_ref)
    old_stem = old_path.stem
    new_stem = new_path.stem

    if verbose:
        print(f"Updating references in {file_path}")
        print(f"  Replacing references from '{old_stem}' to '{new_stem}'")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Update different types of references
        # 1. Toctree entries
        new_content = re.sub(
            rf"^\s*{re.escape(old_stem)}\s*$",
            f"   {new_stem}",
            content,
            flags=re.MULTILINE,
        )
        if new_content != content and verbose:
            print(f"  Updated toctree entries in {file_path}")
        content = new_content

        # 2. :doc: references
        new_content = re.sub(
            rf":doc:`{re.escape(old_stem)}`", f":doc:`{new_stem}`", content
        )
        if new_content != content and verbose:
            print(f"  Updated :doc: references in {file_path}")
        content = new_content

        # 3. Include directives
        for directive in ["include", "literalinclude"]:
            new_content = re.sub(
                rf"^\s*\.\.\s+{directive}::\s+{re.escape(old_ref)}",
                f".. {directive}:: {new_ref}",
                content,
                flags=re.MULTILINE,
            )
            if new_content != content and verbose:
                print(f"  Updated {directive} directive in {file_path}")
            content = new_content

        # 4. Internal links
        new_content = re.sub(
            rf"`([^<>`]+)\s+<{re.escape(old_ref)}>`__?", rf"`\1 <{new_ref}>`_", content
        )
        if new_content != content and verbose:
            print(f"  Updated internal links in {file_path}")
        content = new_content

        # Write back if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            if verbose:
                print(f"  Successfully updated references in {file_path}")
            return True
        else:
            if verbose:
                print(f"  No changes needed in {file_path}")
            return False

    except Exception as e:
        print(f"Error updating references in {file_path}: {e}")
        return False


def move_rst_file(
    source: str,
    destination: str,
    update_references: bool = True,
    dry_run: bool = False,
    context_path: Optional[str] = None,
    verbose: bool = False,
) -> None:
    """Move an RST file and optionally update all references to it."""
    source_path = Path(source).resolve()
    dest_path = Path(destination).resolve()

    if verbose:
        print(f"Preparing to move file from {source} to {destination}")
        print(f"Source full path: {source_path}")
        print(f"Destination full path: {dest_path}")

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    if not source_path.suffix == ".rst":
        raise ValueError(f"Source must be an .rst file: {source}")

    # If destination is a directory, use the same filename
    if dest_path.is_dir():
        if verbose:
            print(
                f"Destination is a directory, using original filename:"
                f" {source_path.name}"
            )
        dest_path = dest_path / source_path.name
    elif not dest_path.suffix:
        if verbose:
            print(f"Adding .rst extension to destination: {dest_path}")
        dest_path = dest_path.with_suffix(".rst")

    # Get the relative paths for updating references
    # Try to find a common root to make relative paths
    try:
        source_rel = source_path.relative_to(Path.cwd())
        dest_rel = dest_path.relative_to(Path.cwd())
        if verbose:
            print(f"Using relative paths from current directory: {Path.cwd()}")
    except ValueError:
        # Fall back to absolute paths if no common root
        source_rel = source_path
        dest_rel = dest_path
        if verbose:
            print("No common root found, using absolute paths")

    print(f"Moving: {source_rel} -> {dest_rel}")

    if not dry_run:
        # Create destination directory if it doesn't exist
        if not dest_path.parent.exists():
            if verbose:
                print(f"Creating parent directory: {dest_path.parent}")
            dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        if verbose:
            print("Executing file move operation")
        shutil.move(str(source_path), str(dest_path))
        if verbose:
            print("File moved successfully")

    if update_references:
        if verbose:
            print("Updating references to the moved file")

        # Find all .rst files that might reference this file
        root_dir = Path.cwd()  # Or use a smarter root detection
        if verbose:
            print(f"Searching for all RST files from root directory: {root_dir}")
        all_files = find_all_rst_files(str(root_dir))
        if verbose:
            print(f"Found {len(all_files)} RST files to check")

        # Find files that reference the moved file, using context if provided
        referencing_files = find_files_referencing(
            str(source_rel), all_files, context_path=context_path, verbose=verbose
        )

        if referencing_files:
            print(f"\nUpdating references in {len(referencing_files)} file(s):")

            for ref_file, ref_type in referencing_files:
                print(f"  - {ref_file} ({ref_type})")

                if not dry_run:
                    source_stem = source_path.stem
                    dest_stem = dest_path.stem

                    if verbose:
                        print(
                            f"Updating references from {source_stem} to"
                            f" {dest_stem} in {ref_file}"
                        )

                    # Update the references
                    updated = update_references_in_file(
                        ref_file, source_stem, dest_stem, verbose=verbose
                    )

                    if updated:
                        print(f"    ✓ Updated references in {ref_file}")
                    else:
                        print(f"    - No changes needed in {ref_file}")
        else:
            print("\nNo references to update.")


def execute(args):
    """Execute the mv command."""
    try:
        # Determine if we should update references (default: yes)
        update_refs = getattr(args, "no_update_refs", False)
        update_references = not update_refs

        # Get global options
        context_path = getattr(args, "context", None)
        dry_run = getattr(args, "dry_run", False)
        verbose = getattr(args, "verbose", False)

        if verbose:
            print("Starting sphinx-cmd mv operation")
            print(f"Source: {args.source}")
            print(f"Destination: {args.destination}")
            print(
                f"Options: dry-run={dry_run},"
                f" update-references={update_references},"
                f" context={context_path}"
            )

        # Perform the move
        move_rst_file(
            args.source,
            args.destination,
            update_references=update_references,
            dry_run=dry_run,
            context_path=context_path,
            verbose=verbose,
        )

        if not dry_run:
            print("\n✓ Move completed successfully!")
        else:
            print("\n[Dry run complete - no files were actually moved]")

        if verbose:
            print("Operation completed successfully")

    except Exception as e:
        print(f"Error: {e}")
        raise
