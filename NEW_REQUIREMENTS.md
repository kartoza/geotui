# Requirements: Bulk Shapefile Publisher Feature

**Document version:** 0.2 (adapted for GeoTUI)
**Author:** Tim Sutton
**Status:** For review

---

## 1. Purpose

This document specifies the requirements for a **Bulk Shapefile Publisher**
feature within GeoTUI. The feature automates the publication of large
collections of ESRI Shapefiles (in the order of 4,000 files) to a GeoServer
instance via the existing `GeoServerClient` REST API client. It must support
both initial bulk publication and idempotent re-runs that update existing
layers in place.

### 1.1 Integration with GeoTUI

This feature integrates with the existing GeoTUI architecture:

- **Connection**: Uses the active `Connection` from `ConfigManager` (already
  managed via the F9 settings screen). No separate connection config needed.
- **URL resolution**: Uses the existing `resolve_base_url()` for automatic
  `/geoserver` path detection.
- **Client**: Extends `GeoServerClient` with new methods for shapefile upload,
  style assignment, and layer checking. Reuses the shared `httpx.AsyncClient`.
- **UI**: Accessible via the F2 context menu on the GeoServer pane as a
  "Bulk Publish Shapefiles" action. Progress and results displayed inline in
  the GeoServer pane's action panel (no popups).
- **CLI**: Additionally available as a CLI subcommand (`geotui publish`) for
  headless/CI usage, using the same `Connection` and `GeoServerClient` code.

## 2. Scope

### 2.1 In scope

- Discovery of shapefile bundles from the local file pane's current directory
  (or a specified path in CLI mode).
- Creation and verification of a target workspace and datastore (of type
  "Directory of spatial files") using the existing `create_workspace()` and
  `create_datastore()` client methods.
- Upload of shapefile bundles (`.shp`, `.shx`, `.dbf`, `.prj` and optional
  siblings) as ZIP archives.
- Layer publication, including assignment of a default SLD style.
- Idempotent behaviour: re-running produces updates, not duplicates.
- Export/import of GeoServer workspace configuration for replication.
- Structured logging and a run report.
- Dry-run mode for validation without modification.

### 2.2 Out of scope

- Conversion of non-shapefile formats (handled separately via store types).
- Generation of custom SLD styles. Only pre-existing SLDs are consumed.
- Migration of tile caches (GWC).
- User and role administration on GeoServer.

## 3. Definitions

| Term | Meaning |
|------|---------|
| Shapefile bundle | Set of files constituting one logical shapefile (minimum: `.shp`, `.shx`, `.dbf`; usually also `.prj`). |
| Layer | A published GeoServer resource, addressable as `workspace:layername`. |
| Workspace | A GeoServer namespace grouping datastores and layers. |
| Datastore | A configured connection to a data source. Here, a "Directory of spatial files" datastore. |
| Source directory | The local directory from which shapefile bundles are discovered (visible in the left pane). |
| Active connection | The currently selected GeoServer connection in GeoTUI's settings. |

## 4. Functional requirements

### 4.1 Configuration

**FR-BP-1.** In TUI mode, the publish operation uses:
- The **active connection** from `ConfigManager` for GeoServer credentials
  and URL (no separate config file needed).
- A **publish configuration** dialog in the action panel specifying: target
  workspace name, target datastore name, source directory, naming strategy,
  optional styles directory, concurrency, and dry-run toggle.

**FR-BP-2.** In CLI mode (`geotui publish`), configuration is accepted from
a TOML file or command-line arguments. The TOML file supports:

```toml
[geoserver]
connection = "My GeoServer"  # Name of a saved connection from config.json

[source]
directory = "/data/shapefiles"
recurse = true
naming = "basename"  # basename | prefixed_basename | path_slug

[styles]
directory = "/data/styles"  # Optional

[run]
workspace = "my_workspace"
datastore = "my_datastore"
dry_run = false
concurrency = 4
retry_max_attempts = 3
retry_backoff_seconds = 5
fail_fast = false
```

**FR-BP-3.** Credentials are never stored in the publish config. They come
from the existing `Connection` in `~/.config/geotui/config.json`.

### 4.2 Source discovery

**FR-BP-4.** The publisher scans the source directory and identifies all
complete shapefile bundles (`.shp` + `.shx` + `.dbf` present with same
basename).

**FR-BP-5.** When `recurse` is true, subdirectories are walked. All layers
land in the single configured workspace regardless of source directory
structure.

**FR-BP-6.** Incomplete bundles are reported as warnings and excluded. They
do not abort the run.

