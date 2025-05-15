import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from sphinx_cmd.commands.rm import (
    build_asset_index,
    execute,
    extract_assets,
    find_rst_files,
    get_transitive_includes,
    remove_empty_dirs,
)


def test_nested_includes_extraction():
    """Test that nested includes are properly extracted."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a more complex nested include structure
        main_file = os.path.join(tmpdir, "main.rst")
        include1 = os.path.join(tmpdir, "include1.rst")
        include2 = os.path.join(tmpdir, "include2.rst")

        # Create the files with content
        with open(include2, "w") as f:
            f.write("Level 2 include\n")

        with open(include1, "w") as f:
            f.write("Level 1 include\n.. include:: include2.rst\n")

        with open(main_file, "w") as f:
            f.write("Main file\n.. include:: include1.rst\n")

        # Mock os.getcwd and Path.cwd to return the temp directory
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    # Test the transitive includes function
                    includes = get_transitive_includes(main_file)

        # Should have found both include files
        assert len(includes) == 2
        assert include1 in includes
        assert include2 in includes


def test_rm_command_functionality():
    """Test the rm command functionality."""
    # Create a temporary directory structure
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        test_dir = os.path.join(tmpdir, "docs")
        os.makedirs(test_dir)

        # Create an RST file
        rst_content = """
Test Page
=========

.. image:: image.png
.. figure:: figure.jpg
"""
        with open(os.path.join(test_dir, "test.rst"), "w") as f:
            f.write(rst_content)

        # Create referenced asset files
        with open(os.path.join(test_dir, "image.png"), "w") as f:
            f.write("fake image")
        with open(os.path.join(test_dir, "figure.jpg"), "w") as f:
            f.write("fake figure")

        # Test finding RST files
        rst_files = find_rst_files(test_dir)
        assert len(rst_files) == 1
        assert "test.rst" in rst_files[0]

        # Test extracting assets
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    assets = extract_assets(rst_files[0])
        assert len(assets) == 2

        # Test building asset index
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    asset_to_files, file_to_assets, asset_directive_map = (
                        build_asset_index(rst_files)
                    )
        assert len(asset_to_files) == 2
        assert len(file_to_assets) == 1

        # Test dry run with mock args
        args = Mock()
        args.path = test_dir
        args.dry_run = True  # Global option, but still accessed in command
        args.directives = None  # Global option, but still accessed in command
        args.context = None  # Global option, accessed the same way

        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    execute(args)

        # Verify files still exist after dry run
        assert os.path.exists(os.path.join(test_dir, "test.rst"))
        assert os.path.exists(os.path.join(test_dir, "image.png"))
        assert os.path.exists(os.path.join(test_dir, "figure.jpg"))


def test_empty_directory_removal():
    """Test that empty directories are properly removed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a nested directory structure
        docs_dir = os.path.join(tmpdir, "docs")
        nested_dir = os.path.join(docs_dir, "nested")
        nested_subdir = os.path.join(nested_dir, "subdir")
        os.makedirs(nested_subdir)

        # Create an RST file in the nested subdirectory
        rst_path = os.path.join(nested_subdir, "test.rst")
        rst_content = """Test page
=========

.. image:: image.png
"""
        with open(rst_path, "w") as f:
            f.write(rst_content)

        # Create an image in the same directory
        img_path = os.path.join(nested_subdir, "image.png")
        with open(img_path, "w") as f:
            f.write("fake image")

        # Verify that directories exist before the test
        assert os.path.exists(docs_dir)
        assert os.path.exists(nested_dir)
        assert os.path.exists(nested_subdir)
        assert os.path.exists(rst_path)
        assert os.path.exists(img_path)

        # Execute the rm command
        args = Mock()
        args.path = docs_dir
        args.dry_run = False
        args.directives = None
        args.context = None

        # Execute the command to remove files
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    execute(args)

        # Verify that the files were removed
        assert not os.path.exists(rst_path)
        assert not os.path.exists(img_path)

        # Verify that all directories were removed
        assert not os.path.exists(nested_subdir)
        assert not os.path.exists(nested_dir)
        assert not os.path.exists(docs_dir)


