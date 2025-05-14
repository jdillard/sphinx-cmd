# Sphinx-CMD

A collection of command-line tools for managing Sphinx documentation.

## Installation

```bash
pip install sphinx-cmd
```

## Commands

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

# Install in development mode
pip install -e .
```

## License

MIT License - see LICENSE file for details.