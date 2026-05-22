# GeoTUI - GeoServer Manager

<div align="center" markdown>

<img src="assets/geotui-logo.png" alt="GeoTUI Logo" width="500">

**Manage your GeoServer instances from the terminal**

[![GitHub Release](https://img.shields.io/github/v/release/kartoza/geotui?style=flat-square)](https://github.com/kartoza/geotui/releases/latest)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=flat-square)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg?style=flat-square)](https://www.python.org/downloads/)

</div>

![GeoTUI publishing shapefiles to GeoServer](assets/images/geotui-screenshot.png)

## What is GeoTUI?

GeoTUI is a terminal application for managing [GeoServer](https://geoserver.org/) instances. It provides a dual-pane interface inspired by [Midnight Commander](https://midnight-commander.org/) — browse your local geospatial files on the left, manage GeoServer workspaces and layers on the right.

**Who is it for?** GIS administrators, data engineers, and anyone who publishes geospatial data to GeoServer and prefers working from the command line.

**Why use it?** Publishing data to GeoServer normally requires navigating the web admin, uploading files, configuring stores, and creating layers — all through a browser. GeoTUI lets you do all of this in a single keystroke: select your files, press F5, done. It also generates PDF reports of every publish operation.

**When would you use it?** Whenever you need to publish Shapefiles, GeoPackages, or GeoTIFFs to a GeoServer instance — whether it's a local development server or a production deployment on [GeoSpatialHosting](https://geospatialhosting.com).

## Key Features

- **Dual-pane interface** — local files on the left, GeoServer tree on the right
- **One-click publishing** — select files, press F5, layers are created automatically
- **Multiple connections** — manage several GeoServer instances simultaneously
- **PDF reports** — every publish operation generates a detailed report
- **Encrypted credentials** — master password vault with AES encryption (PBKDF2, 600k iterations)
- **Cross-platform** — standalone binaries for Windows, Linux, and macOS
- **Multilingual** — English, Portuguese, and Spanish

## Quick Start

**1. Install**

Download from the [latest release](https://github.com/kartoza/geotui/releases/latest), or:

```bash
pip install geotui
```

**2. Launch**

```bash
geotui
```

**3. Connect**

Press **F9** to open Settings, click **Add**, enter your GeoServer URL and credentials.

**4. Publish**

Navigate to your data in the left pane, select a workspace in the right pane, press **F5**.

For a detailed walkthrough with screenshots, see the [Getting Started](user-guide/getting-started.md) guide.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| **Tab** | Switch between panes |
| **F2** | GeoServer Actions (create workspace, etc.) |
| **F5** | Publish selected files to GeoServer |
| **F7** | Create directory |
| **F8** | Delete |
| **F9** | Settings / Connection manager |
| **F10 / q** | Quit |
| **Ctrl+L** | Cycle language (EN / PT / ES) |

## Start Here

New to GeoTUI? Follow these guides in order:

| Step | Guide | What you'll learn |
|------|-------|-------------------|
| 1 | **[Getting Started](user-guide/getting-started.md)** | Install, set up your master password, add a GeoServer connection |
| 2 | **[Navigation](user-guide/navigation.md)** | Dual-pane layout, keyboard shortcuts, switching panes |
| 3 | **[Configuration](user-guide/configuration.md)** | Credential vault, language switching, colour palette |
| 4 | **[Connecting to GSH](user-guide/connecting-gsh.md)** | Set up a hosted GeoServer on GeoSpatialHosting |

## All Documentation

<div class="grid cards" markdown>

- :material-rocket-launch: **[Getting Started](user-guide/getting-started.md)** — install, connect, and publish your first data
- :material-keyboard: **[Navigation](user-guide/navigation.md)** — keyboard shortcuts and publishing workflow
- :material-cloud: **[Connecting to GSH](user-guide/connecting-gsh.md)** — hosted GeoServer on GeoSpatialHosting
- :material-cog: **[Configuration](user-guide/configuration.md)** — vault, language, and colour settings
- :material-download: **[Installation](admin-guide/installation.md)** — all platforms and package formats
- :material-shield-lock: **[Security](admin-guide/security.md)** — encryption, threat model, vulnerability reporting
- :material-file-tree: **[Architecture](developer-guide/architecture.md)** — module structure and design decisions
- :material-code-tags: **[API Reference](developer-guide/api.md)** — full Python API documentation
- :material-hand-heart: **[Contributing](developer-guide/contributing.md)** — development setup and how to help
- :material-bug: **[Security & Supply Chain](developer-guide/security-supply-chain.md)** — SBOM, CVE scanning, auditing

</div>

## Sustainable Funding

GeoTUI is free and open source. If you find it useful, please consider supporting its development through [GitHub Sponsors](https://github.com/sponsors/kartoza).

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
