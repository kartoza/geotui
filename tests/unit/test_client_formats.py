"""Tests for GeoPackage and GeoTIFF upload client methods."""

import pytest

from geotui.client import GeoServerClient
from geotui.config import Connection


class TestClientFormatUploads:
    """Tests for multi-format upload methods."""

    @pytest.mark.asyncio
    async def test_upload_gpkg_unreachable(self, unreachable_conn: Connection) -> None:
        """Test upload_gpkg returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.upload_gpkg("ws", "store", b"fake-gpkg")
            assert result is False

    @pytest.mark.asyncio
    async def test_upload_geotiff_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test upload_geotiff returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.upload_geotiff("ws", "store", b"fake-tiff")
            assert result is False

    @pytest.mark.asyncio
    async def test_recalculate_bbox_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test recalculate_bbox returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.recalculate_bbox("ws", "layer")
            assert result is False


class TestVRTClientMethods:
    """Tests for the VRT-related client methods."""

    @pytest.mark.asyncio
    async def test_upload_resource_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            assert await client.upload_resource("data/x.vrt", b"<VRTDataset/>") is False

    @pytest.mark.asyncio
    async def test_create_vrt_coveragestore_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            assert (
                await client.create_vrt_coveragestore("ws", "s", "file:x.vrt") is False
            )

    @pytest.mark.asyncio
    async def test_create_ogr_vrt_datastore_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            assert (
                await client.create_ogr_vrt_datastore("ws", "s", "file:x.vrt") is False
            )

    @pytest.mark.asyncio
    async def test_create_coverage_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            assert await client.create_coverage("ws", "s", "native", "layer") is False

    @pytest.mark.asyncio
    async def test_get_extension_support_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            support = await client.get_extension_support()
            assert support == {"gdal": False, "ogr": False}
