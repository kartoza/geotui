# Installation

## System Requirements

- Python 3.10 or higher
- Terminal with 256-color support (most modern terminals)
- Windows (PowerShell), Linux, or macOS

## Installation Methods

### PyPI (Recommended)

```bash
pip install geotui
```

### Nix

```bash
# Run directly
nix run github:kartoza/geotui

# Add to your flake
{
  inputs.geotui.url = "github:kartoza/geotui";
}
```

### From Source

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
pip install -e ".[dev,docs]"
```

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
