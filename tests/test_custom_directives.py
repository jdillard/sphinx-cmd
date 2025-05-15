import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from sphinx_cmd.commands.rm import execute, extract_assets


def test_custom_directive_extraction():
    """Test that custom directives are extracted from RST files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config with custom directives
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"
        with open(config_path, "wb") as f:
            f.write(
                b"""
[directives]
drawio-figure = "^\\s*\\.\\.\\s+drawio-figure::\\s+(.+)$"
drawio-image = "^\\s*\\.\\.\\s+drawio-image::\\s+(.+)$"
"""
            )

        # Create a test file with custom directives
        test_file = os.path.join(tmpdir, "test.rst")
        with open(test_file, "w") as f:
            f.write(
                """
Test Document
============

.. image:: standard-image.png
.. drawio-figure:: custom-figure.drawio
.. drawio-image:: custom-image.drawio
            """
            )

        # Mock the config path function to use our temp config
        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            # Extract assets
            assets = extract_assets(test_file)

            # Check we have the right number of assets (3)
            assert len(assets) == 3

            # Check all asset paths are correct
            img_path = os.path.join(tmpdir, "standard-image.png")
            custom_figure_path = os.path.join(tmpdir, "custom-figure.drawio")
            custom_image_path = os.path.join(tmpdir, "custom-image.drawio")

            assert img_path in assets
            assert custom_figure_path in assets
            assert custom_image_path in assets

            # Check the directive types are correct
            assert assets[img_path] == "image"
            assert assets[custom_figure_path] == "drawio-figure"
            assert assets[custom_image_path] == "drawio-image"


def test_rm_command_with_custom_directives():
    """Test the rm command with custom directives."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config with custom directives
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"
        with open(config_path, "wb") as f:
            f.write(
                b"""
[directives]
drawio-figure = "^\\s*\\.\\.\\s+drawio-figure::\\s+(.+)$"
"""
            )

        # Create test directory
        test_dir = os.path.join(tmpdir, "docs")
        os.makedirs(test_dir)

        # Create an RST file with standard and custom directives
        rst_content = """
Test Page
=========

.. image:: standard.png
.. figure:: standard.jpg
.. drawio-figure:: custom.drawio
"""
        with open(os.path.join(test_dir, "test.rst"), "w") as f:
            f.write(rst_content)

        # Create the asset files
        with open(os.path.join(test_dir, "standard.png"), "w") as f:
            f.write("fake image")
        with open(os.path.join(test_dir, "standard.jpg"), "w") as f:
            f.write("fake figure")
        with open(os.path.join(test_dir, "custom.drawio"), "w") as f:
            f.write("fake drawio")

        # Execute the rm command with mocked config
        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            args = Mock()
            args.path = test_dir
            args.dry_run = True

            # First run as dry-run to test detection
            execute(args)

            # Files should still exist
            assert os.path.exists(os.path.join(test_dir, "test.rst"))
            assert os.path.exists(os.path.join(test_dir, "standard.png"))
            assert os.path.exists(os.path.join(test_dir, "standard.jpg"))
            assert os.path.exists(os.path.join(test_dir, "custom.drawio"))

            # Now actually delete the files
            args.dry_run = False
            execute(args)

            # All files should be gone
            assert not os.path.exists(os.path.join(test_dir, "test.rst"))
            assert not os.path.exists(os.path.join(test_dir, "standard.png"))
            assert not os.path.exists(os.path.join(test_dir, "standard.jpg"))
            assert not os.path.exists(os.path.join(test_dir, "custom.drawio"))

            # Directory should be removed too
            assert not os.path.exists(test_dir)
