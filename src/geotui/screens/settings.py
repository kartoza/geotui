"""Settings screen for managing GeoServer connections.

Single-screen layout with connection list on the left and detail/edit form
on the right. No popups - all CRUD happens inline following the cloudbench pattern.
"""

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Static,
)

from geotui.config import ConfigManager, Connection
from geotui.i18n import _


class ConnectionListItem(ListItem):
    """A list item representing a GeoServer connection."""

    def __init__(self, conn: Connection) -> None:
        """Initialize with a connection.

        Args:
            conn: The connection this item represents.
        """
        super().__init__()
        self.conn_id = conn.id
        self.conn_name = conn.name

    def compose(self) -> ComposeResult:
        """Compose the list item."""
        yield Label(self.conn_name or "(unnamed)")


class SettingsScreen(Screen[None]):
    """Settings screen for managing GeoServer connections.

    Layout: connection list (left) | detail/edit form (right).
    Modes: view (read-only detail) and edit (form with inputs).
    """

    BINDINGS = [
        ("escape", "go_back", _("Back")),
        ("a", "add", _("Add")),
        ("e", "edit", _("Edit")),
        ("d", "delete", _("Delete")),
        ("t", "test_connection", _("Test")),
    ]

    CSS = """
    SettingsScreen {
        layout: vertical;
    }

    SettingsScreen #settings-body {
        height: 1fr;
    }

    SettingsScreen #conn-list-panel {
        width: 30;
        border: round #569FC6;
        background: #1a1a2e;
        padding: 0;
    }

    SettingsScreen #conn-list-panel .panel-title {
        width: 100%;
        height: 1;
        background: #0f3460;
        color: #DF9E2F;
        text-style: bold;
        text-align: center;
    }

    SettingsScreen #conn-list {
        height: 1fr;
        background: #1a1a2e;
    }

    SettingsScreen #conn-list > ListItem {
        color: #8A8B8B;
        padding: 0 1;
    }

    SettingsScreen #conn-list > ListItem.-highlight {
        background: #06969A;
        color: #1a1a2e;
        text-style: bold;
    }

    SettingsScreen #list-buttons {
        height: auto;
        width: 100%;
        padding: 1 0;
        align: center middle;
    }

    SettingsScreen #list-buttons Button {
        margin: 0 1;
        min-width: 8;
    }

    SettingsScreen #detail-panel {
        width: 1fr;
        border: round #569FC6;
        background: #1a1a2e;
        padding: 1 2;
    }

    SettingsScreen #detail-panel .panel-title {
        width: 100%;
        height: 1;
        background: #0f3460;
        color: #DF9E2F;
        text-style: bold;
        text-align: center;
        margin: 0 0 1 0;
    }

    SettingsScreen .field-label {
        color: #569FC6;
        margin: 1 0 0 0;
        text-style: bold;
    }

    SettingsScreen .field-value {
        color: #8A8B8B;
        margin: 0 0 0 2;
    }

    SettingsScreen .field-value-password {
        color: #8A8B8B;
        margin: 0 0 0 2;
    }

    SettingsScreen Input {
        margin: 0 0 0 0;
        width: 100%;
    }

    SettingsScreen Input:focus {
        border: round #DF9E2F;
    }

    SettingsScreen #form-buttons {
        height: auto;
        width: 100%;
        margin: 1 0 0 0;
        align: center middle;
    }

    SettingsScreen #form-buttons Button {
        margin: 0 1;
    }

    SettingsScreen .btn-primary {
        background: #569FC6;
        color: #1a1a2e;
    }

    SettingsScreen .btn-success {
        background: #06969A;
        color: #1a1a2e;
    }

    SettingsScreen .btn-danger {
        background: #CC0403;
        color: white;
    }

    SettingsScreen .btn-default {
        background: #8A8B8B;
        color: #1a1a2e;
    }

    SettingsScreen #empty-detail {
        width: 100%;
        height: 100%;
        content-align: center middle;
        color: #8A8B8B;
    }

    SettingsScreen #branding {
        dock: bottom;
        height: 1;
        width: 100%;
        text-align: center;
        color: #8A8B8B;
        background: #0f3460;
    }
    """

    editing: reactive[bool] = reactive(False)
    selected_id: reactive[str] = reactive("")

    def __init__(self, config_manager: ConfigManager) -> None:
        """Initialize the settings screen.

        Args:
            config_manager: The application config manager.
        """
        super().__init__()
        self._config = config_manager

    def compose(self) -> ComposeResult:
        """Compose the settings screen layout."""
        yield Header(show_clock=True)
        with Horizontal(id="settings-body"):
            with Vertical(id="conn-list-panel"):
                yield Label(_("Connections"), classes="panel-title")
                yield ListView(id="conn-list")
                with Horizontal(id="list-buttons"):
                    yield Button(_("Add"), id="btn-add", classes="btn-success")
                    yield Button(_("Delete"), id="btn-delete", classes="btn-danger")
            with Vertical(id="detail-panel"):
                yield Label(_("Connection Details"), classes="panel-title")
                yield Static(
                    _("Select a connection or press Add to create one."),
                    id="empty-detail",
                )
                with Vertical(id="view-mode"):
                    yield Label(_("Name"), classes="field-label")
                    yield Static("", id="view-name", classes="field-value")
                    yield Label(_("URL"), classes="field-label")
                    yield Static("", id="view-url", classes="field-value")
                    yield Label(_("Username"), classes="field-label")
                    yield Static("", id="view-username", classes="field-value")
                    yield Label(_("Password"), classes="field-label")
                    yield Static("", id="view-password", classes="field-value-password")
                    with Horizontal(id="form-buttons"):
                        yield Button(_("Edit"), id="btn-edit", classes="btn-primary")
                        yield Button(
                            _("Connect"), id="btn-connect", classes="btn-success"
                        )
                with Vertical(id="edit-mode"):
                    yield Label(_("Name"), classes="field-label")
                    yield Input(placeholder=_("Connection name"), id="input-name")
                    yield Label(_("URL"), classes="field-label")
                    yield Input(
                        placeholder="https://geoserver.example.com/geoserver",
                        id="input-url",
                    )
                    yield Label(_("Username"), classes="field-label")
                    yield Input(placeholder=_("Username"), id="input-username")
                    yield Label(_("Password"), classes="field-label")
                    yield Input(
                        placeholder=_("Password"), id="input-password", password=True
                    )
                    with Horizontal(id="form-buttons"):
                        yield Button(_("Save"), id="btn-save", classes="btn-success")
                        yield Button(
                            _("Cancel"), id="btn-cancel", classes="btn-default"
                        )
        yield Static(
            "Made with \u2764 by Kartoza | Donate! | GitHub",
            id="branding",
        )
        yield Footer()

    def on_mount(self) -> None:
        """Initialize screen state."""
        self._refresh_list()
        self._show_mode("empty")

    def _refresh_list(self) -> None:
        """Reload the connection list from config."""
        list_view = self.query_one("#conn-list", ListView)
        list_view.clear()
        for conn in self._config.config.connections:
            list_view.append(ConnectionListItem(conn))

    def _show_mode(self, mode: str) -> None:
        """Switch between empty, view, and edit display modes.

        Args:
            mode: One of 'empty', 'view', or 'edit'.
        """
        empty = self.query_one("#empty-detail", Static)
        view = self.query_one("#view-mode", Vertical)
        edit = self.query_one("#edit-mode", Vertical)

        empty.display = mode == "empty"
        view.display = mode == "view"
        edit.display = mode == "edit"
        self.editing = mode == "edit"

    def _show_connection_detail(self, conn: Connection) -> None:
        """Display connection details in view mode.

        Args:
            conn: Connection to display.
        """
        self.query_one("#view-name", Static).update(conn.name or "(unnamed)")
        self.query_one("#view-url", Static).update(conn.url or "(not set)")
        self.query_one("#view-username", Static).update(conn.username or "(not set)")
        masked = "*" * len(conn.password) if conn.password else "(not set)"
        self.query_one("#view-password", Static).update(masked)
        self._show_mode("view")

    def _populate_edit_form(self, conn: Connection | None = None) -> None:
        """Populate the edit form with connection data.

        Args:
            conn: Connection to edit, or None for a new connection.
        """
        self.query_one("#input-name", Input).value = conn.name if conn else ""
        self.query_one("#input-url", Input).value = conn.url if conn else ""
        self.query_one("#input-username", Input).value = conn.username if conn else ""
        self.query_one("#input-password", Input).value = conn.password if conn else ""
        self._show_mode("edit")
        self.query_one("#input-name", Input).focus()

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        """Handle connection selection from the list."""
        item = event.item
        if isinstance(item, ConnectionListItem):
            self.selected_id = item.conn_id
            conn = self._config.get_connection(item.conn_id)
            if conn:
                self._show_connection_detail(conn)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        button_id = event.button.id

        if button_id == "btn-add":
            self.action_add()
        elif button_id == "btn-edit":
            self.action_edit()
        elif button_id == "btn-delete":
            self.action_delete()
        elif button_id == "btn-connect":
            self.action_test_connection()
        elif button_id == "btn-save":
            self._save_form()
        elif button_id == "btn-cancel":
            self._cancel_edit()

    def action_add(self) -> None:
        """Start adding a new connection."""
        self.selected_id = ""
        self._populate_edit_form(None)

    def action_edit(self) -> None:
        """Edit the selected connection."""
        if not self.selected_id:
            self.notify(_("Select a connection first"), severity="warning")
            return
        conn = self._config.get_connection(self.selected_id)
        if conn:
            self._populate_edit_form(conn)

    def action_delete(self) -> None:
        """Delete the selected connection."""
        if not self.selected_id:
            self.notify(_("Select a connection first"), severity="warning")
            return
        conn = self._config.get_connection(self.selected_id)
        name = conn.name if conn else self.selected_id
        if self._config.remove_connection(self.selected_id):
            self.notify(f"{name} deleted", severity="information")
            self.selected_id = ""
            self._refresh_list()
            self._show_mode("empty")
        else:
            self.notify(_("Connection not found"), severity="error")

    def action_test_connection(self) -> None:
        """Test the selected connection."""
        if not self.selected_id:
            self.notify(_("Select a connection first"), severity="warning")
            return
        conn = self._config.get_connection(self.selected_id)
        if conn:
            self.run_worker(self._do_test_connection(conn), exit_on_error=False)

    async def _do_test_connection(self, conn: Connection) -> None:
        """Test and activate the connection.

        Tests credentials via GeoServer REST API. On success, sets
        this connection as active and updates the main dual pane.

        Args:
            conn: Connection to test.
        """
        from geotui.client import test_connection

        self.notify(_("Testing connection..."), severity="information")
        result = await test_connection(conn)
        if result.success:
            self.notify(result.message, severity="information")
            # Mark this connection as active, deactivate others
            for c in self._config.config.connections:
                c.is_active = c.id == conn.id
            self._config.save()
            # Update the dual pane with the active connection
            from geotui.widgets.dual_pane import DualPane

            try:
                dual_pane = self.app.query_one(DualPane)
                dual_pane.set_connection(conn)
            except Exception:  # nosec B110
                self.log.warning("Could not update dual pane")
        else:
            self.notify(result.message, severity="error")

    def _save_form(self) -> None:
        """Save the current form data."""
        name = self.query_one("#input-name", Input).value.strip()
        url = self.query_one("#input-url", Input).value.strip()
        username = self.query_one("#input-username", Input).value.strip()
        password = self.query_one("#input-password", Input).value

        if not name:
            self.notify(_("Name is required"), severity="error")
            self.query_one("#input-name", Input).focus()
            return

        if not url:
            self.notify(_("URL is required"), severity="error")
            self.query_one("#input-url", Input).focus()
            return

        if self.selected_id:
            self._config.update_connection(
                self.selected_id,
                name=name,
                url=url,
                username=username,
                password=password,
            )
            self.notify(f"{name} updated", severity="information")
        else:
            conn = Connection(name=name, url=url, username=username, password=password)
            self._config.add_connection(conn)
            self.selected_id = conn.id
            self.notify(f"{name} added", severity="information")

        self._refresh_list()
        saved_conn = self._config.get_connection(self.selected_id)
        if saved_conn:
            self._show_connection_detail(saved_conn)

    def _cancel_edit(self) -> None:
        """Cancel editing and return to view or empty mode."""
        if self.selected_id:
            conn = self._config.get_connection(self.selected_id)
            if conn:
                self._show_connection_detail(conn)
                return
        self._show_mode("empty")

    def action_go_back(self) -> None:
        """Return to the main screen."""
        if self.editing:
            self._cancel_edit()
        else:
            self.app.pop_screen()
