"""File pane widget - individual pane in the dual-pane layout."""

import platform
import subprocess  # nosec B404
from collections.abc import Iterable
from pathlib import Path

from rich.style import Style
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.reactive import reactive
from textual.widget import Widget
from textual.widgets import DirectoryTree, Label, Static
from textual.widgets._directory_tree import DirEntry
from textual.widgets._tree import TreeNode

from geotui.i18n import _

# Shapefile companion extensions (import from publisher to stay DRY)
SHAPEFILE_ALL_EXTS: frozenset[str] = frozenset(
    {".shp", ".shx", ".dbf", ".prj", ".cpg", ".qix", ".sbn", ".sbx", ".fix", ".qpj"}
)


def find_shapefile_companions(path: Path) -> list[Path]:
    """Find all companion files for a shapefile component.

    Given any shapefile component (e.g. roads.shp, roads.dbf),
    returns all sibling files with the same stem and a shapefile extension.

    Args:
        path: Path to any shapefile component file.

    Returns:
        Sorted list of all companion paths (including the input file).
    """
    stem = path.stem
    parent = path.parent
    companions = []
    for ext in sorted(SHAPEFILE_ALL_EXTS):
        candidate = parent / f"{stem}{ext}"
        if candidate.exists():
            companions.append(candidate)
    return companions


def is_shapefile_component(path: Path) -> bool:
    """Check if a path is a shapefile component file."""
    return path.suffix.lower() in SHAPEFILE_ALL_EXTS


class MCDirectoryTree(DirectoryTree):
    """DirectoryTree with '..' parent directory entry like Midnight Commander."""

    class SelectionChanged(Message):
        """Posted when the tagged-file selection changes."""

    BINDINGS = [
        Binding("space", "tag_cursor", _("Select"), show=False),
    ]

    def __init__(
        self,
        path: str | Path,
        *,
        name: str | None = None,
        id: str | None = None,
        classes: str | None = None,
        disabled: bool = False,
    ) -> None:
        super().__init__(path, name=name, id=id, classes=classes, disabled=disabled)
        self._selected_paths: set[Path] = set()

    def _populate_node(self, node: TreeNode[DirEntry], content: Iterable[Path]) -> None:
        """Populate node with '..' as the first entry."""
        node.remove_children()
        # Add ".." entry for parent navigation (only for root node)
        if node == self.root:
            tree_path = Path(self.path) if isinstance(self.path, str) else self.path
            parent = tree_path.parent
            if parent != tree_path:
                node.add("..", data=DirEntry(parent), allow_expand=False)
        for path in content:
            node.add(
                path.name,
                data=DirEntry(path),
                allow_expand=self._safe_is_dir(path),
            )
        node.expand()

    def render_label(
        self, node: TreeNode[DirEntry], base_style: Style, style: Style
    ) -> Text:
        """Render label with selection marker for tagged files."""
        label = super().render_label(node, base_style, style)
        if node.data and node.data.path in self._selected_paths:
            # Prepend a selection marker like MC
            marker = Text("* ", style=Style(color="yellow", bold=True))
            label = Text.assemble(marker, label)
        return label

    def toggle_select_cursor(self) -> None:
        """Toggle selection on the node under the cursor."""
        if not self.cursor_node or not self.cursor_node.data:
            return
        path = self.cursor_node.data.path
        # Don't allow selecting ".." or directories
        tree_path = Path(self.path) if isinstance(self.path, str) else self.path
        if path == tree_path.parent or path.is_dir():
            return
        if path in self._selected_paths:
            self._selected_paths.discard(path)
        else:
            self._selected_paths.add(path)
        self.refresh()

    def action_tag_cursor(self) -> None:
        """Space handler: toggle selection on the cursor file, then move down.

        Overrides the tree's default space (expand/collapse) so Space tags
        files for a non-contiguous multi-file publish, MC-style.
        """
        self.toggle_select_cursor()
        self.action_cursor_down()
        self.post_message(self.SelectionChanged())

    def clear_selection(self) -> None:
        """Clear all selected files."""
        self._selected_paths.clear()
        self.refresh()

    @property
    def selected_paths(self) -> set[Path]:
        """Return the set of selected file paths."""
        return set(self._selected_paths)


