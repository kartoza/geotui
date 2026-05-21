"""Tests for GeoServer create actions (workspace, stores)."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestGeoServerActions:
    """Test suite for GeoServer pane create actions."""

    @pytest.mark.asyncio
    async def test_create_workspace_no_connection_warns(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that create workspace warns when no connections exist."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert len(tree._connections) == 0
            tree.action_create_workspace()
            await pilot.pause()
            # Should not show action panel when no connection
            panel = tree.query_one("#action-panel")
            assert panel.display is False

    @pytest.mark.asyncio
    async def test_create_workspace_shows_form(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that create workspace shows form when on connection."""
        conn = Connection(
            name="Test",
            url="https://192.0.2.1:9999",
            is_active=True,
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            # The tree should have a connection node; move cursor to it
            from textual.widgets import Tree

            gs_tree = tree.query_one("#gs-tree", Tree)
            if gs_tree.root.children:
                gs_tree.select_node(gs_tree.root.children[0])
            tree.action_create_workspace()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is True

    @pytest.mark.asyncio
    async def test_create_store_no_connection_warns(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that create store warns when no connections exist."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_create_store()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is False

    @pytest.mark.asyncio
    async def test_cancel_hides_action_panel(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that cancel hides the action panel."""
        conn = Connection(
            name="Test",
            url="https://192.0.2.1:9999",
            is_active=True,
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            from textual.widgets import Tree

            gs_tree = tree.query_one("#gs-tree", Tree)
            if gs_tree.root.children:
                gs_tree.select_node(gs_tree.root.children[0])
            tree.action_create_workspace()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is True
            tree._hide_action_panel()
            await pilot.pause()
            assert panel.display is False

    @pytest.mark.asyncio
    async def test_create_workspace_requires_name(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that create workspace requires a non-empty name."""
        conn = Connection(
            name="Test",
            url="https://192.0.2.1:9999",
            is_active=True,
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            from textual.widgets import Tree

            gs_tree = tree.query_one("#gs-tree", Tree)
            if gs_tree.root.children:
                gs_tree.select_node(gs_tree.root.children[0])
            tree.action_create_workspace()
            await pilot.pause()
            # Try to create without entering a name
            tree._do_create()
            await pilot.pause()
            # Panel should still be visible (not dismissed)
            panel = tree.query_one("#action-panel")
            assert panel.display is True

    @pytest.mark.asyncio
    async def test_refresh_action(self, config_manager: ConfigManager) -> None:
        """Test that refresh action works without errors."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_refresh()
            await pilot.pause()
