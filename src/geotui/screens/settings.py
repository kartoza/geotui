"""Settings screen for managing GeoServer connections.

Single-screen layout with connection list on the left and detail/edit form
on the right. No popups - all CRUD happens inline following the cloudbench pattern.
"""

from cryptography.fernet import Fernet
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, VerticalScroll
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

from geotui.config import ConfigManager, Connection, decrypt_value
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

    SettingsScreen #conn-status {
        width: 100%;
        height: auto;
        margin: 1 0 0 0;
        text-align: center;
        text-style: bold;
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

    /* Edit form: fields scroll, action bar stays pinned and always visible. */
    SettingsScreen #edit-mode {
        height: 1fr;
        layout: vertical;
    }

    SettingsScreen #edit-fields {
        height: 1fr;
        overflow-y: auto;
    }

    SettingsScreen .action-bar {
        height: auto;
        width: 100%;
        padding: 1 0 0 0;
        align: center middle;
        background: #1a1a2e;
        border-top: solid #0f3460;
    }

    SettingsScreen .action-bar Button {
        margin: 0 1;
    }

    SettingsScreen #vault-label {
        color: #8A8B8B;
        margin: 0 1 0 0;
        content-align: left middle;
        height: 100%;
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

    SettingsScreen #vault-buttons {
        height: auto;
        width: 100%;
        align: center middle;
        padding: 0 1;
        dock: bottom;
        margin: 0 0 1 0;
    }

    SettingsScreen #vault-buttons Button {
        margin: 0 1;
        min-width: 16;
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
                    yield Static("", id="conn-status")
                    with Horizontal(id="form-buttons"):
                        yield Button(_("Edit"), id="btn-edit", classes="btn-primary")
                        yield Button(
                            _("Connect"), id="btn-connect", classes="btn-success"
                        )
                with Vertical(id="edit-mode"):
                    with VerticalScroll(id="edit-fields"):
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
                            placeholder=_("Password"),
                            id="input-password",
                            password=True,
                        )
                    with Horizontal(id="edit-buttons", classes="action-bar"):
                        yield Button(_("Save"), id="btn-save", classes="btn-success")
                        yield Button(
                            _("Save & Connect"),
                            id="btn-save-connect",
                            classes="btn-primary",
                        )
                        yield Button(
                            _("Cancel"), id="btn-cancel", classes="btn-default"
                        )
        with Horizontal(id="vault-buttons"):
            yield Label(_("Master vault:"), id="vault-label")
            yield Button(
                _("Change Master Password"),
                id="btn-change-pw",
                classes="btn-primary",
            )
            yield Button(
                _("Reset Vault"),
                id="btn-reset-vault",
                classes="btn-danger",
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

        # Hide the master-vault controls while editing a connection so they
        # cannot be mistaken for the form's Save/Cancel actions.
        self.query_one("#vault-buttons").display = mode != "edit"

    def _get_vault_key(self) -> Fernet | None:
        """Get the vault Fernet key from the app."""
        from geotui.app import GeoTUIApp

        app = self.app
        if isinstance(app, GeoTUIApp):
            return app.vault_key
        return None

    def _decrypt_password(self, encrypted: str) -> str:
        """Decrypt a connection password using the vault key.

        Args:
            encrypted: Encrypted password token.

        Returns:
            Decrypted plaintext, or the original value if no vault.
        """
        fernet = self._get_vault_key()
        if fernet and encrypted:
            try:
                return decrypt_value(encrypted, fernet)
            except Exception:
                return encrypted
        return encrypted

    def _show_connection_detail(self, conn: Connection) -> None:
        """Display connection details in view mode.

        Args:
            conn: Connection to display.
        """
        self.query_one("#view-name", Static).update(conn.name or "(unnamed)")
        self.query_one("#view-url", Static).update(conn.url or "(not set)")
        self.query_one("#view-username", Static).update(conn.username or "(not set)")
        pw = self._decrypt_password(conn.password)
        masked = "*" * len(pw) if pw else "(not set)"
        self.query_one("#view-password", Static).update(masked)
        # Reflect any previously-established connection state.
        if conn.is_active:
            self._show_connection_status(_("✓ Connected"), "#06969A")
        else:
            self._show_connection_status("", "#8A8B8B")
        self._show_mode("view")

    def _show_connection_status(self, text: str, color: str) -> None:
        """Update the connection status line in the detail panel.

        Args:
            text: Status text to display (empty to clear).
            color: Hex colour for the status text.
        """
        try:
            status = self.query_one("#conn-status", Static)
        except Exception:
            return
        status.update(f"[b {color}]{text}[/]" if text else "")

    def _populate_edit_form(self, conn: Connection | None = None) -> None:
        """Populate the edit form with connection data.

        Args:
            conn: Connection to edit, or None for a new connection.
        """
        self.query_one("#input-name", Input).value = conn.name if conn else ""
        self.query_one("#input-url", Input).value = conn.url if conn else ""
        self.query_one("#input-username", Input).value = conn.username if conn else ""
        pw = self._decrypt_password(conn.password) if conn else ""
        self.query_one("#input-password", Input).value = pw
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
        elif button_id == "btn-save-connect":
            if self._save_form():
                self.action_test_connection()
        elif button_id == "btn-cancel":
            self._cancel_edit()
        elif button_id == "btn-change-pw":
            self._change_master_password()
        elif button_id == "btn-reset-vault":
            self._reset_vault()

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
        # Decrypt password before testing
        fernet = self._get_vault_key()
        test_conn = conn
        if fernet:
            test_conn = self._config.decrypt_connection(conn, fernet)
        result = await test_connection(test_conn)
        if result.success:
            self.notify(
                _("{name} — {message}").format(name=conn.name, message=result.message),
                title=_("✓ Connected"),
                severity="information",
                timeout=6,
            )
            # Mark this connection as active, deactivate others
            for c in self._config.config.connections:
                c.is_active = c.id == conn.id
            self._config.save()
            # Reflect the connected state in the detail panel.
            self._show_connection_status(_("✓ Connected"), "#06969A")
            # Refresh the tree to pick up the new connection state
            from geotui.widgets.geoserver_tree import GeoServerTree

            try:
                tree = self.app.query_one("#right-pane", GeoServerTree)
                tree.refresh_connections()
            except Exception:
                self.log.warning("Could not update GeoServer tree")
        else:
            self.notify(
                result.message,
                title=_("✗ Connection failed"),
                severity="error",
                timeout=8,
            )
            self._show_connection_status(_("✗ Connection failed"), "#CC0403")

    def _encrypt_password(self, plaintext: str) -> str:
        """Encrypt a password for storage using the vault key.

        Args:
            plaintext: Password in cleartext.

        Returns:
            Encrypted token, or original value if no vault.
        """
        fernet = self._get_vault_key()
        if fernet and plaintext:
            return self._config.encrypt_password(plaintext, fernet)
        return plaintext

    def _save_form(self) -> bool:
        """Save the current form data.

        Returns:
            ``True`` if the connection was saved, ``False`` if validation
            failed or the vault was locked (nothing was persisted).
        """
        name = self.query_one("#input-name", Input).value.strip()
        url = self.query_one("#input-url", Input).value.strip()
        username = self.query_one("#input-username", Input).value.strip()
        password = self.query_one("#input-password", Input).value

        if not name:
            self.notify(_("Name is required"), severity="error")
            self.query_one("#input-name", Input).focus()
            return False

        if not url:
            self.notify(_("URL is required"), severity="error")
            self.query_one("#input-url", Input).focus()
            return False

        # Refuse to save while the vault is locked: doing so would store the
        # password in plaintext (a leak) or double-encrypt an existing token
        # (which later fails to decrypt). Prompt the user to unlock first.
        if self._config.has_vault and self._get_vault_key() is None:
            self.notify(
                _("Vault is locked. Unlock it before saving credentials."),
                severity="error",
            )
            return False

        # Encrypt the password before storing
        encrypted_pw = self._encrypt_password(password)

        if self.selected_id:
            self._config.update_connection(
                self.selected_id,
                name=name,
                url=url,
                username=username,
                password=encrypted_pw,
            )
            self.notify(_("{name} saved").format(name=name), severity="information")
        else:
            conn = Connection(
                name=name, url=url, username=username, password=encrypted_pw
            )
            self._config.add_connection(conn)
            self.selected_id = conn.id
            self.notify(_("{name} saved").format(name=name), severity="information")

        self._refresh_list()
        saved_conn = self._config.get_connection(self.selected_id)
        if saved_conn:
            self._show_connection_detail(saved_conn)
        return True

    def _cancel_edit(self) -> None:
        """Cancel editing and return to view or empty mode."""
        if self.selected_id:
            conn = self._config.get_connection(self.selected_id)
            if conn:
                self._show_connection_detail(conn)
                return
        self._show_mode("empty")

    def _change_master_password(self) -> None:
        """Change the master password via a two-step prompt."""
        from geotui.screens.unlock import UnlockScreen

        # First prompt for the old password
        def handle_old_pw(old_pw: str | None) -> None:
            if not old_pw:
                return
            fernet = self._config.unlock(old_pw)
            if not fernet:
                self.notify(_("Current password is wrong"), severity="error")
                return

            # Now prompt for the new password
            def handle_new_pw(new_pw: str | None) -> None:
                if not new_pw:
                    return
                if self._config.change_master_password(old_pw, new_pw):
                    # Update the app's vault key
                    from geotui.app import GeoTUIApp

                    app = self.app
                    if isinstance(app, GeoTUIApp):
                        app.vault_key = self._config.unlock(new_pw)
                    self.notify(
                        _("Master password changed successfully"),
                        severity="information",
                    )
                else:
                    self.notify(
                        _("Failed to change password"),
                        severity="error",
                    )

            self.app.push_screen(UnlockScreen(is_setup=True), callback=handle_new_pw)

        self.app.push_screen(UnlockScreen(is_setup=False), callback=handle_old_pw)

    def _reset_vault(self) -> None:
        """Reset the vault after confirmation."""
        from geotui.screens.confirm import ConfirmScreen

        def handle_confirm(confirmed: bool | None) -> None:
            if not confirmed:
                return
            self._config.reset_vault()
            from geotui.app import GeoTUIApp

            geo_app = self.app
            if isinstance(geo_app, GeoTUIApp):
                geo_app.vault_key = None
            self.notify(
                _("Vault reset. All connections removed."),
                severity="warning",
                timeout=10,
            )
            self._refresh_list()
            self._show_mode("empty")
            # Prompt for new master password
            if isinstance(geo_app, GeoTUIApp):
                geo_app._show_vault_setup()

        self.app.push_screen(
            ConfirmScreen(
                _("Reset Vault"),
                _(
                    "This will DELETE all saved connections.\n"
                    "You will need to set a new master password\n"
                    "and re-enter all your connections.\n\n"
                    "This cannot be undone!"
                ),
            ),
            callback=handle_confirm,
        )

    def action_go_back(self) -> None:
        """Return to the main screen."""
        if self.editing:
            self._cancel_edit()
        else:
            self.app.pop_screen()
