"""Tests for the GeoServer tree widget."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager, Connection
from geotui.widgets.dual_pane import DualPane
from geotui.widgets.geoserver_tree import GeoServerTree


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestGeoServerTree:
    """Test suite for GeoServerTree widget."""

    @pytest.mark.asyncio
    async def test_app_has_geoserver_tree(self, config_manager: ConfigManager) -> None:
        """Test that the app contains a GeoServer tree in the right pane."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert tree is not None

    @pytest.mark.asyncio
    async def test_no_connection_message(self, config_manager: ConfigManager) -> None:
        """Test that empty state shows no connection message."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert len(tree._connections) == 0
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_connections_loaded_on_mount(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that connections from config are loaded into the tree on mount."""
        conn = Connection(
            name="Test Server",
            url="https://192.0.2.1:9999/geoserver",
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert len(tree._connections) == 1
            assert conn.id in tree._connections
            # The no-connection message should be hidden
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is False

    @pytest.mark.asyncio
    async def test_empty_config_shows_no_connection(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that empty config shows no-connection message."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert len(tree._connections) == 0
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_tree_toggle_active(self, config_manager: ConfigManager) -> None:
        """Test that Tab switches active state to GeoServer tree."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            assert dual_pane.active_pane == "left"
            dual_pane.toggle_active_pane()
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert tree.is_active is True

    @pytest.mark.asyncio
    async def test_connections_loaded_on_startup(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that connections are loaded from config on app startup."""
        conn = Connection(
            name="Startup Server",
            url="https://192.0.2.1:9999",
            is_active=True,
        )
        config_manager.add_connection(conn)
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert len(tree._connections) == 1
            assert conn.id in tree._connections

    @pytest.mark.asyncio
    async def test_tree_store_colors(self) -> None:
        """Test store color mapping."""
        assert GeoServerTree._store_color("datastore") == "#06969A"
        assert GeoServerTree._store_color("coveragestore") == "#DF9E2F"
        assert GeoServerTree._store_color("wmsstore") == "#569FC6"
        assert GeoServerTree._store_color("unknown") == "#8A8B8B"

    @pytest.mark.asyncio
    async def test_tree_store_labels(self) -> None:
        """Test store label mapping."""
        assert GeoServerTree._store_label("datastore") == "vector"
        assert GeoServerTree._store_label("coveragestore") == "raster"
        assert GeoServerTree._store_label("wmsstore") == "WMS"

    @pytest.mark.asyncio
    async def test_populate_connection_tree_with_mock_data(
        self, config_manager: ConfigManager
    ) -> None:
        """Test tree population with mock GeoServer resources."""
        from geotui.client import GeoServerResource
        from geotui.widgets.geoserver_tree import TreeNodeData

        conn = Connection(
            name="Test",
            url="https://192.0.2.1:9999",
        )
        config_manager.add_connection(conn)

        resources = [
            GeoServerResource(
                name="workspace1",
                resource_type="workspace",
                children=[
                    GeoServerResource(
                        name="postgis_store",
                        resource_type="datastore",
                        children=[
                            GeoServerResource(name="buildings", resource_type="layer"),
                            GeoServerResource(name="roads", resource_type="layer"),
                        ],
                    ),
                    GeoServerResource(
                        name="dem_store",
                        resource_type="coveragestore",
                        children=[
                            GeoServerResource(
                                name="elevation", resource_type="coverage"
                            ),
                        ],
                    ),
                ],
            ),
            GeoServerResource(
                name="workspace2",
                resource_type="workspace",
                children=[],
            ),
        ]

        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            tree_widget = pilot.app.query_one("#right-pane", GeoServerTree)
            from textual.widgets import Tree

            gs_tree = tree_widget.query_one("#gs-tree", Tree)

            # Root should have 1 connection node
            assert len(gs_tree.root.children) == 1
            conn_node = gs_tree.root.children[0]
            # Mark as connected so expand_all won't trigger re-fetch
            tree_widget._connection_states[conn.id] = "connected"
            # Clear and populate
            conn_node.remove_children()
            tree_widget._populate_connection_tree(conn_node, conn.id, resources)
            await pilot.pause()
            # Re-fetch the connection node after mutation
            conn_node = gs_tree.root.children[0]
            # Connection node should have 2 workspace children
            ws_children = [
                c
                for c in conn_node.children
                if isinstance(c.data, TreeNodeData) and c.data.node_type == "workspace"
            ]
            assert len(ws_children) == 2

    @pytest.mark.asyncio
    async def test_refresh_tree(self, config_manager: ConfigManager) -> None:
        """Test refresh_tree with no connections is a no-op."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.refresh_tree()
            await pilot.pause()
