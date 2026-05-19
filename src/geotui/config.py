"""Configuration model and manager for GeoTUI.

Manages GeoServer connection instances with atomic JSON persistence.
Follows XDG Base Directory specification for config storage.
"""

import json
import os
import tempfile
import threading
import uuid
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class Connection(BaseModel):
    """A GeoServer connection configuration.

    Attributes:
        id: Unique identifier for this connection.
        name: Human-readable connection name.
        url: GeoServer base URL (e.g. https://geoserver.example.com/geoserver).
        username: GeoServer username.
        password: GeoServer password.
        is_active: Whether this is the currently selected connection.
    """

    model_config = ConfigDict(extra="allow")

    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str = ""
    url: str = ""
    username: str = ""
    password: str = ""
    is_active: bool = False


class AppConfig(BaseModel):
    """Root application configuration.

    Attributes:
        theme: Application theme name.
        language: Interface language code.
        connections: List of GeoServer connections.
    """

    model_config = ConfigDict(extra="allow")

    theme: str = "dark"
    language: str = "en"
    connections: list[Connection] = Field(default_factory=list)


def _get_config_dir() -> Path:
    """Get XDG-compliant config directory.

    Returns:
        Path to the configuration directory.
    """
    xdg = os.environ.get("XDG_CONFIG_HOME", "")
    if xdg:
        base = Path(xdg)
    else:
        base = Path.home() / ".config"
    config_dir = base / "geotui"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir


def _get_config_path() -> Path:
    """Get the configuration file path.

    Returns:
        Path to config.json.
    """
    return _get_config_dir() / "config.json"


class ConfigManager:
    """Thread-safe configuration manager with atomic persistence.

    Provides CRUD operations for GeoServer connections and handles
    loading/saving configuration to disk.
    """

    def __init__(self, config_path: Path | None = None) -> None:
        """Initialize the config manager.

        Args:
            config_path: Override path for config file. Uses XDG default if None.
        """
        self._lock = threading.RLock()
        self._config_path = config_path or _get_config_path()
        self.config = self._load()

    def _load(self) -> AppConfig:
        """Load configuration from disk.

        Returns:
            Loaded or default AppConfig.
        """
        if self._config_path.exists():
            try:
                data = json.loads(self._config_path.read_text(encoding="utf-8"))
                return AppConfig.model_validate(data)
            except (json.JSONDecodeError, ValueError):
                return AppConfig()
        return AppConfig()

    def save(self) -> None:
        """Persist configuration to disk atomically."""
        with self._lock:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            data = self.config.model_dump_json(indent=2)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._config_path.parent), suffix=".tmp"
            )
            try:
                os.write(fd, data.encode("utf-8"))
                os.close(fd)
                os.replace(tmp_path, str(self._config_path))
            except Exception:
                os.close(fd) if not os.get_inheritable(fd) else None
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
                raise

    def add_connection(self, conn: Connection) -> None:
        """Add a new connection.

        Args:
            conn: Connection to add.
        """
        with self._lock:
            self.config.connections.append(conn)
            self.save()

    def update_connection(self, conn_id: str, **kwargs: str | bool) -> bool:
        """Update an existing connection's fields.

        Args:
            conn_id: ID of the connection to update.
            **kwargs: Fields to update.

        Returns:
            True if the connection was found and updated.
        """
        with self._lock:
            for conn in self.config.connections:
                if conn.id == conn_id:
                    for key, value in kwargs.items():
                        if hasattr(conn, key):
                            setattr(conn, key, value)
                    self.save()
                    return True
        return False

    def remove_connection(self, conn_id: str) -> bool:
        """Remove a connection by ID.

        Args:
            conn_id: ID of the connection to remove.

        Returns:
            True if the connection was found and removed.
        """
        with self._lock:
            before = len(self.config.connections)
            self.config.connections = [
                c for c in self.config.connections if c.id != conn_id
            ]
            if len(self.config.connections) < before:
                self.save()
                return True
        return False

    def get_connection(self, conn_id: str) -> Connection | None:
        """Get a connection by ID.

        Args:
            conn_id: ID of the connection to find.

        Returns:
            The Connection if found, None otherwise.
        """
        for conn in self.config.connections:
            if conn.id == conn_id:
                return conn
        return None

    def get_connection_by_name(self, name: str) -> Connection | None:
        """Get a connection by name.

        Args:
            name: Name of the connection to find.

        Returns:
            The Connection if found, None otherwise.
        """
        for conn in self.config.connections:
            if conn.name == name:
                return conn
        return None
