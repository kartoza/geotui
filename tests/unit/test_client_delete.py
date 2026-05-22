"""Tests for GeoServer client delete methods."""

import pytest

from geotui.client import GeoServerClient
from geotui.config import Connection


class TestClientDeleteMethods:
    """Tests for delete_datastore, delete_coveragestore, delete_workspace."""

    @pytest.mark.asyncio
    async def test_delete_datastore_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test delete_datastore returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.delete_datastore("ws", "store", recurse=True)
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_coveragestore_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test delete_coveragestore returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.delete_coveragestore("ws", "store", recurse=True)
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_workspace_unreachable(
        self, unreachable_conn: Connection
    ) -> None:
        """Test delete_workspace returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.delete_workspace("ws", recurse=True)
            assert result is False

    @pytest.mark.asyncio
    async def test_delete_layer_unreachable(self, unreachable_conn: Connection) -> None:
        """Test delete_layer returns False for unreachable server."""
        async with GeoServerClient(unreachable_conn, timeout=1.0) as client:
            result = await client.delete_layer("ws", "my_store", "my_layer")
            assert result is False
