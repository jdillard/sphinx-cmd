import os
import subprocess
import tempfile


def test_integration_rm_command():
    """Integration test for the rm command through the CLI."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create test files
        rst_content = """
Test Page
=========

.. image:: test.png
"""
        with open(os.path.join(tmpdir, "test.rst"), "w") as f:
            f.write(rst_content)

        with open(os.path.join(tmpdir, "test.png"), "w") as f:
            f.write("fake image")

        # Run the command with dry-run (now using global --dry-run option)
        result = subprocess.run(
            ["sphinx-cmd", "--dry-run", "rm", tmpdir], capture_output=True, text=True
        )

        # Check that it executed successfully
        assert result.returncode == 0
        assert "[dry-run]" in result.stdout

        # Verify files still exist after dry run
        assert os.path.exists(os.path.join(tmpdir, "test.rst"))
        assert os.path.exists(os.path.join(tmpdir, "test.png"))


def test_integration_help_commands():
    """Test that all help commands work."""
    commands = [
        ["sphinx-cmd", "--help"],
        ["sphinx-cmd", "rm", "--help"],
        ["sphinx-cmd", "mv", "--help"],
        ["sphinx-cmd", "--version"],
    ]

    for cmd in commands:
        result = subprocess.run(cmd, capture_output=True, text=True)
        # Help commands should exit with 0 or 1 (argparse help exits with 0)
        assert result.returncode in [0, 1]
