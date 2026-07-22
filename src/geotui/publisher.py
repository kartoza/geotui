"""Bulk shapefile publisher engine for GeoTUI.

Provides shapefile discovery, naming strategy resolution, and publish
configuration dataclasses used by the upload execution engine.
"""

from __future__ import annotations

import asyncio
import io
import logging
import time
import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from geotui.client import GeoServerClient, test_connection
from geotui.config import Connection
from geotui.vrt import InvalidVRTError, VRTInfo, parse_vrt

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SHAPEFILE_REQUIRED: frozenset[str] = frozenset({".shp", ".shx", ".dbf"})
SHAPEFILE_OPTIONAL: frozenset[str] = frozenset(
    {".prj", ".cpg", ".qix", ".sbn", ".sbx", ".fix", ".qpj"}
)
SHAPEFILE_ALL: frozenset[str] = SHAPEFILE_REQUIRED | SHAPEFILE_OPTIONAL


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class NamingStrategy(str, Enum):
    """Strategy for deriving a GeoServer layer name from a shapefile stem."""

    BASENAME = "basename"
    """Use the bare filename stem, e.g. ``roads``."""

    PREFIXED_BASENAME = "prefixed_basename"
    """Prepend a user-supplied prefix to the stem, e.g. ``geo_roads``."""

    PATH_SLUG = "path_slug"
    """Build a slug from the relative path components joined by ``_``,
    e.g. ``subdir_roads``.  This guarantees uniqueness across nested
    directories."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShapefileBundle:
    """All component files that make up a single shapefile dataset."""

    name: str
    """The stem of the ``.shp`` file (without extension)."""

    directory: Path
    """Absolute path of the directory that contains the component files."""

    files: tuple[Path, ...]
    """All component files belonging to this bundle (including optional ones)."""

    @property
    def total_size(self) -> int:
        """Sum of byte sizes of all component files."""
        return sum(f.stat().st_size for f in self.files if f.exists())

    def to_zip(self, dest: Path | None = None) -> bytes:
        """Create a ZIP archive of all bundle component files.

        When *dest* is provided the archive is also written to that path.
        Always returns the raw ZIP bytes.

        Args:
            dest: Optional path to write the ZIP file.  The parent directory
                is created if it does not exist.

        Returns:
            Raw ZIP archive bytes.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for component in self.files:
                zf.write(component, component.name)
        data = buf.getvalue()
        if dest is not None:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
        return data


@dataclass(frozen=True)
class SpatialFile:
    """A single spatial file (GeoPackage, GeoTIFF, etc.)."""

    name: str
    """The file stem (without extension), e.g. ``parcels``."""

    path: Path
    """Absolute path to the file."""

    size: int
    """File size in bytes."""

    @classmethod
    def from_path(cls, path: Path) -> SpatialFile:
        """Construct a :class:`SpatialFile` from a filesystem path."""
        return cls(name=path.stem, path=path, size=path.stat().st_size)


@dataclass
class SpatialFileGroup:
    """A collection of spatial files sharing the same format type."""

    format_type: str
    """Logical format identifier, e.g. ``"shapefile"``, ``"geopackage"``,
    ``"geotiff"``."""

    store_type: str
    """GeoServer store type string for this format."""

    store_category: str
    """Broad category used for UI grouping."""

    files: list[SpatialFile | ShapefileBundle]
    """List of :class:`SpatialFile` or :class:`ShapefileBundle` instances."""

    @property
    def total_size(self) -> int:
        """Sum of byte sizes of all files in the group."""
        return sum(
            f.total_size if hasattr(f, "total_size") else f.size for f in self.files
        )


@dataclass
class BundleResult:
    """Outcome of publishing a single :class:`ShapefileBundle`."""

    layer_name: str
    """The GeoServer layer name that was (or would be) created/updated."""

    source_path: Path
    """Path to the ``.shp`` file for this bundle."""

    action: str
    """One of ``"create"``, ``"update"``, or ``"skip"``."""

    status: str
    """``"ok"``, ``"dry_run"``, ``"error"``, or ``"skipped"``."""

    file_size: int = 0
    """Total bytes uploaded (0 if dry-run or skipped)."""

    upload_time: float = 0.0
    """Wall-clock seconds taken for the upload."""

    error: str | None = None
    """Human-readable error message if *status* is ``"error"``."""


@dataclass
class PublishConfig:
    """Configuration for a bulk shapefile publish operation."""

    workspace: str
    """Target GeoServer workspace."""

    datastore: str
    """Target GeoServer datastore within *workspace*."""

    source_directory: Path
    """Root directory to scan for shapefiles."""

    format_type: str = "shapefile"
    """Spatial format to publish: ``"shapefile"``, ``"geopackage"``,
    ``"geotiff"`` or ``"vrt"``.  Determines which discovery and upload path
    :func:`run_publish` uses.  Defaults to ``"shapefile"`` for backwards
    compatibility."""

    vrt_mode: str = "bundle"
    """How VRT source files are handled: ``"bundle"`` uploads the ``.vrt`` and
    every file it references into the GeoServer data directory; ``"server_path"``
    assumes the referenced data already exists on the server filesystem."""

    naming: NamingStrategy = NamingStrategy.BASENAME
    """Strategy for deriving layer names from shapefile stems."""

    prefix: str = ""
    """Prefix applied when *naming* is :attr:`NamingStrategy.PREFIXED_BASENAME`."""

    styles_directory: Path | None = None
    """Optional directory containing SLD style files to associate with layers."""

    styles_mapping: dict[str, str] = field(default_factory=dict)
    """Explicit ``{layer_name: style_name}`` overrides."""

    recurse: bool = False
    """Whether to scan *source_directory* recursively."""

    concurrency: int = 4
    """Number of concurrent upload workers."""

    dry_run: bool = False
    """If ``True``, discover and plan but do not perform any uploads."""

    retry_max_attempts: int = 3
    """Maximum upload retry attempts per bundle."""

    retry_backoff_seconds: float = 2.0
    """Base back-off delay (seconds) between retry attempts."""

    fail_fast: bool = False
    """Abort the entire batch on the first upload failure."""


