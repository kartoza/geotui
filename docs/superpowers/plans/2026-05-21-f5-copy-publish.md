# F5 Copy-to-Publish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the F2-menu bulk publish with Midnight Commander's F5 copy paradigm: select folder on left, select workspace/store on right, press F5 to publish all supported spatial files.

**Architecture:** Extend the publisher's discovery to detect shapefiles, GeoPackage, and GeoTIFF files, grouping them by format. Add client methods for GeoPackage and GeoTIFF upload. Wire F5 in the app to read context from both panes, auto-create stores per format, upload concurrently with live progress, and generate reports automatically.

**Tech Stack:** Python 3.10+, httpx, asyncio, Textual, fpdf2

---

## File Structure

| File | Change | Responsibility |
|------|--------|----------------|
| `src/geotui/publisher.py` | Modify | Add `SpatialFileGroup`, `discover_spatial_files()`, extend `run_publish()` for multi-format |
| `src/geotui/client.py` | Modify | Add `upload_gpkg()`, `upload_geotiff()`, `recalculate_bbox()` |
| `src/geotui/widgets/file_pane.py` | Modify | Add `get_selected_path()` method |
| `src/geotui/widgets/geoserver_tree.py` | Modify | Add `action_copy_from_local()`, remove `action_bulk_publish` |
| `src/geotui/app.py` | Modify | Wire F5 `action_copy()` to delegate to tree |
| `src/geotui/screens/context_menu.py` | Modify | Remove "Bulk Publish Shapefiles" option |
| `tests/unit/test_spatial_discovery.py` | Create | Tests for multi-format discovery |
| `tests/unit/test_f5_copy.py` | Create | Tests for F5 workflow integration |
| `tests/bdd/features/f5_copy_publish.feature` | Create | BDD scenarios |

---

## Task 1: Multi-format spatial file discovery

**Files:**
- Modify: `src/geotui/publisher.py`
- Create: `tests/unit/test_spatial_discovery.py`

- [ ] **Step 1: Write failing tests for multi-format discovery**

```python
# tests/unit/test_spatial_discovery.py
"""Tests for multi-format spatial file discovery."""

from pathlib import Path

import pytest

from geotui.publisher import SpatialFileGroup, discover_spatial_files


@pytest.fixture
def mixed_dir(tmp_path: Path) -> Path:
    """Create directory with mixed spatial formats."""
    # Complete shapefile
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        (tmp_path / f"roads{ext}").touch()
    # Another shapefile
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"buildings{ext}").touch()
    # Incomplete shapefile
    (tmp_path / "broken.shp").touch()
    (tmp_path / "broken.shx").touch()
    # GeoPackage
    (tmp_path / "parcels.gpkg").touch()
    (tmp_path / "zones.gpkg").touch()
    # GeoTIFF
    (tmp_path / "dem.tif").touch()
    (tmp_path / "ortho.tiff").touch()
    # Non-spatial
    (tmp_path / "readme.txt").touch()
    (tmp_path / "data.csv").touch()
    return tmp_path


@pytest.fixture
def shp_only_dir(tmp_path: Path) -> Path:
    """Directory with only shapefiles."""
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"rivers{ext}").touch()
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory."""
    return tmp_path


class TestDiscoverSpatialFiles:
    def test_finds_all_formats(self, mixed_dir: Path) -> None:
        groups, warnings = discover_spatial_files(mixed_dir)
        format_names = {g.format_type for g in groups}
        assert "shapefile" in format_names
        assert "geopackage" in format_names
        assert "geotiff" in format_names

    def test_shapefile_group_has_bundles(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        shp = next(g for g in groups if g.format_type == "shapefile")
        names = {b.name for b in shp.files}
        assert "roads" in names
        assert "buildings" in names
        assert len(shp.files) == 2

    def test_geopackage_group(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        gpkg = next(g for g in groups if g.format_type == "geopackage")
        names = {f.stem for f in gpkg.files}
        assert "parcels" in names
        assert "zones" in names

    def test_geotiff_group(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        tif = next(g for g in groups if g.format_type == "geotiff")
        names = {f.stem for f in tif.files}
        assert "dem" in names
        assert "ortho" in names

    def test_incomplete_shapefile_warned(self, mixed_dir: Path) -> None:
        groups, warnings = discover_spatial_files(mixed_dir)
        assert len(warnings) == 1
        assert "broken" in warnings[0]

    def test_empty_directory(self, empty_dir: Path) -> None:
        groups, warnings = discover_spatial_files(empty_dir)
        assert len(groups) == 0
        assert len(warnings) == 0

    def test_single_format(self, shp_only_dir: Path) -> None:
        groups, _ = discover_spatial_files(shp_only_dir)
        assert len(groups) == 1
        assert groups[0].format_type == "shapefile"

    def test_group_store_type(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        types = {g.format_type: g.store_type for g in groups}
        assert types["shapefile"] == "Directory of spatial files (shapefiles)"
        assert types["geopackage"] == "GeoPackage"
        assert types["geotiff"] == "GeoTIFF"

    def test_group_total_size(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        for g in groups:
            assert g.total_size >= 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_spatial_discovery.py -v`
