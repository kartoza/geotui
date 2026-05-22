# Release Packaging & README Install Guide Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Snap, Flatpak, and macOS arm64 builds to the release workflow, and write comprehensive README install instructions covering all package types with unsigned-package warnings.

**Architecture:** Extend `.github/workflows/release.yml` with new jobs for Snap (via snapcraft), Flatpak (via flatpak-builder), and a macOS arm64 matrix entry. Rewrite the README Installation section with per-platform tabs covering every artifact type, security warnings, and verification steps.

**Tech Stack:** GitHub Actions, PyInstaller, snapcraft, flatpak-builder, dpkg, rpm

---

### Task 1: Add macOS arm64 to the binary build matrix

**Files:**
- Modify: `.github/workflows/release.yml:28-61`

- [ ] **Step 1: Add macos-14 (arm64) to the build matrix**

In `.github/workflows/release.yml`, add a new entry to the `build-binary` matrix:

```yaml
  build-binary:
    strategy:
      matrix:
        include:
          - os: ubuntu-latest
            artifact: geotui-linux-amd64
            binary: dist/geotui
          - os: macos-latest
            artifact: geotui-macos-amd64
            binary: dist/geotui
          - os: macos-14
            artifact: geotui-macos-arm64
            binary: dist/geotui
          - os: windows-latest
            artifact: geotui-windows-amd64.exe
            binary: dist/geotui.exe
```

- [ ] **Step 2: Add arm64 artifact to the github-release job files list**

In the `github-release` job, add to the `files:` list:

```yaml
            artifacts/geotui-macos-arm64/*
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml
git commit -m "ci: add macOS arm64 (Apple Silicon) binary build"
```

---

### Task 2: Add Snap package build

**Files:**
- Create: `snap/snapcraft.yaml`
- Modify: `.github/workflows/release.yml` (add `build-snap` job)

- [ ] **Step 1: Create snap/snapcraft.yaml**

```yaml
name: geotui
version: '0.7.0'
summary: Midnight Commander-style TUI for GeoServer management
description: |
  A beautiful terminal user interface for managing GeoServer instances.
  Built with Python/Textual. Supports shapefile, GeoPackage, and GeoTIFF
  publishing with PDF reports.

  Made with love by Kartoza (https://kartoza.com)
base: core22
grade: stable
confinement: strict

apps:
  geotui:
    command: bin/geotui
    plugs:
      - home
      - network
      - network-bind

parts:
  geotui:
    plugin: python
    source: .
    python-packages:
      - .
    build-packages:
      - python3-dev
      - libffi-dev
    stage-packages:
      - libffi8
```

- [ ] **Step 2: Add build-snap job to release.yml**

Add this job after the `build-appimage` job:

```yaml
  # ── Snap package ─────────────────────────────────────────
  build-snap:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: snapcore/action-build@v1
        id: build
      - uses: actions/upload-artifact@v4
        with:
          name: geotui-snap
          path: ${{ steps.build.outputs.snap }}
```

- [ ] **Step 3: Add build-snap to github-release needs and files**

In the `github-release` job:

```yaml
    needs:
      - build-python
      - build-binary
      - build-deb
      - build-rpm
      - build-appimage
      - build-snap
```

And add to `files:`:

```yaml
            artifacts/geotui-snap/*
```

- [ ] **Step 4: Commit**

```bash
git add snap/snapcraft.yaml .github/workflows/release.yml
git commit -m "ci: add Snap package build to release workflow"
```

---

### Task 3: Add Flatpak package build

**Files:**
- Create: `flatpak/com.kartoza.GeoTUI.yml`
- Create: `flatpak/com.kartoza.GeoTUI.desktop`
- Modify: `.github/workflows/release.yml` (add `build-flatpak` job)

- [ ] **Step 1: Create flatpak/com.kartoza.GeoTUI.desktop**

```ini
[Desktop Entry]
Name=GeoTUI
Comment=Midnight Commander-style TUI for GeoServer management
Exec=geotui
Icon=com.kartoza.GeoTUI
Terminal=true
Type=Application
Categories=Science;Geography;Network;
```

- [ ] **Step 2: Create flatpak/com.kartoza.GeoTUI.yml**

```yaml
app-id: com.kartoza.GeoTUI
runtime: org.freedesktop.Platform
runtime-version: '23.08'
sdk: org.freedesktop.Sdk
command: geotui

finish-args:
  - --share=network
  - --filesystem=home

modules:
  - name: python3-geotui
    buildsystem: simple
    build-commands:
      - pip3 install --no-build-isolation --prefix=/app .
    sources:
      - type: dir
        path: ..
```

