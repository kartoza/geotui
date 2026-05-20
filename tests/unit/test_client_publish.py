"""Tests for GeoServer client publish methods."""

import pytest

from geotui.client import GeoServerClient
from geotui.config import Connection


class TestClientPublishMethods:
    """Tests for layer_exists, upload_shapefile, assign_style, get_datastore_type."""

    @pytest.mark.asyncio
    async def test_layer_exists_unreachable(self, unreachable_conn: Connection) -> None:
        """Test layer_exists returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.layer_exists("ws", "layer")
            assert result is False

    @pytest.mark.asyncio
    async def test_get_datastore_type_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test get_datastore_type returns None for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.get_datastore_type("ws", "store")
            assert result is None

    @pytest.mark.asyncio
    async def test_upload_shapefile_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test upload_shapefile returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.upload_shapefile("ws", "store", b"fake-zip", False)
            assert result is False

    @pytest.mark.asyncio
    async def test_assign_style_unreachable(self, unreachable_conn: Connection) -> None:
        """Test assign_style returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.assign_style("ws", "layer", "style_name")
            assert result is False
