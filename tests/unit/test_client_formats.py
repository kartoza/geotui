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
