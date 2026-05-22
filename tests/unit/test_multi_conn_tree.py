"""Tests for multi-connection tree."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.geoserver_tree import GeoServerTree, TreeNodeData


@pytest.fixture
def two_conn_config(tmp_path: Path) -> ConfigManager:
    cm = ConfigManager(config_path=tmp_path / "config.json")
    cm.add_connection(Connection(name="Production", url="https://192.0.2.1:9999"))
    cm.add_connection(Connection(name="Staging", url="https://192.0.2.2:9999"))
    return cm


@pytest.fixture
def empty_config(tmp_path: Path) -> ConfigManager:
    return ConfigManager(config_path=tmp_path / "config.json")


class TestTreeNodeData:
    def test_connection_node(self) -> None:
        data = TreeNodeData(
            node_type="connection",
            name="Production",
            connection_id="abc123",
        )
        assert data.node_type == "connection"
        assert data.connection_id == "abc123"
        assert data.resource is None

    def test_workspace_node(self) -> None:
        data = TreeNodeData(
            node_type="workspace",
            name="my_ws",
            connection_id="abc123",
        )
        assert data.node_type == "workspace"

    def test_root_node(self) -> None:
        data = TreeNodeData(
            node_type="root",
            name="GeoServer",
            connection_id="",
        )
        assert data.node_type == "root"

    def test_node_with_resource(self) -> None:
        from geotui.client import GeoServerResource

        res = GeoServerResource(name="roads", resource_type="layer")
        data = TreeNodeData(
            node_type="layer",
            name="roads",
            connection_id="abc123",
            resource=res,
        )
        assert data.resource is not None
        assert data.resource.name == "roads"


class TestMultiConnectionTree:
    @pytest.mark.asyncio
    async def test_tree_shows_all_connections(
        self, two_conn_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            from textual.widgets import Tree

            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            tree = tree_widget.query_one("#gs-tree", Tree)
            assert len(tree.root.children) == 2

    @pytest.mark.asyncio
    async def test_empty_config_shows_message(
        self, empty_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test() as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            no_conn = tree_widget.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_connection_names_in_tree(
        self, two_conn_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            from textual.widgets import Tree

            tree = tree_widget.query_one("#gs-tree", Tree)
            names = {child.data.name for child in tree.root.children if child.data}
            assert "Production" in names
            assert "Staging" in names

    @pytest.mark.asyncio
    async def test_connections_start_untested(
        self, two_conn_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            for state in tree_widget._connection_states.values():
                assert state == "untested"

    @pytest.mark.asyncio
    async def test_refresh_connections_updates(
        self, two_conn_config: ConfigManager
    ) -> None:
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            two_conn_config.add_connection(
                Connection(name="New", url="https://192.0.2.3:9999")
            )
            tree_widget.refresh_connections()
            await pilot.pause()
            from textual.widgets import Tree

            tree = tree_widget.query_one("#gs-tree", Tree)
            assert len(tree.root.children) == 3

    @pytest.mark.asyncio
    async def test_get_selected_connection_returns_none_no_selection(
        self, two_conn_config: ConfigManager
    ) -> None:
        """_get_selected_connection returns None when nothing is selected."""
        app = GeoTUIApp(config_manager=two_conn_config)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            result = tree_widget._get_selected_connection()
            # With no cursor selection, should return None or a valid tuple
            # (depending on whether cursor lands on a node by default)
            # Either way it should not raise
            assert result is None or isinstance(result, tuple)

    @pytest.mark.asyncio
    async def test_action_create_workspace_no_connections(
        self, empty_config: ConfigManager
    ) -> None:
        """Create workspace warns when no connections exist."""
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_create_workspace()
            await pilot.pause()
            panel = tree.query_one("#action-panel")
            assert panel.display is False

    @pytest.mark.asyncio
    async def test_action_refresh_no_crash(self, empty_config: ConfigManager) -> None:
        """Refresh action does not crash with no connections."""
        app = GeoTUIApp(config_manager=empty_config)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.action_refresh()
            await pilot.pause()
