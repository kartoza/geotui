"""GeoServer resource tree widget.

Displays the GeoServer resource hierarchy (workspaces > stores > layers)
in a tree view, populated from the active connection.
"""

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import Label, Static, Tree

from geotui.client import GeoServerClient, GeoServerResource
from geotui.config import Connection
from geotui.i18n import _

RESOURCE_ICONS = {
    "workspace": "\U0001f4c2",
    "datastore": "\U0001f5c4",
    "coveragestore": "\U0001f30d",
    "wmsstore": "\U0001f310",
    "layer": "\U0001f5fa",
    "coverage": "\U0001f30e",
    "wms_layer": "\U0001f310",
}


class GeoServerTree(Widget):
    """Tree widget showing GeoServer workspace/store/layer hierarchy."""

    DEFAULT_CSS = """
    GeoServerTree {
        width: 1fr;
        height: 100%;
        border: round $primary;
        padding: 0 1;
    }

    GeoServerTree.active {
        border: round $warning;
    }

    GeoServerTree .tree-header {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    GeoServerTree .tree-header.connected {
        background: #06969A;
        color: #1a1a2e;
    }

    GeoServerTree Tree {
        height: 1fr;
        width: 100%;
    }

    GeoServerTree .tree-footer {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text-muted;
    }

    GeoServerTree #no-connection {
        width: 100%;
        height: 1fr;
        content-align: center middle;
        color: #8A8B8B;
    }
    """

    connection: reactive[Connection | None] = reactive(None)
    is_active: reactive[bool] = reactive(False)
    loading: reactive[bool] = reactive(False)

    def compose(self) -> ComposeResult:
        """Compose the tree widget."""
        with Vertical():
            yield Label(_("GeoServer"), id="tree-title", classes="tree-header")
            yield Static(
                _("No connection active.\nPress F9 to configure connections."),
                id="no-connection",
            )
            yield Tree("GeoServer", id="gs-tree")
            yield Static("", id="tree-status", classes="tree-footer")

    def on_mount(self) -> None:
        """Set initial state."""
        tree = self.query_one("#gs-tree", Tree)
        tree.display = False
        tree.show_root = False

    def watch_is_active(self, value: bool) -> None:
        """Update styling when active state changes."""
        self.set_class(value, "active")

    def watch_connection(self, value: Connection | None) -> None:
        """React to connection changes."""
        if value:
            title = self.query_one("#tree-title", Label)
            title.update(value.name)
            title.set_class(True, "connected")
            self._load_tree(value)
        else:
            title = self.query_one("#tree-title", Label)
            title.update(_("GeoServer"))
            title.set_class(False, "connected")
            self.query_one("#no-connection", Static).display = True
            self.query_one("#gs-tree", Tree).display = False

    def _load_tree(self, conn: Connection) -> None:
        """Start loading the GeoServer resource tree.

        Args:
            conn: Active connection to load from.
        """
        self.loading = True
        self.query_one("#no-connection", Static).display = False
        self.query_one("#gs-tree", Tree).display = True
        self.query_one("#tree-status", Static).update(_("Loading..."))
        self.run_worker(self._fetch_tree(conn), exclusive=True, exit_on_error=False)

    async def _fetch_tree(self, conn: Connection) -> None:
        """Fetch and populate the tree from GeoServer.

        Args:
            conn: Connection to fetch from.
        """
        client = GeoServerClient(conn)
        try:
            resources = await client.get_full_tree()
            if not self.is_mounted:
                return
            self._populate_tree(resources)
            count = sum(
                1 + len(ws.children) + sum(len(s.children) for s in ws.children)
                for ws in resources
            )
            status = self.query_one("#tree-status", Static)
            ws_count = len(resources)
            status.update(f"{ws_count} workspace(s), {count} total resources")
        except Exception:  # nosec B110
            if self.is_mounted:
                status = self.query_one("#tree-status", Static)
                status.update(_("Connection failed"))
        finally:
            self.loading = False

    def _populate_tree(self, resources: list[GeoServerResource]) -> None:
        """Populate the tree widget with GeoServer resources.

        Args:
            resources: List of workspace resources with children.
        """
        tree = self.query_one("#gs-tree", Tree)
        tree.clear()

        for ws in resources:
            ws_node = tree.root.add(
                f"[bold #569FC6]{ws.name}[/]",
                data=ws,
                expand=False,
            )
            for store in ws.children:
                color = self._store_color(store.resource_type)
                store_node = ws_node.add(
                    f"[{color}]{store.name}[/]"
                    f" [{self._store_label(store.resource_type)}]",
                    data=store,
                    expand=False,
                )
                for layer in store.children:
                    store_node.add_leaf(
                        f"[#8A8B8B]{layer.name}[/]",
                        data=layer,
                    )

        tree.root.expand_all()

    @staticmethod
    def _store_color(resource_type: str) -> str:
        """Get the display color for a store type.

        Args:
            resource_type: Type of store resource.

        Returns:
            Rich color string.
        """
        colors = {
            "datastore": "#06969A",
            "coveragestore": "#DF9E2F",
            "wmsstore": "#569FC6",
        }
        return colors.get(resource_type, "#8A8B8B")

    @staticmethod
    def _store_label(resource_type: str) -> str:
        """Get a short label for a store type.

        Args:
            resource_type: Type of store resource.

        Returns:
            Short label string.
        """
        labels = {
            "datastore": "vector",
            "coveragestore": "raster",
            "wmsstore": "WMS",
        }
        return labels.get(resource_type, resource_type)

    def refresh_tree(self) -> None:
        """Refresh the tree from the current connection."""
        if self.connection:
            self._load_tree(self.connection)
