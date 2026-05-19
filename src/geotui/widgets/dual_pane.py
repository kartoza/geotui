"""Dual pane widget - the core Midnight Commander-style layout."""

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget

from geotui.widgets.file_pane import FilePane


class DualPane(Widget):
    """A dual-pane file manager widget in the style of Midnight Commander."""

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
            yield FilePane(id="left-pane", pane_title="Left")
            yield FilePane(id="right-pane", pane_title="Right")

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
        right = self.query_one("#right-pane", FilePane)

        left.is_active = self.active_pane == "left"
        right.is_active = self.active_pane == "right"

        if self.active_pane == "left":
            left.focus()
        else:
            right.focus()
