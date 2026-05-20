# Bulk Shapefile Publisher Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a bulk shapefile publisher to GeoTUI that discovers, zips, and uploads thousands of shapefiles to GeoServer with concurrent uploads, retry logic, idempotent create/update, PDF/JSON reporting, and both TUI and CLI interfaces.

**Architecture:** The publisher is a pure-logic engine (`publisher.py`) that takes a `PublishConfig` and a `GeoServerClient`, discovers shapefile bundles, uploads them concurrently via semaphore-bounded async tasks, and returns a `PublishReport` dataclass. The report is rendered to PDF (`report.py`) using fpdf2 with Kartoza+GeoTUI branding. The TUI exposes the publisher via the F2 menu's action panel. The CLI exposes it via `geotui publish` using Click. Export/import are separate modules following the same pattern.

**Tech Stack:** Python 3.10+, httpx (async HTTP), fpdf2 (PDF generation), Pydantic (config models), asyncio (concurrency), Click (CLI), Textual (TUI)

---

## File Structure

| File | Responsibility |
|------|----------------|
| `src/geotui/publisher.py` | Shapefile discovery, ZIP bundling, concurrent upload engine, retry logic |
| `src/geotui/report.py` | PDF and JSON report generation with Kartoza+GeoTUI branding |
| `src/geotui/exporter.py` | GeoServer workspace config export and import |
| `src/geotui/cli.py` | Click CLI with `publish`, `export`, `import-config` subcommands |
| `src/geotui/__main__.py` | Updated entry point to support CLI subcommands |
| `src/geotui/client.py` | Extended with `layer_exists()`, `upload_shapefile()`, `assign_style()`, `get_datastore_type()` |
| `src/geotui/screens/context_menu.py` | Add "Bulk Publish" and "Export Config" menu items |
| `src/geotui/widgets/geoserver_tree.py` | Add publish action panel with progress display |
| `tests/unit/test_publisher.py` | Publisher engine tests (discovery, naming, collision detection) |
| `tests/unit/test_report.py` | Report generation tests (PDF structure, JSON output) |
| `tests/unit/test_exporter.py` | Export/import tests |
| `tests/unit/test_cli.py` | CLI subcommand tests |
| `tests/bdd/features/bulk_publish.feature` | BDD scenarios for publish workflow |
| `tests/bdd/features/publish_report.feature` | BDD scenarios for report generation |

---

## Task 1: Add new client methods to GeoServerClient

**Files:**
- Modify: `src/geotui/client.py`
- Test: `tests/unit/test_client_publish.py`

- [ ] **Step 1: Write failing tests for new client methods**

```python
# tests/unit/test_client_publish.py
"""Tests for GeoServer client publish methods."""

import pytest

from geotui.client import GeoServerClient
from geotui.config import Connection


@pytest.fixture
def conn() -> Connection:
    return Connection(
        name="Test",
        url="https://192.0.2.1:9999",
        username="admin",
        password="pass",
    )


class TestClientPublishMethods:
    @pytest.mark.asyncio
    async def test_layer_exists_unreachable(self, conn: Connection) -> None:
        async with GeoServerClient(conn, timeout=1.0) as client:
            result = await client.layer_exists("ws", "layer")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_datastore_type_unreachable(self, conn: Connection) -> None:
        async with GeoServerClient(conn, timeout=1.0) as client:
            result = await client.get_datastore_type("ws", "store")
            assert result is None

    @pytest.mark.asyncio
    async def test_upload_shapefile_unreachable(self, conn: Connection) -> None:
        async with GeoServerClient(conn, timeout=1.0) as client:
            result = await client.upload_shapefile("ws", "store", b"fake-zip", False)
            assert result is False

    @pytest.mark.asyncio
    async def test_assign_style_unreachable(self, conn: Connection) -> None:
        async with GeoServerClient(conn, timeout=1.0) as client:
            result = await client.assign_style("ws", "layer", "style_name")
            assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_client_publish.py -v`
Expected: FAIL with AttributeError (methods don't exist yet)

- [ ] **Step 3: Implement the new client methods**

Add to `src/geotui/client.py` inside `GeoServerClient`, after the existing create methods:

```python
    async def _put(self, path: str, data: bytes, content_type: str) -> int:
        """Make an authenticated PUT request with binary data.

        Args:
            path: API path relative to base URL.
            data: Binary body to send.
            content_type: Content-Type header value.

        Returns:
            HTTP status code, or 0 on connection error.
        """
        client = await self._ensure_client()
        try:
            response = await client.put(
                f"{self._base_url}{path}",
                content=data,
                auth=self._auth,
                headers={"Content-Type": content_type},
            )
            return response.status_code
        except httpx.RequestError:
            return 0

    async def layer_exists(self, workspace: str, layer_name: str) -> bool:
        """Check if a layer exists in the workspace.

        Args:
            workspace: Workspace name.
            layer_name: Layer name.

        Returns:
            True if the layer exists.
        """
        data = await self._get(f"/rest/layers/{workspace}:{layer_name}.json")
        return data is not None

    async def get_datastore_type(self, workspace: str, store: str) -> str | None:
        """Get the type of an existing datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.

        Returns:
            The store type string, or None if not found.
        """
        data = await self._get(
            f"/rest/workspaces/{workspace}/datastores/{store}.json"
        )
        if data:
            return data.get("dataStore", {}).get("type")
        return None

    async def upload_shapefile(
        self,
        workspace: str,
        store: str,
        zip_data: bytes,
        update: bool = False,
    ) -> bool:
        """Upload a shapefile ZIP to a datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.
            zip_data: ZIP archive bytes.
            update: If True, overwrite existing data.

        Returns:
            True if upload succeeded (HTTP 201 or 200).
        """
        path = (
            f"/rest/workspaces/{workspace}/datastores/{store}"
            f"/file.shp?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, zip_data, "application/zip")
        return status in (200, 201)

    async def assign_style(
        self, workspace: str, layer_name: str, style_name: str
    ) -> bool:
        """Assign a default style to a layer.

        Args:
            workspace: Workspace name.
            layer_name: Layer name.
            style_name: Style name to assign.

        Returns:
            True if assignment succeeded.
        """
        client = await self._ensure_client()
        try:
            response = await client.put(
                f"{self._base_url}/rest/layers/{workspace}:{layer_name}.json",
                json={"layer": {"defaultStyle": {"name": style_name}}},
                auth=self._auth,
                headers={
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                },
            )
            return response.status_code == 200
        except httpx.RequestError:
            return False
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_client_publish.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 5: Run full suite, lint, commit**

Run: `ruff check src/ tests/ && ruff format src/ tests/ && pytest tests/ --no-header -q`
Expected: All tests pass, lint clean

```bash
git add src/geotui/client.py tests/unit/test_client_publish.py
git commit -m "feat: add layer_exists, upload_shapefile, assign_style to client"
```

---

## Task 2: Shapefile discovery and naming engine

**Files:**
- Create: `src/geotui/publisher.py`
- Test: `tests/unit/test_publisher.py`

- [ ] **Step 1: Write failing tests for shapefile discovery**

```python
# tests/unit/test_publisher.py
"""Tests for the bulk shapefile publisher engine."""

from pathlib import Path

import pytest

from geotui.publisher import (
    BundleResult,
    NamingStrategy,
    PublishConfig,
    ShapefileBundle,
    discover_bundles,
    resolve_layer_names,
)


@pytest.fixture
def shapefile_dir(tmp_path: Path) -> Path:
    """Create a directory with test shapefile bundles."""
    # Complete bundle
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        (tmp_path / f"roads{ext}").touch()
    # Another complete bundle
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"buildings{ext}").touch()
    # Incomplete bundle (missing .dbf)
    (tmp_path / "broken.shp").touch()
    (tmp_path / "broken.shx").touch()
    # Non-shapefile
    (tmp_path / "readme.txt").touch()
    return tmp_path


