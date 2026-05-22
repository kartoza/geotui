# Contributing

## Development Setup

### Using Nix (Recommended)

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop
```

This provides all dependencies including Python, ruff, pre-commit, and mkdocs.

### Using pip

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -e ".[dev,docs,i18n]"
pre-commit install
```

## Running the Application

```bash
python -m geotui
```

## Development Workflow

1. Create a feature branch from `main`
2. Write tests first (TDD approach)
3. Implement the feature
4. Run the test suite: `pytest`
5. Run linting: `ruff check src/ tests/`
6. Format code: `ruff format src/ tests/`
7. Commit with a descriptive message
8. Create a pull request

## Code Style

- **Formatter**: ruff (Black-compatible)
- **Linter**: ruff
- **Docstrings**: Google-style
- **Type hints**: required on all public functions
- **Coverage target**: 80% minimum
- **i18n**: wrap all user-facing strings in `_()`

## Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

| Hook | Purpose |
|------|---------|
| trailing-whitespace | Remove trailing whitespace |
| end-of-file-fixer | Ensure files end with newline |
| check-yaml | Validate YAML syntax |
| check-toml | Validate TOML syntax |
| check-json | Validate JSON syntax |
| ruff | Lint Python code |
| ruff-format | Format Python code |
| mypy | Static type checking |
| bandit | Security vulnerability scanning |
| codespell | Spell checking |
| reuse | REUSE/SPDX license compliance |

## Project Structure

```
geotui/
├── src/geotui/          # Application source
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   └── bdd/             # BDD feature tests
├── docs/                # MkDocs documentation
├── resources/           # Test data and resources
├── scripts/             # Build and utility scripts
├── .github/workflows/   # CI/CD pipelines
├── flake.nix            # Nix development environment
├── pyproject.toml       # Python project configuration
└── docker-compose.yml   # Local GeoServer for testing
```

## Local GeoServer for Testing

A Docker Compose file is provided for running a local GeoServer:

```bash
docker compose up -d
```

This starts a GeoServer instance at `http://localhost:8080/geoserver` with default credentials (`admin`/`geoserver`).

## Building Documentation

```bash
cd docs
mkdocs serve    # Live preview at http://localhost:8000
mkdocs build    # Build static site
```

## Versioning

- Version is maintained in `pyproject.toml` and `src/geotui/__init__.py`
- Bug fixes increment the patch version
- New features increment the minor version
- Breaking changes increment the major version

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
