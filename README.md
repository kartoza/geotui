# GeoTUI

<div align="center">

```
    ,,,
   (o o)   GeoTUI
   ( _ )   GeoServer Manager
    |||
   / | \   An otter-powered TUI
```

**A beautiful Midnight Commander-style TUI for GeoServer management**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/kartoza/geotui/actions/workflows/ci.yml/badge.svg)](https://github.com/kartoza/geotui/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://kartoza.github.io/geotui)

</div>

## Overview

GeoTUI is a terminal user interface (TUI) application for managing GeoServer instances. Built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/), it provides a familiar Midnight Commander-style dual-pane interface that runs everywhere: Windows (PowerShell), Linux, and macOS.

## Features

- **Midnight Commander Layout** - Dual-pane interface with rounded borders
- **Kartoza Branded** - Beautiful color scheme with yellow/orange, blue, teal, and grey accents
- **Cross-Platform** - Runs on Windows, Linux, and macOS
- **Project-Local Config** - Config and reports stored in `.geotui/` within your working directory
- **Internationalization** - English, Portuguese, and Spanish (switchable with Ctrl+L)
- **Secure by Design** - Keyring-based credential storage, HTTPS by default
- **Keyboard-Driven** - Full function key bindings just like MC

## Installation

### Standalone Binary (no Python required)

Download and copy the binary to your PATH:

```bash
# Build the standalone binary
make standalone

# Install to /usr/local/bin so it's available everywhere
make install-bin
```

Or manually:

```bash
sudo cp dist/geotui /usr/local/bin/geotui
```

### Using pipx (recommended for Python users)

```bash
make install
# or:
pipx install .
```

### From PyPI

```bash
pip install geotui
```

### Using Nix / NixOS

```bash
# Run directly without installing
nix run github:kartoza/geotui

# Or build locally
make nix-build
./result/bin/geotui
```

### From Source

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop  # or: pip install -e ".[dev]"
python -m geotui
```

## Quick Start

Run `geotui` from your project directory:

```bash
cd /path/to/your/geodata
geotui
```

The file pane opens at your current directory. Config and reports are saved to `.geotui/` inside your working directory, so each project keeps its own GeoServer connections and publish logs.

## Makefile Reference

| Command | Description |
|---|---|
| `make install` | Install via pipx (globally available) |
| `make install-bin` | Build standalone binary and copy to `/usr/local/bin` |
| `make standalone` | Build standalone binary to `dist/geotui` |
| `make nix-build` | Build via Nix flake (for NixOS) |
| `make nix-run` | Run directly via Nix (for NixOS) |
| `make build` | Build wheel and source distribution |
| `make install-dev` | Install in editable mode for development |
| `make test` | Run test suite |
| `make lint` | Run ruff linter |
| `make format` | Format code |
| `make docs` | Serve documentation locally |
| `make clean` | Remove build artifacts |

## Key Bindings

| Key | Action |
|-----|--------|
| `Tab` | Switch between panes |
| `F1` | Help |
| `F2` | Menu |
| `F5` | Copy / Publish to GeoServer |
| `F6` | Move |
| `F7` | Create directory |
| `F8` | Delete |
| `F9` | Settings |
| `F10` / `q` | Quit |
| `Ctrl+L` | Cycle language |

## Project-Local Configuration

GeoTUI stores all config and reports relative to where you run it:

```
your-project/
└── .geotui/
    ├── config.json      # GeoServer connections for this project
    └── reports/         # Publish reports (PDF + JSON)
```

Add `.geotui/` to your `.gitignore` to keep credentials out of version control.

## Development

```bash
# Enter dev environment
nix develop

# Run the app
python -m geotui

# Run tests
pytest

# Lint
ruff check src/ tests/

# Build docs
cd docs && mkdocs serve
```

## Documentation

Full documentation is available at [kartoza.github.io/geotui](https://kartoza.github.io/geotui).

## Mascot

GeoTUI is guided by an industrious otter - because otters are excellent navigators of both water and land, just like GeoTUI navigates your geospatial infrastructure.

## Contributing

We welcome contributions! Please see the [Contributing Guide](https://kartoza.github.io/geotui/developer-guide/contributing/) for details.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Sustainable Funding

If you find GeoTUI useful, please consider supporting its development:

- [GitHub Sponsors](https://github.com/sponsors/kartoza)

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)