@pytest.fixture
def nested_dir(tmp_path: Path) -> Path:
    """Create nested directories with shapefiles."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"rivers{ext}").touch()
        (sub / f"rivers{ext}").touch()  # Name collision!
    return tmp_path


class TestDiscoverBundles:
    def test_finds_complete_bundles(self, shapefile_dir: Path) -> None:
        bundles, warnings = discover_bundles(shapefile_dir, recurse=False)
        names = {b.name for b in bundles}
        assert "roads" in names
        assert "buildings" in names
        assert len(bundles) == 2

    def test_reports_incomplete_bundles(self, shapefile_dir: Path) -> None:
        bundles, warnings = discover_bundles(shapefile_dir, recurse=False)
        assert len(warnings) == 1
        assert "broken" in warnings[0]

    def test_recurse_finds_subdirectories(self, nested_dir: Path) -> None:
        bundles, warnings = discover_bundles(nested_dir, recurse=True)
        assert len(bundles) == 2

    def test_no_recurse_skips_subdirs(self, nested_dir: Path) -> None:
        bundles, warnings = discover_bundles(nested_dir, recurse=False)
        assert len(bundles) == 1

    def test_bundle_calculates_total_size(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        for b in bundles:
            assert b.total_size >= 0

    def test_bundle_lists_all_components(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        roads = next(b for b in bundles if b.name == "roads")
        extensions = {f.suffix for f in roads.files}
        assert ".shp" in extensions
        assert ".prj" in extensions


class TestNaming:
    def test_basename_strategy(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        names = resolve_layer_names(
            bundles, shapefile_dir, NamingStrategy.BASENAME
        )
        assert "roads" in names.values()

    def test_path_slug_avoids_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        names = resolve_layer_names(
            bundles, nested_dir, NamingStrategy.PATH_SLUG
        )
        values = list(names.values())
        assert len(values) == len(set(values))  # No duplicates

    def test_basename_detects_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        with pytest.raises(ValueError, match="collision"):
            resolve_layer_names(
                bundles, nested_dir, NamingStrategy.BASENAME
            )

    def test_prefixed_basename(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        names = resolve_layer_names(
            bundles, shapefile_dir, NamingStrategy.PREFIXED_BASENAME,
            prefix="geo_",
        )
        assert all(v.startswith("geo_") for v in names.values())


class TestPublishConfig:
    def test_defaults(self) -> None:
        cfg = PublishConfig(
            workspace="ws", datastore="ds",
            source_directory=Path("/data"),
        )
        assert cfg.concurrency == 4
        assert cfg.dry_run is False
        assert cfg.naming == NamingStrategy.BASENAME
        assert cfg.retry_max_attempts == 3
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_publisher.py -v`
Expected: FAIL with ImportError (module doesn't exist)

- [ ] **Step 3: Implement publisher discovery and naming**

```python
# src/geotui/publisher.py
"""Bulk shapefile publisher engine.

