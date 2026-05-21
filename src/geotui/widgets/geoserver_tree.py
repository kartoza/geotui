"""GeoServer resource tree widget.

Displays the GeoServer resource hierarchy (workspaces > stores > layers)
in a tree view, populated from the active connection. Provides actions
for creating workspaces and stores via the F2 context menu.
"""

from pathlib import Path
from typing import Any

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
    STORE_TYPES,
    GeoServerClient,
    GeoServerResource,
    StoreType,
)
from geotui.config import Connection
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

# Maximum number of dynamic form fields
_MAX_FIELDS = 6


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

    connection: reactive[Connection | None] = reactive(None)
    is_active: reactive[bool] = reactive(False)
    loading: reactive[bool] = reactive(False)

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the tree widget."""
        super().__init__(**kwargs)
        self._current_action = ""
        self._current_workspace = ""
        self._selected_store_type: StoreType | None = None

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
        """Set initial state."""
        tree = self.query_one("#gs-tree", Tree)
        tree.display = False
        tree.show_root = False
        self._hide_action_panel()

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

    def _get_selected_workspace(self) -> str | None:
        """Get the workspace name from the selected tree node."""
        tree = self.query_one("#gs-tree", Tree)
        if tree.cursor_node and tree.cursor_node.data:
            node = tree.cursor_node
            data = node.data
            if isinstance(data, GeoServerResource):
                if data.resource_type == "workspace":
                    return data.name
                parent = node.parent
                while parent and parent.data:
                    if (
                        isinstance(parent.data, GeoServerResource)
                        and parent.data.resource_type == "workspace"
                    ):
                        return parent.data.name
                    parent = parent.parent
        return None

    # ── Actions (called from F2 menu) ──────────────────────

    def action_create_workspace(self) -> None:
        """Show the create workspace form."""
        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return
        self._current_action = "workspace"
        self._show_fields(
            _("Create Workspace"),
            [("name", _("Workspace Name"), "my_workspace")],
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
        from geotui.publisher import discover_spatial_files
        from geotui.widgets.file_pane import FilePane

        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return

        # Get source path from left pane.
        try:
            file_pane = self.app.query_one("#left-pane", FilePane)
            source_dir = file_pane.get_selected_path()
        except Exception:
            self.app.notify(
                _("Cannot read the local file pane"),
                severity="error",
            )
            return

        if not source_dir.is_dir():
            self.app.notify(
                _("Selected path is not a directory"),
                severity="warning",
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

        # Discover spatial files.
        groups, warnings = discover_spatial_files(source_dir)
        if not groups:
            self.app.notify(
                _("No spatial files found in ") + str(source_dir),
                severity="warning",
            )
            return

        # Summarise what was found.
        total_files = sum(len(g.files) for g in groups)
        formats = ", ".join(g.format_type for g in groups)
        self.app.notify(
            f"Found {total_files} file(s) [{formats}] in {source_dir.name}",
            severity="information",
        )

        # Run the publish in a background worker.
        self.run_worker(
            self._run_copy_publish(source_dir, workspace, groups, warnings),
            exit_on_error=False,
        )

    async def _run_copy_publish(
        self,
        source_dir: Path,
        workspace: str,
        groups: list,
        warnings: list[str],
    ) -> None:
        """Run copy-to-publish in background for all discovered spatial groups."""
        from geotui.publisher import NamingStrategy, PublishConfig, run_publish
        from geotui.report import generate_json_report, generate_pdf_report

        if self.connection is None:
            return

        total_groups = len(groups)
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
                    status = self.query_one("#tree-status", Static)
                    status.update(
                        f"[{_gi}/{total_groups}] Publishing {current}/{total}: {name}"
                    )

            report = await run_publish(self.connection, config, progress)
            if self.is_mounted:
                self.refresh_tree()

        # Generate reports after all groups are done.
        if self.is_mounted and self.connection is not None:
            from datetime import datetime, timezone

            ts = datetime.now(tz=timezone.utc).strftime("%Y%m%d-%H%M%S")
            out_dir = Path.home() / ".local/share/geotui/reports"
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
        if not self.connection:
            self.app.notify(_("No connection active"), severity="warning")
            return

        tree = self.query_one("#gs-tree", Tree)
        if not tree.cursor_node or not tree.cursor_node.data:
            self.app.notify(_("Select a resource to delete"), severity="warning")
            return

        data = tree.cursor_node.data
        if not isinstance(data, GeoServerResource):
            return

        resource_type = data.resource_type
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

        def handle_confirm(confirmed: bool) -> None:
            if confirmed:
                self.run_worker(
                    self._do_delete(resource_type, name, ws_name or ""),
                    exit_on_error=False,
                )

        self.app.push_screen(
            ConfirmScreen(_("Confirm Delete"), msg),
            callback=handle_confirm,
        )

    async def _do_delete(self, resource_type: str, name: str, workspace: str) -> None:
        """Execute the delete operation.

        Args:
            resource_type: Type of resource to delete.
            name: Resource name.
            workspace: Parent workspace name.
        """
        if self.connection is None:
            return

        async with GeoServerClient(self.connection) as client:
            if resource_type == "workspace":
                ok = await client.delete_workspace(name, recurse=True)
            elif resource_type == "datastore":
                ok = await client.delete_datastore(workspace, name, recurse=True)
            elif resource_type == "coveragestore":
                ok = await client.delete_coveragestore(workspace, name, recurse=True)
            elif resource_type in ("layer", "coverage"):
                ok = await client.delete_layer(workspace, name)
            else:
                ok = False

        if self.is_mounted:
            if ok:
                self.app.notify(f"Deleted '{name}'", severity="information")
                self.refresh_tree()
            else:
                self.app.notify(f"Failed to delete '{name}'", severity="error")

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

        if self._current_action == "workspace":
            name = self.query_one("#field1-input", Input).value.strip()
            if not name:
                self.app.notify(_("Name is required"), severity="error")
                return
            self.run_worker(self._create_workspace(name), exit_on_error=False)
        elif self._current_action == "store_form" and self._selected_store_type:
            values = self._get_field_values(self._selected_store_type.fields)
            if not values.get("name"):
                self.app.notify(_("Name is required"), severity="error")
                return
            self.run_worker(
                self._create_store(self._selected_store_type, values),
                exit_on_error=False,
            )

    async def _create_workspace(self, name: str) -> None:
        """Create a workspace via the API."""
        if self.connection is None:
            return
        async with GeoServerClient(self.connection) as client:
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

    async def _create_store(
        self, store_type: StoreType, field_values: dict[str, str]
    ) -> None:
        """Create a store via the API using the type registry."""
        if self.connection is None:
            return
        ws = self._current_workspace
        name = field_values.get("name", "")
        async with GeoServerClient(self.connection) as client:
            ok = await client.create_store_from_type(ws, store_type, field_values)
        if self.is_mounted:
            if ok:
                self.app.notify(
                    f"{store_type.label} '{name}' created in {ws}",
                    severity="information",
                )
                self._hide_action_panel()
                self.refresh_tree()
            else:
                self.app.notify(
                    f"Failed to create {store_type.label} '{name}'",
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
        """Start loading the GeoServer resource tree."""
        self.loading = True
        self.query_one("#no-connection", Static).display = False
        self.query_one("#gs-tree", Tree).display = True
        self.query_one("#tree-status", Static).update(_("Loading..."))
        self.run_worker(self._fetch_tree(conn), exclusive=True, exit_on_error=False)

    async def _fetch_tree(self, conn: Connection) -> None:
        """Fetch and populate the tree from GeoServer."""
        async with GeoServerClient(conn) as client:
            try:
                resources = await client.get_full_tree()
                if not self.is_mounted:
                    return
                if not resources:
                    status = self.query_one("#tree-status", Static)
                    status.update(
                        "[#CC0403]Server unreachable or returned no workspaces[/]"
                    )
                    self.app.notify(
                        _(
                            "Could not fetch workspaces. Check the "
                            "server URL and credentials in Settings (F9)."
                        ),
                        severity="error",
                        timeout=10,
                    )
                    return
                self._populate_tree(resources)
                count = sum(
                    1 + len(ws.children) + sum(len(s.children) for s in ws.children)
                    for ws in resources
                )
                ws_count = len(resources)
                status = self.query_one("#tree-status", Static)
                status.update(f"{ws_count} workspace(s), {count} total resources")
            except Exception:  # nosec B110
                if self.is_mounted:
                    status = self.query_one("#tree-status", Static)
                    status.update("[#CC0403]Connection failed[/]")
                    self.app.notify(
                        _("Connection to GeoServer failed. Check Settings (F9)."),
                        severity="error",
                        timeout=10,
                    )
            finally:
                self.loading = False

    def _populate_tree(self, resources: list[GeoServerResource]) -> None:
        """Populate the tree widget with GeoServer resources."""
        tree = self.query_one("#gs-tree", Tree)
        tree.clear()

        for ws in resources:
            ws_node = tree.root.add(
                f"[bold {_COLORS['workspace']}]{ws.name}[/]",
                data=ws,
                expand=False,
            )
            for store in ws.children:
                color = _COLORS.get(store.resource_type, _COLORS["default"])
                label = _LABELS.get(store.resource_type, store.resource_type)
                store_node = ws_node.add(
                    f"[{color}]{store.name}[/] [{label}]",
                    data=store,
                    expand=False,
                )
                for layer in store.children:
                    store_node.add_leaf(
                        f"[{_COLORS['default']}]{layer.name}[/]",
                        data=layer,
                    )

        tree.root.expand_all()

    @staticmethod
    def _store_color(resource_type: str) -> str:
        """Get the display color for a store type."""
        return _COLORS.get(resource_type, _COLORS["default"])

    @staticmethod
    def _store_label(resource_type: str) -> str:
        """Get a short label for a store type."""
        return _LABELS.get(resource_type, resource_type)

    def refresh_tree(self) -> None:
        """Refresh the tree from the current connection."""
        if self.connection:
            self._load_tree(self.connection)
