# F5 Copy-to-Publish Design

**Date:** 2026-05-21
**Status:** Approved

## Overview

Replace the F2 menu-driven bulk publish with Midnight Commander's natural
F5 copy paradigm: select a folder of spatial files on the left pane, select
a workspace or store on the right GeoServer pane, press F5 to copy/publish.

## Workflow

1. User navigates to a folder containing spatial data in the left pane
2. User selects a workspace or store in the right GeoServer tree
3. User presses F5 (Copy)
4. GeoTUI scans the folder, groups files by format, uploads concurrently
5. Progress shown in status bar + tree auto-refreshes as layers appear
6. PDF + JSON report generated automatically on completion

## Source Detection

Scan the selected folder for all supported spatial formats:

| Format | Detection | Store Type |
|--------|-----------|------------|
| Shapefile | .shp + .shx + .dbf (+ optional .prj, .cpg, etc.) | Directory of spatial files |
| GeoPackage | .gpkg | GeoPackage |
| GeoTIFF | .tif / .tiff | GeoTIFF |

- Incomplete shapefile bundles (missing .shx or .dbf) are reported as
  warnings and skipped
- Non-spatial files are ignored
- Subdirectories are not recursed (user explicitly selects the folder)

## Target Resolution

| Selected Node | Behaviour |
|---------------|-----------|
| Store | Publish directly into that store |
| Workspace | Auto-create one store per format type found |
| Nothing / root | Show error: "Select a workspace or store" |

Auto-created store naming: `{folder_name}_{format}` where format is
`shapefiles`, `geopackage`, or `geotiff`.

If the auto-created store name already exists and is the correct type,
reuse it (idempotent). If it exists but is a different type, suffix with
a number.

## Upload

- Concurrent uploads bounded by `asyncio.Semaphore` (default: 4)
- Retry with exponential backoff on transient failures (HTTP 5xx, timeouts)
- Each published layer gets:
  - WMS and WFS enabled
  - Bounding box / extents calculated (via GeoServer's auto-recalculate)
  - Layer name derived from filename (basename without extension)
- Name collision detection before upload begins

## Progress Display

- **Status bar** (bottom of GeoServer pane): `Publishing 3/47: roads.shp`
- **Tree**: auto-refreshes periodically as layers appear on the server
- Both update in real-time during the upload

## Reporting

After every F5 copy, automatically generate:

- **PDF report** at `~/.local/share/geotui/reports/publish-{timestamp}.pdf`
  with Kartoza + GeoTUI dual branding, job summary, color-coded detail
  table, and summary statistics
- **JSON report** alongside for programmatic consumption
- **Notification** in TUI with summary (created/updated/failed) and
  report path

## Code Changes

### Modified Files

| File | Change |
|------|--------|
| `src/geotui/app.py` | Wire F5 `action_copy()` to check pane context and delegate |
| `src/geotui/publisher.py` | Extend to handle GeoPackage and GeoTIFF, add format grouping |
| `src/geotui/client.py` | Add methods for GeoPackage/GeoTIFF upload, layer extent recalculation, WMS/WFS enable |
| `src/geotui/widgets/geoserver_tree.py` | Add `action_copy_from_local()`, remove bulk publish form, add periodic tree refresh during upload |
| `src/geotui/widgets/file_pane.py` | Add method to get currently selected path |
| `src/geotui/screens/context_menu.py` | Remove "Bulk Publish Shapefiles" from F2 menu |

### New Concepts

- `SpatialFileGroup` dataclass: groups discovered files by format type,
  holds the list of files and their target store type
- `discover_spatial_files(directory)` replaces `discover_bundles()`:
  returns groups for all supported formats, not just shapefiles

### Removed

- "Bulk Publish Shapefiles" F2 menu item (replaced by F5)
- The 5-field publish config form in the action panel

## Error Handling

- No connection active: "Connect to a GeoServer first (F9)"
- Left pane has no folder selected: "Select a folder in the left pane"
- Right pane has no workspace/store selected: "Select a workspace or store"
- No spatial files found: "No supported spatial files found in {folder}"
- Workspace/store creation fails: abort with error notification
- Individual file upload fails: log error, continue with remaining files
- All shown as red error notifications (no silent failures)

## Testing

- Unit tests for format detection (shapefile, gpkg, geotiff grouping)
- Unit tests for target resolution (workspace vs store selection)
- Unit tests for store auto-naming
- BDD feature: `f5_copy_publish.feature`
- Integration tests against docker GeoServer
