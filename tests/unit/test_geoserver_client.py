"""Tests for GeoServer REST API client extensions."""

import pytest

from geotui.client import GeoServerClient, GeoServerResource
from geotui.config import Connection


class TestGeoServerResource:
    """Test suite for GeoServerResource."""

    def test_resource_fields(self) -> None:
        """Test resource field assignment."""
        r = GeoServerResource(name="test_ws", resource_type="workspace")
        assert r.name == "test_ws"
        assert r.resource_type == "workspace"
        assert r.children == []
        assert r.href == ""

    def test_resource_with_children(self) -> None:
        """Test resource with child resources."""
        child = GeoServerResource(name="layer1", resource_type="layer")
        parent = GeoServerResource(
            name="store1", resource_type="datastore", children=[child]
        )
        assert len(parent.children) == 1
        assert parent.children[0].name == "layer1"


class TestGeoServerClient:
    """Test suite for GeoServerClient."""

    def test_client_initialization(self) -> None:
        """Test client is initialized with connection details."""
        conn = Connection(
            name="Test",
            url="https://example.com/geoserver",
            username="admin",
            password="pass",
        )
        client = GeoServerClient(conn)
        assert client._base_url == "https://example.com/geoserver"

    def test_client_strips_trailing_slash(self) -> None:
        """Test that trailing slash is stripped from URL."""
        conn = Connection(url="https://example.com/geoserver/")
        client = GeoServerClient(conn)
        assert client._base_url == "https://example.com/geoserver"

    @pytest.mark.asyncio
    async def test_get_workspaces_unreachable(self) -> None:
        """Test get_workspaces with unreachable server returns empty list."""
        conn = Connection(url="https://192.0.2.1:9999")
        client = GeoServerClient(conn, timeout=1.0)
        result = await client.get_workspaces()
        assert result == []

    @pytest.mark.asyncio
    async def test_get_datastores_unreachable(self) -> None:
        """Test get_datastores with unreachable server returns empty list."""
        conn = Connection(url="https://192.0.2.1:9999")
        client = GeoServerClient(conn, timeout=1.0)
        result = await client.get_datastores("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_coveragestores_unreachable(self) -> None:
        """Test get_coveragestores with unreachable server returns empty list."""
        conn = Connection(url="https://192.0.2.1:9999")
        client = GeoServerClient(conn, timeout=1.0)
        result = await client.get_coveragestores("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_wmsstores_unreachable(self) -> None:
        """Test get_wmsstores with unreachable server returns empty list."""
        conn = Connection(url="https://192.0.2.1:9999")
        client = GeoServerClient(conn, timeout=1.0)
        result = await client.get_wmsstores("test")
        assert result == []

    @pytest.mark.asyncio
    async def test_get_full_tree_unreachable(self) -> None:
        """Test get_full_tree with unreachable server returns empty list."""
        conn = Connection(url="https://192.0.2.1:9999")
        client = GeoServerClient(conn, timeout=1.0)
        result = await client.get_full_tree()
        assert result == []