Expected: FAIL with ImportError

- [ ] **Step 3: Implement SpatialFileGroup and discover_spatial_files**

Add to `src/geotui/publisher.py` after the existing `ShapefileBundle` class:

```python
@dataclass
class SpatialFile:
    """A single spatial file to be published.

    Attributes:
        name: Layer name (stem of file).
        path: Path to the file.
        size: File size in bytes.
    """

    name: str
    path: Path
    size: int = 0

    def __post_init__(self) -> None:
        if self.path.exists():
            self.size = self.path.stat().st_size


@dataclass
class SpatialFileGroup:
    """A group of spatial files of the same format.

    Attributes:
        format_type: Format identifier (shapefile, geopackage, geotiff).
        store_type: GeoServer store type string for this format.
        files: List of spatial files or shapefile bundles.
        store_category: 'vector' or 'raster' for store creation.
    """

    format_type: str
    store_type: str
    store_category: str
    files: list[SpatialFile | ShapefileBundle]

    @property
    def total_size(self) -> int:
        """Total size of all files in bytes."""
        total = 0
        for f in self.files:
            if isinstance(f, ShapefileBundle):
                total += f.total_size
            else:
                total += f.size
        return total


# Format detection constants
_GEOTIFF_EXTENSIONS = {".tif", ".tiff"}
_GEOPACKAGE_EXTENSIONS = {".gpkg"}

_FORMAT_STORE_MAP = {
    "shapefile": ("Directory of spatial files (shapefiles)", "vector"),
    "geopackage": ("GeoPackage", "vector"),
    "geotiff": ("GeoTIFF", "raster"),
}


def discover_spatial_files(
    directory: Path,
) -> tuple[list[SpatialFileGroup], list[str]]:
    """Discover all supported spatial files in a directory.

    Finds shapefiles, GeoPackage, and GeoTIFF files. Groups them
    by format type. Does not recurse into subdirectories.

    Args:
        directory: Directory to scan.

    Returns:
        Tuple of (groups by format, warning messages).
    """
    groups: list[SpatialFileGroup] = []
    warnings: list[str] = []

    # Discover shapefiles using existing logic
    bundles, shp_warnings = discover_bundles(directory, recurse=False)
    warnings.extend(shp_warnings)
    if bundles:
        store_type, category = _FORMAT_STORE_MAP["shapefile"]
        groups.append(SpatialFileGroup(
            format_type="shapefile",
            store_type=store_type,
            store_category=category,
            files=list(bundles),
        ))

    # Discover GeoPackage files
    gpkg_files = sorted(directory.glob("*.gpkg"))
    if gpkg_files:
        store_type, category = _FORMAT_STORE_MAP["geopackage"]
        groups.append(SpatialFileGroup(
            format_type="geopackage",
            store_type=store_type,
            store_category=category,
            files=[SpatialFile(name=f.stem, path=f) for f in gpkg_files],
        ))

    # Discover GeoTIFF files
    tif_files = sorted(
        f for f in directory.iterdir()
        if f.suffix.lower() in _GEOTIFF_EXTENSIONS
    )
    if tif_files:
        store_type, category = _FORMAT_STORE_MAP["geotiff"]
        groups.append(SpatialFileGroup(
            format_type="geotiff",
            store_type=store_type,
            store_category=category,
            files=[SpatialFile(name=f.stem, path=f) for f in tif_files],
        ))

    return groups, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_spatial_discovery.py -v`