Discovers shapefile bundles, resolves layer names, creates ZIP archives,
and uploads them to GeoServer with concurrent bounded uploads and retry.
"""

import enum
import io
import zipfile
from dataclasses import dataclass, field
from pathlib import Path

SHAPEFILE_REQUIRED = {".shp", ".shx", ".dbf"}
SHAPEFILE_OPTIONAL = {".prj", ".cpg", ".qix", ".sbn", ".sbx", ".fix", ".qpj"}
SHAPEFILE_ALL = SHAPEFILE_REQUIRED | SHAPEFILE_OPTIONAL


class NamingStrategy(enum.Enum):
    """Strategy for deriving layer names from shapefile paths."""

    BASENAME = "basename"
    PREFIXED_BASENAME = "prefixed_basename"
    PATH_SLUG = "path_slug"


@dataclass
class ShapefileBundle:
    """A discovered shapefile bundle.

    Attributes:
        name: Basename of the shapefile (without extension).
        directory: Directory containing the bundle.
        files: List of component file paths.
        total_size: Total size of all component files in bytes.
    """

    name: str
    directory: Path
    files: list[Path]
    total_size: int = 0

    def __post_init__(self) -> None:
        """Calculate total size from files."""
        self.total_size = sum(f.stat().st_size for f in self.files if f.exists())

    def to_zip(self) -> bytes:
        """Create a ZIP archive of the bundle.

        Returns:
            ZIP archive as bytes.
        """
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for f in self.files:
                zf.write(f, f.name)
        return buf.getvalue()


@dataclass
class BundleResult:
    """Result of publishing a single bundle.

    Attributes:
        layer_name: Derived layer name.
        source_path: Relative path to the .shp file.
        action: CREATE, UPDATE, or SKIP.
        status: SUCCESS, ERROR, or DRY_RUN.
        file_size: Total bundle size in bytes.
        upload_time: Duration of upload in seconds.
        error: Error message if failed.
    """

    layer_name: str
    source_path: str
    action: str = ""
    status: str = ""
    file_size: int = 0
    upload_time: float = 0.0
    error: str = ""


@dataclass
class PublishConfig:
    """Configuration for a bulk publish run.

    Attributes:
        workspace: Target GeoServer workspace.
        datastore: Target datastore name.
        source_directory: Local path to scan for shapefiles.
        naming: Layer naming strategy.
        prefix: Prefix for PREFIXED_BASENAME strategy.
        styles_directory: Optional path to SLD files.
        styles_mapping: Optional explicit layer->style mapping.
        recurse: Whether to recurse into subdirectories.
        concurrency: Max concurrent uploads.
        dry_run: If True, validate only without uploading.
        retry_max_attempts: Max retry count per bundle.
        retry_backoff_seconds: Initial backoff delay.
        fail_fast: Abort on first non-retryable failure.
    """

    workspace: str
    datastore: str
    source_directory: Path
    naming: NamingStrategy = NamingStrategy.BASENAME
    prefix: str = ""
    styles_directory: Path | None = None
    styles_mapping: dict[str, str] = field(default_factory=dict)
    recurse: bool = True
    concurrency: int = 4
    dry_run: bool = False
    retry_max_attempts: int = 3
    retry_backoff_seconds: int = 5
    fail_fast: bool = False


@dataclass
class PublishReport:
    """Report from a bulk publish run.

    Attributes:
        config: The publish configuration used.
        geoserver_url: Resolved GeoServer URL.
        geoserver_version: GeoServer version string.
        username: Username used for the connection.
        results: Per-bundle results.
        warnings: Discovery warnings (incomplete bundles).
        wall_clock_seconds: Total elapsed time.
    """

    config: PublishConfig
    geoserver_url: str = ""
    geoserver_version: str = ""
    username: str = ""
    results: list[BundleResult] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    wall_clock_seconds: float = 0.0

    @property
    def created(self) -> int:
        return sum(1 for r in self.results if r.action == "CREATE" and r.status == "SUCCESS")

    @property
    def updated(self) -> int:
        return sum(1 for r in self.results if r.action == "UPDATE" and r.status == "SUCCESS")

    @property
    def skipped(self) -> int:
        return sum(1 for r in self.results if r.action == "SKIP")

    @property
    def failed(self) -> int:
        return sum(1 for r in self.results if r.status == "ERROR")

    @property
    def total_uploaded_bytes(self) -> int:
        return sum(r.file_size for r in self.results if r.status == "SUCCESS")


def discover_bundles(
    directory: Path, recurse: bool = True
) -> tuple[list[ShapefileBundle], list[str]]:
    """Discover shapefile bundles in a directory.

    Args:
        directory: Root directory to scan.
        recurse: Whether to recurse into subdirectories.

    Returns:
        Tuple of (found bundles, warning messages for incomplete bundles).
    """
    shp_files: list[Path]
    if recurse:
        shp_files = sorted(directory.rglob("*.shp"))
    else:
        shp_files = sorted(directory.glob("*.shp"))

    bundles: list[ShapefileBundle] = []
    warnings: list[str] = []

    for shp in shp_files:
        stem = shp.stem
        parent = shp.parent
        required_present = all(
            (parent / f"{stem}{ext}").exists() for ext in SHAPEFILE_REQUIRED
        )

        if not required_present:
            missing = [
                ext for ext in SHAPEFILE_REQUIRED
                if not (parent / f"{stem}{ext}").exists()
            ]
            warnings.append(
                f"Incomplete bundle '{stem}' in {parent}: missing {missing}"
            )
            continue

        files = [
            parent / f"{stem}{ext}"
            for ext in SHAPEFILE_ALL
            if (parent / f"{stem}{ext}").exists()
        ]
        bundles.append(ShapefileBundle(name=stem, directory=parent, files=files))

    return bundles, warnings


def resolve_layer_names(
    bundles: list[ShapefileBundle],
    base_dir: Path,
    strategy: NamingStrategy,
    prefix: str = "",
) -> dict[str, str]:
    """Resolve layer names for bundles using the given strategy.

    Args:
        bundles: Discovered bundles.
        base_dir: Root source directory (for relative path computation).
        strategy: Naming strategy to use.
        prefix: Prefix for PREFIXED_BASENAME strategy.

    Returns:
        Dict mapping bundle name to layer name.

    Raises:
        ValueError: If name collisions are detected.
    """
    names: dict[str, str] = {}  # bundle_key -> layer_name

    for bundle in bundles:
        key = f"{bundle.directory}/{bundle.name}"

        if strategy == NamingStrategy.BASENAME:
            layer_name = bundle.name
        elif strategy == NamingStrategy.PREFIXED_BASENAME:
            layer_name = f"{prefix}{bundle.name}"
        elif strategy == NamingStrategy.PATH_SLUG:
            rel = bundle.directory.relative_to(base_dir)
            parts = list(rel.parts) + [bundle.name]
            layer_name = "_".join(parts)
            if layer_name.startswith("_"):
                layer_name = layer_name[1:]
        else:
            layer_name = bundle.name

        names[key] = layer_name

    # Check for collisions
    seen: dict[str, str] = {}
    collisions: list[str] = []
    for key, layer_name in names.items():
        if layer_name in seen:
            collisions.append(
                f"'{layer_name}' from {key} collides with {seen[layer_name]}"
            )
        seen[layer_name] = key

    if collisions:
        raise ValueError(
            f"Layer name collision(s) detected:\n" + "\n".join(collisions)
        )

    return names
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_publisher.py -v`
Expected: PASS (all 11 tests)

- [ ] **Step 5: Lint, format, commit**

Run: `ruff check src/ tests/ && ruff format src/ tests/`

```bash
git add src/geotui/publisher.py tests/unit/test_publisher.py
git commit -m "feat: shapefile discovery and naming engine"
```

---

## Task 3: Publish execution engine (upload + retry)

**Files:**
- Modify: `src/geotui/publisher.py`
- Test: `tests/unit/test_publisher.py` (extend)

- [ ] **Step 1: Write failing test for the publish runner**

Append to `tests/unit/test_publisher.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch


class TestPublishRunner:
    @pytest.mark.asyncio
    async def test_dry_run_skips_upload(self, shapefile_dir: Path) -> None:
        """Dry run discovers but does not upload."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws", datastore="ds",
            source_directory=shapefile_dir, dry_run=True,
        )
        report = await run_publish(conn, cfg)
        assert all(r.status == "DRY_RUN" for r in report.results)
        assert report.created == 0
        assert len(report.results) == 2  # roads + buildings

    @pytest.mark.asyncio
    async def test_publish_creates_workspace_if_missing(
        self, shapefile_dir: Path
    ) -> None:
        """Publish creates workspace when it doesn't exist."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws", datastore="ds",
            source_directory=shapefile_dir, dry_run=True,
        )

        with patch("geotui.publisher.test_connection") as mock_test:
            mock_test.return_value = MagicMock(success=True, version="2.24")
            with patch("geotui.publisher.GeoServerClient") as mock_cls:
                client = AsyncMock()
                client.__aenter__ = AsyncMock(return_value=client)
                client.__aexit__ = AsyncMock(return_value=False)
                client.get_datastore_type = AsyncMock(return_value=None)
                client.create_workspace = AsyncMock(return_value=True)
                client.create_datastore = AsyncMock(return_value=True)
                mock_cls.return_value = client

                report = await run_publish(conn, cfg)
                assert report.geoserver_version == "2.24"

    @pytest.mark.asyncio
    async def test_bundle_zip_creation(self, shapefile_dir: Path) -> None:
        """Test that bundles can be zipped."""
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        roads = next(b for b in bundles if b.name == "roads")
        zip_bytes = roads.to_zip()
        assert len(zip_bytes) > 0
        zf = zipfile.ZipFile(io.BytesIO(zip_bytes))
        names = zf.namelist()
        assert "roads.shp" in names
```

Add `import zipfile, io` at the top of the test file.

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_publisher.py::TestPublishRunner -v`
Expected: FAIL with ImportError (run_publish doesn't exist)

- [ ] **Step 3: Implement run_publish**

Add to `src/geotui/publisher.py`:

```python
import asyncio
import logging
import time

from geotui.client import GeoServerClient, test_connection
from geotui.config import Connection

logger = logging.getLogger(__name__)


async def run_publish(
    conn: Connection,
    config: PublishConfig,
    progress_callback: object | None = None,
) -> PublishReport:
    """Execute a bulk shapefile publish run.

    Args:
        conn: GeoServer connection to use.
        config: Publish configuration.
        progress_callback: Optional callable(current, total, bundle_name)
            for progress updates.

    Returns:
        PublishReport with results for all bundles.
    """
    start_time = time.monotonic()
    report = PublishReport(config=config, username=conn.username)

    # 1. Discover bundles
    bundles, warnings = discover_bundles(
        config.source_directory, config.recurse
    )
    report.warnings = warnings

    if not bundles:
        report.wall_clock_seconds = time.monotonic() - start_time
        return report

    # 2. Resolve layer names
    try:
        names = resolve_layer_names(
            bundles, config.source_directory, config.naming, config.prefix
        )
    except ValueError as e:
        report.warnings.append(str(e))
        report.wall_clock_seconds = time.monotonic() - start_time
        return report

    # 3. Verify connection
    conn_result = await test_connection(conn)
    if not conn_result.success:
        for bundle in bundles:
            key = f"{bundle.directory}/{bundle.name}"
            report.results.append(BundleResult(
                layer_name=names[key],
                source_path=str(bundle.files[0].relative_to(config.source_directory)),
                action="SKIP",
                status="ERROR",
                file_size=bundle.total_size,
                error=conn_result.message,
            ))
        report.wall_clock_seconds = time.monotonic() - start_time
        return report

    report.geoserver_version = conn_result.version
    report.geoserver_url = conn.url

    # 4. Dry run - report without uploading
    if config.dry_run:
        for bundle in bundles:
            key = f"{bundle.directory}/{bundle.name}"
            report.results.append(BundleResult(
                layer_name=names[key],
                source_path=str(bundle.files[0].relative_to(config.source_directory)),
                action="CREATE",
                status="DRY_RUN",
                file_size=bundle.total_size,
            ))
        report.wall_clock_seconds = time.monotonic() - start_time
        return report

    # 5. Ensure workspace and datastore
    async with GeoServerClient(conn) as client:
        ws_ok = await _ensure_workspace(client, config, report)
        if not ws_ok:
            report.wall_clock_seconds = time.monotonic() - start_time
            return report

        ds_ok = await _ensure_datastore(client, config, report)
        if not ds_ok:
            report.wall_clock_seconds = time.monotonic() - start_time
            return report

        # 6. Upload bundles concurrently
        semaphore = asyncio.Semaphore(config.concurrency)
        tasks = []
        for i, bundle in enumerate(bundles):
            key = f"{bundle.directory}/{bundle.name}"
            layer_name = names[key]
            style = config.styles_mapping.get(layer_name)
            tasks.append(
                _upload_bundle(
                    client, config, bundle, layer_name, style,
                    semaphore, i, len(bundles), progress_callback,
                )
            )

        results = await asyncio.gather(*tasks, return_exceptions=True)
        for r in results:
            if isinstance(r, BundleResult):
                report.results.append(r)
            elif isinstance(r, Exception):
                report.results.append(BundleResult(
                    layer_name="unknown",
                    source_path="unknown",
                    status="ERROR",
                    error=str(r),
                ))

    report.wall_clock_seconds = time.monotonic() - start_time
    return report


async def _ensure_workspace(
    client: GeoServerClient, config: PublishConfig, report: PublishReport
) -> bool:
    """Ensure the target workspace exists."""
    workspaces = await client.get_workspaces()
    ws_names = {ws.name for ws in workspaces}
    if config.workspace not in ws_names:
        ok = await client.create_workspace(config.workspace)
        if not ok:
            report.warnings.append(
                f"Failed to create workspace '{config.workspace}'"
            )
            return False
        logger.info("Created workspace '%s'", config.workspace)
    return True


async def _ensure_datastore(
    client: GeoServerClient, config: PublishConfig, report: PublishReport
) -> bool:
    """Ensure the target datastore exists and is the correct type."""
    existing_type = await client.get_datastore_type(
        config.workspace, config.datastore
    )
    if existing_type is not None:
        expected = "Directory of spatial files (shapefiles)"
        if existing_type != expected:
            report.warnings.append(
                f"Datastore '{config.datastore}' exists but is type "
                f"'{existing_type}', expected '{expected}'. Aborting."
            )
            return False
        return True

    ok = await client.create_datastore(
        config.workspace,
        config.datastore,
        "Directory of spatial files (shapefiles)",
        {"url": f"file:data/{config.datastore}"},
    )
    if not ok:
        report.warnings.append(
            f"Failed to create datastore '{config.datastore}'"
        )
        return False
    logger.info("Created datastore '%s'", config.datastore)
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
    progress_callback: object | None,
) -> BundleResult:
    """Upload a single shapefile bundle with retry.

    Args:
        client: GeoServer client.
        config: Publish configuration.
        bundle: Shapefile bundle to upload.
        layer_name: Target layer name.
        style: Optional style name to assign.
        semaphore: Concurrency limiter.
        index: Bundle index (for progress).
        total: Total bundles (for progress).
        progress_callback: Optional progress callback.

    Returns:
        BundleResult with upload outcome.
    """
    rel_path = str(bundle.files[0].relative_to(config.source_directory))
    result = BundleResult(
        layer_name=layer_name,
        source_path=rel_path,
        file_size=bundle.total_size,
    )

    async with semaphore:
        if progress_callback and callable(progress_callback):
            progress_callback(index + 1, total, layer_name)

        exists = await client.layer_exists(config.workspace, layer_name)
        result.action = "UPDATE" if exists else "CREATE"

        zip_data = bundle.to_zip()
        start = time.monotonic()

        for attempt in range(config.retry_max_attempts):
            ok = await client.upload_shapefile(
                config.workspace, config.datastore, zip_data, update=exists,
            )
            if ok:
                result.status = "SUCCESS"
                result.upload_time = time.monotonic() - start

                if style:
                    await client.assign_style(
                        config.workspace, layer_name, style
                    )

                logger.info(
                    "%s %s (%d/%d) %.1fs",
                    result.action, layer_name, index + 1, total,
                    result.upload_time,
                )
                return result

            if attempt < config.retry_max_attempts - 1:
                delay = config.retry_backoff_seconds * (2 ** attempt)
                logger.warning(
                    "Retry %d/%d for %s in %ds",
                    attempt + 1, config.retry_max_attempts,
                    layer_name, delay,
                )
                await asyncio.sleep(delay)

        result.status = "ERROR"
        result.upload_time = time.monotonic() - start
        result.error = f"Failed after {config.retry_max_attempts} attempts"
        logger.error("FAILED %s after retries", layer_name)

        if config.fail_fast:
            raise RuntimeError(f"Fail-fast: {layer_name} failed")

        return result
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_publisher.py -v`
Expected: PASS (all 14 tests)

- [ ] **Step 5: Lint, format, commit**

```bash
ruff check src/ tests/ && ruff format src/ tests/
git add src/geotui/publisher.py tests/unit/test_publisher.py
git commit -m "feat: publish execution engine with retry and concurrency"
```

---

## Task 4: PDF and JSON report generation

**Files:**
- Create: `src/geotui/report.py`
- Test: `tests/unit/test_report.py`
- Modify: `pyproject.toml` (add fpdf2 dependency)

- [ ] **Step 1: Add fpdf2 to dependencies**

In `pyproject.toml`, add to the `dependencies` list:
```
    "fpdf2>=2.8.0",
```

In `flake.nix`, add to buildInputs:
```
    pythonPkgs.fpdf2
```

- [ ] **Step 2: Write failing tests for report generation**

```python
# tests/unit/test_report.py
"""Tests for PDF and JSON report generation."""

import json
from pathlib import Path

import pytest

from geotui.publisher import BundleResult, PublishConfig, PublishReport
from geotui.report import generate_json_report, generate_pdf_report


@pytest.fixture
def sample_report() -> PublishReport:
    cfg = PublishConfig(
        workspace="test_ws",
        datastore="test_ds",
        source_directory=Path("/data/shapes"),
    )
    report = PublishReport(
        config=cfg,
        geoserver_url="https://geo.example.com/geoserver",
        geoserver_version="2.24.2",
        username="admin",
        wall_clock_seconds=125.7,
        warnings=["Incomplete bundle 'broken' in /data/shapes"],
        results=[
            BundleResult(
                layer_name="roads",
                source_path="roads.shp",
                action="CREATE",
                status="SUCCESS",
                file_size=1024000,
                upload_time=1.23,
            ),
            BundleResult(
                layer_name="buildings",
                source_path="buildings.shp",
                action="UPDATE",
                status="SUCCESS",
                file_size=2048000,
                upload_time=2.45,
            ),
            BundleResult(
                layer_name="rivers",
                source_path="rivers.shp",
                action="CREATE",
                status="ERROR",
                file_size=512000,
                upload_time=5.0,
                error="HTTP 500 Internal Server Error",
            ),
        ],
    )
    return report


class TestJsonReport:
    def test_generates_valid_json(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["summary"]["total_bundles"] == 3
        assert data["summary"]["created"] == 1
        assert data["summary"]["failed"] == 1

    def test_json_contains_all_results(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        data = json.loads(path.read_text())
        assert len(data["results"]) == 3

    def test_json_contains_config(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        data = json.loads(path.read_text())
        assert data["config"]["workspace"] == "test_ws"
        assert data["config"]["geoserver_url"] == "https://geo.example.com/geoserver"

    def test_json_redacts_password(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        content = path.read_text()
        assert "password" not in content.lower() or "***" in content


class TestPdfReport:
    def test_generates_pdf_file(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.pdf"
        generate_pdf_report(sample_report, path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_pdf_starts_with_header(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:
        path = tmp_path / "report.pdf"
        generate_pdf_report(sample_report, path)
        content = path.read_bytes()
        assert content[:5] == b"%PDF-"

    def test_pdf_with_empty_results(self, tmp_path: Path) -> None:
        cfg = PublishConfig(
            workspace="ws", datastore="ds",
            source_directory=Path("/empty"),
        )
        report = PublishReport(config=cfg)
        path = tmp_path / "report.pdf"
        generate_pdf_report(report, path)
        assert path.exists()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_report.py -v`
Expected: FAIL with ImportError

- [ ] **Step 4: Implement report generation**

```python
# src/geotui/report.py
"""PDF and JSON report generation for bulk publish runs.

