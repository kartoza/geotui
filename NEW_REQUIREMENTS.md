# Requirements Specification: GeoServer Bulk Shapefile Publisher

**Document version:** 0.1 (draft)
**Author:** Tim Sutton
**Status:** For review by the development team

---

## 1. Purpose

This document specifies the requirements for a software component that automates the publication of large collections of ESRI Shapefiles (in the order of 4,000 files) to a GeoServer instance via the GeoServer REST API. The component must support both initial bulk publication and idempotent re-runs that update existing layers in place.

## 2. Scope

### 2.1 In scope

- Authenticated interaction with a target GeoServer instance over its REST API.
- Discovery of shapefile sets from a local or mounted source directory.
- Creation and verification of a single target workspace and a single target datastore (of type “Directory of spatial files”).
- Upload of shapefile bundles (`.shp`, `.shx`, `.dbf`, `.prj` and optional siblings such as `.cpg`, `.qix`, `.sbn`, `.sbx`) as ZIP archives.
- Layer publication, including assignment of a default style where supplied.
- Idempotent behaviour: re-running the tool against the same source should result in updated layers, not duplicates or errors.
- Export of the resulting GeoServer configuration so that it can be replayed on a second instance.
- Structured logging and a final run report.

### 2.2 Out of scope

- Conversion of non-shapefile formats (GeoPackage, GeoJSON, etc.).
- Generation of custom SLD styles. The tool consumes pre-existing SLDs only.
- Migration of tile caches (GWC) or seeded tile layers.
- User and role administration on GeoServer.
- Long-term scheduling or orchestration; this is a command-line utility intended to be invoked by an operator or a CI pipeline.

## 3. Definitions

| Term             | Meaning                                                                                                                                                              |
| ---------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Shapefile bundle | The set of files that together constitute one logical shapefile (minimum: `.shp`, `.shx`, `.dbf`; usually also `.prj`).                                              |
| Layer            | A published GeoServer resource, addressable as `workspace:layername` via OGC services.                                                                               |
| Workspace        | A GeoServer-level namespace that groups datastores and layers.                                                                                                       |
| Datastore        | A configured connection to a backing data source. In this spec, always a “Directory of spatial files” datastore pointing at a server-side path managed by GeoServer. |
| Source directory | The local or mounted directory tree from which shapefile bundles are discovered.                                                                                     |
| Target GeoServer | The remote GeoServer instance that receives the publication.                                                                                                         |

## 4. Functional requirements

### 4.1 Configuration

**FR-1.** The tool must accept its configuration from a single YAML or TOML file, the path to which is passed as a command-line argument.

**FR-2.** The configuration file must support, at minimum, the following keys:

- `geoserver.base_url` — e.g. `https://geoserver.example.org/geoserver`
- `geoserver.username` and `geoserver.password` (or a reference to an environment variable / secret store)
- `geoserver.workspace` — target workspace name
- `geoserver.datastore` — target datastore name
- `source.directory` — local path containing shapefile bundles
- `source.recurse` — boolean, default `true`
- `source.naming` — strategy for deriving layer names (see FR-7)
- `styles.directory` — optional path to a directory of SLD files
- `styles.mapping` — optional explicit map of layer name → SLD file
- `run.dry_run` — boolean, default `false`
- `run.concurrency` — integer, default `4`
- `run.retry.max_attempts` — integer, default `3`
- `run.retry.backoff_seconds` — integer, default `5`

**FR-3.** Credentials must not be required to appear in the configuration file in plain text. The tool must support reading credentials from environment variables and from a referenced secrets file.

### 4.2 Source discovery

**FR-4.** The tool must scan `source.directory` and identify all complete shapefile bundles. A bundle is considered complete if at least the `.shp`, `.shx` and `.dbf` files are present and share the same basename in the same directory.

**FR-5.** When `source.recurse` is true, the scan must walk subdirectories. The directory structure of the source must not be reflected in the GeoServer layer hierarchy; all layers land in the single configured workspace.

