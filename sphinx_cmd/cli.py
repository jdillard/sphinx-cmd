#!/usr/bin/env python3
"""
Main CLI entry point for sphinx-cmd with subcommands.
"""

import argparse
import sys

from sphinx_cmd.commands import rm


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="sphinx-cmd",
        description="Command-line tools for Sphinx documentation management",
    )

    # Add version option
    parser.add_argument("--version", action="version", version="%(prog)s 0.1.0")

    # Create subparsers for subcommands
    subparsers = parser.add_subparsers(
        dest="command", help="Available commands", metavar="COMMAND"
    )

    # Add 'rm' subcommand
    rm_parser = subparsers.add_parser(
        "rm", help="Delete unused .rst files and their unique assets"
    )
    rm_parser.add_argument(
        "path", help="Path to a single .rst file or a directory of .rst files"
    )
    rm_parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Preview deletions without removing files",
    )
    rm_parser.set_defaults(func=rm.execute)

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command is provided, show help
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)

    # Execute the appropriate command
    try:
        args.func(args)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
