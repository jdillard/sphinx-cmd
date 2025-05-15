import tempfile
from pathlib import Path
from unittest.mock import patch

from sphinx_cmd.config import find_sphinx_conf, get_directive_patterns, load_config


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
directives = ["image", "figure", "include", "drawio-figure", "drawio-image"]
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
directives = ["drawio-figure"]
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


def test_cli_directives():
    """Test that CLI directives are properly merged with config directives."""
    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / ".sphinx-cmd.toml"

        # Create a custom config file with some directives
        toml_content = """
directives = ["drawio-figure"]
"""
        with open(config_path, "wb") as f:
            f.write(toml_content.encode())

        with patch("sphinx_cmd.config.get_config_path", return_value=config_path):
            # Add CLI directives
            cli_directives = ["drawio-image", "custom-directive"]
            patterns = get_directive_patterns(cli_directives)

            # Default patterns should be included
            assert "image" in patterns
            assert "figure" in patterns
            assert "include" in patterns

            # Config file directives should be included
            assert "drawio-figure" in patterns

            # CLI directives should be included
            assert "drawio-image" in patterns
            assert "custom-directive" in patterns

            # Test a CLI directive pattern works
            test_string = ".. custom-directive:: path/to/custom.file"
            match = patterns["custom-directive"].findall(test_string)
            assert len(match) == 1
            assert match[0] == "path/to/custom.file"


def test_find_sphinx_conf():
    """Test finding the nearest conf.py file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a deep directory structure with conf.py at different levels
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()

        # Create a conf.py file in the docs directory
        docs_conf = docs_dir / "conf.py"
        docs_conf.touch()

        # Create subdirectories
        subdir = docs_dir / "subdir"
        subdir.mkdir()
        subsubdir = subdir / "subsubdir"
        subsubdir.mkdir()

        # Test finding conf.py from docs directory
        found_conf = find_sphinx_conf(docs_dir)
        assert found_conf == docs_conf

        # Test finding conf.py from subdirectory
        found_conf = find_sphinx_conf(subdir)
        assert found_conf == docs_conf

        # Test finding conf.py from sub-subdirectory
        found_conf = find_sphinx_conf(subsubdir)
        assert found_conf == docs_conf

        # Test finding conf.py from a file in the directory
        test_file = subsubdir / "test.rst"
        test_file.touch()
        found_conf = find_sphinx_conf(test_file)
        assert found_conf == docs_conf

        # Test when no conf.py is found
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()
        found_conf = find_sphinx_conf(outside_dir)
        assert found_conf is None


def test_context_in_config():
    """Test that sphinx_context is properly added to config."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        # Create a docs directory with conf.py
        docs_dir = tmp_path / "docs"
        docs_dir.mkdir()
        conf_path = docs_dir / "conf.py"
        conf_path.touch()

        # Test that context is added when path is provided
        with patch("sphinx_cmd.config.get_config_path", return_value=None):
            config = load_config(context_path=str(docs_dir))
            assert "sphinx_context" in config
            assert config["sphinx_context"] == [str(docs_dir)]

        # Test auto-detection when no context_path is provided
        subdir = docs_dir / "subdir"
        subdir.mkdir()

        with patch("sphinx_cmd.config.get_config_path", return_value=None):
            with patch("sphinx_cmd.config.Path.cwd", return_value=subdir):
                config = load_config()
                assert "sphinx_context" in config
                assert config["sphinx_context"] == [str(docs_dir)]

        # Test when no conf.py is found
        outside_dir = tmp_path / "outside"
        outside_dir.mkdir()

        with patch("sphinx_cmd.config.get_config_path", return_value=None):
            with patch("sphinx_cmd.config.Path.cwd", return_value=outside_dir):
                config = load_config()
                assert "sphinx_context" in config
                assert config["sphinx_context"] == []
