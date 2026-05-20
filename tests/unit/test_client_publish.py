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
