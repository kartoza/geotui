# Installation

## System Requirements

- Python 3.10 or higher
- Terminal with 256-colour support (most modern terminals)
- Windows (PowerShell or Windows Terminal), Linux, or macOS

## Installation Methods

### Standalone Binary (Recommended)

Download the latest binary for your platform from the [GitHub Releases](https://github.com/kartoza/geotui/releases) page:

| Platform | File | Notes |
|----------|------|-------|
| **Linux (x86_64)** | `geotui-linux-amd64` | `chmod +x` and run |
| **macOS (Intel)** | `geotui-macos-amd64` | See Gatekeeper note below |
| **macOS (Apple Silicon)** | `geotui-macos-arm64` | See Gatekeeper note below |
| **Windows** | `geotui-windows-amd64.exe` | See SmartScreen note below |

```bash
# Linux / macOS
chmod +x geotui-*
sudo cp geotui-* /usr/local/bin/geotui
geotui
```

!!! note "macOS Gatekeeper"
    Run `xattr -d com.apple.quarantine /usr/local/bin/geotui` or allow in **System Settings > Privacy & Security** on first launch.

!!! note "Windows SmartScreen"
    Click **More info** then **Run anyway** on first launch. See the [Getting Started](../user-guide/getting-started.md) guide for screenshots.

### Linux Packages

| Format | File | Install Command |
|--------|------|-----------------|
| **Debian/Ubuntu** | `geotui_VERSION_amd64.deb` | `sudo dpkg -i geotui_*.deb` |
| **Fedora/RHEL** | `geotui-VERSION-1.x86_64.rpm` | `sudo rpm -i geotui-*.rpm` |
| **AppImage** | `GeoTUI-VERSION-x86_64.AppImage` | `chmod +x GeoTUI-*.AppImage && ./GeoTUI-*.AppImage` |
| **Snap** | `geotui_VERSION_amd64.snap` | `sudo snap install --dangerous geotui_*.snap` |

!!! warning "Unsigned packages"
    The .deb, .rpm, and .snap packages are not signed with a distribution key. For Snap use `--dangerous`. For RPM with GPG checking: `sudo rpm -i --nosignature geotui-*.rpm`.

### PyPI

```bash
pip install geotui
# or with pipx for isolated install:
pipx install geotui
```

### Nix

```bash
# Run directly
nix run github:kartoza/geotui

# Enter development shell
nix develop github:kartoza/geotui

# Add to your flake inputs
{
  inputs.geotui.url = "github:kartoza/geotui";
}
```

### From Source

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
pip install -e ".[dev,docs]"
geotui
```

## Verifying the Installation

Run `geotui` in your terminal. You should see the dual-pane interface with "GeoTUI - GeoServer Manager" in the header.

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
