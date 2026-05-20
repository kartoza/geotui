"""GeoServer resource tree widget.

Displays the GeoServer resource hierarchy (workspaces > stores > layers)
in a tree view, populated from the active connection. Provides context-
sensitive actions for creating workspaces and stores.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    Static,
    Tree,
)
from textual.widgets.option_list import Option

from geotui.client import (
    COVERAGESTORE_TYPES,
    DATASTORE_TYPES,
    GeoServerClient,
    GeoServerResource,
)
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
    """Tree widget showing GeoServer workspace/store/layer hierarchy.

    Provides context-sensitive actions when active:
    - w: Create workspace
    - s: Create store (with type selection)
    - r: Refresh tree
    """

    BINDINGS = [
        ("w", "create_workspace", _("New Workspace")),
        ("s", "create_store", _("New Store")),
        ("r", "refresh", _("Refresh")),
    ]

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

    GeoServerTree #action-panel {
        height: auto;
        max-height: 16;
        width: 100%;
        border-top: solid #569FC6;
        padding: 0 1;
        background: #16213e;
    }

    GeoServerTree #action-panel .action-title {
        color: #DF9E2F;
        text-style: bold;
        height: 1;
        margin: 0 0 1 0;
    }

    GeoServerTree #action-panel .field-label {
        color: #569FC6;
        height: 1;
    }

    GeoServerTree #action-panel Input {
        width: 100%;
        margin: 0 0 0 0;
    }

    GeoServerTree #action-panel Input:focus {
        border: round #DF9E2F;
    }

    GeoServerTree #action-panel OptionList {
        height: auto;
        max-height: 8;
        width: 100%;
        margin: 0 0 1 0;
    }

    GeoServerTree #action-panel #action-buttons {
        height: auto;
        width: 100%;
        margin: 1 0 0 0;
        align: center middle;
    }

    GeoServerTree #action-panel #action-buttons Button {
        margin: 0 1;
        min-width: 10;
    }

    GeoServerTree .btn-success {
        background: #06969A;
        color: #1a1a2e;
    }

    GeoServerTree .btn-default {
        background: #8A8B8B;
        color: #1a1a2e;
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
            with Vertical(id="action-panel"):
                yield Label("", id="action-title", classes="action-title")
                yield Label("", id="field1-label", classes="field-label")
                yield Input(id="field1-input")
                yield Label("", id="field2-label", classes="field-label")
                yield Input(id="field2-input")
                yield Label("", id="field3-label", classes="field-label")
                yield Input(id="field3-input")
                yield Label("", id="field4-label", classes="field-label")
                yield Input(id="field4-input")
                yield Label("", id="field5-label", classes="field-label")
                yield Input(id="field5-input")
                yield Label("", id="field6-label", classes="field-label")
                yield Input(id="field6-input")
                yield OptionList(id="store-type-list")
                with Horizontal(id="action-buttons"):
                    yield Button(
                        _("Create"),
                        id="btn-create",
                        classes="btn-success",
                    )
                    yield Button(
                        _("Cancel"),
                        id="btn-action-cancel",
                        classes="btn-default",
                    )

    def on_mount(self) -> None:
        """Set initial state."""
        tree = self.query_one("#gs-tree", Tree)
        tree.display = False
        tree.show_root = False
        self._hide_action_panel()

    def _hide_action_panel(self) -> None:
        """Hide the action panel and all its fields."""
        self.query_one("#action-panel").display = False

    def _show_action_panel(
        self,
        title: str,
        fields: list[tuple[str, str, str]],
        show_store_types: bool = False,
    ) -> None:
        """Show the action panel with specified fields.

        Args:
            title: Panel title.
            fields: List of (label_id_suffix, label_text, placeholder).
            show_store_types: Whether to show the store type selector.
        """
        panel = self.query_one("#action-panel")
        panel.display = True

        self.query_one("#action-title", Label).update(title)

        # Hide all fields first
        for i in range(1, 7):
            self.query_one(f"#field{i}-label", Label).display = False
            self.query_one(f"#field{i}-input", Input).display = False
            self.query_one(f"#field{i}-input", Input).value = ""

        # Show requested fields
        for idx, (_field_id, label_text, placeholder) in enumerate(fields):
            field_num = idx + 1
            lbl = self.query_one(f"#field{field_num}-label", Label)
            lbl.update(label_text)
            lbl.display = True
            inp = self.query_one(f"#field{field_num}-input", Input)
            inp.placeholder = placeholder
            inp.display = True

        store_list = self.query_one("#store-type-list", OptionList)
        store_list.display = show_store_types

        if fields:
            self.query_one("#field1-input", Input).focus()

    def _get_selected_workspace(self) -> str | None:
        """Get the workspace name from the currently selected tree node.

        Returns:
            Workspace name or None.
        """
        tree = self.query_one("#gs-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            node = tree.cursor_node
            data = node.data
            if isinstance(data, GeoServerResource):
                if data.resource_type == "workspace":
                    return data.name
                # Walk up to find workspace parent
                parent = node.parent
                while parent and parent.data:
                    if (
                        isinstance(parent.data, GeoServerResource)
                        and parent.data.resource_type == "workspace"
                    ):
                        return parent.data.name
                    parent = parent.parent
        return None

    # ── Actions ────────────────────────────────────────────

    def action_create_workspace(self) -> None:
        """Show the create workspace form."""
        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return
        self._current_action = "workspace"
        self._show_action_panel(
            _("Create Workspace"),
            [("name", _("Workspace Name"), _("my_workspace"))],
        )

    def action_create_store(self) -> None:
        """Show the store type selector."""
        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return

        ws = self._get_selected_workspace()
        if not ws:
            self.app.notify(
                _("Select a workspace in the tree first"),
                severity="warning",
            )
            return

        self._current_action = "store_select"
        self._current_workspace = ws

        panel = self.query_one("#action-panel")
        panel.display = True
        self.query_one("#action-title", Label).update(f"{_('Create Store')} ({ws})")

        # Hide fields, show type list
        for i in range(1, 7):
            self.query_one(f"#field{i}-label", Label).display = False
            self.query_one(f"#field{i}-input", Input).display = False

        store_list = self.query_one("#store-type-list", OptionList)
        store_list.clear_options()
        for type_id, desc in DATASTORE_TYPES:
            store_list.add_option(Option(f"[#06969A]{type_id}[/] {desc}"))
        for type_id, desc in COVERAGESTORE_TYPES:
            store_list.add_option(Option(f"[#DF9E2F]{type_id}[/] {desc}"))
        store_list.add_option(Option("[#569FC6]WMS[/] Remote WMS service"))
        store_list.display = True
        store_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle store type selection."""
        if not hasattr(self, "_current_action"):
            return
        if self._current_action != "store_select":
            return

        idx = event.option_index
        all_types = list(DATASTORE_TYPES) + list(COVERAGESTORE_TYPES)
        all_types.append(("WMS", "Remote WMS service"))

        if idx >= len(all_types):
            return

        type_id = all_types[idx][0]
        self._selected_store_type = type_id
        self._current_action = "store_form"

        self.query_one("#store-type-list", OptionList).display = False

        ws = self._current_workspace
        title = f"{_('Create')} {type_id} ({ws})"

        if type_id == "PostGIS":
            self._show_action_panel(
                title,
                [
                    ("name", _("Store Name"), _("my_postgis")),
                    ("host", _("Host"), "localhost"),
                    ("port", _("Port"), "5432"),
                    ("db", _("Database"), _("my_database")),
                    ("user", _("DB User"), "postgres"),
                    ("pass", _("DB Password"), _("password")),
                ],
            )
        elif type_id == "WMS":
            self._show_action_panel(
                title,
                [
                    ("name", _("Store Name"), _("remote_wms")),
                    (
                        "url",
                        _("Capabilities URL"),
                        "https://example.com/wms?service=WMS&request=GetCapabilities",
                    ),
                ],
            )
        elif type_id in ("GeoTIFF", "WorldImage", "ImageMosaic"):
            self._show_action_panel(
                title,
                [
                    ("name", _("Store Name"), _("my_raster")),
                    (
                        "path",
                        _("File Path"),
                        "file:data/raster/dem.tif",
                    ),
                ],
            )
        else:
            self._show_action_panel(
                title,
                [
                    ("name", _("Store Name"), _("my_store")),
                    (
                        "path",
                        _("File/Directory Path"),
                        "file:data/myfile.shp",
                    ),
                ],
            )

    def action_refresh(self) -> None:
        """Refresh the tree."""
        self.refresh_tree()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action panel buttons."""
        if event.button.id == "btn-create":
            self._do_create()
        elif event.button.id == "btn-action-cancel":
            self._hide_action_panel()

    def _do_create(self) -> None:
        """Execute the current create action."""
        if not self.connection:
            return

        action = getattr(self, "_current_action", "")
        if action == "workspace":
            name = self.query_one("#field1-input", Input).value.strip()
            if not name:
                self.app.notify(_("Name is required"), severity="error")
                return
            self.run_worker(
                self._create_workspace(name),
                exit_on_error=False,
            )
        elif action == "store_form":
            self._do_create_store()

    async def _create_workspace(self, name: str) -> None:
        """Create a workspace via the API.

        Args:
            name: Workspace name.
        """
        client = GeoServerClient(self.connection)
        ok = await client.create_workspace(name)
        if self.is_mounted:
            if ok:
                self.app.notify(f"Workspace '{name}' created", severity="information")
                self._hide_action_panel()
                self.refresh_tree()
            else:
                self.app.notify(
                    f"Failed to create workspace '{name}'",
                    severity="error",
                )

    def _do_create_store(self) -> None:
        """Dispatch store creation based on selected type."""
        store_type = getattr(self, "_selected_store_type", "")
        ws = getattr(self, "_current_workspace", "")
        name = self.query_one("#field1-input", Input).value.strip()

        if not name:
            self.app.notify(_("Name is required"), severity="error")
            return

        self.run_worker(
            self._create_store(store_type, ws, name),
            exit_on_error=False,
        )

    async def _create_store(self, store_type: str, workspace: str, name: str) -> None:
        """Create a store via the API.

        Args:
            store_type: Type of store to create.
            workspace: Target workspace.
            name: Store name.
        """
        client = GeoServerClient(self.connection)
        ok = False

        if store_type == "Shapefile":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_datastore_shapefile(workspace, name, path)
        elif store_type == "Directory of Shapefiles":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_datastore_directory(workspace, name, path)
        elif store_type == "GeoPackage":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_datastore_gpkg(workspace, name, path)
        elif store_type == "PostGIS":
            host = self.query_one("#field2-input", Input).value.strip()
            port = self.query_one("#field3-input", Input).value.strip()
            db = self.query_one("#field4-input", Input).value.strip()
            user = self.query_one("#field5-input", Input).value.strip()
            passwd = self.query_one("#field6-input", Input).value
            ok = await client.create_datastore_postgis(
                workspace, name, host, port, db, user, passwd
            )
        elif store_type == "GeoTIFF":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_coveragestore_geotiff(workspace, name, path)
        elif store_type == "WorldImage":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_coveragestore_worldimage(workspace, name, path)
        elif store_type == "ImageMosaic":
            path = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_coveragestore_imagemosaic(workspace, name, path)
        elif store_type == "WMS":
            url = self.query_one("#field2-input", Input).value.strip()
            ok = await client.create_wmsstore(workspace, name, url)

        if self.is_mounted:
            if ok:
                self.app.notify(
                    f"{store_type} '{name}' created in {workspace}",
                    severity="information",
                )
                self._hide_action_panel()
                self.refresh_tree()
            else:
                self.app.notify(
                    f"Failed to create {store_type} '{name}'",
                    severity="error",
                )

    # ── Tree display ───────────────────────────────────────

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
                label = self._store_label(store.resource_type)
                store_node = ws_node.add(
                    f"[{color}]{store.name}[/] [{label}]",
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
        """Get the display color for a store type."""
        colors = {
            "datastore": "#06969A",
            "coveragestore": "#DF9E2F",
            "wmsstore": "#569FC6",
        }
        return colors.get(resource_type, "#8A8B8B")

    @staticmethod
    def _store_label(resource_type: str) -> str:
        """Get a short label for a store type."""
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