@dataclass
class PublishReport:
    """Summary report produced after a bulk publish run."""

    config: PublishConfig
    geoserver_url: str = ""
    geoserver_version: str = ""
    username: str = ""
    results: list[BundleResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    wall_clock_seconds: float = 0.0

    # ------------------------------------------------------------------
    # Computed properties (counts)
    # ------------------------------------------------------------------

    @property
    def created(self) -> int:
        """Number of layers successfully created."""
        return sum(1 for r in self.results if r.action == "create" and r.status == "ok")

    @property
    def updated(self) -> int:
        """Number of layers successfully updated."""
        return sum(1 for r in self.results if r.action == "update" and r.status == "ok")

    @property
    def skipped(self) -> int:
        """Number of layers skipped (including dry-run)."""
        return sum(1 for r in self.results if r.status in ("skipped", "DRY_RUN"))

    @property
    def failed(self) -> int:
        """Number of layers that failed to upload."""
        return sum(1 for r in self.results if r.status == "error")

    @property
    def total_uploaded_bytes(self) -> int:
        """Total bytes uploaded across all successful bundles."""
        return sum(r.file_size for r in self.results)


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------


def discover_bundles(
    directory: Path,
    *,
    recurse: bool = False,
) -> tuple[list[ShapefileBundle], list[str]]:
    """Scan *directory* for shapefile bundles.

    A bundle is considered **complete** when the three required sidecar files
    (``.shp``, ``.shx``, ``.dbf``) are all present alongside the ``.shp``
    file.  Incomplete bundles (missing any required sidecar) produce a warning
    string but are not returned.

    Parameters
    ----------
    directory:
        Root directory to scan.
    recurse:
        When ``True``, descend into sub-directories.

    Returns
    -------
    tuple[list[ShapefileBundle], list[str]]
        A pair of ``(complete_bundles, warning_messages)``.
    """
    bundles: list[ShapefileBundle] = []
    warnings: list[str] = []

    pattern = "**/*.shp" if recurse else "*.shp"

    for shp_path in sorted(directory.glob(pattern)):
        stem = shp_path.stem
        parent = shp_path.parent

        missing = [
            ext
            for ext in sorted(SHAPEFILE_REQUIRED - {".shp"})
            if not (parent / f"{stem}{ext}").exists()
        ]

        if missing:
            warnings.append(
                f"Incomplete bundle '{stem}' in {parent}: missing {', '.join(missing)}"
            )
            continue

        # Collect all files that exist for this stem (required + optional).
        component_files: list[Path] = []
        for ext in sorted(SHAPEFILE_ALL):
            candidate = parent / f"{stem}{ext}"
            if candidate.exists():
                component_files.append(candidate)

        bundles.append(
            ShapefileBundle(
                name=stem,
                directory=parent,
                files=tuple(component_files),
            )
        )

    return bundles, warnings


# ---------------------------------------------------------------------------
# Multi-format discovery constants
# ---------------------------------------------------------------------------

_GEOTIFF_EXTENSIONS: frozenset[str] = frozenset({".tif", ".tiff"})
_VRT_EXTENSIONS: frozenset[str] = frozenset({".vrt"})

_FORMAT_STORE_MAP: dict[str, tuple[str, str]] = {
    "shapefile": ("Directory of spatial files (shapefiles)", "vector"),
    "geopackage": ("GeoPackage", "vector"),
    "geotiff": ("GeoTIFF", "raster"),
    # A .vrt may be raster or vector; the kind is resolved per-file at publish
    # time by parsing the XML, so the group is a single "mixed" category.
    "vrt": ("VRT", "mixed"),
}


def discover_spatial_files(
    directory: Path,
) -> tuple[list[SpatialFileGroup], list[str]]:
    """Scan *directory* (non-recursively) for all supported spatial formats.

    Discovers shapefiles (via :func:`discover_bundles`), GeoPackage (``.gpkg``),
    and GeoTIFF (``.tif`` / ``.tiff``) files.  Results are grouped by format.
    Empty format groups are omitted.

    Parameters
    ----------
    directory:
        Directory to scan (no recursion).

    Returns
    -------
    tuple[list[SpatialFileGroup], list[str]]
        A pair of ``(groups, warning_messages)``.  Warnings originate from
        incomplete shapefile bundles.
    """
    groups: list[SpatialFileGroup] = []

    # --- Shapefiles ---------------------------------------------------------
    shp_bundles, warnings = discover_bundles(directory, recurse=False)
    if shp_bundles:
        store_type, category = _FORMAT_STORE_MAP["shapefile"]
        groups.append(
            SpatialFileGroup(
                format_type="shapefile",
                store_type=store_type,
                store_category=category,
                files=list(shp_bundles),
            )
        )

    # --- GeoPackage ---------------------------------------------------------
    gpkg_files = sorted(directory.glob("*.gpkg"))
    if gpkg_files:
        store_type, category = _FORMAT_STORE_MAP["geopackage"]
        groups.append(
            SpatialFileGroup(
                format_type="geopackage",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in gpkg_files],
            )
        )

    # --- GeoTIFF ------------------------------------------------------------
    tif_files: list[Path] = []
    for ext in sorted(_GEOTIFF_EXTENSIONS):
        tif_files.extend(directory.glob(f"*{ext}"))
    tif_files.sort()
    if tif_files:
        store_type, category = _FORMAT_STORE_MAP["geotiff"]
        groups.append(
            SpatialFileGroup(
                format_type="geotiff",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in tif_files],
            )
        )

    # --- VRT (raster or vector) --------------------------------------------
    vrt_files = sorted(directory.glob("*.vrt"))
    if vrt_files:
        store_type, category = _FORMAT_STORE_MAP["vrt"]
        groups.append(
            SpatialFileGroup(
                format_type="vrt",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in vrt_files],
            )
        )

    return groups, warnings


