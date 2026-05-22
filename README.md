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
- **Secure by Design** - Master password encrypted vault (AES-256), HTTPS by default
- **Keyboard-Driven** - Full function key bindings just like MC

## Installation

### Download Pre-Built Packages

Download the latest release from the [GitHub Releases](https://github.com/kartoza/geotui/releases) page.

#### Linux

| Format | File | Install Command |
|--------|------|-----------------|
| **AppImage** | `GeoTUI-x.y.z-x86_64.AppImage` | `chmod +x GeoTUI-*.AppImage && ./GeoTUI-*.AppImage` |
| **Debian/Ubuntu** | `geotui_x.y.z_amd64.deb` | `sudo dpkg -i geotui_*.deb` |
| **Fedora/RHEL** | `geotui-x.y.z-1.x86_64.rpm` | `sudo rpm -i geotui-*.rpm` |
| **Snap** | `geotui_x.y.z_amd64.snap` | `sudo snap install --dangerous geotui_*.snap` |
| **Flatpak** | `GeoTUI-x.y.z.flatpak` | `flatpak install GeoTUI-*.flatpak` |
| **Standalone** | `geotui-linux-amd64` | `chmod +x geotui-linux-amd64 && sudo cp geotui-linux-amd64 /usr/local/bin/geotui` |

> **Note on unsigned packages:** The .deb, .rpm, and .snap packages are not signed with
> a distribution key. For .deb you may see a warning from `dpkg` which is safe to
> proceed past. For .snap you must use the `--dangerous` flag. For .rpm on systems with
> GPG checking enabled, use `sudo rpm -i --nosignature geotui-*.rpm`.

#### macOS

| Architecture | File |
|-------------|------|
| **Intel (x86_64)** | `geotui-macos-amd64` |
| **Apple Silicon (M1/M2/M3)** | `geotui-macos-arm64` |

```bash
# Download the correct binary for your Mac, then:
chmod +x geotui-macos-*
sudo cp geotui-macos-* /usr/local/bin/geotui
```

> **macOS Gatekeeper warning:** Because the binary is not notarised with an Apple
> Developer certificate, macOS will block it on first run. To allow it:
>
> 1. Try to run `geotui` in Terminal - you will see *"geotui" cannot be opened because the developer cannot be verified.*
> 2. Open **System Settings > Privacy & Security** and scroll to the bottom.
> 3. Click **"Allow Anyway"** next to the GeoTUI message.
> 4. Run `geotui` again and click **"Open"** in the confirmation dialog.
>
> Alternatively, remove the quarantine attribute before first run:
> ```bash
> xattr -d com.apple.quarantine /usr/local/bin/geotui
> ```

#### Windows

Download `geotui-windows-amd64.exe` from the release page.

```powershell
# Move to a directory in your PATH, e.g.:
Move-Item geotui-windows-amd64.exe "$env:LOCALAPPDATA\Microsoft\WindowsApps\geotui.exe"
```

> **Windows SmartScreen warning:** Because the .exe is not code-signed, Windows
> Defender SmartScreen may show *"Windows protected your PC"*. Click
> **"More info"** then **"Run anyway"**. This happens once per new version.

### From PyPI

```bash
pip install geotui
# or with pipx (recommended):
pipx install geotui
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
| `F10` | Quit |
| `Ctrl+T` | Toggle file selection |
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