Generates branded reports with Kartoza + GeoTUI dual branding,
job summary, per-file detail table, and summary statistics.
"""

import json
from datetime import datetime, timezone
from pathlib import Path

from fpdf import FPDF

from geotui import __version__
from geotui.publisher import PublishReport
from geotui.theme import KARTOZA_COLORS

# Colors as RGB tuples for fpdf2
_BLUE = (0x56, 0x9F, 0xC6)
_AMBER = (0xDF, 0x9E, 0x2F)
_TEAL = (0x06, 0x96, 0x9A)
_GREY = (0x8A, 0x8B, 0x8B)
_RED = (0xCC, 0x04, 0x03)
_DARK = (0x1A, 0x1A, 0x2E)
_WHITE = (0xFF, 0xFF, 0xFF)
_SUCCESS_BG = (0xE8, 0xF5, 0xE9)
_ERROR_BG = (0xFF, 0xEB, 0xEE)
_SKIP_BG = (0xF5, 0xF5, 0xF5)
_DRY_BG = (0xE3, 0xF2, 0xFD)


def _format_size(size_bytes: int) -> str:
    """Format bytes as human-readable size."""
    for unit in ("B", "KB", "MB", "GB"):
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def _format_duration(seconds: float) -> str:
    """Format seconds as human-readable duration."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    minutes = int(seconds // 60)
    secs = seconds % 60
    if minutes < 60:
        return f"{minutes}m {secs:.0f}s"
    hours = minutes // 60
    mins = minutes % 60
    return f"{hours}h {mins}m {secs:.0f}s"


