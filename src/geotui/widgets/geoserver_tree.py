"""GeoServer resource tree widget.

Displays the GeoServer resource hierarchy (workspaces > stores > layers)
in a tree view, populated from all configured connections. Provides actions
for creating workspaces and stores via the F2 context menu.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

logger = logging.getLogger("geotui.tree")

if TYPE_CHECKING:
    from geotui.publisher import SpatialFileGroup

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import (
    Button,
    Input,
    Label,
    OptionList,
    ProgressBar,
    Static,
    Tree,
)
from textual.widgets.option_list import Option

from geotui.client import (
    STORE_TYPES,
    GeoServerClient,
    GeoServerResource,
    StoreType,
)
from geotui.config import ConfigManager, Connection
from geotui.i18n import _
from geotui.theme import KARTOZA_COLORS

# Colors for resource types
_COLORS = {
    "datastore": KARTOZA_COLORS["highlight4"],
    "coveragestore": KARTOZA_COLORS["highlight1"],
    "wmsstore": KARTOZA_COLORS["highlight2"],
    "workspace": KARTOZA_COLORS["highlight2"],
    "default": KARTOZA_COLORS["highlight3"],
}

_LABELS = {
    "datastore": "vector",
    "coveragestore": "raster",
    "wmsstore": "WMS",
}

_CATEGORY_COLORS = {
    "vector": KARTOZA_COLORS["highlight4"],
    "raster": KARTOZA_COLORS["highlight1"],
    "remote": KARTOZA_COLORS["highlight2"],
}

# Connection state colors
_STATE_COLORS = {
    "untested": "#8A8B8B",
    "connected": "#06969A",
    "failed": "#CC0403",
}

# Maximum number of dynamic form fields
_MAX_FIELDS = 6


@dataclass
class TreeNodeData:
    """Data attached to each tree node for identification.

    Attributes:
        node_type: One of 'root', 'connection', 'workspace',
            'datastore', 'coveragestore', 'wmsstore', 'layer',
            'coverage', 'error'.
        name: Display name of the node.
        connection_id: ID of the Connection this node belongs to.
        resource: Optional GeoServerResource for resource nodes.
    """

    node_type: str
    name: str
    connection_id: str
    resource: GeoServerResource | None = None


class GeoServerTree(Widget):
    """Tree widget showing GeoServer workspace/store/layer hierarchy."""

    BINDINGS = [
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

    GeoServerTree #publish-progress {
        height: auto;
        width: 100%;
        padding: 0 1;
        background: $surface;
    }

    GeoServerTree .progress-label {
        height: 1;
        width: 100%;
        color: $warning;
        text-style: bold;
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

    is_active: reactive[bool] = reactive(False)

    def __init__(self, config_manager: ConfigManager, **kwargs: Any) -> None:
        """Initialize the tree widget.

        Args:
            config_manager: The application config manager containing connections.
        """
        super().__init__(**kwargs)
        self._config_manager = config_manager
        self._connections: dict[str, Connection] = {}  # keyed by connection ID
        self._connection_states: dict[str, str] = {}  # "untested"/"connected"/"failed"
        self._connection_errors: dict[str, str] = {}  # error messages
        self._current_action = ""
        self._current_workspace = ""
        self._selected_store_type: StoreType | None = None

    def _decrypt_conn(self, conn: Connection) -> Connection:
        """Decrypt a connection's password via the app vault key.

        Args:
            conn: Connection with potentially encrypted password.

        Returns:
            Connection with plaintext password.
        """
        from geotui.app import GeoTUIApp

        app = self.app
        if isinstance(app, GeoTUIApp):
            if app.config_manager.has_vault and not app.vault_key:
                logger.warning(
                    "Vault locked - cannot decrypt connection '%s'", conn.name
                )
                self.app.notify(
                    _("Vault is locked. Press F9 to unlock."),
                    severity="error",
                )
            return app.decrypt_connection(conn)
        return conn

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
            with Vertical(id="publish-progress"):
                yield Label("", id="progress-label", classes="progress-label")
                yield ProgressBar(total=100, show_eta=False, id="progress-bar")
            with Vertical(id="action-panel"):
                yield Label("", id="action-title", classes="action-title")
                for i in range(1, _MAX_FIELDS + 1):
                    yield Label("", id=f"field{i}-label", classes="field-label")
                    yield Input(id=f"field{i}-input")
                yield OptionList(id="store-type-list")
                with Horizontal(id="action-buttons"):
                    yield Button(_("Create"), id="btn-create", classes="btn-success")
                    yield Button(
                        _("Cancel"), id="btn-action-cancel", classes="btn-default"
                    )

    def on_mount(self) -> None:
        """Set initial state and load connections."""
        tree = self.query_one("#gs-tree", Tree)
        tree.show_root = False
        self._hide_action_panel()
        self.query_one("#publish-progress").display = False
        self.refresh_connections()

    # ── Multi-connection management ───────────────────────

    def refresh_connections(self) -> None:
        """Rebuild the tree from the config manager's connections."""
        connections = self._config_manager.config.connections

        # Update internal connection dicts
        new_ids = {c.id for c in connections}
        # Remove stale entries
        for old_id in list(self._connections.keys()):
            if old_id not in new_ids:
                self._connections.pop(old_id, None)
                self._connection_states.pop(old_id, None)
                self._connection_errors.pop(old_id, None)

        # Add/update connections
        for conn in connections:
            self._connections[conn.id] = conn
            if conn.id not in self._connection_states:
                self._connection_states[conn.id] = "untested"

        tree = self.query_one("#gs-tree", Tree)
        no_conn = self.query_one("#no-connection", Static)

        if not connections:
            tree.display = False
            no_conn.display = True
            self.query_one("#tree-title", Label).update(_("GeoServer"))
            self.query_one("#tree-title", Label).set_class(False, "connected")
            return

        no_conn.display = False
        tree.display = True
        tree.clear()

        for conn in connections:
            state = self._connection_states.get(conn.id, "untested")
            color = _STATE_COLORS[state]
            node = tree.root.add(
                f"[bold {color}]{conn.name}[/]",
                data=TreeNodeData(
                    node_type="connection",
                    name=conn.name,
                    connection_id=conn.id,
                ),
                expand=False,
            )
            # If already connected, we keep the children (they'll be re-fetched
            # on expand). If failed, show error child.
            if state == "failed":
                err = self._connection_errors.get(conn.id, "Connection failed")
                node.add_leaf(
                    f"[#CC0403]{err}[/]",
                    data=TreeNodeData(
                        node_type="error",
                        name=err,
                        connection_id=conn.id,
                    ),
                )

        # Update header
        count = len(connections)
        connected = sum(1 for s in self._connection_states.values() if s == "connected")
        title = self.query_one("#tree-title", Label)
        if connected > 0:
            title.update(f"GeoServer ({connected}/{count})")
            title.set_class(True, "connected")
        else:
            title.update(f"GeoServer ({count})")
            title.set_class(False, "connected")

    def on_tree_node_expanded(self, event: Tree.NodeExpanded) -> None:
        """Handle tree node expansion - lazy-load connection trees."""
        node = event.node
        if not node.data or not isinstance(node.data, TreeNodeData):
            return
        if node.data.node_type != "connection":
            return

        conn_id = node.data.connection_id
        state = self._connection_states.get(conn_id, "untested")

        if state in ("untested", "failed"):
            # Clear any existing error children
            node.remove_children()
            node.add_leaf(
                "[#8A8B8B]Loading...[/]",
                data=TreeNodeData(
                    node_type="error",
                    name="Loading...",
                    connection_id=conn_id,
                ),
            )
            self.run_worker(
                self._fetch_connection_tree(conn_id),
                exclusive=False,
                exit_on_error=False,
            )

    async def _fetch_connection_tree(self, conn_id: str) -> None:
        """Fetch and populate the tree for a specific connection.

        Args:
            conn_id: The connection ID to fetch the tree for.
        """
        from geotui.client import test_connection

        conn = self._connections.get(conn_id)
        if conn is None:
            return

        # Test the connection first (decrypt for API use)
        result = await test_connection(self._decrypt_conn(conn))

        if not self.is_mounted:
            return

        # Find the connection node
        conn_node = self._find_connection_node(conn_id)
        if conn_node is None:
            return

        if not result.success:
            self._connection_states[conn_id] = "failed"
            self._connection_errors[conn_id] = result.message
            conn_node.remove_children()
            conn_node.set_label(f"[bold {_STATE_COLORS['failed']}]{conn.name}[/]")
            conn_node.add_leaf(
                f"[#CC0403]{result.message}[/]",
                data=TreeNodeData(
                    node_type="error",
                    name=result.message,
                    connection_id=conn_id,
                ),
            )
            self._update_header()
            return

        # Connection succeeded - fetch full tree
        self._connection_states[conn_id] = "connected"
        self._connection_errors.pop(conn_id, None)
        conn_node.set_label(f"[bold {_STATE_COLORS['connected']}]{conn.name}[/]")

        try:
            async with GeoServerClient(self._decrypt_conn(conn)) as client:
                resources = await client.get_full_tree()

            if not self.is_mounted:
                return

            conn_node.remove_children()

            if not resources:
                conn_node.add_leaf(
                    "[#8A8B8B]No workspaces found[/]",
                    data=TreeNodeData(
                        node_type="error",
                        name="No workspaces found",
                        connection_id=conn_id,
                    ),
                )
            else:
                self._populate_connection_tree(conn_node, conn_id, resources)

            # Update status
            if resources:
                count = sum(
                    1 + len(ws.children) + sum(len(s.children) for s in ws.children)
                    for ws in resources
                )
                ws_count = len(resources)
                status = self.query_one("#tree-status", Static)
                status.update(f"{conn.name}: {ws_count} workspace(s), {count} total")

        except Exception as exc:
            if self.is_mounted:
                self._connection_states[conn_id] = "failed"
                err_msg = str(exc) or "Connection failed"
                self._connection_errors[conn_id] = err_msg
                conn_node.set_label(f"[bold {_STATE_COLORS['failed']}]{conn.name}[/]")
                conn_node.remove_children()
                conn_node.add_leaf(
                    f"[#CC0403]{err_msg}[/]",
                    data=TreeNodeData(
                        node_type="error",
                        name=err_msg,
                        connection_id=conn_id,
                    ),
                )

        self._update_header()

    def _find_connection_node(self, conn_id: str) -> Any:
        """Find the tree node for a given connection ID.

        Args:
            conn_id: Connection ID to find.

        Returns:
            The tree node or None.
        """
        tree = self.query_one("#gs-tree", Tree)
        for child in tree.root.children:
            if (
                child.data
                and isinstance(child.data, TreeNodeData)
                and child.data.node_type == "connection"
                and child.data.connection_id == conn_id
            ):
                return child
        return None

    def _populate_connection_tree(
        self,
        conn_node: Any,
        conn_id: str,
        resources: list[GeoServerResource],
    ) -> None:
        """Populate workspace/store/layer children under a connection node.

        Args:
            conn_node: The connection tree node.
            conn_id: The connection ID.
            resources: List of GeoServerResource workspace objects.
        """
        for ws in resources:
            ws_node = conn_node.add(
                f"[bold {_COLORS['workspace']}]{ws.name}[/]",
                data=TreeNodeData(
                    node_type="workspace",
                    name=ws.name,
                    connection_id=conn_id,
                    resource=ws,
                ),
                expand=False,
            )
            for store in ws.children:
                color = _COLORS.get(store.resource_type, _COLORS["default"])
                label = _LABELS.get(store.resource_type, store.resource_type)
                store_node = ws_node.add(
                    f"[{color}]{store.name}[/] [{label}]",
                    data=TreeNodeData(
                        node_type=store.resource_type,
                        name=store.name,
                        connection_id=conn_id,
                        resource=store,
                    ),
                    expand=False,
                )
                for layer in store.children:
                    store_node.add_leaf(
                        f"[{_COLORS['default']}]{layer.name}[/]",
                        data=TreeNodeData(
                            node_type=layer.resource_type,
                            name=layer.name,
                            connection_id=conn_id,
                            resource=layer,
                        ),
                    )

        conn_node.expand_all()

    def _update_header(self) -> None:
        """Update the tree header based on connection states."""
        count = len(self._connections)
        connected = sum(1 for s in self._connection_states.values() if s == "connected")
        title = self.query_one("#tree-title", Label)
        if connected > 0:
            title.update(f"GeoServer ({connected}/{count})")
            title.set_class(True, "connected")
        else:
            title.update(f"GeoServer ({count})")
            title.set_class(False, "connected")

    # ── Navigation helpers ────────────────────────────────

    def _get_selected_connection(self) -> tuple[Connection, str | None] | None:
        """Get the connection and optional workspace from the cursor node.

        Walks from the cursor node up through parents to find the connection
        node and optionally the workspace node.

        Returns:
            Tuple of (Connection, workspace_name_or_None) or None if no
            connection node is found.
        """
        tree = self.query_one("#gs-tree", Tree)
        if not tree.cursor_node or not tree.cursor_node.data:
            return None

        node = tree.cursor_node
        workspace_name: str | None = None
        conn_id: str | None = None

        # Walk up from cursor to find connection and workspace nodes
        current = node
        while current is not None:
            if isinstance(current.data, TreeNodeData):
                if current.data.node_type == "workspace" and workspace_name is None:
                    workspace_name = current.data.name
                if current.data.node_type == "connection":
                    conn_id = current.data.connection_id
                    break
            current = current.parent

        if conn_id is None:
            return None

        conn = self._connections.get(conn_id)
        if conn is None:
            return None

        return (conn, workspace_name)

    def _get_selected_workspace(self) -> str | None:
        """Get the workspace name from the selected tree node."""
        result = self._get_selected_connection()
        if result is None:
            return None
        return result[1]

    def _refresh_connection(self, conn_id: str) -> None:
        """Clear and re-fetch the tree for a specific connection.

        Args:
            conn_id: The connection ID to refresh.
        """
        self._connection_states[conn_id] = "untested"
        self._connection_errors.pop(conn_id, None)

        conn_node = self._find_connection_node(conn_id)
        if conn_node is not None:
            conn = self._connections.get(conn_id)
            if conn:
                conn_node.remove_children()
                conn_node.set_label(f"[bold {_STATE_COLORS['untested']}]{conn.name}[/]")
                conn_node.add_leaf(
                    "[#8A8B8B]Loading...[/]",
                    data=TreeNodeData(
                        node_type="error",
                        name="Loading...",
                        connection_id=conn_id,
                    ),
                )
                self.run_worker(
                    self._fetch_connection_tree(conn_id),
                    exclusive=False,
                    exit_on_error=False,
                )

    # ── Action panel management ────────────────────────────

    def _hide_action_panel(self) -> None:
        """Hide the action panel."""
        self.query_one("#action-panel").display = False

    def _show_fields(self, title: str, fields: list[tuple[str, str, str]]) -> None:
        """Show the action panel with the given fields.

        Args:
            title: Panel title.
            fields: List of (field_name, label, placeholder).
        """
        panel = self.query_one("#action-panel")
        panel.display = True
        self.query_one("#action-title", Label).update(title)
        self.query_one("#store-type-list", OptionList).display = False

        for i in range(1, _MAX_FIELDS + 1):
            show = i <= len(fields)
            self.query_one(f"#field{i}-label", Label).display = show
            inp = self.query_one(f"#field{i}-input", Input)
            inp.display = show
            inp.value = ""
            if show:
                _name, label, placeholder = fields[i - 1]
                self.query_one(f"#field{i}-label", Label).update(label)
                inp.placeholder = placeholder

        if fields:
            self.query_one("#field1-input", Input).focus()

    def _get_field_values(self, fields: list[tuple[str, str, str]]) -> dict[str, str]:
        """Read form values keyed by field name.

        Args:
            fields: Field definitions to read from.

        Returns:
            Dict mapping field name to input value.
        """
        values = {}
        for i, (field_name, _label, _ph) in enumerate(fields):
            inp = self.query_one(f"#field{i + 1}-input", Input)
            values[field_name] = inp.value.strip()
        return values

    # ── Actions (called from F2 menu) ──────────────────────

    def action_create_workspace(self) -> None:
        """Show the create workspace form."""
        result = self._get_selected_connection()
        if not result:
            self.app.notify(_("No connection active"), severity="warning")
            return
        self._current_action = "workspace"
        self._show_fields(
            _("Create Workspace"),
            [("name", _("Workspace Name"), "my_workspace")],
        )

    def action_create_store(self) -> None:
        """Show the store type selector."""
        result = self._get_selected_connection()
        if not result:
            self.app.notify(_("No connection active"), severity="warning")
            return

        ws = result[1]
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

        for i in range(1, _MAX_FIELDS + 1):
            self.query_one(f"#field{i}-label", Label).display = False
            self.query_one(f"#field{i}-input", Input).display = False

        store_list = self.query_one("#store-type-list", OptionList)
        store_list.clear_options()
        for st in STORE_TYPES:
            color = _CATEGORY_COLORS.get(st.category, _COLORS["default"])
            store_list.add_option(Option(f"[{color}]{st.label}[/] {st.category}"))
        store_list.display = True
        store_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle store type selection from the list."""
        if self._current_action != "store_select":
            return

        idx = event.option_index
        if idx >= len(STORE_TYPES):
            return

        st = STORE_TYPES[idx]
        self._selected_store_type = st
        self._current_action = "store_form"

        self.query_one("#store-type-list", OptionList).display = False
        self._show_fields(
            f"{_('Create')} {st.label} ({self._current_workspace})",
            st.fields,
        )

    def action_copy_from_local(self) -> None:
        """Copy spatial files from the local pane to GeoServer (F5 handler)."""
        from geotui.publisher import (
            discover_spatial_files,
            discover_spatial_files_from_paths,
        )
        from geotui.widgets.file_pane import FilePane

        result = self._get_selected_connection()
        if not result:
            self.app.notify(_("No connection active"), severity="warning")
            return

        conn, _ws = result

        # Get source from left pane.
        try:
            file_pane = self.app.query_one("#left-pane", FilePane)
            selected_files = file_pane.get_selected_files()
            source_dir = file_pane.get_selected_path()
        except Exception:
            self.app.notify(
                _("Cannot read the local file pane"),
                severity="error",
            )
            return

        # Get selected workspace from tree.
        workspace = self._get_selected_workspace()
        if not workspace:
            self.app.notify(
                _("Select a workspace in the tree first"),
                severity="warning",
            )
            return

        # Use Ctrl+T selected files if any, otherwise scan directory.
        if selected_files:
            groups, warnings = discover_spatial_files_from_paths(selected_files)
        else:
            if not source_dir.is_dir():
                self.app.notify(
                    _("Selected path is not a directory"),
                    severity="warning",
                )
                return
            groups, warnings = discover_spatial_files(source_dir)

        if not groups:
            self.app.notify(
                _("No spatial files found"),
                severity="warning",
            )
            return

        # Summarise what was found.
        total_files = sum(len(g.files) for g in groups)
        formats = ", ".join(g.format_type for g in groups)
        source_label = (
            f"{len(selected_files)} selected file(s)"
            if selected_files
            else source_dir.name
        )
        self.app.notify(
            f"Found {total_files} file(s) [{formats}] from {source_label}",
            severity="information",
        )

        # Warn about incomplete bundles that were skipped during discovery.
        for warning in warnings:
            self.app.notify(warning, severity="warning", timeout=15)

        # Run the publish in a background worker.
        self.run_worker(
            self._run_copy_publish(conn, source_dir, workspace, groups, warnings),
            exit_on_error=False,
        )

    async def _run_copy_publish(
        self,
        conn: Connection,
        source_dir: Path,
        workspace: str,
        groups: list[SpatialFileGroup],
        warnings: list[str],
    ) -> None:
        """Run copy-to-publish in background for all discovered spatial groups.

        Args:
            conn: The GeoServer connection to publish to.
            source_dir: Source directory path.
            workspace: Target workspace name.
            groups: Discovered spatial file groups.
            warnings: Discovery warnings.
        """
        from geotui.publisher import NamingStrategy, PublishConfig, run_publish
        from geotui.report import generate_json_report, generate_pdf_report

        total_groups = len(groups)
        progress_panel = self.query_one("#publish-progress")
        progress_bar = self.query_one("#progress-bar", ProgressBar)
        progress_label = self.query_one("#progress-label", Label)
        progress_panel.display = True

        for idx, group in enumerate(groups, start=1):
            store_name = f"{source_dir.name}_{group.format_type}"

            config = PublishConfig(
                workspace=workspace,
                datastore=store_name,
                source_directory=source_dir,
                naming=NamingStrategy.BASENAME,
                concurrency=4,
            )

            group_idx = idx  # bind loop variable for closure

            def progress(
                current: int, total: int, name: str, _gi: int = group_idx
            ) -> None:
                if self.is_mounted:
                    progress_bar.update(total=total, progress=current)
                    progress_label.update(
                        f"[{_gi}/{total_groups}] {current}/{total}: {name}"
                    )
                    self.query_one("#tree-status", Static).update(
                        f"[{_gi}/{total_groups}] Publishing {current}/{total}: {name}"
                    )

            report = await run_publish(self._decrypt_conn(conn), config, progress)
            if self.is_mounted:
                # Refresh the connection that was published to
                self._refresh_connection(conn.id)

        progress_panel.display = False

        # Generate reports after all groups are done.
        if self.is_mounted:
            from datetime import datetime, timezone

            ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            out_dir = Path.cwd() / ".geotui" / "reports"
            out_dir.mkdir(parents=True, exist_ok=True)
            pdf_path = out_dir / f"publish-{ts}.pdf"
            json_path = out_dir / f"publish-{ts}.json"

            # Use the last report for summary generation.
            generate_pdf_report(report, pdf_path)
            generate_json_report(report, json_path)

            summary = (
                f"Published {total_groups} group(s) to '{workspace}'\n"
                f"Report: {pdf_path}"
            )
            self.app.notify(summary, severity="information", timeout=10)
            self._hide_action_panel()

    def action_delete_selected(self) -> None:
        """Delete the selected resource after confirmation."""
        result = self._get_selected_connection()
        if not result:
            self.app.notify(_("No connection active"), severity="warning")
            return

        conn, _ws = result

        tree = self.query_one("#gs-tree", Tree)
        if not tree.cursor_node or not tree.cursor_node.data:
            self.app.notify(_("Select a resource to delete"), severity="warning")
            return

        data = tree.cursor_node.data
        if not isinstance(data, TreeNodeData) or data.resource is None:
            self.app.notify(_("Select a resource to delete"), severity="warning")
            return

        resource_type = data.resource.resource_type
        name = data.name

        # Find parent workspace for stores/layers
        ws_name = self._get_selected_workspace()
        if not ws_name and resource_type != "workspace":
            self.app.notify(_("Cannot determine workspace"), severity="error")
            return

        from geotui.screens.confirm import ConfirmScreen

        if resource_type == "workspace":
            msg = f"Delete workspace '{name}' and ALL its stores and layers?"
        elif resource_type in ("datastore", "coveragestore", "wmsstore"):
            msg = (
                f"Delete {resource_type} '{name}' and all its "
                f"layers in workspace '{ws_name}'?"
            )
        elif resource_type in ("layer", "coverage"):
            msg = f"Delete layer '{name}' from workspace '{ws_name}'?"
        else:
            self.app.notify(
                _("Cannot delete this resource type"),
                severity="warning",
            )
            return

        def handle_confirm(confirmed: bool | None) -> None:
            if confirmed:
                self.run_worker(
                    self._do_delete(conn, resource_type, name, ws_name or ""),
                    exit_on_error=False,
                )

        # Require typing the name for stores and workspaces
        require_name: str | None = None
        if resource_type in (
            "workspace",
            "datastore",
            "coveragestore",
            "wmsstore",
        ):
            require_name = name

        self.app.push_screen(
            ConfirmScreen(_("Confirm Delete"), msg, require_name=require_name),
            callback=handle_confirm,
        )

    async def _do_delete(
        self, conn: Connection, resource_type: str, name: str, workspace: str
    ) -> None:
        """Execute the delete operation.

        Args:
            conn: The GeoServer connection.
            resource_type: Type of resource to delete.
            name: Resource name.
            workspace: Parent workspace name.
        """
        logger.info(
            "Deleting %s '%s' in workspace '%s' on connection '%s'",
            resource_type, name, workspace, conn.name,
        )
        try:
            decrypted = self._decrypt_conn(conn)
            async with GeoServerClient(decrypted) as client:
                if resource_type == "workspace":
                    ok = await client.delete_workspace(name, recurse=True)
                elif resource_type == "datastore":
                    ok = await client.delete_datastore(workspace, name, recurse=True)
                elif resource_type == "coveragestore":
                    ok = await client.delete_coveragestore(
                        workspace, name, recurse=True
                    )
                elif resource_type in ("layer", "coverage"):
                    ok = await client.delete_layer(workspace, name)
                else:
                    logger.warning("Unknown resource type: %s", resource_type)
                    ok = False
        except Exception:
            logger.exception("Delete failed for %s '%s'", resource_type, name)
            ok = False

        if self.is_mounted:
            if ok:
                logger.info("Deleted %s '%s' successfully", resource_type, name)
                self.app.notify(f"Deleted '{name}'", severity="information")
                self._refresh_connection(conn.id)
            else:
                logger.error("Failed to delete %s '%s'", resource_type, name)
                self.app.notify(f"Failed to delete '{name}'", severity="error")

    def action_refresh(self) -> None:
        """Refresh the selected connection, or all connections if none selected."""
        result = self._get_selected_connection()
        if result:
            conn, _ws = result
            self._refresh_connection(conn.id)
        else:
            # No selection - refresh all connections
            for conn_id in list(self._connections.keys()):
                self._refresh_connection(conn_id)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle action panel buttons."""
        if event.button.id == "btn-create":
            self._do_create()
        elif event.button.id == "btn-action-cancel":
            self._hide_action_panel()

    def _do_create(self) -> None:
        """Execute the current create action."""
        result = self._get_selected_connection()
        if not result:
            return

        conn, _ws = result

        if self._current_action == "workspace":
            name = self.query_one("#field1-input", Input).value.strip()
            if not name:
                self.app.notify(_("Name is required"), severity="error")
                return
            self.run_worker(self._create_workspace(conn, name), exit_on_error=False)
        elif self._current_action == "store_form" and self._selected_store_type:
            values = self._get_field_values(self._selected_store_type.fields)
            if not values.get("name"):
                self.app.notify(_("Name is required"), severity="error")
                return
            self.run_worker(
                self._create_store(conn, self._selected_store_type, values),
                exit_on_error=False,
            )

    async def _create_workspace(self, conn: Connection, name: str) -> None:
        """Create a workspace via the API.

        Args:
            conn: The GeoServer connection.
            name: Workspace name.
        """
        async with GeoServerClient(self._decrypt_conn(conn)) as client:
            ok = await client.create_workspace(name)
        if self.is_mounted:
            if ok:
                self.app.notify(f"Workspace '{name}' created", severity="information")
                self._hide_action_panel()
                self._refresh_connection(conn.id)
            else:
                self.app.notify(
                    f"Failed to create workspace '{name}'",
                    severity="error",
                )

    async def _create_store(
        self, conn: Connection, store_type: StoreType, field_values: dict[str, str]
    ) -> None:
        """Create a store via the API using the type registry.

        Args:
            conn: The GeoServer connection.
            store_type: Store type definition.
            field_values: Form field values.
        """
        ws = self._current_workspace
        name = field_values.get("name", "")
        async with GeoServerClient(self._decrypt_conn(conn)) as client:
            ok = await client.create_store_from_type(ws, store_type, field_values)
        if self.is_mounted:
            if ok:
                self.app.notify(
                    f"{store_type.label} '{name}' created in {ws}",
                    severity="information",
                )
                self._hide_action_panel()
                self._refresh_connection(conn.id)
            else:
                self.app.notify(
                    f"Failed to create {store_type.label} '{name}'",
                    severity="error",
                )

    # ── Tree display ───────────────────────────────────────

    def watch_is_active(self, value: bool) -> None:
        """Update styling when active state changes."""
        self.set_class(value, "active")

    @staticmethod
    def _store_color(resource_type: str) -> str:
        """Get the display color for a store type."""
        return _COLORS.get(resource_type, _COLORS["default"])

    @staticmethod
    def _store_label(resource_type: str) -> str:
        """Get a short label for a store type."""
        return _LABELS.get(resource_type, resource_type)

    def refresh_tree(self) -> None:
        """Refresh the tree - delegates to refresh_connections.

        Kept for backwards compatibility with action_menu and other callers.
        """
        self.refresh_connections()
