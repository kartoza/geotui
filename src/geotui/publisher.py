"""Bulk shapefile publisher engine for GeoTUI.

Provides shapefile discovery, naming strategy resolution, and publish
configuration dataclasses used by the upload execution engine.
"""

from __future__ import annotations

import zipfile
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

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

    def to_zip(self, dest: Path) -> Path:
        """Write the bundle into a ZIP archive at *dest* and return the path."""
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for component in self.files:
                zf.write(component, component.name)
        return dest


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
    # Computed properties
    # ------------------------------------------------------------------

    @property
    def created(self) -> list[BundleResult]:
        return [r for r in self.results if r.action == "create" and r.status == "ok"]

    @property
    def updated(self) -> list[BundleResult]:
        return [r for r in self.results if r.action == "update" and r.status == "ok"]

    @property
    def skipped(self) -> list[BundleResult]:
        return [r for r in self.results if r.status in ("skipped", "dry_run")]

    @property
    def failed(self) -> list[BundleResult]:
        return [r for r in self.results if r.status == "error"]

    @property
    def total_uploaded_bytes(self) -> int:
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
