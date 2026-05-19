"""File pane widget - individual pane in the dual-pane layout."""

from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Vertical
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DirectoryTree, Label, Static


class FilePane(Widget):
    """A single file browser pane with directory tree and details."""

    DEFAULT_CSS = """
    FilePane {
        width: 1fr;
        height: 100%;
        border: round $primary;
        padding: 0 1;
    }

    FilePane.active {
        border: round $warning;
    }

    FilePane .pane-header {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text;
        text-align: center;
        text-style: bold;
    }

    FilePane .pane-header.active {
        background: $warning;
        color: $background;
    }

    FilePane DirectoryTree {
        height: 1fr;
        width: 100%;
    }

    FilePane .pane-footer {
        height: 1;
        width: 100%;
        background: $surface;
        color: $text-muted;
    }
    """

    is_active: reactive[bool] = reactive(False)
    current_path: reactive[str] = reactive(str(Path.home()))

    def __init__(
        self,
        pane_title: str = "Files",
        *,
        id: str | None = None,
    ) -> None:
        """Initialize the file pane.

        Args:
            pane_title: Title displayed in the pane header.
            id: Widget ID.
        """
        super().__init__(id=id)
        self._pane_title = pane_title

    def compose(self) -> ComposeResult:
        """Compose the file pane layout."""
        with Vertical():
            yield Label(self._pane_title, classes="pane-header")
            yield DirectoryTree(self.current_path)
            yield Static(self.current_path, classes="pane-footer")

    def watch_is_active(self, value: bool) -> None:
        """Update styling when active state changes."""
        self.set_class(value, "active")
        header = self.query_one(".pane-header", Label)
        header.set_class(value, "active")

    def watch_current_path(self, value: str) -> None:
        """Update footer when path changes."""
        try:
            footer = self.query_one(".pane-footer", Static)
            footer.update(value)
        except Exception:
            pass

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection."""
        self.current_path = str(event.path)
