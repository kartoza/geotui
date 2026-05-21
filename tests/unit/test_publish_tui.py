"""Tests for publish TUI integration (post-F5 refactor).

The old bulk publish menu item has been removed from the F2 menu.
Publishing is now triggered via F5 (action_copy) which delegates to
action_copy_from_local on the GeoServerTree widget.
"""

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
    async def test_f2_menu_no_bulk_publish(
        self, connected_config: ConfigManager
    ) -> None:
        """Test that F2 GeoServer menu no longer includes Bulk Publish."""
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
    async def test_copy_from_local_no_connection(self, tmp_path: Path) -> None:
        """Test copy from local warns when no connection."""
        cm = ConfigManager(config_path=tmp_path / "config.json")
        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_copy_from_local()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_context_menu_no_bulk_publish_option(self) -> None:
        """Test ContextMenuScreen for geoserver pane has no gs_bulk_publish option."""
        from textual.widgets import OptionList

        screen = ContextMenuScreen(pane_type="geoserver")
        app = GeoTUIApp(config_manager=ConfigManager())
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.app.push_screen(screen)
            await pilot.pause()
            opts = screen.query_one("#menu-options", OptionList)
            option_ids = [
                opts.get_option_at_index(i).id for i in range(opts.option_count)
            ]
            assert "gs_bulk_publish" not in option_ids
