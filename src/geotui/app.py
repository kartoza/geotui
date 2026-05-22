"""Main GeoTUI application."""

import logging

from cryptography.fernet import Fernet
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.design import ColorSystem
from textual.widgets import Footer, Header

from geotui.config import ConfigManager, Connection
from geotui.i18n import _
from geotui.theme import KARTOZA_DARK, KARTOZA_LIGHT
from geotui.widgets.dual_pane import DualPane
from geotui.widgets.status_bar import StatusBar

# Binding specs: (key, action, english_msgid, show)
# Used to rebuild BINDINGS with fresh translations after language change.
_APP_BINDING_SPECS = [
    ("tab", "switch_pane", "Switch Pane", False),
    ("f1", "help", "Help", True),
    ("f2", "menu", "Menu", True),
    ("f5", "copy", "Copy", True),
    ("f6", "move", "Move", True),
    ("f7", "mkdir", "MkDir", True),
    ("f8", "delete", "Delete", True),
    ("f9", "settings", "Settings", True),
    ("f10", "quit", "Quit", True),
    ("ctrl+l", "toggle_language", "Language", False),
]

# Binding specs for screens — same format: (key, action, msgid, show)
_SETTINGS_BINDING_SPECS = [
    ("escape", "go_back", "Back", True),
    ("a", "add", "Add", True),
    ("e", "edit", "Edit", True),
    ("d", "delete", "Delete", True),
    ("t", "test_connection", "Test", True),
]

_CONTEXT_MENU_BINDING_SPECS = [
    ("escape", "cancel", "Close", True),
]

_UNLOCK_BINDING_SPECS = [
    ("escape", "cancel", "Cancel", True),
]

_CONFIRM_BINDING_SPECS = [
    ("escape", "cancel", "Cancel", True),
]


def _rebuild_all_bindings() -> None:
    """Rebuild BINDINGS on all widget classes with fresh translations.

    Textual caches merged bindings on each class via ``_merged_bindings``.
    After updating ``BINDINGS``, we must also rebuild that cache so the
    Footer picks up the new descriptions.
    """
    from geotui.i18n import _
    from geotui.screens.confirm import ConfirmScreen
    from geotui.screens.context_menu import ContextMenuScreen
    from geotui.screens.settings import SettingsScreen
    from geotui.screens.unlock import UnlockScreen

    specs_map = {
        GeoTUIApp: _APP_BINDING_SPECS,
        SettingsScreen: _SETTINGS_BINDING_SPECS,
        ContextMenuScreen: _CONTEXT_MENU_BINDING_SPECS,
        UnlockScreen: _UNLOCK_BINDING_SPECS,
        ConfirmScreen: _CONFIRM_BINDING_SPECS,
    }
    for cls, specs in specs_map.items():
        cls.BINDINGS = [
            Binding(key, action, _(desc), show=show)
            for key, action, desc, show in specs
        ]
        # Rebuild Textual's internal bindings cache (frozen Binding objects)
        cls._merged_bindings = cls._merge_bindings()


