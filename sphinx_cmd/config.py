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
DEFAULT_CONFIG = {
    "directives": ["image", "figure", "include"]
}


def get_config_path() -> Optional[Path]:
    """Get the path to the configuration file."""
    # Check for config in user's home directory
    home_config = Path.home() / ".sphinx-cmd.toml"
    if home_config.exists():
        return home_config

    return None


def load_config() -> Dict:
    """
    Load configuration from a TOML file.

    The function looks for a config file at:
    - user's home directory

    Returns:
        Dict: The merged configuration (defaults + user config)
    """
    config = DEFAULT_CONFIG.copy()

    config_path = get_config_path()
    if not config_path:
        return config

    try:
        with open(config_path, "rb") as f:
            user_config = tomllib.load(f)

        # Merge user directives with default directives
        if "directives" in user_config:
            if isinstance(user_config["directives"], list):
                # If user config has list of directive names, extend default list
                config["directives"].extend([
                    name for name in user_config["directives"]
                    if name not in config["directives"]
                ])
            elif isinstance(user_config["directives"], dict):
                # Handle legacy format for backward compatibility
                for name in user_config["directives"]:
                    if name not in config["directives"]:
                        config["directives"].append(name)

    except Exception as e:
        print(f"Warning: Error loading config from {config_path}: {e}")

    return config


def get_directive_patterns() -> Dict[str, re.Pattern]:
    """
    Get compiled regex patterns for all directives.

    Returns:
        Dict[str, re.Pattern]: Dictionary of directive names to compiled regex patterns
    """
    config = load_config()
    patterns = {}

    for name in config["directives"]:
        # Generate regex pattern from directive name
        pattern = fr"^\s*\.\.\s+{name}::\s+(.+)$"
        patterns[name] = re.compile(pattern, re.MULTILINE)

    return patterns