**FR-BP-7.** Layer naming strategies:
- `basename` -- shapefile basename as layer name.
- `prefixed_basename` -- configured prefix prepended.
- `path_slug` -- relative path with separators replaced by underscores.

Name collisions are detected before upload and abort with a clear error.

### 4.3 GeoServer preconditions

**FR-BP-8.** Before upload, verify the connection using the existing
`test_connection()` function.

**FR-BP-9.** If the workspace does not exist, create it via the existing
`GeoServerClient.create_workspace()`.

**FR-BP-10.** If the datastore does not exist, create it via the existing
`GeoServerClient.create_datastore()` with type "Directory of spatial files".
If it exists but is a different type, abort with a clear error.

### 4.4 Publication

**FR-BP-11.** For each bundle:
1. Create a ZIP archive of the bundle's component files.
2. Check if the layer already exists (`GET /rest/layers/{ws}:{layer}`).
3. If new, `PUT` the ZIP to publish it.
4. If existing, `PUT` with `update=overwrite` to replace.
5. If a style is mapped, assign it as default.

**FR-BP-12.** Bundles are processed concurrently up to the configured
concurrency limit using `asyncio.Semaphore`.

**FR-BP-13.** Retries with exponential backoff on transient failures
(HTTP 5xx, timeouts). HTTP 4xx (except 408/429) are not retried.

**FR-BP-14.** Honour `429 Too Many Requests` with `Retry-After`.

### 4.5 Atomicity and consistency

**FR-BP-15.** On failure of a single bundle, log the error and continue
with remaining bundles (unless `fail_fast` is true).

**FR-BP-16.** Transactional row-level updates are out of scope.

### 4.6 Dry run

**FR-BP-17.** When `dry_run` is true, perform discovery, validation, and
connectivity check but make no modifications to GeoServer. The report
clearly indicates dry-run mode.

### 4.7 Configuration export and replay

**FR-BP-18.** Export subcommand/action (`geotui export` or F2 menu):
downloads workspace config (workspace, datastores, feature types, layers,
referenced styles) to a local directory using the existing `GeoServerClient`
fetch methods.

**FR-BP-19.** Import subcommand/action (`geotui import-config` or F2 menu):
recreates configuration on a target GeoServer from the exported bundle.

### 4.8 TUI integration

**FR-BP-20.** In TUI mode, the bulk publish action:
- Is accessible from the F2 GeoServer context menu as "Bulk Publish Shapefiles".
- Shows a configuration form in the action panel (workspace, datastore,
  source directory from left pane path, naming strategy, concurrency).
- Displays a progress indicator during upload (bundle X of Y).
- Shows the run report inline in the action panel on completion.
- Does not use popups.

**FR-BP-21.** Export and import actions are also available in the F2 menu.

### 4.9 Reporting

**FR-BP-22.** On completion, a detailed PDF report must be generated. The
report is saved to a configurable output path (defaults to
`~/.local/share/geotui/reports/publish-{timestamp}.pdf`).

**FR-BP-23.** The PDF report must contain three sections:

**Section 1: Job Summary Header**

| Field | Example |
|-------|---------|
| Report Title | "GeoTUI Bulk Publish Report" |
| Generated | 2026-05-20 14:32:05 UTC |
| GeoServer URL | https://geo.example.com/geoserver |
| GeoServer Version | 2.24.2 |
| Username | admin |
| Workspace | my_workspace |
| Datastore | my_datastore |
| Source Directory | /data/shapefiles |
| Naming Strategy | basename |
| Concurrency | 4 |
| Dry Run | No |

The header should include both the Kartoza logo and the GeoTUI application
logo/name, establishing dual branding throughout the report.

**Section 2: File Detail Table**

A table listing every discovered shapefile bundle with columns:

| Column | Description |
|--------|-------------|
| # | Row number |
| Layer Name | Derived layer name |
| Source Path | Relative path to the .shp file |
| Action | `CREATE`, `UPDATE`, or `SKIP` |
| Status | `SUCCESS`, `ERROR`, or `DRY_RUN` |
| File Size | Total bundle size (all component files) |
| Upload Time | Duration of the upload in seconds |
| Error Detail | Error message if failed, empty if successful |

Rows should be color-coded: green for success, red for errors, grey for
skipped, blue for dry-run. The table must handle 4,000+ rows across
multiple pages with repeating column headers.

**Section 3: Summary Footer**

