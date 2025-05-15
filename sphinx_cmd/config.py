#!/usr/bin/env python3
"""
Configuration handling for sphinx-cmd.
"""

import re
import sys
from pathlib import Path
from typing import Dict, Optional

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


def load_config(cli_directives=None) -> Dict:
    """
    Load configuration from a TOML file and merge with CLI directives.

    The function looks for a config file at:
    - user's home directory

    Args:
        cli_directives: Optional list of directive names passed from the command line

    Returns:
        Dict: The merged configuration (defaults + user config + CLI directives)
    """
    config = DEFAULT_CONFIG.copy()

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


def get_directive_patterns(cli_directives=None) -> Dict[str, re.Pattern]:
    """
    Get compiled regex patterns for all directives.

    Args:
        cli_directives: Optional list of directive names passed from the command line

    Returns:
        Dict[str, re.Pattern]: Dictionary of directive names to compiled regex patterns
    """
    config = load_config(cli_directives)
    patterns = {}

    for name in config["directives"]:
        # Generate regex pattern from directive name
        pattern = rf"^\s*\.\.\s+{name}::\s+(.+)$"
        patterns[name] = re.compile(pattern, re.MULTILINE)

    return patterns