def discover_spatial_files_from_paths(
    paths: list[Path],
) -> tuple[list[SpatialFileGroup], list[str]]:
    """Build spatial file groups from an explicit list of file paths.

    Shapefile components are grouped into bundles by stem.  GeoPackage and
    GeoTIFF files are grouped by format.  Shapefile companion files that
    are present on disk but missing from *paths* are included automatically.

    Parameters
    ----------
    paths:
        Explicit list of file paths (companions already expanded by caller).

    Returns
    -------
    tuple[list[SpatialFileGroup], list[str]]
        A pair of ``(groups, warning_messages)``.
    """
    groups: list[SpatialFileGroup] = []
    warnings: list[str] = []

    # Classify files by format
    shp_stems: dict[str, dict[str, Path]] = {}  # stem -> {ext: path}
    gpkg_files: list[Path] = []
    tif_files: list[Path] = []
    vrt_files: list[Path] = []

    for path in paths:
        if not path.is_file():
            continue
        suffix = path.suffix.lower()
        if suffix in SHAPEFILE_ALL:
            stem = path.stem
            shp_stems.setdefault(stem, {})[suffix] = path
        elif suffix == ".gpkg":
            gpkg_files.append(path)
        elif suffix in _GEOTIFF_EXTENSIONS:
            tif_files.append(path)
        elif suffix in _VRT_EXTENSIONS:
            vrt_files.append(path)

    # --- Shapefiles ---------------------------------------------------------
    shp_bundles: list[ShapefileBundle] = []
    for stem, ext_map in sorted(shp_stems.items()):
        # Check required files exist
        missing = [ext for ext in sorted(SHAPEFILE_REQUIRED) if ext not in ext_map]
        if missing:
            warnings.append(f"Incomplete bundle '{stem}': missing {', '.join(missing)}")
            continue
        component_files = sorted(ext_map.values(), key=lambda p: p.suffix)
        directory = component_files[0].parent
        shp_bundles.append(
            ShapefileBundle(
                name=stem,
                directory=directory,
                files=tuple(component_files),
            )
        )

    if shp_bundles:
        store_type, category = _FORMAT_STORE_MAP["shapefile"]
        groups.append(
            SpatialFileGroup(
                format_type="shapefile",
                store_type=store_type,
                store_category=category,
                files=list(shp_bundles),
            )
        )

    # --- GeoPackage ---------------------------------------------------------
    if gpkg_files:
        store_type, category = _FORMAT_STORE_MAP["geopackage"]
        groups.append(
            SpatialFileGroup(
                format_type="geopackage",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in sorted(gpkg_files)],
            )
        )

    # --- GeoTIFF ------------------------------------------------------------
    if tif_files:
        store_type, category = _FORMAT_STORE_MAP["geotiff"]
        groups.append(
            SpatialFileGroup(
                format_type="geotiff",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in sorted(tif_files)],
            )
        )

    # --- VRT (raster or vector) --------------------------------------------
    if vrt_files:
        store_type, category = _FORMAT_STORE_MAP["vrt"]
        groups.append(
            SpatialFileGroup(
                format_type="vrt",
                store_type=store_type,
                store_category=category,
                files=[SpatialFile.from_path(p) for p in sorted(vrt_files)],
            )
        )

    return groups, warnings


# ---------------------------------------------------------------------------
# Naming
# ---------------------------------------------------------------------------


