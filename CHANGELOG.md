# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0] - 2026-07-23

### Changed
- **F5 publish selection is precise.** F5 on a highlighted **file** publishes
  only that dataset (shapefile companions included); F5 on a highlighted
  **folder** publishes every valid dataset inside it. Press **Space** to
  tag/untag files for a non-contiguous multi-file publish. The publish engine
  now honours an explicit file list (`PublishConfig.source_files`) instead of
  re-scanning the whole directory, so it never uploads more than what you
  selected.
- **Connection edit form UX.** The Save/Cancel action bar is now pinned to the
  bottom of the detail panel and always visible (the fields scroll above it),
  so the apply action is no longer clipped off-screen on short terminals. Added
  a **Save & Connect** button that saves and immediately tests the connection.
  The master-vault controls are hidden while editing, and **"Change Password"**
  is relabelled **"Change Master Password"** so it can't be mistaken for the
  connection's apply button.
- **Positive connection feedback.** A successful connection test now shows a
  clear "✓ Connected" notification and status line; failures show a labelled
  "✗ Connection failed" message.

### Added
- **VRT (GDAL/OGR Virtual Format) publishing via F5.** GeoTUI discovers
  `.vrt` files, parses them (with `defusedxml`, hardened against XXE/entity
  attacks) to classify raster (`<VRTDataset>` → coverage store) vs vector
  (`<OGRVRTDataSource>` → OGR datastore) and enumerate referenced sources. On
  publish it prompts whether to **bundle & upload** the `.vrt` plus its
  referenced files into the GeoServer data directory (via the Resource API) or
  point the store at data already on the **server filesystem**. GeoServer is
  probed for the GDAL / OGR extensions and warns if the required one is
  missing. New dependency: `defusedxml`.
- **GeoTIFF publishing** — the F5 copy-to-publish pipeline now uploads
  `.tif` / `.tiff` rasters to GeoServer. Each raster is published to its own
  auto-created coverage store via the `file.geotiff` REST endpoint, with the
  same concurrency, retry/back-off, dry-run, style-assignment and reporting
  behaviour as the shapefile path.
- `PublishConfig.format_type` field so `run_publish()` dispatches by spatial
  format (`shapefile` / `geotiff`).
- Raster discovery and naming helpers: `discover_rasters()` and
  `resolve_raster_names()`.

### Fixed
- Raster groups discovered by the UI are now routed to the raster upload path
  instead of being silently ignored by the shapefile-only publisher, making the
  README's "Shapefiles, GeoPackages, and GeoTIFFs via F5" claim accurate for
  GeoTIFF.
- **Master-password prompt loop** — decrypting connections while the vault was
  locked pushed a separate unlock screen per connection, stacking identical
  prompts that felt like the correct password was being rejected in a loop.
  The unlock prompt is now shown at most once at a time (`app._show_unlock`
  is idempotent).
- **Credential leak on locked save** — editing a connection while the vault was
  locked silently stored the GeoServer password in plaintext (or double-encrypted
  an existing token, breaking later decryption). The Settings screen now refuses
  to save credentials until the vault is unlocked.

## [1.1.0]

### Added
- Improved local GeoServer Docker management.

## [1.0.0]

### Added
- Initial release: dual-pane Midnight Commander-style TUI for GeoServer,
  multi-connection management, F5 copy-to-publish for shapefiles, PDF/JSON
  reports, i18n, and Kartoza branding.

[1.2.0]: https://github.com/kartoza/geotui/releases/tag/v1.2.0
[1.1.0]: https://github.com/kartoza/geotui/releases/tag/v1.1.0
[1.0.0]: https://github.com/kartoza/geotui/releases/tag/v1.0.0
