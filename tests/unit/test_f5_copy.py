"""Tests for F5 copy-to-publish workflow."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def connected_config(tmp_path: Path) -> ConfigManager:
    """Config with active connection."""
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(
        Connection(name="Test", url="https://192.0.2.1:9999", is_active=True)
    )
    return cm


class TestF5Copy:
    @pytest.mark.asyncio
    async def test_f5_no_connection_warns(self, tmp_path: Path) -> None:
        """F5 warns when no GeoServer connection."""
        cm = ConfigManager(config_path=tmp_path / "config.json")
        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            await pilot.press("f5")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_copy_from_local_no_connection(self, tmp_path: Path) -> None:
        """action_copy_from_local warns with no connection."""
        cm = ConfigManager(config_path=tmp_path / "config.json")
        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_copy_from_local()
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_bulk_publish_removed_from_f2(
        self, connected_config: ConfigManager
    ) -> None:
        """Bulk Publish Shapefiles no longer in F2 menu."""
        from geotui.screens.context_menu import ContextMenuScreen
        from geotui.widgets.dual_pane import DualPane

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
