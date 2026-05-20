"""Tests for bulk publish TUI integration."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.screens.context_menu import ContextMenuScreen
from geotui.widgets.dual_pane import DualPane
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def connected_config(tmp_path: Path) -> ConfigManager:
    """Create a config with an active connection."""
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(
        Connection(name="Test", url="https://192.0.2.1:9999", is_active=True)
    )
    return cm


class TestPublishTUI:
    @pytest.mark.asyncio
    async def test_f2_menu_has_bulk_publish(
        self, connected_config: ConfigManager
    ) -> None:
        """Test that F2 GeoServer menu includes Bulk Publish."""
        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.toggle_active_pane()
            await pilot.pause()
            await pilot.press("f2")
            await pilot.pause()
            screen = app.screen
            assert isinstance(screen, ContextMenuScreen)

    @pytest.mark.asyncio
    async def test_bulk_publish_action_no_connection(self, tmp_path: Path) -> None:
        """Test bulk publish warns when no connection."""
        cm = ConfigManager(config_path=tmp_path / "config.json")
        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_bulk_publish()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is False

    @pytest.mark.asyncio
    async def test_bulk_publish_shows_form(
        self, connected_config: ConfigManager
    ) -> None:
        """Test bulk publish shows config form when connected."""
        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_bulk_publish()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is True

    @pytest.mark.asyncio
    async def test_bulk_publish_requires_workspace(
        self, connected_config: ConfigManager
    ) -> None:
        """Test that bulk publish requires workspace to be set."""
        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_bulk_publish()
            await pilot.pause()
            # Try to submit without filling in workspace
            tree._do_create()
            await pilot.pause()
            # Panel should still be visible (not dismissed)
            panel = tree.query_one("#action-panel")
            assert panel.display is True

    @pytest.mark.asyncio
    async def test_bulk_publish_requires_datastore(
        self, connected_config: ConfigManager
    ) -> None:
        """Test that bulk publish requires datastore to be set."""
        from textual.widgets import Input

        app = GeoTUIApp(config_manager=connected_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_bulk_publish()
            await pilot.pause()
            # Fill workspace but leave datastore empty
            tree.query_one("#field1-input", Input).value = "my_workspace"
            tree._do_create()
            await pilot.pause()
            # Panel should still be visible
            panel = tree.query_one("#action-panel")
            assert panel.display is True

    @pytest.mark.asyncio
    async def test_context_menu_contains_bulk_publish_option(self) -> None:
        """Test ContextMenuScreen for geoserver pane has gs_bulk_publish option."""
        from textual.widgets import OptionList

        screen = ContextMenuScreen(pane_type="geoserver")
        # Instantiate a minimal app to host the screen
        app = GeoTUIApp(config_manager=ConfigManager())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.app.push_screen(screen)
            await pilot.pause()
            opts = screen.query_one("#menu-options", OptionList)
            option_ids = [
                opts.get_option_at_index(i).id for i in range(opts.option_count)
            ]
            assert "gs_bulk_publish" in option_ids
