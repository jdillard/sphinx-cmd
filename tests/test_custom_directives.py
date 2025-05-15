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

        # Create config with proper TOML syntax
        toml_content = """
directives = ["drawio-figure", "drawio-image"]
"""
        with open(config_path, "wb") as f:
            f.write(toml_content.encode())

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
    """Test the rm command with custom directives (using dry-run)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a test config with custom directives
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"

        # Create config with proper TOML syntax
        toml_content = """
directives = ["drawio-figure"]
"""
        with open(config_path, "wb") as f:
            f.write(toml_content.encode())

        # Create test directory
        test_dir = os.path.join(tmpdir, "docs")
        os.makedirs(test_dir)

        # Create an RST file with custom directives
        rst_content = """
Test Page
=========

.. drawio-figure:: custom.drawio
"""
        with open(os.path.join(test_dir, "test.rst"), "w") as f:
            f.write(rst_content)

        # Create the asset files
        with open(os.path.join(test_dir, "custom.drawio"), "w") as f:
            f.write("fake drawio")

        # Execute the rm command with mocked config
        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            # Setup to capture stdout
            import sys
            from io import StringIO

            captured_output = StringIO()
            original_stdout = sys.stdout
            sys.stdout = captured_output

            try:
                args = Mock()
                args.path = test_dir
                args.dry_run = True
                args.directives = None
                args.context = None

                # Run with dry-run to test detection
                execute(args)

                # Get the captured output
                output = captured_output.getvalue()

                # Verify the correct files would be deleted
                assert "[dry-run] Would delete drawio-figure:" in output
                assert "custom.drawio" in output
                assert "[dry-run] Would delete page:" in output
                assert "test.rst" in output
            finally:
                sys.stdout = original_stdout

            # Files should still exist after dry run
            assert os.path.exists(os.path.join(test_dir, "test.rst"))
            assert os.path.exists(os.path.join(test_dir, "custom.drawio"))
            assert os.path.exists(test_dir)