def resolve_layer_names(
    bundles: list[ShapefileBundle],
    base_dir: Path,
    strategy: NamingStrategy,
    prefix: str = "",
) -> dict[ShapefileBundle, str]:
    """Derive a unique GeoServer layer name for each bundle.

    Parameters
    ----------
    bundles:
        The bundles returned by :func:`discover_bundles`.
    base_dir:
        The root directory used as the reference for relative path slugs.
    strategy:
        How to derive names (see :class:`NamingStrategy`).
    prefix:
        Applied only when *strategy* is
        :attr:`NamingStrategy.PREFIXED_BASENAME`.

    Returns
    -------
    dict[ShapefileBundle, str]
        Mapping from each bundle to its resolved layer name.

    Raises
    ------
    ValueError
        If the chosen strategy would produce duplicate layer names (collision).
    """
    result: dict[ShapefileBundle, str] = {}

    for bundle in bundles:
        if strategy is NamingStrategy.BASENAME:
            layer_name = bundle.name
        elif strategy is NamingStrategy.PREFIXED_BASENAME:
            layer_name = f"{prefix}{bundle.name}"
        elif strategy is NamingStrategy.PATH_SLUG:
            try:
                rel = bundle.directory.relative_to(base_dir)
                parts = [*list(rel.parts), bundle.name]
            except ValueError:
                parts = [bundle.name]
            # Filter out the trivial "." part produced by same-dir bundles.
            slug_parts = [p for p in parts if p not in (".", "")]
            layer_name = "_".join(slug_parts) if slug_parts else bundle.name
        else:
            layer_name = bundle.name  # pragma: no cover

        result[bundle] = layer_name

    # Detect collisions.
    names = list(result.values())
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)

    if duplicates:
        raise ValueError(
            f"Layer name collision detected with strategy '{strategy.value}': "
            f"{sorted(duplicates)}.  Use NamingStrategy.PATH_SLUG or add a "
            f"prefix to avoid duplicates."
        )

    return result


# ---------------------------------------------------------------------------
# Publish execution engine
# ---------------------------------------------------------------------------


async def run_publish(
    conn: Connection,
    config: PublishConfig,
    progress_callback: object = None,
) -> PublishReport:
    """Execute a bulk shapefile publish operation.

    Discovers bundles under *config.source_directory*, resolves layer names,
    verifies the GeoServer connection, then uploads each bundle concurrently
    (honouring *config.concurrency*).

    Args:
        conn: GeoServer connection to target.
        config: Publish configuration (workspace, datastore, options).
        progress_callback: Optional callable with signature
            ``(current: int, total: int, bundle_name: str) -> None``
            called before each upload attempt.

    Returns:
        A :class:`PublishReport` summarising the outcome of every bundle.
    """
    start = time.monotonic()

    # Raster (coverage) formats use a separate discovery and upload path.
    if config.format_type == "geotiff":
        return await _run_publish_rasters(conn, config, progress_callback, start)

    # VRT (raster or vector, resolved per-file) uses its own path.
    if config.format_type == "vrt":
        return await _run_publish_vrt(conn, config, progress_callback, start)

    # Discover bundles.
    bundles, disc_warnings = discover_bundles(
        config.source_directory, recurse=config.recurse
    )

    # Resolve layer names (may raise ValueError on collision).
    try:
        name_map = resolve_layer_names(
            bundles, config.source_directory, config.naming, config.prefix
        )
    except ValueError as exc:
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version="",
            username=conn.username,
            warnings=[*disc_warnings, str(exc)],
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    # Build style map: explicit overrides first, then auto-match by layer name.
    def _resolve_style(layer_name: str) -> str | None:
        if layer_name in config.styles_mapping:
            return config.styles_mapping[layer_name]
        if config.styles_directory:
            candidate = config.styles_directory / f"{layer_name}.sld"
            if candidate.exists():
                return layer_name
        return None

    # Build BundleResult entries for skipped (incomplete) bundles from warnings.
    skipped_results: list[BundleResult] = []
    for warning_msg in disc_warnings:
        name = ""
        if "'" in warning_msg:
            name = warning_msg.split("'")[1]
        skipped_results.append(
            BundleResult(
                layer_name=name,
                source_path=Path(name),
                action="skip",
                status="skipped",
                error=warning_msg,
            )
        )

    # Dry-run: return DRY_RUN results immediately without touching GeoServer.
    if config.dry_run:
        results = [
            BundleResult(
                layer_name=layer_name,
                source_path=bundle.directory / f"{bundle.name}.shp",
                action="create",
                status="DRY_RUN",
            )
            for bundle, layer_name in name_map.items()
        ]
        results.extend(skipped_results)
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version="",
            username=conn.username,
            results=results,
            warnings=list(disc_warnings),
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    # Verify connection before attempting any uploads.
    conn_result = await test_connection(conn)
    if not conn_result.success:
        results = [
            BundleResult(
                layer_name=layer_name,
                source_path=bundle.directory / f"{bundle.name}.shp",
                action="create",
                status="error",
                error=f"Connection failed: {conn_result.message}",
            )
            for bundle, layer_name in name_map.items()
        ]
        results.extend(skipped_results)
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version="",
            username=conn.username,
            results=results,
            warnings=list(disc_warnings),
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    # Upload via shared client.
    async with GeoServerClient(conn) as client:
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version=conn_result.version,
            username=conn.username,
            warnings=list(disc_warnings),
        )

        # Ensure workspace and datastore exist.
        if not await _ensure_workspace(client, config, report):
            report.wall_clock_seconds = time.monotonic() - start
            return report
        if not await _ensure_datastore(client, config, report):
            report.wall_clock_seconds = time.monotonic() - start
            return report

        semaphore = asyncio.Semaphore(config.concurrency)
        total = len(name_map)
        tasks = [
            _upload_bundle(
                client,
                config,
                bundle,
                layer_name,
                _resolve_style(layer_name),
                semaphore,
                index,
                total,
                progress_callback,
            )
            for index, (bundle, layer_name) in enumerate(name_map.items(), start=1)
        ]

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for outcome in task_results:
            if isinstance(outcome, RuntimeError):
                # fail_fast raised - remaining bundles show as error.
                break
            if isinstance(outcome, BaseException):
                logger.exception("Unexpected error in upload task: %s", outcome)
            else:
                report.results.append(outcome)

        # Append skipped (incomplete) bundles so they appear in the report.
        report.results.extend(skipped_results)

    report.wall_clock_seconds = time.monotonic() - start
    return report


