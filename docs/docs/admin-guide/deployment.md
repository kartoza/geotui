# Deployment

## Deployment Model

GeoTUI is a client-side application that runs on individual workstations. It connects to remote GeoServer instances over HTTPS. There is no server component to deploy — each user installs and runs GeoTUI locally.

## Recommended Setup

1. **Install GeoTUI** on each user's workstation using the [installation guide](installation.md)
2. **Ensure network access** to the target GeoServer instances (HTTPS, typically port 443)
3. **Distribute connection details** — each user configures their own connections via F9

## Multi-User Considerations

- Each user has their own encrypted credential vault
- Master passwords are per-user and not recoverable
- Connection configurations are stored locally and not shared
- No central user management is required

## Updating

### Standalone Binary

Download the latest release from [GitHub Releases](https://github.com/kartoza/geotui/releases) and replace the existing binary.

### PyPI

```bash
pip install --upgrade geotui
```

### Linux Packages

```bash
# Debian/Ubuntu
sudo dpkg -i geotui_NEW-VERSION_amd64.deb

# Fedora/RHEL
sudo rpm -U geotui-NEW-VERSION-1.x86_64.rpm

# Snap
sudo snap install --dangerous geotui_NEW-VERSION_amd64.snap
```

## Network Requirements

| Service | Protocol | Port | Purpose |
|---------|----------|------|---------|
| GeoServer | HTTPS | 443 | REST API for management operations |
| GeoServer | HTTP | 8080 | Local development instances |

GeoTUI automatically detects the `/geoserver` path prefix used by many deployments. Users should enter the base URL without including `/geoserver`.

## Data Flow

```
User workstation                    Remote server
┌──────────┐   HTTPS REST API   ┌──────────────┐
│  GeoTUI  │ ◄───────────────► │  GeoServer   │
│          │                    │              │
│ Local    │   File upload      │  Datastores  │
│ files    │ ────────────────► │  Layers      │
└──────────┘                    └──────────────┘
```

Files (Shapefiles, GeoPackages, GeoTIFFs) are uploaded from the user's local file system to GeoServer via the REST API. No intermediate staging server is required.

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
