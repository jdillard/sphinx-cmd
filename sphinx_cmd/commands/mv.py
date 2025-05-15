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
    file_path: str, context_path: Optional[str] = None
) -> Dict[str, List[str]]:
    """Extract all file references from an .rst file."""
    references = defaultdict(list)

    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Find toctree entries
    toctree_matches = TOCTREE_PATTERN.findall(content)
    for toctree_content in toctree_matches:
        # Extract file references from toctree
        lines = toctree_content.split("\n")
        for line in lines:
            line = line.strip()
            if line and not line.startswith(":"):  # Skip options
                # Handle both relative and absolute paths
                ref_file = line.split()[0] if line.split() else ""
                if ref_file:
                    references["toctree"].append(ref_file)

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

    return dict(references)


def find_files_referencing(
    target_file: str, all_files: List[str], context_path: Optional[str] = None
) -> List[Tuple[str, str]]:
    """Find all files that reference the target file."""
    referencing_files = []
    target_path = Path(target_file)
    target_stem = target_path.stem  # filename without extension

    for file_path in all_files:
        if file_path == target_file:
            continue

        try:
            # Extract references using context from conf.py if provided
            references = extract_references(file_path, context_path=context_path)

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
                        break
        except Exception as e:
            print(f"Warning: Could not analyze {file_path}: {e}")

    return referencing_files


def update_references_in_file(file_path: str, old_ref: str, new_ref: str) -> bool:
    """Update references to the moved file in a single file."""
    old_path = Path(old_ref)
    new_path = Path(new_ref)
    old_stem = old_path.stem
    new_stem = new_path.stem

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        original_content = content

        # Update different types of references
        # 1. Toctree entries
        content = re.sub(
            rf"^\s*{re.escape(old_stem)}\s*$",
            f"   {new_stem}",
            content,
            flags=re.MULTILINE,
        )

        # 2. :doc: references
        content = re.sub(
            rf":doc:`{re.escape(old_stem)}`", f":doc:`{new_stem}`", content
        )

        # 3. Include directives
        for directive in ["include", "literalinclude"]:
            content = re.sub(
                rf"^\s*\.\.\s+{directive}::\s+{re.escape(old_ref)}",
                f".. {directive}:: {new_ref}",
                content,
                flags=re.MULTILINE,
            )

        # 4. Internal links
        content = re.sub(
            rf"`([^<>`]+)\s+<{re.escape(old_ref)}>`__?", rf"`\1 <{new_ref}>`_", content
        )

        # Write back if changes were made
        if content != original_content:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)
            return True

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
) -> None:
    """Move an RST file and optionally update all references to it."""
    source_path = Path(source).resolve()
    dest_path = Path(destination).resolve()

    if not source_path.exists():
        raise FileNotFoundError(f"Source file not found: {source}")

    if not source_path.suffix == ".rst":
        raise ValueError(f"Source must be an .rst file: {source}")

    # If destination is a directory, use the same filename
    if dest_path.is_dir():
        dest_path = dest_path / source_path.name
    elif not dest_path.suffix:
        dest_path = dest_path.with_suffix(".rst")

    # Get the relative paths for updating references
    # Try to find a common root to make relative paths
    try:
        source_rel = source_path.relative_to(Path.cwd())
        dest_rel = dest_path.relative_to(Path.cwd())
    except ValueError:
        # Fall back to absolute paths if no common root
        source_rel = source_path
        dest_rel = dest_path

    print(f"Moving: {source_rel} -> {dest_rel}")

    if not dry_run:
        # Create destination directory if it doesn't exist
        dest_path.parent.mkdir(parents=True, exist_ok=True)

        # Move the file
        shutil.move(str(source_path), str(dest_path))

    if update_references:
        # Find all .rst files that might reference this file
        root_dir = Path.cwd()  # Or use a smarter root detection
        all_files = find_all_rst_files(str(root_dir))

        # Find files that reference the moved file, using context if provided
        referencing_files = find_files_referencing(
            str(source_rel), all_files, context_path=context_path
        )

        if referencing_files:
            print(f"\nUpdating references in {len(referencing_files)} file(s):")

            for ref_file, ref_type in referencing_files:
                print(f"  - {ref_file} ({ref_type})")

                if not dry_run:
                    source_stem = source_path.stem
                    dest_stem = dest_path.stem

                    # Update the references
                    updated = update_references_in_file(
                        ref_file, source_stem, dest_stem
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

        # Perform the move
        move_rst_file(
            args.source,
            args.destination,
            update_references=update_references,
            dry_run=dry_run,
            context_path=context_path,
        )

        if not dry_run:
            print("\n✓ Move completed successfully!")
        else:
            print("\n[Dry run complete - no files were actually moved]")

    except Exception as e:
        print(f"Error: {e}")
        raise