async def _ensure_workspace(
    client: GeoServerClient,
    config: PublishConfig,
    report: PublishReport,
) -> bool:
    """Ensure the target workspace exists, creating it if necessary.

    Args:
        client: Connected GeoServerClient.
        config: Publish configuration.
        report: Report to append warnings to.

    Returns:
        ``True`` if the workspace is available, ``False`` on failure.
    """
    workspaces = await client.get_workspaces()
    ws_names = {ws.name for ws in workspaces}
    if config.workspace in ws_names:
        return True

    logger.info("Creating workspace '%s'", config.workspace)
    created = await client.create_workspace(config.workspace)
    if not created:
        report.warnings.append(f"Failed to create workspace '{config.workspace}'")
        return False
    return True


async def _ensure_datastore(
    client: GeoServerClient,
    config: PublishConfig,
    report: PublishReport,
) -> bool:
    """Ensure the target datastore exists and is of a compatible type.

    If the datastore does not exist it is created as a Shapefile datastore.
    If it exists but is not a Shapefile or Directory store the publish is
    aborted with a warning.

    Args:
        client: Connected GeoServerClient.
        config: Publish configuration.
        report: Report to append warnings to.

    Returns:
        ``True`` if the datastore is ready, ``False`` on type mismatch or
        creation failure.
    """
    store_type = await client.get_datastore_type(config.workspace, config.datastore)

    if store_type is not None:
        # Validate existing store is compatible with shapefile upload.
        compatible = {"Shapefile", "Directory of spatial files (shapefiles)"}
        if store_type not in compatible:
            report.warnings.append(
                f"Datastore '{config.datastore}' already exists with incompatible "
                f"type '{store_type}'. Expected one of {sorted(compatible)}."
            )
            return False
    # If the datastore doesn't exist yet, GeoServer will auto-create it
    # when the first shapefile ZIP is uploaded via the file.shp endpoint.
    # Pre-creating a "Directory of spatial files" store causes HTTP 500
    # because it conflicts with the file upload mechanism.
    return True


async def _upload_bundle(
    client: GeoServerClient,
    config: PublishConfig,
    bundle: ShapefileBundle,
    layer_name: str,
    style: str | None,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    progress_callback: object,
) -> BundleResult:
    """Upload a single shapefile bundle to GeoServer with retry logic.

    Args:
        client: Connected GeoServerClient.
        config: Publish configuration.
        bundle: The shapefile bundle to upload.
        layer_name: Resolved GeoServer layer name.
        style: Style name to assign after upload, or ``None``.
        semaphore: Concurrency limiter.
        index: 1-based position of this bundle in the batch (for progress).
        total: Total number of bundles in the batch.
        progress_callback: Optional progress callable.

    Returns:
        :class:`BundleResult` describing the outcome.

    Raises:
        RuntimeError: If *config.fail_fast* is ``True`` and the upload fails.
    """
    source_path = bundle.directory / f"{bundle.name}.shp"

    async with semaphore:
        if callable(progress_callback):
            progress_callback(index, total, bundle.name)

        exists = await client.layer_exists(config.workspace, layer_name)
        action = "update" if exists else "create"

        last_error: str = ""
        for attempt in range(config.retry_max_attempts):
            try:
                t0 = time.monotonic()
                zip_data = bundle.to_zip()
                success = await client.upload_shapefile(
                    config.workspace, config.datastore, zip_data, update=exists
                )
                elapsed = time.monotonic() - t0

                if success:
                    # configure=first only runs on store creation; if the layer
                    # was not auto-configured, create the featuretype explicitly.
                    if not await client.layer_exists(config.workspace, layer_name):
                        await client.create_featuretype(
                            config.workspace,
                            config.datastore,
                            bundle.name,
                            layer_name,
                        )
                    if style:
                        await client.assign_style(config.workspace, layer_name, style)
                    return BundleResult(
                        layer_name=layer_name,
                        source_path=source_path,
                        action=action,
                        status="ok",
                        file_size=len(zip_data),
                        upload_time=elapsed,
                    )

                last_error = (
                    f"HTTP {client._last_status_code}: "
                    f"{client._last_response_text[:200]}"
                )

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Attempt %d/%d failed for '%s': %s",
                    attempt + 1,
                    config.retry_max_attempts,
                    bundle.name,
                    last_error,
                )

            # Exponential backoff before next attempt.
            if attempt < config.retry_max_attempts - 1:
                backoff = config.retry_backoff_seconds * (2**attempt)
                await asyncio.sleep(backoff)

        result = BundleResult(
            layer_name=layer_name,
            source_path=source_path,
            action=action,
            status="error",
            error=last_error,
        )

        if config.fail_fast:
            raise RuntimeError(
                f"Upload failed for '{bundle.name}' and fail_fast is enabled: "
                f"{last_error}"
            )

        return result


# ---------------------------------------------------------------------------
# Raster (coverage) publish execution
# ---------------------------------------------------------------------------