def test_non_empty_directory_retained():
    """Test that non-empty directories are not removed."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a nested directory structure
        docs_dir = os.path.join(tmpdir, "docs")
        nested_dir = os.path.join(docs_dir, "nested")
        nested_subdir = os.path.join(nested_dir, "subdir")
        os.makedirs(nested_subdir)

        # Create an RST file in the nested subdirectory
        rst_path = os.path.join(nested_subdir, "test.rst")
        with open(rst_path, "w") as f:
            f.write("Test page\n=========\n\n.. image:: image.png")

        # Create an image in the same directory
        img_path = os.path.join(nested_subdir, "image.png")
        with open(img_path, "w") as f:
            f.write("fake image")

        # Create another file in the parent directory that should be retained
        other_file = os.path.join(nested_dir, "other.txt")
        with open(other_file, "w") as f:
            f.write("This file should be retained")

        # Execute the rm command
        args = Mock()
        args.path = docs_dir
        args.dry_run = False
        args.directives = None
        args.context = None

        # Execute the command to remove files
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    execute(args)

        # Verify that subdir was removed but nested_dir was retained
        assert not os.path.exists(nested_subdir)
        assert os.path.exists(nested_dir)
        assert os.path.exists(docs_dir)
        assert os.path.exists(other_file)


def test_extract_assets_basic():
    """Test that extract_assets finds assets in a simple file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test file with multiple directives
        test_file = os.path.join(tmpdir, "test.rst")

        with open(test_file, "w") as f:
            f.write(
                """
Test Document
============

.. image:: img.png
.. figure:: fig.jpg
.. include:: inc.rst
"""
            )

        # Extract assets
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    assets = extract_assets(test_file)

        # Check we have the right number of assets
        assert len(assets) == 3

        # Check all asset paths are correct
        img_path = os.path.join(tmpdir, "img.png")
        fig_path = os.path.join(tmpdir, "fig.jpg")
        inc_path = os.path.join(tmpdir, "inc.rst")

        assert img_path in assets
        assert fig_path in assets
        assert inc_path in assets


def test_get_transitive_includes():
    """Test that get_transitive_includes correctly finds all included files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a multi-level include structure
        main_file = os.path.join(tmpdir, "main.rst")
        first_include = os.path.join(tmpdir, "first.rst")
        second_include = os.path.join(tmpdir, "second.rst")

        # Create the files
        with open(second_include, "w") as f:
            f.write("Content in second include\n")

        with open(first_include, "w") as f:
            f.write(".. include:: second.rst\n")

        with open(main_file, "w") as f:
            f.write(".. include:: first.rst\n")

        # Get all transitive includes from main file
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    includes = get_transitive_includes(main_file)

        # Should find both included files
        assert len(includes) == 2
        assert first_include in includes
        assert second_include in includes


def test_circular_includes_detection():
    """Test that circular includes are detected and don't cause infinite recursion."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create two files that include each other
        file1 = os.path.join(tmpdir, "file1.rst")
        file2 = os.path.join(tmpdir, "file2.rst")

        with open(file1, "w") as f:
            f.write("File 1\n\n.. include:: file2.rst\n")

        with open(file2, "w") as f:
            f.write("File 2\n\n.. include:: file1.rst\n")

        # Should find both includes but avoid infinite recursion
        with patch("os.getcwd", return_value=tmpdir):
            with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                with patch("sphinx_cmd.config.get_config_path", return_value=None):
                    includes = get_transitive_includes(file1)
        assert len(includes) == 2  # Changed from 1 to 2
        assert file2 in includes
        assert file1 in includes  # file1 is included by file2