Expected: PASS (all 9 tests)

- [ ] **Step 5: Lint, format, full suite**

Run: `ruff check src/ tests/ && ruff format src/ tests/ && pytest tests/ --no-header -q`

- [ ] **Step 6: Commit**

```
git add src/geotui/publisher.py tests/unit/test_spatial_discovery.py
git commit -m "feat: multi-format spatial file discovery (shapefile, gpkg, geotiff)"
```

---

## Task 2: Client methods for GeoPackage and GeoTIFF upload

**Files:**
- Modify: `src/geotui/client.py`
- Create: `tests/unit/test_client_formats.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_client_formats.py
"""Tests for GeoPackage and GeoTIFF upload client methods."""

import pytest

from geotui.client import GeoServerClient
from geotui.config import Connection


class TestClientFormatUploads:
    """Tests for multi-format upload methods."""

    @pytest.mark.asyncio
    async def test_upload_gpkg_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test upload_gpkg returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.upload_gpkg(
                "ws", "store", b"fake-gpkg"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_upload_geotiff_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test upload_geotiff returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.upload_geotiff(
                "ws", "store", b"fake-tiff"
            )
            assert result is False

    @pytest.mark.asyncio
    async def test_recalculate_bbox_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test recalculate_bbox returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.recalculate_bbox("ws", "layer")
            assert result is False
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_client_formats.py -v`
Expected: FAIL with AttributeError

- [ ] **Step 3: Implement upload methods**

Add to `GeoServerClient` in `src/geotui/client.py`, after `upload_shapefile`:

```python
    async def upload_gpkg(
        self,
        workspace: str,
        store: str,
        data: bytes,
        update: bool = False,
    ) -> bool:
        """Upload a GeoPackage file to a datastore.

        Args:
            workspace: Workspace name.
            store: Datastore name.
            data: GeoPackage file bytes.
            update: If True, overwrite existing.

        Returns:
            True if upload succeeded.
        """
        path = (
            f"/rest/workspaces/{workspace}/datastores/{store}"
            f"/file.gpkg?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, data, "application/x-gpkg")
        return status in (200, 201)

    async def upload_geotiff(
        self,
        workspace: str,
        store: str,
        data: bytes,
        update: bool = False,
    ) -> bool:
        """Upload a GeoTIFF file to a coverage store.

        Args:
            workspace: Workspace name.
            store: Coverage store name.
            data: GeoTIFF file bytes.
            update: If True, overwrite existing.

        Returns:
            True if upload succeeded.
        """
        path = (
            f"/rest/workspaces/{workspace}/coveragestores/{store}"
            f"/file.geotiff?configure=first"
        )
        if update:
            path += "&update=overwrite"
        status = await self._put(path, data, "image/tiff")
        return status in (200, 201)

    async def recalculate_bbox(
        self, workspace: str, layer_name: str
    ) -> bool:
        """Recalculate bounding box for a layer.

        Args:
            workspace: Workspace name.
            layer_name: Layer name.

        Returns:
            True if successful.
        """
        return await self._put_json(
            f"/rest/layers/{workspace}:{layer_name}.json",
            {
                "layer": {
                    "resource": {
                        "recalculate": "nativebbox,latlonbbox"
                    }
                }
            },
        )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/test_client_formats.py -v`
Expected: PASS (all 3 tests)

- [ ] **Step 5: Lint, format, full suite**

