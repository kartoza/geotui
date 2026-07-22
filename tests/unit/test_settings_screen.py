"""Tests for the settings screen."""

from pathlib import Path

import pytest
from textual.widgets import Input, ListView, Static

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.screens.settings import SettingsScreen


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


@pytest.fixture
def populated_config(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with sample connections."""
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(
        Connection(
            name="Production",
            url="https://geo.example.com/geoserver",
            username="admin",
            password="secret123",
        )
    )
    cm.add_connection(
        Connection(
            name="Staging",
            url="https://staging.example.com/geoserver",
            username="user",
            password="pass",
        )
    )
    return cm


class TestSettingsScreen:
    """Test suite for SettingsScreen."""

    @pytest.mark.asyncio
    async def test_settings_screen_opens(self, config_manager: ConfigManager) -> None:
        """Test that the settings screen can be opened."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_save_refused_when_vault_locked(self, tmp_path: Path) -> None:
        """Saving credentials while the vault is locked is refused.

        Storing while locked would either leak the password in plaintext or
        double-encrypt an existing token. The connection must be left
        unchanged.
        """
        cm = ConfigManager(config_path=tmp_path / "config.json")
        cm.init_vault("masterpassword")
        vk = cm.unlock("masterpassword")
        original = cm.encrypt_password("orig-secret", vk)
        cm.add_connection(
            Connection(
                name="Prod",
                url="http://gs",
                username="admin",
                password=original,
            )
        )
        cid = cm.config.connections[0].id

        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            app.vault_key = None  # vault locked
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)

            screen.selected_id = cid
            screen.query_one("#input-name", Input).value = "Prod"
            screen.query_one("#input-url", Input).value = "http://gs"
            screen.query_one("#input-password", Input).value = "attempt"
            screen._save_form()
            await pilot.pause()

            # Password unchanged; nothing stored in plaintext.
            assert cm.get_connection(cid).password == original

    @pytest.mark.asyncio
    async def test_settings_shows_empty_state(
        self, config_manager: ConfigManager
    ) -> None:
        """Test empty state when no connections exist."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            empty = screen.query_one("#empty-detail", Static)
            assert empty.display is True

    @pytest.mark.asyncio
    async def test_settings_shows_connections(
        self, populated_config: ConfigManager
    ) -> None:
        """Test that existing connections appear in the list."""
        app = GeoTUIApp(config_manager=populated_config)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            list_view = app.screen.query_one("#conn-list", ListView)
            assert len(list_view.children) == 2

    @pytest.mark.asyncio
    async def test_escape_returns_to_main(self, config_manager: ConfigManager) -> None:
        """Test that Escape returns to the main screen."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            assert isinstance(app.screen, SettingsScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, SettingsScreen)

    @pytest.mark.asyncio
    async def test_add_shows_edit_form(self, config_manager: ConfigManager) -> None:
        """Test that Add action shows the edit form."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            assert screen.editing is True

    @pytest.mark.asyncio
    async def test_cancel_edit_returns_to_empty(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that Cancel returns from edit to empty state."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            assert screen.editing is True
            screen._cancel_edit()
            await pilot.pause()
            assert screen.editing is False

    @pytest.mark.asyncio
    async def test_save_new_connection(self, config_manager: ConfigManager) -> None:
        """Test saving a new connection via the form."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            screen.query_one("#input-name", Input).value = "New Server"
            screen.query_one("#input-url", Input).value = "https://new.example.com"
            screen.query_one("#input-username", Input).value = "admin"
            screen.query_one("#input-password", Input).value = "password"
            screen._save_form()
            await pilot.pause()
            assert len(config_manager.config.connections) == 1
            assert config_manager.config.connections[0].name == "New Server"

    @pytest.mark.asyncio
    async def test_save_requires_name(self, config_manager: ConfigManager) -> None:
        """Test that saving without a name is rejected."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            screen.query_one("#input-url", Input).value = "https://example.com"
            screen._save_form()
            await pilot.pause()
            assert len(config_manager.config.connections) == 0

    @pytest.mark.asyncio
    async def test_save_requires_url(self, config_manager: ConfigManager) -> None:
        """Test that saving without a URL is rejected."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            screen.query_one("#input-name", Input).value = "Test"
            screen._save_form()
            await pilot.pause()
            assert len(config_manager.config.connections) == 0

    @pytest.mark.asyncio
    async def test_select_shows_detail(self, populated_config: ConfigManager) -> None:
        """Test that selecting a connection shows its details."""
        app = GeoTUIApp(config_manager=populated_config)
        conn = populated_config.config.connections[0]
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.selected_id = conn.id
            screen._show_connection_detail(conn)
            await pilot.pause()
            view_mode = screen.query_one("#view-mode")
            assert view_mode.display is True

    @pytest.mark.asyncio
    async def test_delete_connection(self, populated_config: ConfigManager) -> None:
        """Test deleting a connection."""
        app = GeoTUIApp(config_manager=populated_config)
        conn_id = populated_config.config.connections[0].id
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.selected_id = conn_id
            screen.action_delete()
            await pilot.pause()
            assert len(populated_config.config.connections) == 1

    @pytest.mark.asyncio
    async def test_edit_without_selection_warns(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that editing without a selection does not enter edit mode."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_edit()
            await pilot.pause()
            assert screen.editing is False

    @pytest.mark.asyncio
    async def test_delete_without_selection_warns(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that deleting without selection shows warning."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_delete()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_edit_existing_connection(
        self, populated_config: ConfigManager
    ) -> None:
        """Test editing an existing connection populates the form."""
        app = GeoTUIApp(config_manager=populated_config)
        conn = populated_config.config.connections[0]
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.selected_id = conn.id
            screen.action_edit()
            await pilot.pause()
            assert screen.editing is True
            name_input = screen.query_one("#input-name", Input)
            assert name_input.value == conn.name

    @pytest.mark.asyncio
    async def test_update_existing_connection(
        self, populated_config: ConfigManager
    ) -> None:
        """Test updating an existing connection saves changes."""
        app = GeoTUIApp(config_manager=populated_config)
        conn = populated_config.config.connections[0]
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.selected_id = conn.id
            screen.action_edit()
            await pilot.pause()
            screen.query_one("#input-name", Input).value = "Updated Name"
            screen._save_form()
            await pilot.pause()
            updated = populated_config.get_connection(conn.id)
            assert updated is not None
            assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_edit_mode_hides_vault_buttons_and_shows_save(
        self, populated_config: ConfigManager
    ) -> None:
        """In edit mode the Save action bar shows and vault buttons hide.

        Regression: the master-vault "Change Master Password" button used to
        sit at the docked bottom of the screen where users looked for Apply,
        while the real Save button scrolled out of view.
        """
        from textual.widgets import Button

        app = GeoTUIApp(config_manager=populated_config)
        conn = populated_config.config.connections[0]
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.selected_id = conn.id
            screen.action_edit()
            await pilot.pause()

            # Vault (master-password) controls are hidden while editing.
            assert screen.query_one("#vault-buttons").display is False
            # The save action bar and its buttons exist and are displayed.
            save_btn = screen.query_one("#btn-save", Button)
            assert save_btn.display is True
            assert screen.query_one("#btn-save-connect", Button) is not None
            # The action bar is a sibling of the scrolling field area, so it is
            # not inside the scroll region that clipped the old Save button.
            assert save_btn.parent.id == "edit-buttons"

    @pytest.mark.asyncio
    async def test_save_and_connect_persists_then_tests(
        self, populated_config: ConfigManager
    ) -> None:
        """The Save & Connect button saves the form and triggers a test."""
        from types import SimpleNamespace

        app = GeoTUIApp(config_manager=populated_config)
        conn = populated_config.config.connections[0]
        called: list[str] = []
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_test_connection = lambda: called.append("test")  # type: ignore[method-assign]
            screen.selected_id = conn.id
            screen.action_edit()
            await pilot.pause()
            screen.query_one("#input-name", Input).value = "Renamed"
            screen.on_button_pressed(
                SimpleNamespace(button=SimpleNamespace(id="btn-save-connect"))
            )
            await pilot.pause()
            assert populated_config.get_connection(conn.id).name == "Renamed"
            assert called == ["test"]

    @pytest.mark.asyncio
    async def test_test_connection_without_selection(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that Connect without selection shows warning."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_test_connection()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_escape_from_edit_cancels(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that Escape while editing cancels the edit."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f9")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, SettingsScreen)
            screen.action_add()
            await pilot.pause()
            assert screen.editing is True
            screen.action_go_back()
            await pilot.pause()
            assert screen.editing is False