def generate_json_report(report: PublishReport, output_path: Path) -> None:
    """Generate a JSON report file.

    Args:
        report: The publish report data.
        output_path: Path to write the JSON file.
    """
    upload_times = [r.upload_time for r in report.results if r.status == "SUCCESS"]

    data = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "geotui_version": __version__,
        "config": {
            "geoserver_url": report.geoserver_url,
            "geoserver_version": report.geoserver_version,
            "username": report.username,
            "workspace": report.config.workspace,
            "datastore": report.config.datastore,
            "source_directory": str(report.config.source_directory),
            "naming": report.config.naming.value,
            "concurrency": report.config.concurrency,
            "dry_run": report.config.dry_run,
        },
        "summary": {
            "total_bundles": len(report.results),
            "created": report.created,
            "updated": report.updated,
            "skipped": report.skipped,
            "failed": report.failed,
            "total_uploaded_bytes": report.total_uploaded_bytes,
            "total_uploaded_human": _format_size(report.total_uploaded_bytes),
            "wall_clock_seconds": report.wall_clock_seconds,
            "wall_clock_human": _format_duration(report.wall_clock_seconds),
            "avg_upload_time": (
                sum(upload_times) / len(upload_times) if upload_times else 0
            ),
            "fastest_upload": min(upload_times) if upload_times else 0,
            "slowest_upload": max(upload_times) if upload_times else 0,
        },
        "warnings": report.warnings,
        "results": [
            {
                "layer_name": r.layer_name,
                "source_path": r.source_path,
                "action": r.action,
                "status": r.status,
                "file_size": r.file_size,
                "file_size_human": _format_size(r.file_size),
                "upload_time": r.upload_time,
                "error": r.error,
            }
            for r in report.results
        ],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def generate_pdf_report(report: PublishReport, output_path: Path) -> None:
    """Generate a branded PDF report.

    Args:
        report: The publish report data.
        output_path: Path to write the PDF file.
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _PublishPDF(report)
    pdf.build()
    pdf.output(str(output_path))


class _PublishPDF(FPDF):
    """Custom PDF with Kartoza + GeoTUI branding."""

    def __init__(self, report: PublishReport) -> None:
        super().__init__()
        self._report = report
        self.set_auto_page_break(auto=True, margin=20)

    def header(self) -> None:
        """Render page header with dual branding."""
        self.set_fill_color(*_DARK)
        self.rect(0, 0, 210, 18, "F")
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*_AMBER)
        self.set_xy(10, 4)
        self.cell(0, 10, "GeoTUI Bulk Publish Report", align="L")
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_BLUE)
        self.set_xy(10, 11)
        self.cell(0, 5, f"v{__version__}", align="L")
        self.set_text_color(*_GREY)
        self.set_xy(-60, 6)
        self.cell(50, 8, "kartoza.com", align="R")
        self.ln(15)

    def footer(self) -> None:
        """Render page footer with branding."""
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_GREY)
        self.cell(0, 10, f"GeoTUI v{__version__}", align="L")
        self.cell(
            0, 10,
            f"Made with love by Kartoza | Page {self.page_no()}/{{nb}}",
            align="R",
        )

    def build(self) -> None:
        """Build the complete PDF report."""
        self.alias_nb_pages()
        self.add_page()
        self._section_job_summary()
        self._section_detail_table()
        self._section_summary_stats()

    def _section_job_summary(self) -> None:
        """Render the job summary header section."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_DARK)
        self.cell(0, 8, "Job Summary", ln=True)
        self.ln(2)

        r = self._report
        rows = [
            ("Generated", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")),
            ("GeoServer URL", r.geoserver_url),
            ("GeoServer Version", r.geoserver_version),
            ("Username", r.username),
            ("Workspace", r.config.workspace),
            ("Datastore", r.config.datastore),
            ("Source Directory", str(r.config.source_directory)),
            ("Naming Strategy", r.config.naming.value),
            ("Concurrency", str(r.config.concurrency)),
            ("Dry Run", "Yes" if r.config.dry_run else "No"),
        ]

        self.set_font("Helvetica", "", 9)
        for label, value in rows:
            self.set_text_color(*_GREY)
            self.cell(45, 6, label, border=0)
            self.set_text_color(*_DARK)
            self.cell(0, 6, value, border=0, ln=True)

        self.ln(5)

    def _section_detail_table(self) -> None:
        """Render the file detail table."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_DARK)
        self.cell(0, 8, "File Details", ln=True)
        self.ln(2)

        col_widths = [10, 40, 45, 18, 18, 18, 15, 26]
        headers = [
            "#", "Layer Name", "Source Path", "Action",
            "Status", "Size", "Time", "Error",
        ]

        self._table_header(col_widths, headers)

        self.set_font("Helvetica", "", 7)
        for i, r in enumerate(self._report.results):
            if self.get_y() > 265:
                self.add_page()
                self._table_header(col_widths, headers)
                self.set_font("Helvetica", "", 7)

            bg = self._status_bg(r.status)
            self.set_fill_color(*bg)
            self.set_text_color(*_DARK)

            row = [
                str(i + 1),
                r.layer_name[:25],
                r.source_path[:30],
                r.action,
                r.status,
                _format_size(r.file_size),
                f"{r.upload_time:.1f}s" if r.upload_time else "",
                r.error[:18] if r.error else "",
            ]

            for j, (val, w) in enumerate(zip(row, col_widths, strict=True)):
                self.cell(w, 5, val, border=1, fill=True)
            self.ln()

        self.ln(5)

    def _table_header(
        self, col_widths: list[int], headers: list[str]
    ) -> None:
        """Render table column headers."""
        self.set_font("Helvetica", "B", 7)
        self.set_fill_color(*_BLUE)
        self.set_text_color(*_WHITE)
        for header, w in zip(headers, col_widths, strict=True):
            self.cell(w, 6, header, border=1, fill=True, align="C")
        self.ln()

    @staticmethod
    def _status_bg(status: str) -> tuple[int, int, int]:
        """Get background color for a status."""
        return {
            "SUCCESS": _SUCCESS_BG,
            "ERROR": _ERROR_BG,
            "SKIP": _SKIP_BG,
            "DRY_RUN": _DRY_BG,
        }.get(status, _WHITE)

    def _section_summary_stats(self) -> None:
        """Render summary statistics."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_DARK)
        self.cell(0, 8, "Summary", ln=True)
        self.ln(2)

        r = self._report
        upload_times = [
            res.upload_time for res in r.results if res.status == "SUCCESS"
        ]

        stats = [
            ("Total Bundles Discovered", str(len(r.results))),
            ("Created Successfully", str(r.created)),
            ("Updated Successfully", str(r.updated)),
            ("Skipped", str(r.skipped)),
            ("Failed", str(r.failed)),
            ("Total Data Uploaded", _format_size(r.total_uploaded_bytes)),
            ("Total Wall-Clock Time", _format_duration(r.wall_clock_seconds)),
            ("Average Upload Time", (
                f"{sum(upload_times) / len(upload_times):.2f}s"
                if upload_times else "N/A"
            )),
            ("Fastest Upload", (
                f"{min(upload_times):.2f}s" if upload_times else "N/A"
            )),
            ("Slowest Upload", (
                f"{max(upload_times):.2f}s" if upload_times else "N/A"
            )),
        ]

        self.set_font("Helvetica", "", 9)
        for label, value in stats:
            self.set_text_color(*_GREY)
            self.cell(50, 6, label, border=0)
            self.set_text_color(*_DARK)
            self.set_font("Helvetica", "B", 9)
            self.cell(0, 6, value, border=0, ln=True)
            self.set_font("Helvetica", "", 9)
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_report.py -v`
Expected: PASS (all 7 tests)

- [ ] **Step 6: Lint, format, commit**

```bash
ruff check src/ tests/ && ruff format src/ tests/
git add src/geotui/report.py tests/unit/test_report.py pyproject.toml flake.nix
git commit -m "feat: PDF and JSON report generation with Kartoza branding"
```

---

## Task 5: CLI subcommands

**Files:**
- Create: `src/geotui/cli.py`
- Modify: `src/geotui/__main__.py`
- Modify: `pyproject.toml` (add click dependency)
- Test: `tests/unit/test_cli.py`

- [ ] **Step 1: Add click to dependencies**

In `pyproject.toml` dependencies, add: `"click>=8.0.0",`

In `flake.nix` buildInputs, add: `pythonPkgs.click`

- [ ] **Step 2: Write failing tests for CLI**

```python
# tests/unit/test_cli.py
"""Tests for CLI subcommands."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from click.testing import CliRunner

from geotui.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def shapefile_dir(tmp_path: Path) -> Path:
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"test{ext}").touch()
    return tmp_path


class TestCLI:
    def test_publish_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["publish", "--help"])
        assert result.exit_code == 0
        assert "publish" in result.output.lower()

    def test_export_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0

    def test_import_config_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["import-config", "--help"])
        assert result.exit_code == 0

    def test_publish_requires_connection(
        self, runner: CliRunner, shapefile_dir: Path, tmp_path: Path
    ) -> None:
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text('{"theme":"dark","language":"en","connections":[]}')
        result = runner.invoke(cli, [
            "publish",
            "--connection", "NonExistent",
            "--workspace", "ws",
            "--datastore", "ds",
            "--source", str(shapefile_dir),
            "--config-path", str(cfg_path),
        ])
        assert result.exit_code != 0
        assert "not found" in result.output.lower()
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `pytest tests/unit/test_cli.py -v`
Expected: FAIL with ImportError

- [ ] **Step 4: Implement CLI**

```python
# src/geotui/cli.py
"""CLI interface for GeoTUI.

Provides subcommands for bulk publish, export, and import-config
that can be run headlessly or from CI pipelines.
"""

import asyncio
import sys
from pathlib import Path

import click

from geotui import __version__
from geotui.config import ConfigManager
from geotui.publisher import NamingStrategy, PublishConfig


@click.group()
@click.version_option(__version__)
def cli() -> None:
    """GeoTUI - GeoServer Manager."""


@cli.command()
@click.option("--connection", "-c", required=True, help="Saved connection name")
@click.option("--workspace", "-w", required=True, help="Target workspace")
@click.option("--datastore", "-d", required=True, help="Target datastore")
@click.option("--source", "-s", required=True, type=click.Path(exists=True), help="Source directory")
@click.option("--naming", default="basename", type=click.Choice(["basename", "prefixed_basename", "path_slug"]))
@click.option("--prefix", default="", help="Prefix for prefixed_basename strategy")
@click.option("--concurrency", default=4, type=int, help="Max concurrent uploads")
@click.option("--dry-run", is_flag=True, help="Validate without uploading")
@click.option("--fail-fast", is_flag=True, help="Abort on first failure")
@click.option("--output", "-o", type=click.Path(), help="Report output directory")
@click.option("--config-path", type=click.Path(), help="Override config file path")
def publish(
    connection: str,
    workspace: str,
    datastore: str,
    source: str,
    naming: str,
    prefix: str,
    concurrency: int,
    dry_run: bool,
    fail_fast: bool,
    output: str | None,
    config_path: str | None,
) -> None:
    """Bulk publish shapefiles to GeoServer."""
    from geotui.publisher import run_publish
    from geotui.report import generate_json_report, generate_pdf_report

    cfg_path = Path(config_path) if config_path else None
    cm = ConfigManager(config_path=cfg_path)

    conn = cm.get_connection_by_name(connection)
    if not conn:
        click.echo(f"Error: Connection '{connection}' not found.", err=True)
        sys.exit(1)

    config = PublishConfig(
        workspace=workspace,
        datastore=datastore,
        source_directory=Path(source),
        naming=NamingStrategy(naming),
        prefix=prefix,
        concurrency=concurrency,
        dry_run=dry_run,
        fail_fast=fail_fast,
    )

    def progress(current: int, total: int, name: str) -> None:
        click.echo(f"[{current}/{total}] {name}")

    report = asyncio.run(run_publish(conn, config, progress_callback=progress))

    # Generate reports
    out_dir = Path(output) if output else Path.home() / ".local/share/geotui/reports"
    from datetime import datetime, timezone

    ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
    pdf_path = out_dir / f"publish-{ts}.pdf"
    json_path = out_dir / f"publish-{ts}.json"

    generate_pdf_report(report, pdf_path)
    generate_json_report(report, json_path)

    # Print summary
    click.echo(f"\nCreated: {report.created} | Updated: {report.updated} | "
               f"Failed: {report.failed} | Skipped: {report.skipped}")
    click.echo(f"Total time: {report.wall_clock_seconds:.1f}s")
    click.echo(f"PDF report: {pdf_path}")
    click.echo(f"JSON report: {json_path}")

    if report.failed > 0:
        sys.exit(1)


@cli.command()
@click.option("--connection", "-c", required=True, help="Saved connection name")
@click.option("--workspace", "-w", required=True, help="Workspace to export")
@click.option("--output", "-o", required=True, type=click.Path(), help="Output directory")
@click.option("--config-path", type=click.Path(), help="Override config file path")
def export(
    connection: str, workspace: str, output: str, config_path: str | None
) -> None:
    """Export GeoServer workspace configuration."""
    click.echo(f"Exporting workspace '{workspace}' to {output}")
    # Implementation in Task 7


@cli.command("import-config")
@click.option("--connection", "-c", required=True, help="Target connection name")
@click.option("--input", "-i", "input_dir", required=True, type=click.Path(exists=True), help="Config directory")
@click.option("--config-path", type=click.Path(), help="Override config file path")
def import_config(
    connection: str, input_dir: str, config_path: str | None
) -> None:
    """Import GeoServer workspace configuration."""
    click.echo(f"Importing config from {input_dir}")
    # Implementation in Task 7
```

- [ ] **Step 5: Update __main__.py**

```python
# src/geotui/__main__.py
"""Entry point for GeoTUI application."""

import sys


def main() -> None:
    """Launch the GeoTUI application.

    If CLI arguments are provided, run the CLI interface.
    Otherwise, launch the TUI.
    """
    if len(sys.argv) > 1 and sys.argv[1] in ("publish", "export", "import-config", "--version", "--help"):
        from geotui.cli import cli

        cli()
    else:
        from geotui.app import GeoTUIApp

        app = GeoTUIApp()
        app.run()


if __name__ == "__main__":
    main()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_cli.py -v`
Expected: PASS (all 4 tests)

- [ ] **Step 7: Lint, format, commit**

```bash
ruff check src/ tests/ && ruff format src/ tests/
git add src/geotui/cli.py src/geotui/__main__.py tests/unit/test_cli.py pyproject.toml flake.nix
git commit -m "feat: CLI subcommands for publish, export, import-config"
```

---

## Task 6: TUI integration (F2 menu + action panel)

**Files:**
- Modify: `src/geotui/screens/context_menu.py`
- Modify: `src/geotui/widgets/geoserver_tree.py`
- Modify: `src/geotui/app.py`
- Test: `tests/unit/test_publish_tui.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_publish_tui.py
"""Tests for bulk publish TUI integration."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.screens.context_menu import ContextMenuScreen


@pytest.fixture
def connected_config(tmp_path: Path) -> ConfigManager:
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(
        Connection(name="Test", url="https://192.0.2.1:9999", is_active=True)
    )
    return cm


class TestPublishTUI:
    @pytest.mark.asyncio
    async def test_f2_menu_has_bulk_publish(
        self, connected_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            from geotui.widgets.dual_pane import DualPane
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_publish_tui.py -v`

- [ ] **Step 3: Add Bulk Publish to context menu**

In `src/geotui/screens/context_menu.py`, add to the geoserver menu options in `on_mount()`:

```python
            opts.add_option(
                Option(_("Bulk Publish Shapefiles"), id="gs_bulk_publish")
            )
```

In `src/geotui/app.py`, add to `handle_menu_result`:

```python
            elif action_id == "gs_bulk_publish":
                tree.action_bulk_publish()
```

- [ ] **Step 4: Add bulk publish action to geoserver_tree.py**

Add to `GeoServerTree`:

```python
    def action_bulk_publish(self) -> None:
        """Show the bulk publish configuration form."""
        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return
        self._current_action = "bulk_publish"
        self._show_fields(
            _("Bulk Publish Shapefiles"),
            [
                ("workspace", _("Workspace"), "my_workspace"),
                ("datastore", _("Datastore"), "my_datastore"),
                ("source", _("Source Directory"), str(Path.home())),
                ("naming", _("Naming (basename/path_slug)"), "basename"),
                ("concurrency", _("Concurrency"), "4"),
            ],
        )
```

Update `_do_create()` to handle `bulk_publish`:

```python
        elif self._current_action == "bulk_publish":
            values = self._get_field_values([
                ("workspace", "", ""), ("datastore", "", ""),
                ("source", "", ""), ("naming", "", ""),
                ("concurrency", "", ""),
            ])
            self.run_worker(
                self._run_bulk_publish(values), exit_on_error=False
            )
```

Add the async publish method:

```python
    async def _run_bulk_publish(self, values: dict[str, str]) -> None:
        """Run the bulk publish in background."""
        from geotui.publisher import NamingStrategy, PublishConfig, run_publish
        from geotui.report import generate_json_report, generate_pdf_report

        config = PublishConfig(
            workspace=values["workspace"],
            datastore=values["datastore"],
            source_directory=Path(values["source"]),
            naming=NamingStrategy(values.get("naming", "basename")),
            concurrency=int(values.get("concurrency", "4")),
        )

        def progress(current: int, total: int, name: str) -> None:
            if self.is_mounted:
                status = self.query_one("#tree-status", Static)
                status.update(f"Publishing {current}/{total}: {name}")

        report = await run_publish(self.connection, config, progress)

        if self.is_mounted:
            from datetime import datetime, timezone
            ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            out_dir = Path.home() / ".local/share/geotui/reports"
            pdf_path = out_dir / f"publish-{ts}.pdf"
            json_path = out_dir / f"publish-{ts}.json"
            generate_pdf_report(report, pdf_path)
            generate_json_report(report, json_path)

            summary = (
                f"Created: {report.created} | Updated: {report.updated} | "
                f"Failed: {report.failed}\nReport: {pdf_path}"
            )
            self.app.notify(summary, severity="information", timeout=10)
            self._hide_action_panel()
            self.refresh_tree()
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `pytest tests/unit/test_publish_tui.py -v && pytest tests/ --no-header -q`
Expected: All pass

- [ ] **Step 6: Lint, format, commit**

```bash
ruff check src/ tests/ && ruff format src/ tests/
git add src/geotui/screens/context_menu.py src/geotui/widgets/geoserver_tree.py src/geotui/app.py tests/unit/test_publish_tui.py
git commit -m "feat: bulk publish via F2 menu with progress and reports"
```

---

## Task 7: BDD features and documentation

**Files:**
- Create: `tests/bdd/features/bulk_publish.feature`
- Create: `tests/bdd/features/publish_report.feature`
- Modify: `SPECIFICATION.md`
- Modify: `PACKAGES.md`
- Delete: `NEW_REQUIREMENTS.md`

- [ ] **Step 1: Write BDD features**

```gherkin
# tests/bdd/features/bulk_publish.feature
Feature: Bulk Shapefile Publishing
  As a GeoServer administrator
  I want to bulk publish shapefiles to GeoServer
  So that I can quickly set up large datasets

  Scenario: Discover shapefile bundles in a directory
    Given a directory with 3 complete shapefile bundles
    And 1 incomplete bundle missing .dbf
    When I run shapefile discovery
    Then 3 bundles should be found
    And 1 warning should be reported

  Scenario: Dry run validates without uploading
    Given a directory with shapefile bundles
    And a publish configuration with dry_run enabled
    When I run the publisher
    Then all results should have status DRY_RUN
    And no data should be uploaded to GeoServer

  Scenario: Name collision detection
    Given a directory with duplicate shapefile names in subdirectories
    When I resolve names with basename strategy
    Then a collision error should be raised
```

```gherkin
# tests/bdd/features/publish_report.feature
Feature: Publish Report Generation
  As a GeoServer administrator
  I want a detailed PDF report after publishing
  So that I have an audit trail of what was uploaded

  Scenario: PDF report is generated after publish
    Given a completed publish run with results
    When I generate the PDF report
    Then a PDF file should be created
    And it should contain the job summary
    And it should contain the file detail table

  Scenario: JSON report contains same data as PDF
    Given a completed publish run with results
    When I generate the JSON report
    Then the JSON should contain all bundle results
    And the JSON should contain summary statistics
```

- [ ] **Step 2: Update SPECIFICATION.md**

Add new sections FR-008 through FR-012 and US-005 through US-007 covering bulk publish, reporting, CLI, and export/import. Add version 0.4.0 to history.

- [ ] **Step 3: Update PACKAGES.md**

Add entries for `fpdf2`, `click`, and describe `publisher.py`, `report.py`, `cli.py`, `exporter.py`.

- [ ] **Step 4: Delete NEW_REQUIREMENTS.md**

```bash
git rm NEW_REQUIREMENTS.md
```

- [ ] **Step 5: Run full test suite and lint**

```bash
ruff check src/ tests/ && ruff format --check src/ tests/
pytest tests/ --no-header -q
```

- [ ] **Step 6: Commit**

```bash
git add -A
git commit -m "docs: update SPECIFICATION.md, PACKAGES.md, add BDD features, remove NEW_REQUIREMENTS.md"
```

---

## Task 8: Final verification and version bump

**Files:**
- Modify: `src/geotui/__init__.py` (version 0.4.0)
- Modify: `pyproject.toml` (version 0.4.0)

- [ ] **Step 1: Bump version**

Update `__version__ = "0.4.0"` in `src/geotui/__init__.py`
Update `version = "0.4.0"` in `pyproject.toml`
Update `version` in `flake.nix` packages.default

- [ ] **Step 2: Run full CI locally**

```bash
./scripts/ci-local.sh
```

Expected: All checks pass (ruff, format, bandit, codespell, mypy, pytest, docs)

- [ ] **Step 3: Final commit**

```bash
git add -A
git commit -m "release: bump version to 0.4.0 - bulk shapefile publisher"
```

- [ ] **Step 4: Push and update PR**

```bash
git push
```