| Metric | Value |
|--------|-------|
| Total Bundles Discovered | 4,127 |
| Created Successfully | 4,100 |
| Updated Successfully | 15 |
| Skipped (incomplete) | 8 |
| Failed | 4 |
| Total Data Uploaded | 2.3 GB |
| Total Wall-Clock Time | 1h 42m 17s |
| Average Upload Time | 1.48s |
| Fastest Upload | 0.12s |
| Slowest Upload | 34.7s |

Followed by dual branding footer: GeoTUI logo/version on the left,
"Made with :heart: by Kartoza" on the right, with links to the GitHub
repo and kartoza.com.

**FR-BP-24.** In addition to the PDF, a machine-readable JSON report must
be written alongside it (`publish-{timestamp}.json`) containing the same
data for programmatic consumption.

**FR-BP-25.** In TUI mode, a summary of the report is displayed inline in
the action panel on completion, with the PDF path shown for the user to
open. In CLI mode, the summary is printed to stdout.

## 5. Non-functional requirements

**NFR-BP-1. Idempotency.** Running twice against the same source produces
the same end state with no errors on the second run.

**NFR-BP-2. Observability.** HTTP requests logged at DEBUG. One log line
per bundle at INFO. Structured JSON logging option for CLI mode.

**NFR-BP-3. Performance.** 4,000 small shapefiles published in under two
hours at concurrency=4 on a LAN. (Target, not guarantee.)

**NFR-BP-4. Resource use.** Temporary ZIPs cleaned up after each upload.
Peak disk use bounded by `concurrency * largest_bundle * 2`.

**NFR-BP-5. Portability.** Runs on Linux, macOS, Windows (PowerShell)
via the existing cross-platform support.

**NFR-BP-6. Security.** Credentials never in logs. TLS verification
enforced (already handled by `GeoServerClient`). Custom CA bundle
support via `REQUESTS_CA_BUNDLE` or `SSL_CERT_FILE` environment variables.

**NFR-BP-7. Testability.** Publisher logic isolated behind
`GeoServerClient` which can be mocked. Integration tests against a
containerised GeoServer in CI (docker-compose with GeoServer image).

## 6. Error handling

**EH-BP-1.** Error messages include: bundle name, HTTP method/path,
response status, first 1KB of response body.

**EH-BP-2.** Single bundle failure does not abort the run by default.

**EH-BP-3.** Workspace/datastore creation failure aborts the run.

**EH-BP-4.** Unexpected exceptions caught at top level and reported in
the run report.

## 7. Open questions

1. Should a metadata sidecar (JSON) be written per layer for drift
   detection on subsequent runs?
2. Should layer metadata (title, abstract, keywords) be preserved on
   update, or accept GeoServer defaults on first publish only?
3. Should export/import include GWC tile caching configuration?
4. Minimum supported GeoServer version? (Endpoints stable since 2.20+.)
5. In TUI mode, should the left pane auto-navigate to the source
   directory when starting a bulk publish?

## 8. Deliverables

1. `src/geotui/publisher.py` -- bulk publish engine using `GeoServerClient`.
2. `src/geotui/report.py` -- PDF and JSON report generation (using
   `reportlab` or `fpdf2` for PDF rendering with Kartoza branding).
3. `src/geotui/screens/publish.py` -- TUI publish action panel (or
   integrated into `geoserver_tree.py` action panel).
4. CLI subcommands: `geotui publish`, `geotui export`, `geotui import-config`.
5. Publish config TOML schema documented in mkdocs.
6. Integration test suite with containerised GeoServer (`docker-compose.yml`).
7. BDD features: `bulk_publish.feature`, `export_import.feature`,
   `publish_report.feature`.
8. Updated SPECIFICATION.md, PACKAGES.md, README.md.
9. `fpdf2` added to dependencies (lightweight PDF generation, no system
   deps, cross-platform).

## 9. Acceptance criteria

The feature is accepted when:

- 4,000 shapefile bundles can be published end-to-end against a clean
  GeoServer with no manual intervention (CLI or TUI).
- A second run produces zero failures and zero duplicate layers.
- Export followed by import on a second GeoServer reproduces the same
  workspace, datastores, feature types, layers, and style assignments.
- A PDF report is generated containing the job summary header, a
  complete file detail table (all 4,000+ rows with correct pagination),
  and the summary footer with accurate statistics.
- A JSON report is generated alongside the PDF with identical data.
- The run report correctly accounts for every discovered bundle.
- All logged credentials are redacted (including in PDF/JSON reports).
- All existing GeoTUI tests continue to pass.
