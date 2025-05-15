import os
import tempfile
from pathlib import Path
from unittest.mock import Mock

from sphinx_cmd.commands.mv import (
    extract_references,
    find_all_rst_files,
    find_files_referencing,
    update_references_in_file,
)


def test_find_rst_files():
    """Test finding RST files in a directory tree."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        (Path(tmpdir) / "test1.rst").touch()
        (Path(tmpdir) / "test2.txt").touch()  # Not RST
        subdir = Path(tmpdir) / "subdir"
        subdir.mkdir()
        (subdir / "test3.rst").touch()

        files = find_all_rst_files(tmpdir)
        rst_files = [Path(f).name for f in files]

        assert "test1.rst" in rst_files
        assert "test3.rst" in rst_files
        assert "test2.txt" not in str(files)


def test_extract_references():
    """Test extracting references from RST content."""
    with tempfile.TemporaryDirectory() as tmpdir:
        rst_file = Path(tmpdir) / "test.rst"
        content = """
Test Document
=============

.. toctree::
   :maxdepth: 2

   intro
   tutorial/basic
   api

See :doc:`intro` for more information.

.. include:: snippets/example.rst

.. literalinclude:: code/example.py
"""
        rst_file.write_text(content)

        refs = extract_references(str(rst_file))

        assert "toctree" in refs
        assert "intro" in refs["toctree"]
        assert "tutorial/basic" in refs["toctree"]

        assert "reference" in refs
        assert "intro" in refs["reference"]

        assert "include" in refs
        assert "snippets/example.rst" in refs["include"]


def test_find_files_referencing():
    """Test finding files that reference a target file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create target file
        target = Path(tmpdir) / "target.rst"
        target.write_text("Target content")

        # Create referencing file
        ref_file = Path(tmpdir) / "referencing.rst"
        ref_content = """
.. toctree::

   target

See :doc:`target` for details.
"""
        ref_file.write_text(ref_content)

        # Create non-referencing file
        other_file = Path(tmpdir) / "other.rst"
        other_file.write_text("Other content")

        all_files = [str(target), str(ref_file), str(other_file)]
        refs = find_files_referencing(str(target), all_files)

        # The function finds multiple types of references in the same file
        # We expect 2 references: one from toctree and one from :doc:
        assert len(refs) == 2
        assert all(r[0] == str(ref_file) for r in refs)

        # Check that we found both types of references
        ref_types = {r[1] for r in refs}
        assert "toctree" in ref_types
        assert "reference" in ref_types


def test_update_references():
    """Test updating references in a file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = Path(tmpdir) / "test.rst"
        content = """
.. toctree::

   oldname

See :doc:`oldname` for details.
"""
        test_file.write_text(content)

        updated = update_references_in_file(str(test_file), "oldname", "newname")

        assert updated
        new_content = test_file.read_text()
        assert "newname" in new_content
        assert "oldname" not in new_content


def test_move_command_dry_run():
    """Test mv command in dry run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.chdir(tmpdir)

        # Create source file
        source = Path("source.rst")
        source.write_text("Source content")

        # Create file that references it
        ref_file = Path("index.rst")
        ref_file.write_text(
            """
.. toctree::

   source
"""
        )

        # Mock args
        args = Mock()
        args.source = "source.rst"
        args.destination = "destination.rst"
        args.dry_run = True  # Global option, but still accessed in command
        args.no_update_refs = False
        args.directives = None  # Mock the global directives option
        args.context = None  # Mock the global context option

        # Run the move command
        from sphinx_cmd.commands.mv import execute

        execute(args)

        # Verify source still exists (dry run)
        assert source.exists()
        assert not Path("destination.rst").exists()
