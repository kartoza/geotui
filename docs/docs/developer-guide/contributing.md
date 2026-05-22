# Contributing

## Development Setup

### Using Nix (Recommended)

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop
```

This provides all dependencies including Python 3.13, ruff, mypy, bandit, pre-commit, mkdocs, gettext, and Docker.

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

## Coding Standards

### Style & Formatting

| Tool | Purpose | Configuration |
|------|---------|---------------|
| **ruff** | Linting + formatting (replaces flake8, black, isort) | `pyproject.toml [tool.ruff]` |
| **mypy** | Static type checking (strict mode) | `pyproject.toml [tool.mypy]` |
| **bandit** | Security vulnerability scanning | `pyproject.toml [tool.bandit]` |
| **codespell** | Spell checking in source and docs | `.pre-commit-config.yaml` |

### Code Conventions

- **Docstrings**: Google-style on all public classes and functions
- **Type hints**: Required on all public function signatures
- **Imports**: Sorted by ruff (isort-compatible)
- **Line length**: 88 characters (Black default)
- **Coverage target**: 80% minimum
- **i18n**: All user-facing strings wrapped in `_()`
- **Async**: Use `async/await` for I/O operations (httpx, file operations)
- **DRY**: Single form/UI for CRUD with mode switching (see `UnlockScreen` for unlock vs setup)

### Security Rules

- No `shell=True` in subprocess calls
- No hardcoded credentials or secrets
- All HTTP calls use `verify=True` (HTTPS enforced)
- GeoServer resource names validated against `[a-zA-Z0-9_.\-]+` regex
- Config files written with `0o600` permissions
- Pre-commit `detect-private-key` hook prevents accidental key commits

## Technology Stack

### Runtime Libraries

| Library | Version | Why we use it |
|---------|---------|---------------|
| **[Textual](https://textual.textualize.io/)** | >=1.0.0 | TUI framework with CSS-like styling, reactive data binding, widget composition, and async event handling. Chosen for cross-platform terminal support and rich widget library. |
| **[Rich](https://rich.readthedocs.io/)** | >=13.0.0 | Terminal rendering engine used by Textual. Provides styled text, tables, progress bars, and syntax highlighting. |
| **[httpx](https://www.python-httpx.org/)** | >=0.27.0 | Async HTTP client for GeoServer REST API calls. Chosen over `requests` for native async support, keeping the UI responsive during uploads. |
| **[Pydantic](https://docs.pydantic.dev/)** | >=2.0.0 | Data validation and serialisation for connection configuration. Provides type-safe models with JSON schema generation. |
| **[cryptography](https://cryptography.io/)** | >=42.0.0 | Fernet symmetric encryption (AES-128-CBC + HMAC-SHA256) with PBKDF2-HMAC-SHA256 key derivation (600k iterations) for the credential vault. |
| **[fpdf2](https://py-pdf.github.io/fpdf2/)** | >=2.8.0 | Lightweight PDF generation for publish reports. No external dependencies (pure Python). |
| **[Click](https://click.palletsprojects.com/)** | >=8.0.0 | CLI framework for headless subcommands (`publish`, `export`, `import-config`). |
| **[keyring](https://keyring.readthedocs.io/)** | >=25.0.0 | System keyring integration (reserved for future OS-level credential storage). |

### Development Libraries

| Library | Version | Why we use it |
|---------|---------|---------------|
| **[pytest](https://docs.pytest.org/)** | >=8.0.0 | Test framework with fixture injection, parametrisation, and plugin ecosystem. |
| **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)** | >=0.24.0 | Async test support for Textual `AppTest` widget testing. |
| **[pytest-bdd](https://pytest-bdd.readthedocs.io/)** | >=7.0.0 | BDD testing with Gherkin feature files for user story validation. |
| **[pytest-cov](https://pytest-cov.readthedocs.io/)** | >=5.0.0 | Coverage measurement and enforcement (minimum 60%, target 80%). |
| **[ruff](https://docs.astral.sh/ruff/)** | >=0.8.0 | Unified Python linter and formatter. Replaces flake8+black+isort with a single Rust-based tool. |
| **[mypy](https://mypy.readthedocs.io/)** | >=1.0.0 | Static type checker with strict mode enabled. |
| **[bandit](https://bandit.readthedocs.io/)** | >=1.7.0 | Security-focused static analysis (OWASP patterns, injection risks). |
| **[Babel](https://babel.pocoo.org/)** | >=2.16.0 | Translation extraction and `.po`/`.mo` file management. |

### Documentation Libraries

| Library | Version | Why we use it |
|---------|---------|---------------|
| **[MkDocs](https://www.mkdocs.org/)** | >=1.6.0 | Static site generator for project documentation. |
| **[mkdocs-material](https://squidfunk.github.io/mkdocs-material/)** | >=9.5.0 | Material Design theme with Kartoza brand customisation. |
| **[mkdocstrings](https://mkdocstrings.github.io/)** | >=0.27.0 | Auto-generates API reference pages from Google-style docstrings. |

## Pre-commit Hooks

Pre-commit hooks run automatically on every commit:

| Hook | Purpose |
|------|---------|
| trailing-whitespace | Remove trailing whitespace |
| end-of-file-fixer | Ensure files end with newline |
| check-yaml | Validate YAML syntax |
| check-toml | Validate TOML syntax |
| check-json | Validate JSON syntax |
| detect-private-key | Prevent accidental key commits |
| check-added-large-files | Block files > 500KB |
| ruff | Lint Python code |
| ruff-format | Format Python code |
| mypy | Static type checking |
| bandit | Security vulnerability scanning |
| codespell | Spell checking |
| reuse | REUSE/SPDX license compliance |

Pre-push hooks (slower checks):

| Hook | Purpose |
|------|---------|
| pytest | Run full test suite |
| docs-build | Validate mkdocs builds cleanly |

## Project Structure

```
geotui/
├── src/geotui/          # Application source
│   ├── app.py           # Main Textual App class
│   ├── cli.py           # Click CLI subcommands
│   ├── client.py        # GeoServer REST API client (async)
│   ├── config.py        # Config, encryption, vault
│   ├── publisher.py     # Bulk publish engine
│   ├── report.py        # PDF/JSON report generator
│   ├── theme.py         # Kartoza brand colour theme
│   ├── screens/         # Modal screen components
│   ├── widgets/         # TUI widget components
│   ├── styles/          # Textual CSS styles
│   └── i18n/            # Translations (.pot/.po/.mo)
├── tests/               # Test suite
│   ├── unit/            # Unit tests
│   └── bdd/             # BDD feature tests
├── docs/                # MkDocs documentation
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
