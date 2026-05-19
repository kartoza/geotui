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
    async def test_app_has_geoserver_tree(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that the app contains a GeoServer tree in the right pane."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert tree is not None

    @pytest.mark.asyncio
    async def test_no_connection_message(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that empty state shows no connection message."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert tree.connection is None
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_dual_pane_set_connection(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that DualPane.set_connection passes connection to tree."""
        conn = Connection(
            name="Test Server",
            url="https://192.0.2.1:9999/geoserver",
        )
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.set_connection(conn)
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            # Connection should be set (tree loading happens async)
            assert tree.connection is not None
            assert tree.connection.name == "Test Server"
            # The no-connection message should be hidden
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is False

    @pytest.mark.asyncio
    async def test_dual_pane_clear_connection(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that clearing connection shows empty state."""
        conn = Connection(name="Test", url="https://192.0.2.1:9999")
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test(size=(120, 40)) as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            dual_pane.set_connection(conn)
            await pilot.pause()
            dual_pane.set_connection(None)
            await pilot.pause()
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            assert tree.connection is None
            no_conn = tree.query_one("#no-connection")
            assert no_conn.display is True

    @pytest.mark.asyncio
    async def test_tree_toggle_active(
        self, config_manager: ConfigManager
    ) -> None:
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
    async def test_active_connection_on_startup(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that active connection is loaded on app startup."""
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
            assert tree.connection is not None
            assert tree.connection.name == "Startup Server"

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
    async def test_populate_tree_with_mock_data(
        self, config_manager: ConfigManager
    ) -> None:
        """Test tree population with mock GeoServer resources."""
        from geotui.client import GeoServerResource

        resources = [
            GeoServerResource(
                name="workspace1",
                resource_type="workspace",
                children=[
                    GeoServerResource(
                        name="postgis_store",
                        resource_type="datastore",
                        children=[
                            GeoServerResource(
                                name="buildings", resource_type="layer"
                            ),
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
            tree_widget._populate_tree(resources)
            await pilot.pause()
            from textual.widgets import Tree

            tree = tree_widget.query_one("#gs-tree", Tree)
            # Root should have 2 workspace nodes
            assert len(tree.root.children) == 2

    @pytest.mark.asyncio
    async def test_refresh_tree(
        self, config_manager: ConfigManager
    ) -> None:
        """Test refresh_tree with no connection is a no-op."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            tree = pilot.app.query_one("#right-pane", GeoServerTree)
            tree.refresh_tree()
            await pilot.pause()
