"""Dual pane widget - the core Midnight Commander-style layout."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget

from geotui.config import Connection
from geotui.widgets.file_pane import FilePane
from geotui.widgets.geoserver_tree import GeoServerTree


class DualPane(Widget):
    """A dual-pane widget in the style of Midnight Commander.

    Left pane: local file browser.
    Right pane: GeoServer resource tree from active connection.
    """

    DEFAULT_CSS = """
    DualPane {
        height: 1fr;
        width: 100%;
    }

    DualPane > Horizontal {
        height: 100%;
        width: 100%;
    }
    """

    active_pane: reactive[str] = reactive("left")

    def compose(self) -> ComposeResult:
        """Compose dual pane layout."""
        with Horizontal():
            yield FilePane(id="left-pane", pane_title="Local Files")
            yield GeoServerTree(id="right-pane")

    def on_mount(self) -> None:
        """Set initial focus to left pane."""
        self._update_active_pane()

    def toggle_active_pane(self) -> None:
        """Toggle between left and right pane."""
        self.active_pane = "right" if self.active_pane == "left" else "left"

    def watch_active_pane(self, value: str) -> None:
        """React to active pane changes."""
        self._update_active_pane()

    def _update_active_pane(self) -> None:
        """Update visual state of panes."""
        left = self.query_one("#left-pane", FilePane)
        right = self.query_one("#right-pane", GeoServerTree)

        left.is_active = self.active_pane == "left"
        right.is_active = self.active_pane == "right"

        if self.active_pane == "left":
            left.focus()
        else:
            right.focus()

    def set_connection(self, conn: Connection | None) -> None:
        """Set the active GeoServer connection for the right pane.

        Args:
            conn: Connection to display, or None to clear.
        """
        right = self.query_one("#right-pane", GeoServerTree)
        right.connection = conn

    def get_active_pane_type(self) -> str:
        """Get the type of the currently active pane.

        Returns:
            'geoserver' if the active pane has a GeoServer connection,
            'local' otherwise.
        """
        if self.active_pane == "right":
            right = self.query_one("#right-pane", GeoServerTree)
            if right.connection is not None:
                return "geoserver"
        return "local"
