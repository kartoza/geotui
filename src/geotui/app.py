"""Main GeoTUI application."""

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

    BINDINGS = [
        Binding("q", "quit", _("Quit")),
        Binding("tab", "switch_pane", _("Switch Pane")),
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
        yield DualPane()
        yield StatusBar()
        yield Footer()

    def on_mount(self) -> None:
        """Show splash screen and restore active connection on startup."""
        from geotui.screens.splash import SplashScreen

        self.push_screen(SplashScreen())

        for conn in self.config_manager.config.connections:
            if conn.is_active:
                dual_pane = self.query_one(DualPane)
                dual_pane.set_connection(conn)
                break

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
            elif action_id == "local_mkdir":
                self.action_mkdir()
            elif action_id == "local_open_reports":
                self._open_reports_folder()

        self.push_screen(ContextMenuScreen(active), callback=handle_menu_result)

    def _open_reports_folder(self) -> None:
        """Open the reports folder in the system file manager."""
        from pathlib import Path

        from geotui.widgets.file_pane import FilePane

        reports_dir = Path.home() / ".local/share/geotui/reports"
        reports_dir.mkdir(parents=True, exist_ok=True)
        FilePane.open_file(reports_dir)

    def action_copy(self) -> None:
        """F5 Copy: publish local spatial files to GeoServer."""
        from geotui.widgets.geoserver_tree import GeoServerTree

        tree = self.query_one("#right-pane", GeoServerTree)
        if tree.connection is None:
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