def discover_rasters(
    directory: Path,
    *,
    recurse: bool = False,
) -> list[SpatialFile]:
    """Scan *directory* for GeoTIFF rasters.

    Parameters
    ----------
    directory:
        Root directory to scan.
    recurse:
        When ``True``, descend into sub-directories.

    Returns
    -------
    list[SpatialFile]
        Discovered GeoTIFF files, sorted by path.
    """
    matches: list[Path] = []
    for ext in sorted(_GEOTIFF_EXTENSIONS):
        pattern = f"**/*{ext}" if recurse else f"*{ext}"
        matches.extend(directory.glob(pattern))
    return [SpatialFile.from_path(p) for p in sorted(set(matches))]


def resolve_raster_names(
    rasters: list[SpatialFile],
    base_dir: Path,
    strategy: NamingStrategy,
    prefix: str = "",
) -> dict[SpatialFile, str]:
    """Derive a unique GeoServer coverage name for each raster.

    Mirrors :func:`resolve_layer_names` but operates on :class:`SpatialFile`
    instances.

    Raises
    ------
    ValueError
        If the chosen strategy would produce duplicate names (collision).
    """
    result: dict[SpatialFile, str] = {}

    for raster in rasters:
        if strategy is NamingStrategy.PREFIXED_BASENAME:
            layer_name = f"{prefix}{raster.name}"
        elif strategy is NamingStrategy.PATH_SLUG:
            try:
                rel = raster.path.parent.relative_to(base_dir)
                parts = [*list(rel.parts), raster.name]
            except ValueError:
                parts = [raster.name]
            slug_parts = [p for p in parts if p not in (".", "")]
            layer_name = "_".join(slug_parts) if slug_parts else raster.name
        else:  # BASENAME (and any unknown strategy)
            layer_name = raster.name
        result[raster] = layer_name

    names = list(result.values())
    seen: set[str] = set()
    duplicates: set[str] = set()
    for name in names:
        if name in seen:
            duplicates.add(name)
        seen.add(name)

    if duplicates:
        raise ValueError(
            f"Coverage name collision detected with strategy '{strategy.value}': "
            f"{sorted(duplicates)}.  Use NamingStrategy.PATH_SLUG or add a "
            f"prefix to avoid duplicates."
        )

    return result


async def _run_publish_rasters(
    conn: Connection,
    config: PublishConfig,
    progress_callback: object,
    start: float,
) -> PublishReport:
    """Execute a bulk GeoTIFF publish operation.

    Discovers ``.tif`` / ``.tiff`` files under *config.source_directory*,
    resolves coverage names, verifies the connection, then uploads each raster
    to its own coverage store (a GeoTIFF store maps to a single file).

    Args:
        conn: GeoServer connection to target.
        config: Publish configuration (``format_type`` must be ``"geotiff"``).
        progress_callback: Optional ``(current, total, name)`` progress callable.
        start: ``time.monotonic()`` timestamp captured by :func:`run_publish`.

    Returns:
        A :class:`PublishReport` summarising the outcome of every raster.
    """
    rasters = discover_rasters(config.source_directory, recurse=config.recurse)

    try:
        name_map = resolve_raster_names(
            rasters, config.source_directory, config.naming, config.prefix
        )
    except ValueError as exc:
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            username=conn.username,
            warnings=[str(exc)],
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    def _resolve_style(layer_name: str) -> str | None:
        if layer_name in config.styles_mapping:
            return config.styles_mapping[layer_name]
        if config.styles_directory:
            candidate = config.styles_directory / f"{layer_name}.sld"
            if candidate.exists():
                return layer_name
        return None

    # Dry-run: plan without touching GeoServer.
    if config.dry_run:
        results = [
            BundleResult(
                layer_name=layer_name,
                source_path=raster.path,
                action="create",
                status="DRY_RUN",
            )
            for raster, layer_name in name_map.items()
        ]
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            username=conn.username,
            results=results,
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    # Verify connection before attempting any uploads.
    conn_result = await test_connection(conn)
    if not conn_result.success:
        results = [
            BundleResult(
                layer_name=layer_name,
                source_path=raster.path,
                action="create",
                status="error",
                error=f"Connection failed: {conn_result.message}",
            )
            for raster, layer_name in name_map.items()
        ]
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            username=conn.username,
            results=results,
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    async with GeoServerClient(conn) as client:
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version=conn_result.version,
            username=conn.username,
        )

        # Coverage stores are auto-created on upload; only the workspace needs
        # to exist beforehand.
        if not await _ensure_workspace(client, config, report):
            report.wall_clock_seconds = time.monotonic() - start
            return report

        semaphore = asyncio.Semaphore(config.concurrency)
        total = len(name_map)
        tasks = [
            _upload_raster(
                client,
                config,
                raster,
                layer_name,
                _resolve_style(layer_name),
                semaphore,
                index,
                total,
                progress_callback,
            )
            for index, (raster, layer_name) in enumerate(name_map.items(), start=1)
        ]

        task_results = await asyncio.gather(*tasks, return_exceptions=True)

        for outcome in task_results:
            if isinstance(outcome, RuntimeError):
                # fail_fast raised - stop collecting remaining results.
                break
            if isinstance(outcome, BaseException):
                logger.exception("Unexpected error in raster upload task: %s", outcome)
            else:
                report.results.append(outcome)

    report.wall_clock_seconds = time.monotonic() - start
    return report


