import sys
from unittest.mock import patch

import pytest

from sphinx_cmd.cli import create_parser, main


def test_cli_help():
    """Test that the main CLI shows help information."""
    parser = create_parser()
    # This should not raise an exception
    assert parser is not None
    assert "sphinx-cmd" in parser.format_help()
    assert "rm" in parser.format_help()
    assert "mv" in parser.format_help()
    # Check that global arguments are present
    assert "--context" in parser.format_help()
    assert "-c" in parser.format_help()
    assert "--dry-run" in parser.format_help()
    assert "-n" in parser.format_help()
    assert "--directives" in parser.format_help()


def test_cli_no_command():
    """Test CLI behavior when no command is provided."""
    # Mock argv to simulate running with no arguments
    with patch.object(sys, "argv", ["sphinx-cmd"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        assert excinfo.value.code == 1


def test_cli_rm_help():
    """Test that rm subcommand help works."""
    with patch.object(sys, "argv", ["sphinx-cmd", "rm", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        # Help should exit with code 0
        assert excinfo.value.code == 0


def test_cli_mv_help():
    """Test that mv subcommand help works."""
    with patch.object(sys, "argv", ["sphinx-cmd", "mv", "--help"]):
        with pytest.raises(SystemExit) as excinfo:
            main()
        # Help should exit with code 0
        assert excinfo.value.code == 0


def test_cli_invalid_context():
    """Test CLI behavior when an invalid context path is provided."""
    with patch.object(
        sys,
        "argv",
        ["sphinx-cmd", "--context", "/nonexistent/path", "rm", "some_file.rst"],
    ):
        with patch.object(sys, "exit") as mock_exit:
            main()
            mock_exit.assert_called_once_with(1)