- [ ] **Step 3: Add build-flatpak job to release.yml**

Add this job after the `build-snap` job:

```yaml
  # ── Flatpak package ─────────────────────────────────────
  build-flatpak:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Install Flatpak tools
        run: |
          sudo apt-get update
          sudo apt-get install -y flatpak flatpak-builder
          flatpak remote-add --user --if-not-exists \
            flathub https://dl.flathub.org/repo/flathub.flatpakrepo
          flatpak install --user -y \
            flathub org.freedesktop.Platform//23.08 \
            org.freedesktop.Sdk//23.08
      - name: Build Flatpak bundle
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          flatpak-builder --user --install-deps-from=flathub \
            --force-clean build-dir flatpak/com.kartoza.GeoTUI.yml
          flatpak build-export repo build-dir
          flatpak build-bundle repo \
            GeoTUI-${VERSION}.flatpak com.kartoza.GeoTUI
      - uses: actions/upload-artifact@v4
        with:
          name: geotui-flatpak
          path: "*.flatpak"
```

- [ ] **Step 4: Add build-flatpak to github-release needs and files**

In the `github-release` job, add `build-flatpak` to `needs:` and add to `files:`:

```yaml
            artifacts/geotui-flatpak/*
```

- [ ] **Step 5: Commit**

```bash
git add flatpak/ .github/workflows/release.yml
git commit -m "ci: add Flatpak package build to release workflow"
```

---

### Task 4: Rewrite README Installation section

**Files:**
- Modify: `README.md:36-88`

- [ ] **Step 1: Replace the Installation section with comprehensive instructions**

Replace everything between `## Installation` and `## Quick Start` with:

```markdown
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
> proceed past. For .snap you must use `--dangerous` flag. For .rpm on systems with
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
> 1. Try to run `geotui` in Terminal - you will see _"geotui" cannot be opened because the developer cannot be verified._
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
> Defender SmartScreen may show _"Windows protected your PC"_. Click
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

# Or add to your flake inputs
```

### From Source

```bash
git clone https://github.com/kartoza/geotui.git
cd geotui
nix develop  # or: pip install -e ".[dev]"
python -m geotui
```
```

- [ ] **Step 2: Update Key Bindings table to remove old q reference**

Replace:
```markdown
| `F10` / `q` | Quit |
```
With:
```markdown
| `F10` | Quit |
| `Ctrl+T` | Toggle file selection |
```

- [ ] **Step 3: Update the "Secure by Design" feature line**

Replace:
```markdown
- **Secure by Design** - Keyring-based credential storage, HTTPS by default
```
With:
```markdown
- **Secure by Design** - Master password encrypted vault (AES-256), HTTPS by default
```

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs: comprehensive install instructions with unsigned package warnings"
```

---

### Task 5: Update snapcraft version dynamically and final integration

**Files:**
- Modify: `snap/snapcraft.yaml:2`
- Modify: `.github/workflows/release.yml` (update snap version from tag)

- [ ] **Step 1: Make snap version dynamic from git tag**

In the `build-snap` job, add a step before the build to patch the version:

```yaml
  build-snap:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Set version from tag
        run: |
          VERSION=${GITHUB_REF_NAME#v}
          sed -i "s/^version: .*/version: '${VERSION}'/" snap/snapcraft.yaml
      - uses: snapcore/action-build@v1
        id: build
      - uses: actions/upload-artifact@v4
        with:
          name: geotui-snap
          path: ${{ steps.build.outputs.snap }}
```

- [ ] **Step 2: Verify the complete github-release job has all needs and files**

The final `github-release` job should look like:

```yaml
  github-release:
    needs:
      - build-python
      - build-binary
      - build-deb
      - build-rpm
      - build-appimage
      - build-snap
      - build-flatpak
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/download-artifact@v4
        with:
          path: artifacts/
      - name: List artifacts
        run: find artifacts/ -type f | sort
      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          generate_release_notes: true
          files: |
            artifacts/python-dist/*
            artifacts/geotui-linux-amd64/*
            artifacts/geotui-macos-amd64/*
            artifacts/geotui-macos-arm64/*
            artifacts/geotui-windows-amd64.exe/*
            artifacts/geotui-deb/*
            artifacts/geotui-rpm/**/*
            artifacts/geotui-appimage/*
            artifacts/geotui-snap/*
            artifacts/geotui-flatpak/*
```

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/release.yml snap/snapcraft.yaml
git commit -m "ci: finalize release workflow with all package targets"
```
