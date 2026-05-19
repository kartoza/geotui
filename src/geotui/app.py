"""Main GeoTUI application."""

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.design import ColorSystem
from textual.widgets import Footer, Header

from geotui.i18n import _
from geotui.theme import KARTOZA_DARK, KARTOZA_LIGHT
from geotui.widgets.dual_pane import DualPane
from geotui.widgets.status_bar import StatusBar


class GeoTUIApp(App[None]):
    """GeoTUI - Midnight Commander-style geospatial server manager."""

    TITLE = "GeoTUI"
    SUB_TITLE = "Geospatial Server Manager"
    CSS_PATH = "styles/app.tcss"

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

    def get_css_variables(self) -> dict[str, str]:
        """Override CSS variables with Kartoza theme."""
        variables = super().get_css_variables()
        return variables

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

    def action_switch_pane(self) -> None:
        """Switch focus between left and right panes."""
        dual_pane = self.query_one(DualPane)
        dual_pane.toggle_active_pane()

    def action_help(self) -> None:
        """Show help dialog."""
        self.notify(_("Help - Press F1 for assistance"), title=_("GeoTUI Help"))

    def action_menu(self) -> None:
        """Show menu."""
        self.notify(_("Menu"), title=_("GeoTUI"))

    def action_copy(self) -> None:
        """Copy selected item."""
        self.notify(_("Copy"), title=_("GeoTUI"))

    def action_move(self) -> None:
        """Move selected item."""
        self.notify(_("Move"), title=_("GeoTUI"))

    def action_mkdir(self) -> None:
        """Create directory."""
        self.notify(_("Create Directory"), title=_("GeoTUI"))

    def action_delete(self) -> None:
        """Delete selected item."""
        self.notify(_("Delete"), title=_("GeoTUI"))

    def action_settings(self) -> None:
        """Show settings."""
        self.notify(_("Settings"), title=_("GeoTUI"))

    def action_toggle_language(self) -> None:
        """Cycle through available languages."""
        from geotui.i18n import cycle_language, get_current_language

        cycle_language()
        lang = get_current_language()
        self.notify(f"Language: {lang}", title="GeoTUI")
