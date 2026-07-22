"""Parsing and classification of GDAL/OGR VRT (Virtual Format) datasets.

A ``.vrt`` file is an XML wrapper that references other datasets by path:

* **Raster** VRTs (``gdalbuildvrt`` output, warped VRTs) have a
  ``<VRTDataset>`` root and reference source rasters via
  ``<SourceFilename>`` elements.
* **Vector** VRTs (OGR VRT) have an ``<OGRVRTDataSource>`` root and reference
  source datasets via ``<SrcDataSource>`` elements.

This module extracts the kind and the referenced source files so the publisher
can either upload them alongside the ``.vrt`` (bundle mode) or leave them to be
resolved on the GeoServer filesystem (server-path mode).

Security: parsing uses :mod:`defusedxml` and additionally rejects any document
containing a ``DOCTYPE``/entity declaration up front (VRT files never
legitimately contain one). Together these close XML external-entity (XXE) and
entity-expansion attacks.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from xml.etree import ElementTree as ET

import defusedxml.ElementTree as SafeET

__all__ = [
    "InvalidVRTError",
    "VRTInfo",
    "VRTSource",
    "is_vrt",
    "parse_vrt",
]

# Matches a DOCTYPE declaration (case-insensitive), used to reject entity
# bombs / external entity references before handing the text to the parser.
_DOCTYPE_RE = re.compile(rb"<!DOCTYPE", re.IGNORECASE)

_RASTER_ROOT = "VRTDataset"
_VECTOR_ROOT = "OGRVRTDataSource"


class InvalidVRTError(ValueError):
    """Raised when a file is not a well-formed, recognised VRT dataset."""


@dataclass(frozen=True)
class VRTSource:
    """A single source dataset referenced by a VRT."""

    raw: str
    """The path exactly as written in the VRT."""

    relative_to_vrt: bool
    """Whether *raw* is resolved relative to the VRT's own directory."""

    resolved: Path
    """Absolute path the reference resolves to (may not exist on disk)."""


@dataclass(frozen=True)
class VRTInfo:
    """Structured information extracted from a VRT file."""

    path: Path
    """Absolute path to the ``.vrt`` file."""

    kind: str
    """``"raster"`` or ``"vector"``."""

    sources: tuple[VRTSource, ...]
    """Every source dataset the VRT references, in document order."""

    @property
    def referenced_files(self) -> tuple[Path, ...]:
        """Resolved absolute paths of all referenced sources (deduplicated)."""
        seen: dict[Path, None] = {}
        for src in self.sources:
            seen.setdefault(src.resolved, None)
        return tuple(seen)

    @property
    def missing_files(self) -> tuple[Path, ...]:
        """Referenced files that do not exist on the local filesystem."""
        return tuple(p for p in self.referenced_files if not p.exists())


def is_vrt(path: Path) -> bool:
    """Return ``True`` if *path* has a ``.vrt`` extension (case-insensitive)."""
    return path.suffix.lower() == ".vrt"


def _resolve(raw: str, relative_to_vrt: bool, vrt_dir: Path) -> Path:
    """Resolve a raw source reference to an absolute path."""
    candidate = Path(raw)
    if relative_to_vrt or not candidate.is_absolute():
        candidate = vrt_dir / candidate
    # Normalise without requiring the target to exist (server-path mode).
    return Path(candidate).resolve(strict=False)


def _attr_true(elem: ET.Element, name: str) -> bool:
    """Return True if an element's attribute is the string ``"1"``."""
    return elem.get(name, "0") == "1"


def parse_vrt(path: Path) -> VRTInfo:
    """Parse and classify a VRT file.

    Args:
        path: Path to a ``.vrt`` file.

    Returns:
        A :class:`VRTInfo` describing the VRT kind and referenced sources.

    Raises:
        InvalidVRTError: If the file is missing, malformed, contains a DOCTYPE
            declaration, or is not a recognised raster/vector VRT.
    """
    path = Path(path)
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise InvalidVRTError(f"Cannot read VRT '{path}': {exc}") from exc

    if _DOCTYPE_RE.search(data):
        raise InvalidVRTError(
            f"VRT '{path}' contains a DOCTYPE declaration and was rejected "
            f"for security reasons."
        )

    try:
        root = SafeET.fromstring(data)
    except ET.ParseError as exc:
        raise InvalidVRTError(f"Malformed XML in VRT '{path}': {exc}") from exc

    tag = _localname(root.tag)
    vrt_dir = path.resolve(strict=False).parent

    if tag == _RASTER_ROOT:
        sources = _collect_sources(root, vrt_dir, "SourceFilename")
        kind = "raster"
    elif tag == _VECTOR_ROOT:
        sources = _collect_sources(root, vrt_dir, "SrcDataSource")
        kind = "vector"
    else:
        raise InvalidVRTError(
            f"'{path}' is not a recognised VRT (root element <{tag}>). "
            f"Expected <{_RASTER_ROOT}> or <{_VECTOR_ROOT}>."
        )

    return VRTInfo(path=path.resolve(strict=False), kind=kind, sources=sources)


def _localname(tag: str) -> str:
    """Strip any XML namespace from a tag name."""
    return tag.rsplit("}", 1)[-1]


def _collect_sources(
    root: ET.Element, vrt_dir: Path, tag_name: str
) -> tuple[VRTSource, ...]:
    """Collect source references from elements named *tag_name*.

    Used for both ``<SourceFilename>`` (raster) and ``<SrcDataSource>``
    (vector) references.
    """
    sources: list[VRTSource] = []
    for elem in root.iter():
        if _localname(elem.tag) != tag_name:
            continue
        raw = (elem.text or "").strip()
        if not raw:
            continue
        rel = _attr_true(elem, "relativeToVRT")
        sources.append(
            VRTSource(
                raw=raw,
                relative_to_vrt=rel,
                resolved=_resolve(raw, rel, vrt_dir),
            )
        )
    return tuple(sources)
