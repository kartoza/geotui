"""Tests for the context-sensitive F2 menu."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.screens.context_menu import ContextMenuScreen
from geotui.widgets.dual_pane import DualPane


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestContextMenu:
    """Test suite for context-sensitive F2 menu."""

    @pytest.mark.asyncio
    async def test_f2_opens_menu(self, config_manager: ConfigManager) -> None:
        """Test that F2 opens the context menu."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, ContextMenuScreen)

    @pytest.mark.asyncio
    async def test_local_pane_shows_file_actions(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that local file pane shows File Actions menu."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)
            assert screen._pane_type == "local"

    @pytest.mark.asyncio
    async def test_geoserver_pane_shows_geoserver_actions(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that GeoServer pane shows GeoServer Actions menu."""
        conn = Connection(
            name="Test",
            url="https://192.0.2.1:9999",
            is_active=True,
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)
            assert screen._pane_type == "geoserver"

    @pytest.mark.asyncio
    async def test_right_pane_without_connection_shows_local(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that right pane without connection shows local menu."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)
            # No connection = local type even on right pane
            assert screen._pane_type == "local"

    @pytest.mark.asyncio
    async def test_escape_closes_menu(self, config_manager: ConfigManager) -> None:
        """Test that Escape closes the menu."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.press("f2")
            await pilot.pause()
            assert isinstance(app.screen, ContextMenuScreen)
            await pilot.press("escape")
            await pilot.pause()
            assert not isinstance(app.screen, ContextMenuScreen)
