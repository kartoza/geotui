"""Tests for VRT discovery and the VRT publish path."""

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from geotui.config import Connection
from geotui.publisher import (
    PublishConfig,
    discover_spatial_files,
    discover_vrts,
    run_publish,
)

RASTER_VRT = """<VRTDataset rasterXSize="4" rasterYSize="4">
  <VRTRasterBand dataType="Byte" band="1">
    <SimpleSource>
      <SourceFilename relativeToVRT="1">a.tif</SourceFilename>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
"""

VECTOR_VRT = """<OGRVRTDataSource>
  <OGRVRTLayer name="pts">
    <SrcDataSource relativeToVRT="1">pts.csv</SrcDataSource>
  </OGRVRTLayer>
</OGRVRTDataSource>
"""


@pytest.fixture
def vrt_dir(tmp_path: Path) -> Path:
    (tmp_path / "a.tif").write_bytes(b"II*\x00tile")
    (tmp_path / "pts.csv").write_text("x,y\n1,2\n")
    (tmp_path / "dem.vrt").write_text(RASTER_VRT)
    (tmp_path / "pts.vrt").write_text(VECTOR_VRT)
    return tmp_path


class TestVRTDiscovery:
    def test_discover_vrts(self, vrt_dir: Path) -> None:
        vrts = discover_vrts(vrt_dir)
        assert sorted(v.name for v in vrts) == ["dem", "pts"]

    def test_spatial_discovery_includes_vrt_group(self, vrt_dir: Path) -> None:
        groups, _ = discover_spatial_files(vrt_dir)
        vrt_groups = [g for g in groups if g.format_type == "vrt"]
        assert len(vrt_groups) == 1
        assert len(vrt_groups[0].files) == 2


class TestVRTPublishRunner:
    @pytest.mark.asyncio
    async def test_dry_run(self, vrt_dir: Path) -> None:
        conn = Connection(name="T", url="https://192.0.2.1:9999")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=vrt_dir,
            format_type="vrt",
            dry_run=True,
        )
        report = await run_publish(conn, cfg)
        dry = [r for r in report.results if r.status == "DRY_RUN"]
        assert len(dry) == 2

    @pytest.mark.asyncio
    async def test_bundle_mode_uploads_and_creates_stores(
        self, vrt_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from geotui import publisher

        monkeypatch.setattr(
            publisher,
            "test_connection",
            AsyncMock(
                return_value=SimpleNamespace(success=True, version="2.25", message="ok")
            ),
        )

        client = MagicMock()
        client.get_workspaces = AsyncMock(return_value=[SimpleNamespace(name="ws")])
        client.get_extension_support = AsyncMock(
            return_value={"gdal": True, "ogr": True}
        )
        client.upload_resource = AsyncMock(return_value=True)
        client.create_vrt_coveragestore = AsyncMock(return_value=True)
        client.create_coverage = AsyncMock(return_value=True)
        client.create_ogr_vrt_datastore = AsyncMock(return_value=True)
        client.create_featuretype = AsyncMock(return_value=True)
        client._last_status_code = 201
        client._last_response_text = ""

        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr(publisher, "GeoServerClient", MagicMock(return_value=cm))

        conn = Connection(name="T", url="https://example.invalid")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=vrt_dir,
            format_type="vrt",
            vrt_mode="bundle",
        )
        report = await run_publish(conn, cfg)

        assert report.created == 2
        assert report.failed == 0
        # Raster VRT -> coverage store; vector VRT -> OGR datastore.
        assert client.create_vrt_coveragestore.await_count == 1
        assert client.create_ogr_vrt_datastore.await_count == 1
        # Bundle mode uploaded the .vrt files and their referenced sources.
        assert client.upload_resource.await_count >= 4

    @pytest.mark.asyncio
    async def test_server_path_mode_skips_upload(
        self, vrt_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        from geotui import publisher

        monkeypatch.setattr(
            publisher,
            "test_connection",
            AsyncMock(
                return_value=SimpleNamespace(success=True, version="2.25", message="ok")
            ),
        )
        client = MagicMock()
        client.get_workspaces = AsyncMock(return_value=[SimpleNamespace(name="ws")])
        client.get_extension_support = AsyncMock(
            return_value={"gdal": True, "ogr": True}
        )
        client.upload_resource = AsyncMock(return_value=True)
        client.create_vrt_coveragestore = AsyncMock(return_value=True)
        client.create_coverage = AsyncMock(return_value=True)
        client.create_ogr_vrt_datastore = AsyncMock(return_value=True)
        client.create_featuretype = AsyncMock(return_value=True)
        client._last_status_code = 201
        client._last_response_text = ""
        cm = MagicMock()
        cm.__aenter__ = AsyncMock(return_value=client)
        cm.__aexit__ = AsyncMock(return_value=False)
        monkeypatch.setattr(publisher, "GeoServerClient", MagicMock(return_value=cm))

        conn = Connection(name="T", url="https://example.invalid")
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=vrt_dir,
            format_type="vrt",
            vrt_mode="server_path",
        )
        report = await run_publish(conn, cfg)
        assert report.created == 2
        client.upload_resource.assert_not_awaited()
