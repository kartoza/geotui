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
    geoserver_url: str
    geoserver_version: str
    username: str
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
        return True

    # Datastore does not exist - create a Shapefile directory store.
    logger.info("Creating datastore '%s'", config.datastore)
    created = await client.create_datastore(
        workspace=config.workspace,
        name=config.datastore,
        store_type="Directory of spatial files (shapefiles)",
        params={"url": f"file:data/{config.datastore}"},
    )
    if not created:
        report.warnings.append(f"Failed to create datastore '{config.datastore}'")
        return False
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

                last_error = "Upload returned failure status"

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
