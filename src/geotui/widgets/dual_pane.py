"""Dual pane widget - the core Midnight Commander-style layout."""

from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal
from textual.reactive import reactive
from textual.widget import Widget

from geotui.config import ConfigManager
from geotui.widgets.file_pane import FilePane
from geotui.widgets.geoserver_tree import GeoServerTree


class DualPane(Widget):
    """A dual-pane widget in the style of Midnight Commander.

    Left pane: local file browser.
    Right pane: GeoServer resource tree from all configured connections.
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

    def __init__(self, config_manager: ConfigManager, **kwargs: Any) -> None:
        """Initialize the dual pane.

        Args:
            config_manager: Application configuration manager.
        """
        super().__init__(**kwargs)
        self._config_manager = config_manager

    def compose(self) -> ComposeResult:
        """Compose dual pane layout."""
        with Horizontal():
            yield FilePane(id="left-pane", pane_title="Local Files")
            yield GeoServerTree(config_manager=self._config_manager, id="right-pane")

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

    def get_active_pane_type(self) -> str:
        """Get the type of the currently active pane.

        Checks both the reactive state and actual focus to determine
        which pane is active. Returns 'geoserver' if the GeoServer
        pane is active and has connections, 'local' otherwise.

        Returns:
            'geoserver' or 'local'.
        """
        right = self.query_one("#right-pane", GeoServerTree)

        # Check reactive state or if any child of the right pane has focus
        right_active = self.active_pane == "right"
        if not right_active and self.app.focused is not None:
            current = self.app.focused
            while current is not None:
                if current is right:
                    right_active = True
                    break
                current = current.parent  # type: ignore[assignment]

        if right_active and right._connections:
            return "geoserver"
        return "local"
