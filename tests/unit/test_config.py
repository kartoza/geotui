"""Tests for configuration management."""

import json
from pathlib import Path

import pytest

from geotui.config import AppConfig, ConfigManager, Connection


@pytest.fixture
def tmp_config(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with a temporary config file."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestConnection:
    """Test suite for Connection model."""

    def test_connection_has_auto_id(self) -> None:
        """Test that connections get auto-generated IDs."""
        conn = Connection(name="Test")
        assert conn.id
        assert len(conn.id) == 12

    def test_connection_fields(self) -> None:
        """Test connection field assignment."""
        conn = Connection(
            name="My GeoServer",
            url="https://geo.example.com/geoserver",
            username="admin",
            password="secret",
        )
        assert conn.name == "My GeoServer"
        assert conn.url == "https://geo.example.com/geoserver"
        assert conn.username == "admin"
        assert conn.password == "secret"

    def test_connection_defaults(self) -> None:
        """Test connection default values."""
        conn = Connection()
        assert conn.name == ""
        assert conn.url == ""
        assert conn.username == ""
        assert conn.password == ""
        assert conn.is_active is False

    def test_unique_ids(self) -> None:
        """Test that each connection gets a unique ID."""
        c1 = Connection(name="A")
        c2 = Connection(name="B")
        assert c1.id != c2.id


class TestAppConfig:
    """Test suite for AppConfig model."""

    def test_default_config(self) -> None:
        """Test default configuration values."""
        config = AppConfig()
        assert config.theme == "dark"
        assert config.language == "en"
        assert config.connections == []

    def test_config_with_connections(self) -> None:
        """Test config with connections list."""
        conn = Connection(name="Test")
        config = AppConfig(connections=[conn])
        assert len(config.connections) == 1
        assert config.connections[0].name == "Test"

    def test_config_serialization(self) -> None:
        """Test config round-trip through JSON."""
        conn = Connection(name="Test", url="https://example.com")
        config = AppConfig(connections=[conn])
        data = json.loads(config.model_dump_json())
        restored = AppConfig.model_validate(data)
        assert restored.connections[0].name == "Test"
        assert restored.connections[0].url == "https://example.com"


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_creates_default_config(self, tmp_config: ConfigManager) -> None:
        """Test that a new config manager creates default config."""
        assert tmp_config.config.connections == []

    def test_add_connection(self, tmp_config: ConfigManager) -> None:
        """Test adding a connection."""
        conn = Connection(name="Test", url="https://example.com")
        tmp_config.add_connection(conn)
        assert len(tmp_config.config.connections) == 1
        assert tmp_config.config.connections[0].name == "Test"

    def test_add_persists_to_disk(self, tmp_config: ConfigManager) -> None:
        """Test that adding a connection persists to disk."""
        conn = Connection(name="Persist")
        tmp_config.add_connection(conn)
        reloaded = ConfigManager(config_path=tmp_config._config_path)
        assert len(reloaded.config.connections) == 1
        assert reloaded.config.connections[0].name == "Persist"

    def test_remove_connection(self, tmp_config: ConfigManager) -> None:
        """Test removing a connection."""
        conn = Connection(name="ToRemove")
        tmp_config.add_connection(conn)
        assert tmp_config.remove_connection(conn.id) is True
        assert len(tmp_config.config.connections) == 0

    def test_remove_nonexistent(self, tmp_config: ConfigManager) -> None:
        """Test removing a non-existent connection returns False."""
        assert tmp_config.remove_connection("nope") is False

    def test_update_connection(self, tmp_config: ConfigManager) -> None:
        """Test updating a connection."""
        conn = Connection(name="Old", url="https://old.com")
        tmp_config.add_connection(conn)
        assert tmp_config.update_connection(conn.id, name="New", url="https://new.com")
        updated = tmp_config.get_connection(conn.id)
        assert updated is not None
        assert updated.name == "New"
        assert updated.url == "https://new.com"

    def test_update_nonexistent(self, tmp_config: ConfigManager) -> None:
        """Test updating a non-existent connection returns False."""
        assert tmp_config.update_connection("nope", name="X") is False

    def test_get_connection(self, tmp_config: ConfigManager) -> None:
        """Test getting a connection by ID."""
        conn = Connection(name="FindMe")
        tmp_config.add_connection(conn)
        found = tmp_config.get_connection(conn.id)
        assert found is not None
        assert found.name == "FindMe"

    def test_get_connection_not_found(self, tmp_config: ConfigManager) -> None:
        """Test getting a non-existent connection returns None."""
        assert tmp_config.get_connection("nope") is None

    def test_get_connection_by_name(self, tmp_config: ConfigManager) -> None:
        """Test getting a connection by name."""
        conn = Connection(name="ByName")
        tmp_config.add_connection(conn)
        found = tmp_config.get_connection_by_name("ByName")
        assert found is not None
        assert found.id == conn.id

    def test_get_connection_by_name_not_found(
        self, tmp_config: ConfigManager
    ) -> None:
        """Test getting a non-existent connection by name returns None."""
        assert tmp_config.get_connection_by_name("nope") is None

    def test_multiple_connections(self, tmp_config: ConfigManager) -> None:
        """Test managing multiple connections."""
        for i in range(5):
            tmp_config.add_connection(Connection(name=f"Server {i}"))
        assert len(tmp_config.config.connections) == 5
        tmp_config.remove_connection(tmp_config.config.connections[2].id)
        assert len(tmp_config.config.connections) == 4

    def test_corrupt_config_falls_back(self, tmp_path: Path) -> None:
        """Test that corrupt config file falls back to defaults."""
        config_file = tmp_path / "config.json"
        config_file.write_text("not valid json{{{", encoding="utf-8")
        cm = ConfigManager(config_path=config_file)
        assert cm.config.connections == []