def test_remove_empty_dirs_function():
    """Test the remove_empty_dirs function directly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a nested directory structure
        parent_dir = os.path.join(tmpdir, "parent")
        child_dir = os.path.join(parent_dir, "child")
        grandchild_dir = os.path.join(child_dir, "grandchild")
        os.makedirs(grandchild_dir)

        # Create a separate directory that should not be removed
        other_dir = os.path.join(parent_dir, "other")
        os.makedirs(other_dir)
        with open(os.path.join(other_dir, "file.txt"), "w") as f:
            f.write("Keep this directory")

        # Test dry run
        affected_dirs = {child_dir, grandchild_dir}
        deleted_dirs = remove_empty_dirs(affected_dirs, parent_dir, dry_run=True)

        # Verify nothing was deleted in dry run
        assert os.path.exists(grandchild_dir)
        assert os.path.exists(child_dir)
        assert os.path.exists(parent_dir)
        assert len(deleted_dirs) == 0

        # Test actual removal
        deleted_dirs = remove_empty_dirs(affected_dirs, parent_dir, dry_run=False)

        # Verify directories were removed
        assert not os.path.exists(grandchild_dir)
        assert not os.path.exists(child_dir)
        assert os.path.exists(parent_dir)  # Parent has 'other' dir so is not empty
        assert os.path.exists(other_dir)

        # Should have removed exactly 2 dirs
        assert len(deleted_dirs) == 2
        assert grandchild_dir in deleted_dirs
        assert child_dir in deleted_dirs

        # Now test removal of the original path when empty
        # First remove the file in other_dir
        os.remove(os.path.join(other_dir, "file.txt"))

        # Then remove the now-empty other_dir
        affected_dirs = {other_dir}
        deleted_dirs = remove_empty_dirs(affected_dirs, parent_dir, dry_run=False)

        # Now parent_dir should also be removed since it's empty
        assert not os.path.exists(other_dir)
        assert not os.path.exists(parent_dir)
        assert len(deleted_dirs) == 2
        assert other_dir in deleted_dirs
        assert parent_dir in deleted_dirs


def test_context_path_protection():
    """Test that files outside the context path are identified in dry-run mode."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a docs directory that will serve as our context
        docs_dir = os.path.join(tmpdir, "docs")
        os.makedirs(docs_dir)

        # Create another directory outside the context
        outside_dir = os.path.join(tmpdir, "outside")
        os.makedirs(outside_dir)

        # Create a conf.py file in the docs directory to mark it as a Sphinx context
        with open(os.path.join(docs_dir, "conf.py"), "w") as f:
            f.write("# Sphinx configuration file")

        # Create an RST file in the docs directory that references a file outside
        # the context
        rst_content = """
Test Page
=========

.. image:: ../outside/image.png
"""
        rst_file = os.path.join(docs_dir, "test.rst")
        with open(rst_file, "w") as f:
            f.write(rst_content)

        # Create the referenced asset in the outside directory
        outside_img = os.path.join(outside_dir, "image.png")
        with open(outside_img, "w") as f:
            f.write("fake image")

        # Execute the rm command with context_path set to docs_dir (DRY RUN ONLY)
        args = Mock()
        args.path = docs_dir
        args.dry_run = True  # Only use dry run mode
        args.directives = None
        args.context = docs_dir

        # Capture stdout to verify the messages
        import sys
        from io import StringIO

        captured_output = StringIO()
        original_stdout = sys.stdout
        sys.stdout = captured_output

        try:
            # Execute in dry run mode
            with patch("os.getcwd", return_value=tmpdir):
                with patch("pathlib.Path.cwd", return_value=Path(tmpdir)):
                    with patch("sphinx_cmd.config.get_config_path", return_value=None):
                        execute(args)

            # Get the captured output
            output = captured_output.getvalue()

            # Verify that it shows the outside file would be skipped
            assert "Skipping" in output
            assert "outside context" in output
            assert outside_img in output

            # Verify the RST file would be deleted (not skipped)
            assert "Would delete page:" in output
            assert rst_file in output

            # Verify both files still exist after dry run
            assert os.path.exists(rst_file)
            assert os.path.exists(outside_img)

        finally:
            sys.stdout = original_stdout
