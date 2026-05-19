"""Status bar widget for GeoTUI."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.widgets import Static
from textual.widget import Widget

from geotui.i18n import _


class StatusBar(Widget):
    """Status bar showing connection info and branding."""

    DEFAULT_CSS = """
    StatusBar {
        height: 1;
        width: 100%;
        dock: bottom;
        background: $surface;
    }

    StatusBar > Horizontal {
        height: 1;
        width: 100%;
    }

    StatusBar .status-left {
        width: 1fr;
        color: $text;
        padding: 0 1;
    }

    StatusBar .status-right {
        width: auto;
        color: $text-muted;
        padding: 0 1;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose status bar."""
        with Horizontal():
            yield Static(_("Ready"), classes="status-left")
            yield Static(
                "Made with \u2764 by Kartoza | Donate! | GitHub",
                classes="status-right",
            )
