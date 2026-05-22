"""Configuration model and manager for GeoTUI.

Manages GeoServer connection instances with atomic JSON persistence.
Follows XDG Base Directory specification for config storage.
Credentials are encrypted at rest using Fernet (AES-128-CBC + HMAC-SHA256)
with a key derived from the user's master password via PBKDF2-HMAC-SHA256.
"""

import base64
import json
import os
import secrets
import sys
import tempfile
import threading
import uuid
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel, ConfigDict, Field

_PBKDF2_ITERATIONS = 600_000


def _derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a Fernet key from a master password and salt.

    Uses PBKDF2-HMAC-SHA256 with 600k iterations (OWASP recommendation).

    Args:
        master_password: The user's master password.
        salt: Random salt bytes (16 bytes recommended).

    Returns:
        URL-safe base64-encoded 32-byte key suitable for Fernet.
    """
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=_PBKDF2_ITERATIONS,
    )
    return base64.urlsafe_b64encode(kdf.derive(master_password.encode("utf-8")))


def encrypt_value(plaintext: str, fernet: Fernet) -> str:
    """Encrypt a string value and return base64 token.

    Args:
        plaintext: Value to encrypt.
        fernet: Initialised Fernet instance.

    Returns:
        Fernet token as a UTF-8 string.
    """
    if not plaintext:
        return ""
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_value(token: str, fernet: Fernet) -> str:
    """Decrypt a Fernet token back to plaintext.

    Args:
        token: Fernet token string.
        fernet: Initialised Fernet instance.

    Returns:
        Decrypted plaintext string.

    Raises:
        InvalidToken: If the token is invalid or the key is wrong.
    """
    if not token:
        return ""
    return fernet.decrypt(token.encode("utf-8")).decode("utf-8")


def verify_master_password(master_password: str, salt: bytes, check_token: str) -> bool:
    """Verify a master password against a stored check token.

    Args:
        master_password: Password to verify.
        salt: Salt bytes from config.
        check_token: Stored encrypted verification token.

    Returns:
        True if the password is correct.
    """
    try:
        key = _derive_key(master_password, salt)
        f = Fernet(key)
        result = f.decrypt(check_token.encode("utf-8")).decode("utf-8")
        return result == "geotui-vault-ok"
    except (InvalidToken, Exception):
        return False


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
        vault_salt: Base64-encoded salt for PBKDF2 key derivation.
        vault_check: Fernet token used to verify master password.
    """

    model_config = ConfigDict(extra="allow")

    theme: str = "dark"
    language: str = "en"
    connections: list[Connection] = Field(default_factory=list)
    vault_salt: str = ""
    vault_check: str = ""

    @property
    def has_vault(self) -> bool:
        """Return True if a master password vault has been initialised."""
        return bool(self.vault_salt and self.vault_check)


