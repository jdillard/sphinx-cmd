import os
import tempfile
from unittest.mock import Mock

from sphinx_cmd.commands.rm import (
    build_asset_index,
    execute,
    extract_assets,
    find_rst_files,
)


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
        assets = extract_assets(rst_files[0])
        assert len(assets) == 2

        # Test building asset index
        asset_to_files, file_to_assets, asset_directive_map = build_asset_index(
            rst_files
        )
        assert len(asset_to_files) == 2
        assert len(file_to_assets) == 1

        # Test dry run with mock args
        args = Mock()
        args.path = test_dir
        args.dry_run = True
        execute(args)

        # Verify files still exist after dry run
        assert os.path.exists(os.path.join(test_dir, "test.rst"))
        assert os.path.exists(os.path.join(test_dir, "image.png"))
        assert os.path.exists(os.path.join(test_dir, "figure.jpg"))
