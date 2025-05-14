# Sphinx-CMD

A collection of command-line tools for managing Sphinx documentation.

## Installation

```bash
pip install sphinx-cmd
```

## Commands

The `sphinx-cmd` tool provides subcommands for different Sphinx documentation management tasks.

### `sphinx-cmd rm`

Delete unused .rst files and their unique assets if not used elsewhere.

```bash
# Remove files and assets
sphinx-cmd rm path/to/docs

# Dry run to preview deletions
sphinx-cmd rm path/to/docs --dry-run
```

## Development

```bash
# Clone the repository
git clone https://github.com/yourusername/sphinx-cmd.git
cd sphinx-cmd

# Install in development mode with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linters
black sphinx_cmd tests
flake8 sphinx_cmd tests
mypy sphinx_cmd

# Test the command
sphinx-cmd --help
sphinx-cmd rm --help
```

## Adding New Commands

The architecture is designed to make adding new commands easy:

1. Create a new file in `sphinx_cmd/commands/` (e.g., `new_command.py`)
2. Implement an `execute(args)` function in your new file
3. Import the command in `sphinx_cmd/cli.py`
4. Add a new subparser for your command in `create_parser()`

## License

MIT License - see LICENSE file for details.