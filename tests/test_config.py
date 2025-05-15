import tempfile
from pathlib import Path
from unittest.mock import patch

from sphinx_cmd.config import get_directive_patterns, load_config


def test_default_config():
    """Test that default config is returned when no config file exists."""
    with patch("sphinx_cmd.config.get_config_path", return_value=None):
        config = load_config()

        # Check that default directives are present
        assert "directives" in config
        assert "image" in config["directives"]
        assert "figure" in config["directives"]
        assert "include" in config["directives"]


def test_load_custom_config():
    """Test loading a custom configuration file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"

        # Create a custom config file with proper TOML syntax
        toml_content = """
[directives]
image = "^\\\\s*\\\\.\\\\.\\\\s+image::\\\\s+(.+)$"
figure = "^\\\\s*\\\\.\\\\.\\\\s+figure::\\\\s+(.+)$"
include = "^\\\\s*\\\\.\\\\.\\\\s+include::\\\\s+(.+)$"
drawio-figure = "^\\\\s*\\\\.\\\\.\\\\s+drawio-figure::\\\\s+(.+)$"
drawio-image = "^\\\\s*\\\\.\\\\.\\\\s+drawio-image::\\\\s+(.+)$"
"""
        with open(config_path, "wb") as f:
            f.write(toml_content.encode())

        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            config = load_config()

            # Check that custom directives are present
            assert "directives" in config
            assert "drawio-figure" in config["directives"]
            assert "drawio-image" in config["directives"]

            # Check original directives are still there
            assert "image" in config["directives"]
            assert "figure" in config["directives"]
            assert "include" in config["directives"]


def test_get_directive_patterns():
    """Test that directive patterns are compiled correctly."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"

        # Create a custom config file with drawio directives with proper TOML syntax
        toml_content = """
[directives]
drawio-figure = "^\\\\s*\\\\.\\\\.\\\\s+drawio-figure::\\\\s+(.+)$"
"""
        with open(config_path, "wb") as f:
            f.write(toml_content.encode())

        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            patterns = get_directive_patterns()

            # Default patterns should be included
            assert "image" in patterns
            assert "figure" in patterns
            assert "include" in patterns

            # Custom pattern should be included and be a compiled regex
            assert "drawio-figure" in patterns

            # Test the pattern works
            test_string = ".. drawio-figure:: path/to/diagram.drawio"
            match = patterns["drawio-figure"].findall(test_string)
            assert len(match) == 1
            assert match[0] == "path/to/diagram.drawio"
