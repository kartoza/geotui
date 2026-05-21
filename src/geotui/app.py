"""Main GeoTUI application."""

import logging

from cryptography.fernet import Fernet
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.design import ColorSystem
from textual.widgets import Footer, Header

from geotui.config import ConfigManager
from geotui.i18n import _
from geotui.theme import KARTOZA_DARK, KARTOZA_LIGHT
from geotui.widgets.dual_pane import DualPane
from geotui.widgets.status_bar import StatusBar


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

    def decrypt_connection(self, conn) -> object:
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
        Binding("tab", "switch_pane", _("Switch Pane"), show=False),
        Binding("f1", "help", _("Help")),
        Binding("f2", "menu", _("Menu")),
        Binding("f5", "copy", _("Copy")),
        Binding("f6", "move", _("Move")),
        Binding("f7", "mkdir", _("MkDir")),
        Binding("f8", "delete", _("Delete")),
        Binding("f9", "settings", _("Settings")),
        Binding("f10", "quit", _("Quit")),
        Binding("ctrl+l", "toggle_language", _("Language"), show=False),
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
        """After splash dismisses, show unlock if needed."""
        if self.config_manager.has_vault:
            self._show_unlock()
        elif self.config_manager.config.connections:
            # Existing unencrypted connections - prompt to set up vault
            self.notify(
                _("Your credentials are not encrypted. "
                  "Go to Settings (F9) to set up a master password."),
                severity="warning",
                timeout=15,
            )

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
        except Exception:
            pass

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
        """Cycle through available languages."""
        from geotui.i18n import cycle_language, get_current_language

        cycle_language()
        lang = get_current_language()
        self.notify(f"Language: {lang}", title="GeoTUI")
