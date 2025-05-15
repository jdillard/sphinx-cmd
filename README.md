# Sphinx-CMD

A collection of command-line tools for managing Sphinx documentation.

## Installation

```bash
pip install sphinx-cmd
```

## Commands

The `sphinx-cmd` tool provides subcommands for different Sphinx documentation management tasks.

### `sphinx-cmd rm`

Delete unused .rst files and their unique assets (images, includes, etc) if not used elsewhere.

```bash
# Remove files and assets
sphinx-cmd rm path/to/docs

# Dry run to preview deletions
sphinx-cmd rm path/to/docs --dry-run

# Process additional directives beyond defaults
sphinx-cmd rm path/to/docs --directives drawio-figure,drawio-image
```

#### Features

- Configure custom directives to be processed

### `sphinx-cmd mv`

Move/rename .rst files and automatically update all references to them.

```bash
# Move and update all references
sphinx-cmd mv old-file.rst new-file.rst

# Move to a different directory
sphinx-cmd mv chapter1.rst topics/chapter1.rst

# Preview the move without making changes
sphinx-cmd mv old-file.rst new-file.rst --dry-run

# Move without updating references
sphinx-cmd mv old-file.rst new-file.rst --no-update-refs

# Process additional directives beyond defaults
sphinx-cmd mv old-file.rst new-file.rst --directives drawio-figure,drawio-image
```

#### Features

- Automatically updates `toctree` entries
- Updates `:doc:` references
- Updates `include` and `literalinclude` directives
- Handles relative paths correctly
- Preserves file relationships
- Configure custom directives to be processed

## Configuration

You can add custom directives to be processed in two ways:

### 1. Command Line

Use the `--directives` option with any command to add custom directives for a single run:

```bash
sphinx-cmd rm path/to/docs --directives drawio-figure,drawio-image
```

### 2. Configuration File

Create a `.sphinx-cmd.toml` file in your home directory with your custom directives:

```toml
directives = [
  "drawio-figure",
  "drawio-image"
]
```

Command line directives will be combined with those in the configuration file and the built-in defaults.


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
sphinx-cmd mv --help
```

## Adding New Commands

The architecture is designed to make adding new commands easy:

1. Create a new file in `sphinx_cmd/commands/` (e.g., `new_command.py`)
2. Implement an `execute(args)` function in your new file
3. Import the command in `sphinx_cmd/cli.py`
4. Add a new subparser for your command in `create_parser()`

## License

MIT License - see LICENSE file for details.