# Sphinx-CMD

A collection of command-line tools for managing Sphinx documentation.

[![PyPI version](https://img.shields.io/pypi/v/sphinx-cmd.svg)](https://pypi.python.org/pypi/sphinx-cmd)
[![Downloads](https://static.pepy.tech/badge/sphinx-cmd/month)](https://pepy.tech/project/sphinx-cmd)

## Installation

```bash
pip install sphinx-cmd
```

## Commands

The `sphinx-cmd` tool provides subcommands for different Sphinx documentation management tasks.

### Global Options

Options that apply to all commands:

```bash
# Specify a context path (directory containing conf.py)
sphinx-cmd --context /path/to/docs COMMAND

# Dry run to preview changes without executing them
sphinx-cmd --dry-run COMMAND

# Process additional directives beyond defaults
sphinx-cmd --directives drawio-figure,drawio-image COMMAND

# Enable verbose output with detailed processing information
sphinx-cmd --verbose COMMAND
```

By default, `sphinx-cmd` will automatically detect the context of your documentation project by finding the nearest `conf.py` file in the directory tree.

### `sphinx-cmd rm`

Delete unused .rst files and their unique assets (images, includes, etc) if not used elsewhere.

```bash
# Remove files and assets
sphinx-cmd rm path/to/docs

# Using global options
sphinx-cmd --dry-run --directives drawio-figure,drawio-image rm path/to/docs
```

#### Features

- Configure custom directives to be processed
- Only deletes unused unique assets in the provided context path

### `sphinx-cmd mv`

Move/rename .rst files and automatically update all references to them.

```bash
# Move and update all references
sphinx-cmd mv old-file.rst new-file.rst

# Move to a different directory
sphinx-cmd mv chapter1.rst topics/chapter1.rst

# Move without updating references
sphinx-cmd mv old-file.rst new-file.rst --no-update-refs

# Using global options
sphinx-cmd --dry-run --directives drawio-figure mv old-file.rst new-file.rst
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

Use the `--directives` global option with any command to add custom directives for a single run:

```bash
sphinx-cmd --directives drawio-figure,drawio-image rm path/to/docs
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
isort sphinx_cmd tests
flake8 sphinx_cmd tests
mypy sphinx_cmd

# Test the command
sphinx-cmd --help
sphinx-cmd rm --help
sphinx-cmd mv --help
```

### Adding New Commands

The architecture is designed to make adding new commands easy:

1. Create a new file in `sphinx_cmd/commands/` (e.g., `new_command.py`)
2. Implement an `execute(args)` function in your new file
3. Import the command in `sphinx_cmd/cli.py`
4. Add a new subparser for your command in `create_parser()`
5. Create new tests (e.g., `tests/test_new_command.py`)

## License

MIT License - see LICENSE file for details.