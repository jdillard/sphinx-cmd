#!/usr/bin/env python3
"""
Configuration handling for sphinx-cmd.
"""

import re
import sys
from pathlib import Path
from typing import Any, Dict, Optional, Union

# Use the standard library tomllib if Python 3.11+, otherwise use tomli package
if sys.version_info >= (3, 11):
    import tomllib
else:
    import tomli as tomllib

# Default configuration with built-in directives
DEFAULT_CONFIG = {"directives": ["image", "figure", "include"]}


def get_config_path() -> Optional[Path]:
    """Get the path to the configuration file."""
    # Check for config in user's home directory
    home_config = Path.home() / ".sphinx-cmd.toml"
    if home_config.exists():
        return home_config

    return None


def find_sphinx_conf(start_path: Optional[Union[str, Path]] = None) -> Optional[Path]:
    """
    Find the nearest conf.py file by traversing up from the starting path.

    Args:
        start_path: The path to start searching from. Defaults to current directory.

    Returns:
        Path to conf.py if found, None otherwise.
    """
    if start_path is None:
        start_path = Path.cwd()
    else:
        start_path = Path(start_path)

    # Make sure we have an absolute path
    start_path = start_path.resolve()

    # If start_path is a file, use its parent directory
    if start_path.is_file():
        start_path = start_path.parent

    # Traverse up the directory tree
    current_dir = start_path
    while current_dir != current_dir.parent:  # Stop at root
        conf_path = current_dir / "conf.py"
        if conf_path.exists():
            return conf_path
        current_dir = current_dir.parent

    return None


def load_config(cli_directives=None, context_path=None) -> Dict[str, Any]:
    """
    Load configuration from a TOML file and merge with CLI directives.

    The function looks for a config file at:
    - user's home directory

    Args:
        cli_directives: Optional list of directive names passed from the command line
        context_path: Optional path to use as context for finding conf.py

    Returns:
        Dict: The merged configuration (defaults + user config + CLI directives)
    """
    config = DEFAULT_CONFIG.copy()

    # Add docs context information
    config["sphinx_context"] = []

    # Try to find Sphinx conf.py if context_path is provided or automatically
    if context_path:
        sphinx_conf = find_sphinx_conf(context_path)
        if sphinx_conf:
            config["sphinx_context"] = [str(sphinx_conf.parent)]
    else:
        # Auto-detect from current directory
        sphinx_conf = find_sphinx_conf()
        if sphinx_conf:
            config["sphinx_context"] = [str(sphinx_conf.parent)]

    config_path = get_config_path()
    if config_path:
        try:
            with open(config_path, "rb") as f:
                user_config = tomllib.load(f)

            # Merge user directives with default directives
            if "directives" in user_config:
                # If user config has list of directive names, extend default list
                config["directives"].extend(
                    [
                        name
                        for name in user_config["directives"]
                        if name not in config["directives"]
                    ]
                )

        except Exception as e:
            print(f"Warning: Error loading config from {config_path}: {e}")

    # Add CLI directives if provided
    if cli_directives:
        config["directives"].extend(
            [name for name in cli_directives if name not in config["directives"]]
        )

    return config


def get_directive_patterns(
    cli_directives=None, context_path=None
) -> Dict[str, re.Pattern]:
    """
    Get compiled regex patterns for all directives.

    Args:
        cli_directives: Optional list of directive names passed from the command line
        context_path: Optional path to use as context for finding conf.py

    Returns:
        Dict[str, re.Pattern]: Dictionary of directive names to compiled regex patterns
    """
    config = load_config(cli_directives, context_path)
    patterns = {}

    for name in config["directives"]:
        # Generate regex pattern from directive name
        pattern = rf"^\s*\.\.\s+{name}::\s+(.+)$"
        patterns[name] = re.compile(pattern, re.MULTILINE)

    return patterns


def get_sphinx_context(cli_context: Optional[str] = None) -> Optional[Path]:
    """
    Get the Sphinx documentation context directory.

    Args:
        cli_context: Optional path provided via command line

    Returns:
        Path to the Sphinx docs directory (containing conf.py) if found, None otherwise
    """
    config = load_config(context_path=cli_context)
    sphinx_context = config.get("sphinx_context")
    if sphinx_context and len(sphinx_context) > 0:
        return Path(sphinx_context[0])
    return None
