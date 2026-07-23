"""Tests for the bulk shapefile publisher engine."""

import io
import zipfile
from pathlib import Path

import pytest

from geotui.publisher import (
    NamingStrategy,
    PublishConfig,
    discover_bundles,
    resolve_layer_names,
)


@pytest.fixture
def shapefile_dir(tmp_path: Path) -> Path:
    """Create a directory with test shapefile bundles."""
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        (tmp_path / f"roads{ext}").touch()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"buildings{ext}").touch()
    (tmp_path / "broken.shp").touch()
    (tmp_path / "broken.shx").touch()
    (tmp_path / "readme.txt").touch()
    return tmp_path


@pytest.fixture
def nested_dir(tmp_path: Path) -> Path:
    """Create nested directories with shapefiles."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"rivers{ext}").touch()
        (sub / f"rivers{ext}").touch()
    return tmp_path


class TestDiscoverBundles:
    def test_finds_complete_bundles(self, shapefile_dir: Path) -> None:
        bundles, _warnings = discover_bundles(shapefile_dir, recurse=False)
        names = {b.name for b in bundles}
        assert "roads" in names
        assert "buildings" in names
        assert len(bundles) == 2

    def test_reports_incomplete_bundles(self, shapefile_dir: Path) -> None:
        _bundles, warnings = discover_bundles(shapefile_dir, recurse=False)
        assert len(warnings) == 1
        assert "broken" in warnings[0]

    def test_recurse_finds_subdirectories(self, nested_dir: Path) -> None:
        bundles, _warnings = discover_bundles(nested_dir, recurse=True)
        assert len(bundles) == 2

    def test_no_recurse_skips_subdirs(self, nested_dir: Path) -> None:
        bundles, _warnings = discover_bundles(nested_dir, recurse=False)
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
        names = resolve_layer_names(bundles, shapefile_dir, NamingStrategy.BASENAME)
        assert "roads" in names.values()

    def test_path_slug_avoids_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        names = resolve_layer_names(bundles, nested_dir, NamingStrategy.PATH_SLUG)
        values = list(names.values())
        assert len(values) == len(set(values))

    def test_basename_detects_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        with pytest.raises(ValueError, match="collision"):
            resolve_layer_names(bundles, nested_dir, NamingStrategy.BASENAME)

    def test_prefixed_basename(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        names = resolve_layer_names(
            bundles,
            shapefile_dir,
            NamingStrategy.PREFIXED_BASENAME,
            prefix="geo_",
        )
        assert all(v.startswith("geo_") for v in names.values())


class TestPublishConfig:
    def test_defaults(self) -> None:
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=Path("/data"),
        )
        assert cfg.concurrency == 4
        assert cfg.dry_run is False
        assert cfg.naming == NamingStrategy.BASENAME
        assert cfg.retry_max_attempts == 3


class TestPublishRunner:
    @pytest.mark.asyncio
    async def test_dry_run_skips_upload(self, shapefile_dir: Path) -> None:
        """Dry run discovers but does not upload."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=shapefile_dir,
            dry_run=True,
        )
        report = await run_publish(conn, cfg)
        dry_run_results = [r for r in report.results if r.status == "DRY_RUN"]
        skipped_results = [r for r in report.results if r.status == "skipped"]
        assert len(dry_run_results) == 2
        assert len(skipped_results) == 1  # incomplete 'broken' bundle
        assert skipped_results[0].layer_name == "broken"
        assert report.created == 0
        assert len(report.results) == 3

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

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path: Path) -> None:
        """Empty directory returns empty report."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=tmp_path,
        )
        report = await run_publish(conn, cfg)
        assert len(report.results) == 0


class TestExplicitSourceFiles:
    """PublishConfig.source_files restricts publishing to specific files."""

    def test_build_shapefile_bundles_includes_companions(
        self, shapefile_dir: Path
    ) -> None:
        from geotui.publisher import build_shapefile_bundles

        # Pass only the .shp; companions on disk should be picked up.
        bundles, _warnings = build_shapefile_bundles([shapefile_dir / "roads.shp"])
        assert len(bundles) == 1
        assert bundles[0].name == "roads"
        exts = {p.suffix for p in bundles[0].files}
        assert ".dbf" in exts and ".shx" in exts

    @pytest.mark.asyncio
    async def test_shapefile_source_files_restricts(self, shapefile_dir: Path) -> None:
        """Only the selected shapefile is published, not the whole folder."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="T", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=shapefile_dir,
            source_files=[shapefile_dir / "roads.shp"],
            dry_run=True,
        )
        report = await run_publish(conn, cfg)
        dry = [r for r in report.results if r.status == "DRY_RUN"]
        assert [r.layer_name for r in dry] == ["roads"]

    @pytest.mark.asyncio
    async def test_geotiff_source_files_restricts(self, tmp_path: Path) -> None:
        """Only the selected GeoTIFF is published, not every tif in the folder."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        (tmp_path / "dem.tif").write_bytes(b"II*\x00")
        (tmp_path / "other.tif").write_bytes(b"II*\x00")
        conn = Connection(name="T", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=tmp_path,
            source_files=[tmp_path / "dem.tif"],
            format_type="geotiff",
            dry_run=True,
        )
        report = await run_publish(conn, cfg)
        names = [r.layer_name for r in report.results if r.status == "DRY_RUN"]
        assert names == ["dem"]


@pytest.fixture
def raster_dir(tmp_path: Path) -> Path:
    """Create a directory with test GeoTIFF rasters."""
    (tmp_path / "dem.tif").write_bytes(b"II*\x00fake-geotiff-dem")
    (tmp_path / "landcover.tiff").write_bytes(b"II*\x00fake-geotiff-lc")
    (tmp_path / "readme.txt").touch()
    return tmp_path


class TestDiscoverRasters:
    def test_finds_tif_and_tiff(self, raster_dir: Path) -> None:
        from geotui.publisher import discover_rasters

        rasters = discover_rasters(raster_dir)
        names = sorted(r.name for r in rasters)
        assert names == ["dem", "landcover"]

    def test_ignores_non_rasters(self, raster_dir: Path) -> None:
        from geotui.publisher import discover_rasters

        rasters = discover_rasters(raster_dir)
        assert all(r.path.suffix.lower() in {".tif", ".tiff"} for r in rasters)

    def test_recurse(self, tmp_path: Path) -> None:
        from geotui.publisher import discover_rasters

        sub = tmp_path / "sub"
        sub.mkdir()
        (tmp_path / "top.tif").write_bytes(b"x")
        (sub / "nested.tif").write_bytes(b"x")
        assert len(discover_rasters(tmp_path, recurse=False)) == 1
        assert len(discover_rasters(tmp_path, recurse=True)) == 2


class TestResolveRasterNames:
    def test_basename(self, raster_dir: Path) -> None:
        from geotui.publisher import discover_rasters, resolve_raster_names

        rasters = discover_rasters(raster_dir)
        names = resolve_raster_names(rasters, raster_dir, NamingStrategy.BASENAME)
        assert sorted(names.values()) == ["dem", "landcover"]

    def test_prefixed(self, raster_dir: Path) -> None:
        from geotui.publisher import discover_rasters, resolve_raster_names

        rasters = discover_rasters(raster_dir)
        names = resolve_raster_names(
            rasters, raster_dir, NamingStrategy.PREFIXED_BASENAME, prefix="r_"
        )
        assert all(v.startswith("r_") for v in names.values())

    def test_collision_raises(self, tmp_path: Path) -> None:
        from geotui.publisher import SpatialFile, resolve_raster_names

        a = tmp_path / "a"
        b = tmp_path / "b"
        a.mkdir()
        b.mkdir()
        (a / "dem.tif").write_bytes(b"x")
        (b / "dem.tif").write_bytes(b"x")
        rasters = [
            SpatialFile.from_path(a / "dem.tif"),
            SpatialFile.from_path(b / "dem.tif"),
        ]
        with pytest.raises(ValueError, match="collision"):
            resolve_raster_names(rasters, tmp_path, NamingStrategy.BASENAME)


class TestRasterPublishRunner:
    @pytest.mark.asyncio
    async def test_dry_run(self, raster_dir: Path) -> None:
        """Raster dry run discovers but does not upload."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=raster_dir,
            format_type="geotiff",
            dry_run=True,
        )
        report = await run_publish(conn, cfg)
        dry = [r for r in report.results if r.status == "DRY_RUN"]
        assert len(dry) == 2
        assert report.created == 0

    @pytest.mark.asyncio
    async def test_connection_failure(self, raster_dir: Path) -> None:
        """Unreachable server yields error results for each raster."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=raster_dir,
            format_type="geotiff",
            retry_max_attempts=1,
        )
        report = await run_publish(conn, cfg)
        assert report.failed == 2
        assert all("Connection failed" in r.error for r in report.results)

    @pytest.mark.asyncio
    async def test_empty_directory(self, tmp_path: Path) -> None:
        """No rasters yields an empty report without contacting GeoServer."""
        from geotui.config import Connection
        from geotui.publisher import run_publish

        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=tmp_path,
            format_type="geotiff",
        )
        report = await run_publish(conn, cfg)
        assert len(report.results) == 0

    @pytest.mark.asyncio
    async def test_upload_invokes_geotiff_endpoint(
        self, raster_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """End-to-end: each raster is uploaded via upload_geotiff."""
        from types import SimpleNamespace
        from unittest.mock import AsyncMock, MagicMock

        from geotui import publisher
        from geotui.config import Connection
        from geotui.publisher import run_publish

        # Fake a successful connection test.
        monkeypatch.setattr(
            publisher,
            "test_connection",
            AsyncMock(
                return_value=SimpleNamespace(success=True, version="2.25", message="ok")
            ),
        )

        # Build a mock client usable as an async context manager.
        client = MagicMock()
        client.get_workspaces = AsyncMock(return_value=[SimpleNamespace(name="ws")])
        client.layer_exists = AsyncMock(return_value=False)
        client.upload_geotiff = AsyncMock(return_value=True)
        client.assign_style = AsyncMock(return_value=True)
        client._last_status_code = 201
        client._last_response_text = ""

        client_cm = MagicMock()
        client_cm.__aenter__ = AsyncMock(return_value=client)
        client_cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr(
            publisher, "GeoServerClient", MagicMock(return_value=client_cm)
        )

        conn = Connection(name="Test", url="https://example.invalid")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=raster_dir,
            format_type="geotiff",
        )
        report = await run_publish(conn, cfg)

        assert report.created == 2
        assert report.failed == 0
        assert client.upload_geotiff.await_count == 2
        # Store name equals the coverage/layer name (one store per raster).
        called_stores = sorted(
            call.args[1] for call in client.upload_geotiff.await_args_list
        )
        assert called_stores == ["dem", "landcover"]