class FilePane(Widget):
    """A single file browser pane with directory tree and details."""

    BINDINGS = [
        Binding("ctrl+t", "toggle_select", _("Select"), show=False),
    ]

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

    FilePane MCDirectoryTree {
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
    current_path: reactive[str] = reactive(str(Path.cwd()))

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
            yield MCDirectoryTree(self.current_path)
            yield Static(self.current_path, classes="pane-footer")

    def watch_is_active(self, value: bool) -> None:
        """Update styling when active state changes."""
        self.set_class(value, "active")
        header = self.query_one(".pane-header", Label)
        header.set_class(value, "active")

    def watch_current_path(self, value: str) -> None:
        """Update footer when path changes."""
        if self.is_mounted:
            footer = self.query_one(".pane-footer", Static)
            footer.update(value)
            self._update_footer()

    def _update_footer(self) -> None:
        """Update footer with path and selection count."""
        tree = self.query_one(MCDirectoryTree)
        count = len(tree.selected_paths)
        text = self.current_path
        if count:
            text = f"{text}  [{count} selected]"
        footer = self.query_one(".pane-footer", Static)
        footer.update(text)

    def get_selected_path(self) -> Path:
        """Get the path of the highlighted item in the tree.

        If the cursor is on a directory, returns that directory.
        If on a file, returns its parent directory.
        Falls back to current_path if no cursor node.

        Returns:
            Path to the selected directory.
        """
        tree = self.query_one(MCDirectoryTree)
        if tree.cursor_node and tree.cursor_node.data:
            node_path = tree.cursor_node.data.path
            if node_path.is_dir():
                return node_path
            return node_path.parent
        return Path(self.current_path)

    def get_cursor_target(self) -> Path | None:
        """Return the path of the item under the cursor (file or directory).

        Excludes the ".." parent entry. Returns ``None`` when there is no
        usable cursor node. Unlike :meth:`get_selected_path`, a file returns
        the file itself (not its parent), so F5 can publish just that dataset.
        """
        tree = self.query_one(MCDirectoryTree)
        if not (tree.cursor_node and tree.cursor_node.data):
            return None
        path = tree.cursor_node.data.path
        # Exclude the ".." parent-navigation entry.
        if path == Path(self.current_path).parent:
            return None
        return path

    def get_selected_files(self) -> list[Path]:
        """Get files selected via Ctrl+T, with smart shapefile companion detection.

        If files are selected via Ctrl+T, returns those files plus any
        shapefile companions. If no files are tagged, returns an empty list
        (caller should fall back to directory-level discovery).

        Returns:
            List of selected file paths with companions included.
        """
        tree = self.query_one(MCDirectoryTree)
        selected = tree.selected_paths
        if not selected:
            return []

        # Expand shapefile companions
        result: set[Path] = set()
        for path in selected:
            if is_shapefile_component(path):
                result.update(find_shapefile_companions(path))
            else:
                result.add(path)
        return sorted(result)

    def action_toggle_select(self) -> None:
        """Toggle selection on the file under cursor, then move down."""
        tree = self.query_one(MCDirectoryTree)
        tree.toggle_select_cursor()
        # Move cursor down like MC does after tagging
        tree.action_cursor_down()
        self._update_footer()

    def on_mc_directory_tree_selection_changed(
        self, event: MCDirectoryTree.SelectionChanged
    ) -> None:
        """Refresh the footer count when Space toggles a selection."""
        event.stop()
        self._update_footer()

    def navigate_to(self, path: Path) -> None:
        """Navigate the tree to a new root directory.

        Args:
            path: Directory to navigate to.
        """
        if not path.is_dir():
            return
        self.current_path = str(path)
        tree = self.query_one(MCDirectoryTree)
        tree.clear_selection()
        tree.path = path
        tree.reload()

    def on_directory_tree_directory_selected(
        self, event: DirectoryTree.DirectorySelected
    ) -> None:
        """Handle directory selection - navigate into selected directory."""
        event.stop()
        self.navigate_to(event.path)

    def on_directory_tree_file_selected(
        self, event: DirectoryTree.FileSelected
    ) -> None:
        """Open file with system default viewer."""
        self.open_file(event.path)

    @staticmethod
    def open_file(path: Path) -> None:
        """Open a file with the system default application.

        Cross-platform: uses xdg-open (Linux), open (macOS),
        or start (Windows).

        Args:
            path: Path to the file to open.
        """
        system = platform.system()
        cmd: list[str] = []
        if system == "Darwin":
            cmd = ["open", str(path)]
        elif system == "Windows":
            cmd = ["cmd", "/c", "start", "", str(path)]
        else:
            cmd = ["xdg-open", str(path)]
        try:
            subprocess.Popen(cmd)  # noqa: S603  # nosec B603
        except FileNotFoundError:
            pass