Run: `ruff check src/ tests/ && ruff format src/ tests/ && pytest tests/ --no-header -q`

- [ ] **Step 6: Commit**

```
git add src/geotui/client.py tests/unit/test_client_formats.py
git commit -m "feat: add upload_gpkg, upload_geotiff, recalculate_bbox to client"
```

---

## Task 3: FilePane get_selected_path method

**Files:**
- Modify: `src/geotui/widgets/file_pane.py`
- Modify: `tests/unit/test_app.py` (or new test)

- [ ] **Step 1: Write failing test**

Add to a new file `tests/unit/test_file_pane.py`:

```python
# tests/unit/test_file_pane.py
"""Tests for FilePane widget."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager
from geotui.widgets.file_pane import FilePane


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestFilePane:
    @pytest.mark.asyncio
    async def test_get_selected_path_returns_current(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that get_selected_path returns the current path."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            path = pane.get_selected_path()
            assert path is not None
            assert isinstance(path, Path)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/test_file_pane.py -v`
Expected: FAIL with AttributeError

- [ ] **Step 3: Implement get_selected_path**

Add to `FilePane` in `src/geotui/widgets/file_pane.py`:

```python
    def get_selected_path(self) -> Path:
        """Get the currently selected/displayed directory path.

        Returns:
            The current directory path.
        """
        return Path(self.current_path)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/test_file_pane.py -v`
Expected: PASS

- [ ] **Step 5: Lint, commit**

```
git add src/geotui/widgets/file_pane.py tests/unit/test_file_pane.py
git commit -m "feat: add get_selected_path to FilePane"
```

---

## Task 4: Wire F5 action_copy and GeoServer tree copy handler

**Files:**
- Modify: `src/geotui/app.py`
- Modify: `src/geotui/widgets/geoserver_tree.py`
- Modify: `src/geotui/screens/context_menu.py`
- Create: `tests/unit/test_f5_copy.py`

- [ ] **Step 1: Write failing tests**

```python
# tests/unit/test_f5_copy.py
"""Tests for F5 copy-to-publish workflow."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def connected_config(tmp_path: Path) -> ConfigManager:
    """Config with active connection."""
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(
        Connection(name="Test", url="https://192.0.2.1:9999", is_active=True)
    )
    return cm


class TestF5Copy:
    @pytest.mark.asyncio
    async def test_f5_no_connection_warns(self, tmp_path: Path) -> None:
        """F5 warns when no GeoServer connection."""
        cm = ConfigManager(config_path=tmp_path / "config.json")
        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            await pilot.press("f5")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_f5_with_connection_no_selection_warns(
        self, connected_config: ConfigManager
    ) -> None:
        """F5 warns when no workspace/store selected."""
        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            await pilot.press("f5")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_bulk_publish_removed_from_f2(
        self, connected_config: ConfigManager
    ) -> None:
        """Bulk Publish Shapefiles no longer in F2 menu."""
        from geotui.screens.context_menu import ContextMenuScreen
        from geotui.widgets.dual_pane import DualPane

        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/test_f5_copy.py -v`

- [ ] **Step 3: Update app.py action_copy**

Replace the stub `action_copy` in `src/geotui/app.py`:

```python
    def action_copy(self) -> None:
        """F5 Copy: publish local spatial files to GeoServer."""
        from geotui.widgets.geoserver_tree import GeoServerTree

        tree = self.query_one("#right-pane", GeoServerTree)
        if tree.connection is None:
            self.notify(
                _("Connect to a GeoServer first (F9)"),
                severity="error",
            )
            return
        tree.action_copy_from_local()
```

- [ ] **Step 4: Remove Bulk Publish from F2 menu**

In `src/geotui/screens/context_menu.py`, in `on_mount()`, remove:
```python
            opts.add_option(
                Option(_("Bulk Publish Shapefiles"), id="gs_bulk_publish")
            )
```

In `src/geotui/app.py`, in `handle_menu_result`, remove:
```python
            elif action_id == "gs_bulk_publish":
                tree.action_bulk_publish()
```

