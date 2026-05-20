# GeoTUI - Package Architecture

## Runtime Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **textual** | >=1.0.0 | TUI framework providing widgets, layout, CSS styling, and event handling |
| **rich** | >=13.0.0 | Rich text rendering, used by Textual for terminal output |
| **httpx** | >=0.27.0 | Async HTTP client for communicating with GeoServer REST API |
| **pydantic** | >=2.0.0 | Data validation and settings management |
| **pydantic-settings** | >=2.0.0 | Configuration management with environment variable support |
| **keyring** | >=25.0.0 | Secure credential storage using system keyring |
| **fpdf2** | >=2.8.0 | Lightweight PDF generation for publish reports |
| **click** | >=8.0.0 | CLI framework for publish, export, import-config subcommands |

## Development Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **pytest** | >=8.0.0 | Test framework |
| **pytest-asyncio** | >=0.24.0 | Async test support for Textual widget tests |
| **pytest-bdd** | >=7.0.0 | BDD test support with Gherkin feature files |
| **pytest-cov** | >=5.0.0 | Code coverage measurement (target: 80%) |
| **textual-dev** | >=1.0.0 | Textual development tools (console, devtools) |
| **ruff** | >=0.8.0 | Python linter and formatter (replaces flake8, black, isort) |
| **mypy** | >=1.0.0 | Static type checking |
| **pre-commit** | >=4.0.0 | Git pre-commit hook manager |
| **bandit** | >=1.7.0 | Security linting |

## Documentation Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **mkdocs** | >=1.6.0 | Documentation site generator |
| **mkdocs-material** | >=9.5.0 | Material theme with Kartoza brand customization |
| **mkdocstrings[python]** | >=0.27.0 | Auto-generate API docs from Google-style docstrings |
| **mkdocs-git-revision-date-localized-plugin** | >=1.2.0 | Show last updated dates on docs |

## i18n Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| **babel** | >=2.16.0 | Translation extraction and compilation tools |

## Application Modules

| Module | Purpose |
|--------|---------|
| **publisher.py** | Shapefile discovery, ZIP bundling, concurrent upload engine with retry |
| **report.py** | PDF and JSON report generation with Kartoza+GeoTUI branding |
| **cli.py** | Click CLI with publish, export, import-config subcommands |

## System Dependencies (via Nix)

| Package | Purpose |
|---------|---------|
| **python313** | Python runtime |
| **gettext** | Translation file compilation (msgfmt) |
| **gh** | GitHub CLI for repo management |
| **pre-commit** | Pre-commit hook runner |
