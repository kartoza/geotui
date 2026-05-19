# Contributing

## Development Setup

### Using Nix (Recommended)

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop
```

### Using pip

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
pip install -e ".[dev,docs,i18n]"
pre-commit install
```

## Development Workflow

1. Create a feature branch from `main`
2. Write tests first (TDD approach)
3. Implement the feature
4. Run the test suite: `pytest`
5. Run linting: `ruff check src/ tests/`
6. Create a pull request

## Code Style

- Python code follows ruff formatting (Black-compatible)
- Google-style docstrings
- Type hints on all public functions
- 80% minimum test coverage

## Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

- Trailing whitespace removal
- YAML/TOML/JSON validation
- Ruff linting and formatting
- mypy type checking
- Bandit security checks
- Codespell spell checking
- REUSE license compliance

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