- [ ] **Step 5: Add action_copy_from_local to GeoServerTree**

Add to `GeoServerTree` in `src/geotui/widgets/geoserver_tree.py`. Remove `action_bulk_publish` and `_run_bulk_publish`. Replace with:

```python
    def action_copy_from_local(self) -> None:
        """Copy spatial files from the local pane to GeoServer.

        Reads the selected path from the left pane and the selected
        workspace/store from the right pane tree, then publishes
        all supported spatial files.
        """
        if self.connection is None:
            self.app.notify(
                _("No connection active"), severity="warning"
            )
            return

        # Get source directory from left pane
        from geotui.widgets.file_pane import FilePane

        left_pane = self.app.query_one("#left-pane", FilePane)
        source_dir = left_pane.get_selected_path()

        if not source_dir.is_dir():
            self.app.notify(
                _("Select a folder in the left pane"),
                severity="warning",
            )
            return

        # Get target workspace from right pane
        ws_name = self._get_selected_workspace()
        if not ws_name:
            self.app.notify(
                _("Select a workspace or store in the tree"),
                severity="warning",
            )
            return

        # Discover spatial files
        from geotui.publisher import discover_spatial_files

        groups, warnings = discover_spatial_files(source_dir)
        if not groups:
            self.app.notify(
                _("No supported spatial files found in ")
                + str(source_dir),
                severity="warning",
            )
            return

        # Show summary and start upload
        total_files = sum(len(g.files) for g in groups)
        format_summary = ", ".join(
            f"{len(g.files)} {g.format_type}" for g in groups
        )
        self.app.notify(
            f"Publishing {total_files} files ({format_summary}) "
            f"to {ws_name}",
            severity="information",
        )

        self.run_worker(
            self._run_copy_publish(
                source_dir, ws_name, groups, warnings
            ),
            exit_on_error=False,
        )

    async def _run_copy_publish(
        self,
        source_dir: Path,
        workspace: str,
        groups: list,
        warnings: list[str],
    ) -> None:
        """Execute the F5 copy-to-publish operation.

        Args:
            source_dir: Source directory path.
            workspace: Target workspace name.
            groups: Discovered spatial file groups.
            warnings: Discovery warnings.
        """
        from geotui.publisher import (
            NamingStrategy,
            PublishConfig,
            run_publish,
        )
        from geotui.report import (
            generate_json_report,
            generate_pdf_report,
        )

        if self.connection is None:
            return

        folder_name = source_dir.name

        # Process each format group
        all_results = []
        for group in groups:
            store_name = f"{folder_name}_{group.format_type}"
            config = PublishConfig(
                workspace=workspace,
                datastore=store_name,
                source_directory=source_dir,
                naming=NamingStrategy.BASENAME,
                concurrency=4,
            )

            def progress(
                current: int, total: int, name: str
            ) -> None:
                if self.is_mounted:
                    status = self.query_one("#tree-status", Static)
                    status.update(
                        f"Publishing {current}/{total}: {name}"
                    )

            report = await run_publish(
                self.connection, config, progress
            )
            all_results.append(report)

            # Refresh tree after each group
            if self.is_mounted:
                self.refresh_tree()

        # Generate combined report
        if self.is_mounted and all_results:
            from datetime import datetime, timezone

            ts = datetime.now(tz=timezone.utc).strftime(
                "%Y%m%d-%H%M%S"
            )
            out_dir = (
                Path.home() / ".local/share/geotui/reports"
            )
            pdf_path = out_dir / f"publish-{ts}.pdf"
            json_path = out_dir / f"publish-{ts}.json"

            # Use the first report as base, merge results
            combined = all_results[0]
            for r in all_results[1:]:
                combined.results.extend(r.results)
                combined.warnings.extend(r.warnings)
                combined.wall_clock_seconds += (
                    r.wall_clock_seconds
                )

            generate_pdf_report(combined, pdf_path)
            generate_json_report(combined, json_path)

            created = combined.created
            updated = combined.updated
            failed = combined.failed
            self.app.notify(
                f"Created: {created} | Updated: {updated}"
                f" | Failed: {failed}\n"
                f"Report: {pdf_path}",
                severity="information",
                timeout=10,
            )
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `pytest tests/unit/test_f5_copy.py -v && pytest tests/ --no-header -q`

- [ ] **Step 7: Lint, format, commit**

Run: `ruff check src/ tests/ && ruff format src/ tests/`

```
git add src/geotui/app.py src/geotui/widgets/geoserver_tree.py src/geotui/screens/context_menu.py tests/unit/test_f5_copy.py
git commit -m "feat: F5 copy-to-publish from local pane to GeoServer"
```

---

## Task 5: Remove old bulk publish code and cleanup

**Files:**
- Modify: `src/geotui/widgets/geoserver_tree.py`
- Modify: `tests/unit/test_publish_tui.py`
- Modify: `tests/unit/test_geoserver_actions.py`

- [ ] **Step 1: Remove action_bulk_publish references from tests**

In `tests/unit/test_publish_tui.py`, remove or update any tests referencing `action_bulk_publish` or `gs_bulk_publish`. Keep tests that verify the F2 menu opens and general structure.

- [ ] **Step 2: Remove _do_create bulk_publish branch**

In `src/geotui/widgets/geoserver_tree.py`, remove the `elif self._current_action == "bulk_publish":` branch from `_do_create()`.

- [ ] **Step 3: Run full test suite**

Run: `pytest tests/ --no-header -q`
Expected: All pass

- [ ] **Step 4: Lint, commit**

```
git add -A
git commit -m "refactor: remove old bulk publish form, F5 replaces it"
```

---

## Task 6: BDD feature and documentation

**Files:**
- Create: `tests/bdd/features/f5_copy_publish.feature`
- Modify: `SPECIFICATION.md`

- [ ] **Step 1: Write BDD feature**

```gherkin
# tests/bdd/features/f5_copy_publish.feature
Feature: F5 Copy to Publish
  As a GeoServer administrator
  I want to press F5 to copy spatial files from my local folder
  to a GeoServer workspace
  So that I can publish data using the familiar MC workflow

  Scenario: F5 with no connection shows error
    Given the application is running with no connections
    When I press F5
    Then I should see an error about connecting first

  Scenario: F5 discovers multiple formats
    Given a folder with shapefiles, GeoPackage, and GeoTIFF files
    When I run spatial file discovery
    Then groups for shapefile, geopackage, and geotiff are found

  Scenario: F5 auto-creates stores per format
    Given a connected GeoServer instance
    And a folder with shapefiles and GeoTIFF files
    When I press F5 with a workspace selected
    Then a shapefile store and a GeoTIFF store are created

  Scenario: Bulk Publish removed from F2 menu
    Given the application is running with a connection
    When I open the F2 GeoServer menu
    Then Bulk Publish Shapefiles should not be listed
```

- [ ] **Step 2: Update SPECIFICATION.md**

Add/update FR-008 to reflect F5 copy paradigm replacing F2 bulk publish. Add mention of multi-format support (shapefile, GeoPackage, GeoTIFF).

- [ ] **Step 3: Lint, full suite, commit**

```
git add -A
git commit -m "docs: F5 copy-to-publish BDD feature and spec update"
```

---

## Task 7: Final verification

**Files:**
- Modify: `src/geotui/__init__.py` (version bump to 0.5.0)
- Modify: `pyproject.toml`
- Modify: `flake.nix`

- [ ] **Step 1: Version bump**

Update version to `0.5.0` in `__init__.py`, `pyproject.toml`, `flake.nix`.

- [ ] **Step 2: Run full CI locally**

Run: `./scripts/ci-local.sh`
Expected: All checks pass

- [ ] **Step 3: Commit and push**

```
git add -A
git commit -m "release: v0.5.0 - F5 copy-to-publish workflow"
git push
```