async def _upload_raster(
    client: GeoServerClient,
    config: PublishConfig,
    raster: SpatialFile,
    layer_name: str,
    style: str | None,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    progress_callback: object,
) -> BundleResult:
    """Upload a single GeoTIFF raster to GeoServer with retry logic.

    Each raster is uploaded to its own coverage store named *layer_name*; the
    ``file.geotiff`` endpoint auto-creates the store and configures the
    coverage.

    Args:
        client: Connected GeoServerClient.
        config: Publish configuration.
        raster: The GeoTIFF file to upload.
        layer_name: Resolved GeoServer coverage/store name.
        style: Style name to assign after upload, or ``None``.
        semaphore: Concurrency limiter.
        index: 1-based position of this raster in the batch (for progress).
        total: Total number of rasters in the batch.
        progress_callback: Optional progress callable.

    Returns:
        :class:`BundleResult` describing the outcome.

    Raises:
        RuntimeError: If *config.fail_fast* is ``True`` and the upload fails.
    """
    async with semaphore:
        if callable(progress_callback):
            progress_callback(index, total, raster.name)

        exists = await client.layer_exists(config.workspace, layer_name)
        action = "update" if exists else "create"

        last_error: str = ""
        for attempt in range(config.retry_max_attempts):
            try:
                t0 = time.monotonic()
                data = raster.path.read_bytes()
                success = await client.upload_geotiff(
                    config.workspace, layer_name, data, update=exists
                )
                elapsed = time.monotonic() - t0

                if success:
                    if style:
                        await client.assign_style(config.workspace, layer_name, style)
                    return BundleResult(
                        layer_name=layer_name,
                        source_path=raster.path,
                        action=action,
                        status="ok",
                        file_size=len(data),
                        upload_time=elapsed,
                    )

                last_error = (
                    f"HTTP {client._last_status_code}: "
                    f"{client._last_response_text[:200]}"
                )

            except Exception as exc:
                last_error = str(exc)
                logger.warning(
                    "Attempt %d/%d failed for raster '%s': %s",
                    attempt + 1,
                    config.retry_max_attempts,
                    raster.name,
                    last_error,
                )

            if attempt < config.retry_max_attempts - 1:
                backoff = config.retry_backoff_seconds * (2**attempt)
                await asyncio.sleep(backoff)

        result = BundleResult(
            layer_name=layer_name,
            source_path=raster.path,
            action=action,
            status="error",
            error=last_error,
        )

        if config.fail_fast:
            raise RuntimeError(
                f"Upload failed for raster '{raster.name}' and fail_fast is "
                f"enabled: {last_error}"
            )

        return result


# ---------------------------------------------------------------------------
# VRT (GDAL/OGR Virtual Format) publish execution
# ---------------------------------------------------------------------------


def discover_vrts(directory: Path, *, recurse: bool = False) -> list[SpatialFile]:
    """Scan *directory* for ``.vrt`` files (raster or vector).

    Args:
        directory: Root directory to scan.
        recurse: When ``True``, descend into sub-directories.

    Returns:
        Discovered VRT files as :class:`SpatialFile` instances, sorted by path.
    """
    pattern = "**/*.vrt" if recurse else "*.vrt"
    return [SpatialFile.from_path(p) for p in sorted(directory.glob(pattern))]


def _parse_vrt_entries(
    vrts: list[SpatialFile],
) -> tuple[list[tuple[VRTInfo, str]], list[str]]:
    """Parse each VRT, returning ``(info, layer_name)`` pairs and warnings."""
    entries: list[tuple[VRTInfo, str]] = []
    warnings: list[str] = []
    for sf in vrts:
        try:
            info = parse_vrt(sf.path)
        except InvalidVRTError as exc:
            warnings.append(str(exc))
            continue
        entries.append((info, sf.name))
    return entries, warnings