class GeoTUIApp(App[None]):
    """GeoTUI - Midnight Commander-style GeoServer manager."""

    TITLE = "GeoTUI"
    SUB_TITLE = "GeoServer Manager"
    CSS_PATH = "styles/app.tcss"

    def __init__(self, config_manager: ConfigManager | None = None) -> None:
        """Initialize the application.

        Args:
            config_manager: Optional config manager override (useful for testing).
        """
        super().__init__()
        self.config_manager = config_manager or ConfigManager()
        self.vault_key: Fernet | None = None
        self._setup_logging()

    @staticmethod
    def _setup_logging() -> None:
        """Configure file logging to ~/.config/geotui/geotui.log."""
        from geotui.config import _get_config_dir

        log_path = _get_config_dir() / "geotui.log"
        handler = logging.FileHandler(str(log_path), encoding="utf-8")
        handler.setFormatter(
            logging.Formatter(
                "%(asctime)s %(levelname)s %(name)s: %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S",
            )
        )
        root = logging.getLogger("geotui")
        root.setLevel(logging.DEBUG)
        root.addHandler(handler)

    def decrypt_connection(self, conn: Connection) -> Connection:
        """Return a connection with its password decrypted.

        Args:
            conn: Connection with potentially encrypted password.

        Returns:
            Connection with plaintext password for API use.
        """
        if self.vault_key:
            return self.config_manager.decrypt_connection(conn, self.vault_key)
        if self.config_manager.has_vault and not self.vault_key:
            # Vault exists but not unlocked — prompt now
            self._show_unlock()
        return conn

    BINDINGS = [
        Binding(key, action, _(desc), show=show)
        for key, action, desc, show in _APP_BINDING_SPECS
    ]

    @property
    def design(self) -> dict[str, ColorSystem]:
        """Return custom Kartoza color schemes."""
        return {"dark": KARTOZA_DARK, "light": KARTOZA_LIGHT}

    def compose(self) -> ComposeResult:
        """Compose the application layout."""
        yield Header(show_clock=True)
        yield DualPane(config_manager=self.config_manager)
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Show splash screen, then unlock if needed."""
        if self.is_headless:
            # Skip splash and unlock in test/headless mode
            return
        from geotui.screens.splash import SplashScreen

        self.push_screen(SplashScreen(), callback=self._after_splash)

    def _after_splash(self, _result: None = None) -> None:
        """After splash dismisses, show unlock or setup as needed."""
        if self.config_manager.load_error:
            self.notify(
                _("Failed to load config: {error}").format(
                    error=self.config_manager.load_error
                ),
                severity="error",
                timeout=20,
            )
        if self.config_manager.has_vault:
            self._show_unlock()
        else:
            # No vault configured — always prompt for master password setup
            self._show_vault_setup()

    def _show_unlock(self) -> None:
        """Show the unlock screen for existing vault."""
        from geotui.screens.unlock import UnlockScreen

        def handle_unlock(password: str | None) -> None:
            if password is None:
                # User chose to reset vault
                self.config_manager.reset_vault()
                self.notify(
                    _("Vault reset. All connections removed."),
                    severity="warning",
                    timeout=10,
                )
                self._show_vault_setup()
                return
            fernet = self.config_manager.unlock(password)
            if fernet:
                self.vault_key = fernet
                self.notify(_("Vault unlocked"), severity="information")
                # Refresh tree now that credentials can be decrypted
                self._refresh_geoserver_tree()
            else:
                self.notify(
                    _("Wrong password. Try again."),
                    severity="error",
                    timeout=5,
                )
                self._show_unlock()

        self.push_screen(UnlockScreen(is_setup=False), callback=handle_unlock)

    def _show_vault_setup(self) -> None:
        """Show vault setup screen for first-time or post-reset."""
        from geotui.screens.unlock import UnlockScreen

        def handle_setup(password: str | None) -> None:
            if password is None:
                # Cancelled setup - still usable but no encryption
                return
            self.config_manager.init_vault(password)
            self.vault_key = self.config_manager.unlock(password)
            self.notify(
                _("Master password created. Credentials are now encrypted."),
                severity="information",
                timeout=10,
            )

        self.push_screen(UnlockScreen(is_setup=True), callback=handle_setup)

    def _refresh_geoserver_tree(self) -> None:
        """Refresh the GeoServer tree after vault unlock."""
        from geotui.widgets.geoserver_tree import GeoServerTree

        try:
            tree = self.query_one("#right-pane", GeoServerTree)
            tree.refresh_connections()
        except Exception:  # nosec B110
            pass  # Tree may not be mounted yet

    def action_switch_pane(self) -> None:
        """Switch focus between left and right panes."""
        dual_pane = self.query_one(DualPane)
        dual_pane.toggle_active_pane()

    def action_help(self) -> None:
        """Show help dialog."""
        self.notify(_("Help - Press F1 for assistance"), title=_("GeoTUI Help"))

    def action_menu(self) -> None:
        """Show context-sensitive F2 menu."""
        from geotui.screens.context_menu import ContextMenuScreen
        from geotui.widgets.geoserver_tree import GeoServerTree

        dual_pane = self.query_one(DualPane)
        active = dual_pane.get_active_pane_type()

        def handle_menu_result(action_id: str | None) -> None:
            if not action_id:
                return
            tree = self.query_one("#right-pane", GeoServerTree)
            if action_id == "gs_create_workspace":
                tree.action_create_workspace()
            elif action_id == "gs_create_store":
                tree.action_create_store()
            elif action_id == "gs_refresh":
                tree.refresh_tree()
            elif action_id == "local_open_reports":
                self._open_reports_folder()

        self.push_screen(ContextMenuScreen(active), callback=handle_menu_result)

    def _open_reports_folder(self) -> None:
        """Open the reports folder in the system file manager."""
        from pathlib import Path

        from geotui.widgets.file_pane import FilePane

        reports_dir = Path.cwd() / ".geotui" / "reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        FilePane.open_file(reports_dir)

    def action_copy(self) -> None:
        """F5 Copy: publish local spatial files to GeoServer."""
        from geotui.widgets.geoserver_tree import GeoServerTree

        tree = self.query_one("#right-pane", GeoServerTree)
        if not tree._connections:
            self.notify(
                _("Connect to a GeoServer first (F9)"),
                severity="error",
            )
            return
        tree.action_copy_from_local()

    def action_move(self) -> None:
        """Move selected item."""
        self.notify(_("Move"), title=_("GeoTUI"))

    def action_mkdir(self) -> None:
        """Create directory."""
        self.notify(_("Create Directory"), title=_("GeoTUI"))

    def action_delete(self) -> None:
        """F8 Delete: delete selected resource on GeoServer."""
        from geotui.widgets.geoserver_tree import GeoServerTree

        dual_pane = self.query_one(DualPane)
        pane_type = dual_pane.get_active_pane_type()

        if pane_type == "geoserver":
            tree = self.query_one("#right-pane", GeoServerTree)
            tree.action_delete_selected()
        else:
            self.notify(_("Delete not implemented for local files"), severity="warning")

    def action_settings(self) -> None:
        """Show settings screen."""
        from geotui.screens.settings import SettingsScreen

        self.push_screen(SettingsScreen(self.config_manager))

    def action_toggle_language(self) -> None:
        """Cycle through available languages and refresh all UI text."""
        from geotui.i18n import SUPPORTED_LANGUAGES, _, cycle_language

        new_lang = cycle_language()
        lang_name = SUPPORTED_LANGUAGES[new_lang]

        # Rebuild class BINDINGS and Textual's internal _merged_bindings cache
        _rebuild_all_bindings()

        # Copy fresh _merged_bindings into instance _bindings for all live nodes
        # (Textual copies _merged_bindings into _bindings once during __init__,
        # so class-level changes don't propagate automatically.)
        self._bindings = type(self)._merged_bindings.copy()

        # Signal footer to re-render with updated descriptions
        self.refresh_bindings()

        # Update status bar text
        try:
            from textual.widgets import Static

            status_bar = self.query_one(StatusBar)
            left = status_bar.query_one(".status-left", Static)
            left.update(_("Ready"))
        except Exception:
            pass

        self.notify(f"Language: {lang_name}", title="GeoTUI")
