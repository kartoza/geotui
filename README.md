# GeoTUI

<div align="center">

```
    ,,,
   (o o)   GeoTUI
   ( _ )   Geospatial Server Manager
    |||
   / | \   An otter-powered TUI
```

**A beautiful Midnight Commander-style TUI for geospatial server management**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![CI](https://github.com/kartoza/geotui/actions/workflows/ci.yml/badge.svg)](https://github.com/kartoza/geotui/actions)
[![Documentation](https://img.shields.io/badge/docs-mkdocs-blue.svg)](https://kartoza.github.io/geotui)

</div>

## Overview

GeoTUI is a terminal user interface (TUI) application for managing geospatial servers. Built with [Textual](https://textual.textualize.io/) and [Rich](https://rich.readthedocs.io/), it provides a familiar Midnight Commander-style dual-pane interface that runs everywhere: Windows (PowerShell), Linux, and macOS.

## Features

- **Midnight Commander Layout** - Dual-pane interface with rounded borders
- **Kartoza Branded** - Beautiful color scheme with yellow/orange, blue, teal, and grey accents
- **Cross-Platform** - Runs on Windows, Linux, and macOS
- **Internationalization** - English, Portuguese, and Spanish (switchable with Ctrl+L)
- **Secure by Design** - Keyring-based credential storage, HTTPS by default
- **Keyboard-Driven** - Full function key bindings just like MC

## Installation

### From PyPI

```bash
pip install geotui
```

### Using Nix

```bash
nix run github:kartoza/geotui
```

### From Source

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop  # or: pip install -e ".[dev]"
python -m geotui
```

## Quick Start

```bash
geotui
```

## Key Bindings

| Key | Action |
|-----|--------|
| `Tab` | Switch between panes |
| `F1` | Help |
| `F2` | Menu |
| `F5` | Copy |
| `F6` | Move |
| `F7` | Create directory |
| `F8` | Delete |
| `F9` | Settings |
| `F10` / `q` | Quit |
| `Ctrl+L` | Cycle language |

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
