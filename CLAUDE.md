# GeoTUI - Project Instructions

## Project Overview
GeoTUI is a Midnight Commander-style TUI for geospatial server management, built with Python/Textual.

## Key Paths
- Source: `src/geotui/`
- Tests: `tests/` (unit + BDD)
- Docs: `docs/`
- Styles: `src/geotui/styles/app.tcss`
- i18n: `src/geotui/i18n/`

## Development Commands
```bash
nix develop                    # Enter dev environment
python -m geotui               # Run the app
pytest                         # Run tests
ruff check src/ tests/         # Lint
ruff format src/ tests/        # Format
cd docs && mkdocs serve        # Serve docs
```

## Conventions
- Kartoza brand colors: #DF9E2F (orange), #569FC6 (blue), #8A8B8B (grey), #06969A (teal), #CC0403 (red)
- Rounded borders (`border: round`) for all pane containers
- Google-style docstrings
- 80% minimum test coverage
- TDD/BDD testing approach
- i18n: wrap all user-facing strings in `_()`
- Version in: `pyproject.toml` and `src/geotui/__init__.py`

## GitHub
- Org: kartoza
- Repo: geotui
- Pages: kartoza.github.io/geotui