def _get_config_dir() -> Path:
    """Get platform-appropriate config directory.

    Uses %APPDATA% on Windows, XDG_CONFIG_HOME (or ~/.config) on Unix.

    Returns:
        Path to the configuration directory.
    """
    if sys.platform == "win32":
        appdata = os.environ.get("APPDATA", "")
        base = Path(appdata) if appdata else Path.home() / "AppData" / "Roaming"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME", "")
        base = Path(xdg) if xdg else Path.home() / ".config"
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
        self.load_error: str | None = None
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
            except Exception as exc:
                self.load_error = str(exc)
                return AppConfig()
        return AppConfig()

    def save(self) -> None:
        """Persist configuration to disk atomically.

        Sets restrictive file permissions (0o600) on the config file
        and (0o700) on the config directory since it contains credentials.
        """
        with self._lock:
            self._config_path.parent.mkdir(parents=True, exist_ok=True)
            # Restrict config directory permissions
            try:
                os.chmod(str(self._config_path.parent), 0o700)
            except OSError:
                pass  # Windows or permission denied
            data = self.config.model_dump_json(indent=2)
            fd, tmp_path = tempfile.mkstemp(
                dir=str(self._config_path.parent), suffix=".tmp"
            )
            try:
                os.write(fd, data.encode("utf-8"))
                os.close(fd)
                os.replace(tmp_path, str(self._config_path))
                # Restrict config file permissions (owner read/write only)
                try:
                    os.chmod(str(self._config_path), 0o600)
                except OSError:
                    pass  # Windows or permission denied
            except Exception:
                try:
                    os.close(fd)
                except OSError:
                    pass
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

    # ----- Vault / encryption ------------------------------------------------

    @property
    def has_vault(self) -> bool:
        """Return True if a master password vault has been set up."""
        return self.config.has_vault

    def _get_salt(self) -> bytes:
        """Return the vault salt bytes (decoded from base64)."""
        return base64.b64decode(self.config.vault_salt)

    def _make_fernet(self, master_password: str) -> Fernet:
        """Create a Fernet instance from the master password + stored salt."""
        return Fernet(_derive_key(master_password, self._get_salt()))

    def init_vault(self, master_password: str) -> None:
        """Initialise the encryption vault with a new master password.

        Generates a random salt, derives a key, stores a verification
        token, and encrypts all existing connection passwords.

        Args:
            master_password: The new master password.
        """
        with self._lock:
            salt = secrets.token_bytes(16)
            self.config.vault_salt = base64.b64encode(salt).decode("utf-8")
            key = _derive_key(master_password, salt)
            f = Fernet(key)
            # Store a check token so we can verify the password later
            self.config.vault_check = f.encrypt(b"geotui-vault-ok").decode("utf-8")
            # Encrypt existing plaintext passwords
            for conn in self.config.connections:
                if conn.password and not self._looks_encrypted(conn.password):
                    conn.password = encrypt_value(conn.password, f)
            self.save()

    def unlock(self, master_password: str) -> Fernet | None:
        """Verify the master password and return a Fernet instance.

        Args:
            master_password: Password to verify.

        Returns:
            Fernet instance if correct, None if wrong password.
        """
        if not self.has_vault:
            return None
        if verify_master_password(
            master_password, self._get_salt(), self.config.vault_check
        ):
            return self._make_fernet(master_password)
        return None

    def decrypt_connection(self, conn: Connection, fernet: Fernet) -> Connection:
        """Return a copy of the connection with password decrypted.

        Args:
            conn: Connection with encrypted password.
            fernet: Fernet instance from a successful unlock.

        Returns:
            New Connection with plaintext password.
        """
        decrypted_pw = decrypt_value(conn.password, fernet)
        return conn.model_copy(update={"password": decrypted_pw})

    def encrypt_password(self, plaintext: str, fernet: Fernet) -> str:
        """Encrypt a password for storage.

        Args:
            plaintext: Password in cleartext.
            fernet: Fernet instance from a successful unlock.

        Returns:
            Encrypted token string.
        """
        return encrypt_value(plaintext, fernet)

    def change_master_password(self, old_password: str, new_password: str) -> bool:
        """Change the master password, re-encrypting all connections.

        Args:
            old_password: Current master password.
            new_password: New master password.

        Returns:
            True if successful, False if old password is wrong.
        """
        old_fernet = self.unlock(old_password)
        if not old_fernet:
            return False
        with self._lock:
            # Decrypt all passwords with old key
            plaintext_passwords: dict[str, str] = {}
            for conn in self.config.connections:
                plaintext_passwords[conn.id] = decrypt_value(conn.password, old_fernet)
            # Generate new salt and key
            salt = secrets.token_bytes(16)
            self.config.vault_salt = base64.b64encode(salt).decode("utf-8")
            key = _derive_key(new_password, salt)
            new_fernet = Fernet(key)
            self.config.vault_check = new_fernet.encrypt(b"geotui-vault-ok").decode(
                "utf-8"
            )
            # Re-encrypt with new key
            for conn in self.config.connections:
                conn.password = encrypt_value(plaintext_passwords[conn.id], new_fernet)
            self.save()
            return True

    def reset_vault(self) -> None:
        """Reset the vault, wiping all connections.

        This is the only recovery option when the master password is forgotten.
        """
        with self._lock:
            self.config.connections.clear()
            self.config.vault_salt = ""
            self.config.vault_check = ""
            self.save()

    @staticmethod
    def _looks_encrypted(value: str) -> bool:
        """Heuristic: Fernet tokens are base64 and start with 'gAAAAA'.

        Args:
            value: String to check.

        Returns:
            True if value looks like a Fernet token.
        """
        return value.startswith("gAAAAA") and len(value) > 100
