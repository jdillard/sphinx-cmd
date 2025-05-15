#!/usr/bin/env python3
"""
Main CLI entry point for sphinx-cmd with subcommands.
"""

import argparse
import os
import sys

from sphinx_cmd import __version__


def create_parser():
    """Create the main argument parser with subcommands."""
    parser = argparse.ArgumentParser(
        prog="sphinx-cmd",
        description="Command-line tools for Sphinx documentation management",
    )

    # Add version option
    parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Add global options
    parser.add_argument(
        "--context",
        "-c",
        help="Path to Sphinx documentation context"
        "(will auto-detect nearest conf.py by default)",
    )
    parser.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="Preview operations without making any changes",
    )
    parser.add_argument(
        "--directives",
        type=lambda s: [x.strip() for x in s.split(",")],
        help="Additional directives to process as comma-separated list"
        " (e.g. 'drawio-figure,drawio-image')",
    )

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
    rm_parser.set_defaults(command_name="rm")

    # Add 'mv' subcommand
    mv_parser = subparsers.add_parser(
        "mv", help="Move/rename .rst files and update references"
    )
    mv_parser.add_argument("source", help="Source file to move")
    mv_parser.add_argument("destination", help="Destination file or directory")
    mv_parser.add_argument(
        "--no-update-refs",
        action="store_true",
        help="Do not update references to the moved file",
    )
    mv_parser.set_defaults(command_name="mv")

    return parser


def main():
    """Main entry point for the CLI."""
    parser = create_parser()
    args = parser.parse_args()

    # If no command is provided, show help
    if not hasattr(args, "command_name"):
        parser.print_help()
        sys.exit(1)

    # If context path is provided, check that it exists
    if args.context and not os.path.exists(args.context):
        print(f"Error: Context path does not exist: {args.context}", file=sys.stderr)
        sys.exit(1)

    # Import and execute the appropriate command
    try:
        if args.command_name == "rm":
            from sphinx_cmd.commands.rm import execute

            execute(args)
        elif args.command_name == "mv":
            from sphinx_cmd.commands.mv import execute

            execute(args)
        else:
            print(f"Unknown command: {args.command_name}", file=sys.stderr)
            sys.exit(1)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