async def _run_publish_vrt(
    conn: Connection,
    config: PublishConfig,
    progress_callback: object,
    start: float,
) -> PublishReport:
    """Execute a VRT publish operation (raster and/or vector).

    Discovers ``.vrt`` files under *config.source_directory*, parses each to
    determine whether it is a raster (coverage store) or vector (OGR datastore)
    VRT, then publishes each according to *config.vrt_mode* ("bundle" uploads
    the referenced sources via the Resource API; "server_path" points the store
    at data already on the server).
    """
    vrts = discover_vrts(config.source_directory, recurse=config.recurse)
    entries, warnings = _parse_vrt_entries(vrts)

    if config.dry_run:
        results = [
            BundleResult(
                layer_name=name,
                source_path=info.path,
                action="create",
                status="DRY_RUN",
            )
            for info, name in entries
        ]
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            username=conn.username,
            results=results,
            warnings=warnings,
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    conn_result = await test_connection(conn)
    if not conn_result.success:
        results = [
            BundleResult(
                layer_name=name,
                source_path=info.path,
                action="create",
                status="error",
                error=f"Connection failed: {conn_result.message}",
            )
            for info, name in entries
        ]
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            username=conn.username,
            results=results,
            warnings=warnings,
        )
        report.wall_clock_seconds = time.monotonic() - start
        return report

    async with GeoServerClient(conn) as client:
        report = PublishReport(
            config=config,
            geoserver_url=conn.url,
            geoserver_version=conn_result.version,
            username=conn.username,
            warnings=list(warnings),
        )

        if not await _ensure_workspace(client, config, report):
            report.wall_clock_seconds = time.monotonic() - start
            return report

        # Warn early if the server lacks the extension a VRT kind needs.
        support = await client.get_extension_support()
        if any(info.kind == "raster" for info, _ in entries) and not support.get(
            "gdal"
        ):
            report.warnings.append(
                "GeoServer GDAL/ImageIO-Ext coverage extension not detected; "
                "raster VRT publishing may fail."
            )
        if any(info.kind == "vector" for info, _ in entries) and not support.get("ogr"):
            report.warnings.append(
                "GeoServer OGR datastore extension not detected; vector VRT "
                "publishing may fail."
            )

        # Note VRTs backed by remote sources (e.g. /vsis3/, /vsicurl/): the
        # data is not uploaded; the server's GDAL must resolve it.
        for info, name in entries:
            if info.remote_sources:
                report.warnings.append(
                    f"'{name}': {len(info.remote_sources)} remote source(s) "
                    f"(e.g. '{info.remote_sources[0]}') are read by the server's "
                    f"GDAL — ensure the driver and credentials are configured "
                    f"there. Nothing is uploaded for these."
                )

        semaphore = asyncio.Semaphore(config.concurrency)
        total = len(entries)
        tasks = [
            _publish_vrt_one(
                client, config, info, name, semaphore, index, total, progress_callback
            )
            for index, (info, name) in enumerate(entries, start=1)
        ]
        task_results = await asyncio.gather(*tasks, return_exceptions=True)
        for outcome in task_results:
            if isinstance(outcome, RuntimeError):
                break
            if isinstance(outcome, BaseException):
                logger.exception("Unexpected error in VRT upload task: %s", outcome)
            else:
                report.results.append(outcome)

    report.wall_clock_seconds = time.monotonic() - start
    return report


async def _bundle_upload_vrt(
    client: GeoServerClient,
    store_name: str,
    info: VRTInfo,
) -> tuple[str, list[str]]:
    """Upload a VRT and its referenced sources via the Resource API.

    Files are placed under ``data/vrt/{store_name}/`` in the GeoServer data
    directory, preserving each source's path relative to the ``.vrt`` so that
    ``relativeToVRT`` references still resolve.

    Returns:
        A ``(data_url, warnings)`` pair where *data_url* is the ``file:`` URL
        the store should point at.
    """
    base = f"data/vrt/{store_name}"
    vrt_dir = info.path.parent
    warnings: list[str] = []

    await client.upload_resource(
        f"{base}/{info.path.name}", info.path.read_bytes(), "application/xml"
    )

    for src in info.sources:
        # Remote sources (vsi/URL/DB) are resolved by the server's GDAL and
        # must not be bundled — the uploaded VRT keeps their reference verbatim.
        if src.remote:
            continue
        p = src.resolved
        if p is None or not p.exists():
            warnings.append(
                f"Referenced source '{src.raw}' not found locally; not bundled."
            )
            continue
        if not src.relative_to_vrt and p.is_absolute():
            warnings.append(
                f"Source '{src.raw}' uses an absolute path; the uploaded VRT "
                f"may not resolve it in bundle mode."
            )
        try:
            rel = p.relative_to(vrt_dir)
        except ValueError:
            rel = Path(p.name)
        await client.upload_resource(f"{base}/{rel.as_posix()}", p.read_bytes())

    return f"file:{base}/{info.path.name}", warnings


async def _publish_vrt_one(
    client: GeoServerClient,
    config: PublishConfig,
    info: VRTInfo,
    layer_name: str,
    semaphore: asyncio.Semaphore,
    index: int,
    total: int,
    progress_callback: object,
) -> BundleResult:
    """Publish a single VRT (raster coverage or vector OGR datastore)."""
    store_name = layer_name
    async with semaphore:
        if callable(progress_callback):
            progress_callback(index, total, layer_name)

        last_error = ""
        try:
            t0 = time.monotonic()
            if config.vrt_mode == "bundle":
                data_url, _warns = await _bundle_upload_vrt(client, store_name, info)
            else:
                data_url = f"file:{info.path}"

            if info.kind == "raster":
                ok = await client.create_vrt_coveragestore(
                    config.workspace, store_name, data_url
                )
                if ok:
                    await client.create_coverage(
                        config.workspace, store_name, info.path.stem, layer_name
                    )
            else:  # vector
                ok = await client.create_ogr_vrt_datastore(
                    config.workspace, store_name, data_url
                )
                if ok:
                    await client.create_featuretype(
                        config.workspace, store_name, info.path.stem, layer_name
                    )

            if ok:
                return BundleResult(
                    layer_name=layer_name,
                    source_path=info.path,
                    action="create",
                    status="ok",
                    file_size=info.path.stat().st_size,
                    upload_time=time.monotonic() - t0,
                )
            last_error = (
                f"HTTP {client._last_status_code}: {client._last_response_text[:200]}"
            )
        except Exception as exc:
            last_error = str(exc)
            logger.warning("VRT publish failed for '%s': %s", layer_name, last_error)

        result = BundleResult(
            layer_name=layer_name,
            source_path=info.path,
            action="create",
            status="error",
            error=last_error,
        )
        if config.fail_fast:
            raise RuntimeError(
                f"VRT publish failed for '{layer_name}' and fail_fast is enabled: "
                f"{last_error}"
            )
        return result
