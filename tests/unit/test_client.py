"""Tests for GeoServer API client."""

import pytest

from geotui.client import ConnectionResult
from geotui.client import test_connection as _test_connection
from geotui.config import Connection


class TestConnectionResult:
    """Test suite for ConnectionResult."""

    def test_success_result(self) -> None:
        """Test successful connection result."""
        result = ConnectionResult(success=True, message="Connected", version="2.24.0")
        assert result.success is True
        assert result.version == "2.24.0"

    def test_failure_result(self) -> None:
        """Test failed connection result."""
        result = ConnectionResult(success=False, message="Connection refused")
        assert result.success is False
        assert result.version == ""


class TestTestConnection:
    """Test suite for test_connection function."""

    @pytest.mark.asyncio
    async def test_empty_url_returns_error(self) -> None:
        """Test that an empty URL returns an error immediately."""
        conn = Connection(name="Empty", url="")
        result = await _test_connection(conn)
        assert result.success is False
        assert "URL is required" in result.message

    @pytest.mark.asyncio
    async def test_unreachable_host(self) -> None:
        """Test connection to unreachable host."""
        conn = Connection(
            name="Bad",
            url="https://192.0.2.1:9999",
            username="admin",
            password="pass",
        )
        result = await _test_connection(conn, timeout=2.0)
        assert result.success is False

    @pytest.mark.asyncio
    async def test_invalid_host(self) -> None:
        """Test connection to invalid hostname."""
        conn = Connection(
            name="Invalid",
            url="https://this-host-does-not-exist.invalid",
            username="admin",
            password="pass",
        )
        result = await _test_connection(conn, timeout=2.0)
        assert result.success is False