**FR-6.** Incomplete bundles (missing mandatory components) must be reported as warnings and excluded from publication. They must not abort the run.

**FR-7.** Layer naming must be deterministic and configurable. Supported strategies:

- `basename` — use the shapefile basename as the layer name.
- `prefixed_basename` — prepend a configured prefix.
- `path_slug` — derive the name from the relative path within the source directory, replacing path separators with underscores, to avoid collisions across subdirectories.

The tool must detect name collisions before any upload begins and abort with a clear error listing the conflicts.

### 4.3 GeoServer preconditions

**FR-8.** Before any upload, the tool must verify that the target GeoServer is reachable and that the supplied credentials are valid. This is done by a `GET` to `/rest/about/version.json`.

**FR-9.** If the configured workspace does not exist, the tool must create it via `POST /rest/workspaces`.

**FR-10.** If the configured datastore does not exist within the workspace, the tool must create it as a “Directory of spatial files” datastore via `POST /rest/workspaces/{ws}/datastores`. If it does exist but is of a different type, the tool must abort with a clear error rather than reconfiguring it.

### 4.4 Publication

**FR-11.** For each discovered bundle, the tool must:

1. Construct a ZIP archive in a temporary directory containing the bundle’s component files at the root of the archive.
1. Determine whether a layer of the target name already exists within the target workspace (`GET /rest/layers/{workspace}:{layer}`).
1. If the layer does not exist, `PUT` the ZIP to `/rest/workspaces/{ws}/datastores/{ds}/file.shp?configure=first` (or equivalent) to publish it.
1. If the layer does exist, `PUT` the ZIP to the same endpoint with `update=overwrite` so that the underlying shapefile is replaced and the existing feature type configuration is preserved where possible.
1. If a style is mapped to this layer, assign it as the default style via `PUT /rest/layers/{ws}:{layer}` with the appropriate JSON body.

**FR-12.** The tool must process bundles concurrently up to `run.concurrency`. Concurrency must be bounded and configurable to protect the target GeoServer.

**FR-13.** Each individual upload must be retried up to `run.retry.max_attempts` with exponential backoff seeded by `run.retry.backoff_seconds` on transient failures (HTTP 5xx, network timeouts, connection resets). HTTP 4xx responses other than 408 and 429 must not be retried.

**FR-14.** The tool must honour `429 Too Many Requests` responses by respecting any `Retry-After` header before retrying.

### 4.5 Atomicity and consistency

**FR-15.** The team acknowledges that GeoServer’s REST API does not provide a transactional guarantee that an updated layer remains continuously available in its previous form until the new version is fully published. The specification accepts this limitation. The tool must, however:

- Process layers serially within a single bundle (the ZIP upload is a single REST call, which is the smallest atomic unit available).
- On failure of an update, leave clear log evidence and continue with remaining bundles.
- Provide an option `run.fail_fast` (default `false`) that aborts the entire run on the first non-retryable failure.

**FR-16.** True transactional row-level updates are out of scope. If transactional updates become a requirement in the future, this would be addressed by switching to a PostGIS-backed datastore and using WFS-T, and is noted here as a known follow-up.

### 4.6 Dry run

**FR-17.** When `run.dry_run` is `true`, the tool must perform discovery, validation, collision detection, and a connectivity check against GeoServer, but must not create workspaces, datastores or layers, and must not upload any files. The run report must clearly indicate that the run was a dry run.

### 4.7 Configuration export and replay

**FR-18.** The tool must provide a separate subcommand (`export`) that downloads the full configuration of the workspace from a source GeoServer and writes it to a local directory in a structured form. At minimum, the export must include:

- Workspace definition (`GET /rest/workspaces/{ws}.json`)
- Datastore definitions (`GET /rest/workspaces/{ws}/datastores.json` and per-store)
- Feature type definitions (`GET /rest/workspaces/{ws}/datastores/{ds}/featuretypes.json` and per-type)
- Layer definitions (`GET /rest/layers.json` filtered to the workspace)
- Styles referenced by these layers (`GET /rest/styles/{name}.sld` and the JSON metadata)

**FR-19.** The tool must provide a complementary subcommand (`import-config`) that recreates the same configuration on a target GeoServer instance from the exported bundle. This is intended to bring a second GeoServer into matching state without re-uploading the shapefile data, on the assumption that the shapefile data has been transferred to the target by other means (e.g. rsync of the data directory).

### 4.8 Reporting

**FR-20.** On completion, the tool must emit a run report in both human-readable form (stdout) and machine-readable form (JSON file, path configurable). The report must include:

- Total bundles discovered
- Bundles published successfully (with elapsed time per bundle)
- Bundles updated
- Bundles skipped (with reason)
- Bundles failed (with HTTP status and error body)
- Total wall-clock time
- Target GeoServer version

## 5. Non-functional requirements

**NFR-1. Idempotency.** Running the tool twice against the same source must produce the same end state on the GeoServer without errors on the second run.

**NFR-2. Observability.** All HTTP requests and responses must be logged at `DEBUG` level. At `INFO` level, the tool must emit one log line per bundle indicating its outcome. Logs must be structured (JSON option) for ingestion by log aggregators.

**NFR-3. Performance.** With `run.concurrency = 4` and an unloaded GeoServer on the same LAN, the tool should publish 4,000 small (<10 MB) shapefiles in under two hours. This is a target, not a hard guarantee.

**NFR-4. Resource use.** Temporary ZIP archives must be cleaned up after each upload, whether successful or not. Peak local disk use should not exceed `run.concurrency × largest_bundle_size × 2`.

**NFR-5. Portability.** The tool must run on Linux and macOS. A container image must be provided.

**NFR-6. Security.** Credentials must never appear in log output. The tool must support TLS verification against the target GeoServer and must allow a CA bundle to be supplied for instances using a private CA.

**NFR-7. Testability.** The interaction with the GeoServer REST API must be isolated behind an interface that can be substituted with a fake for unit tests. Integration tests must run against a containerised GeoServer in CI.

## 6. Error handling

**EH-1.** All error messages must include the layer or bundle in question, the HTTP method and path, the response status, and the first 1 KB of the response body.

**EH-2.** A failure to publish a single bundle must not, by default, abort the run.

**EH-3.** A failure to create the workspace or datastore must abort the run, because no useful work can follow.

**EH-4.** Unexpected exceptions must be caught at the top level and reported in the run report as failures attributed to the relevant bundle (or as a global failure if not bundle-specific).

## 7. Open questions

1. Should the tool also write a small metadata sidecar (JSON) per layer recording the source path and a checksum, to aid drift detection on subsequent runs?
1. Is preservation of layer-level metadata (title, abstract, keywords) required on update, or is it acceptable for GeoServer’s defaults to apply on first publish only?
1. Should the export/import subcommands round-trip GWC tile caching configuration as a follow-up, or is this firmly out of scope?
1. Confirm the target GeoServer version. The endpoints described above are stable across recent releases (2.20+), but the team should pin a minimum supported version.

## 8. Deliverables

1. Command-line tool with subcommands `publish`, `export`, and `import-config`.
1. Container image.
1. Sample configuration file with inline comments.
1. Integration test suite that runs against a GeoServer container in CI.
1. README covering installation, configuration, and the operator runbook for a 4,000-file publish.

## 9. Acceptance criteria

The component is accepted when:

- A 4,000-bundle source can be published end-to-end against a clean GeoServer with no manual intervention.
- A second run against the same source produces zero failures and zero duplicate layers.
- An `export` followed by an `import-config` against a second GeoServer reproduces the same workspace, datastores, feature types, layers, and default style assignments.
- The run report correctly accounts for every discovered bundle.
- All logged credentials are redacted.
