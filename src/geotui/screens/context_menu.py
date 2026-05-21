"""Context-sensitive F2 menu.

Shows different actions depending on the active pane type:
- GeoServer pane (with active connection): workspace/store operations
- Local file pane: filesystem operations
"""

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import ModalScreen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from geotui.i18n import _


class ContextMenuScreen(ModalScreen[str | None]):
    """Modal context menu triggered by F2.

    Returns the selected action ID or None if cancelled.
    """

    CSS = """
    ContextMenuScreen {
        align: center middle;
    }

    ContextMenuScreen #menu-container {
        width: 44;
        height: auto;
        max-height: 24;
        border: round #569FC6;
        background: #16213e;
        padding: 1 2;
    }

    ContextMenuScreen #menu-title {
        width: 100%;
        height: 1;
        text-align: center;
        text-style: bold;
        color: #DF9E2F;
        margin: 0 0 1 0;
    }

    ContextMenuScreen OptionList {
        height: auto;
        max-height: 18;
        width: 100%;
        background: #1a1a2e;
    }
    """

    BINDINGS = [
        ("escape", "cancel", _("Close")),
    ]

    def __init__(self, pane_type: str) -> None:
        """Initialize the context menu.

        Args:
            pane_type: Type of active pane ('geoserver' or 'local').
        """
        super().__init__()
        self._pane_type = pane_type

    def compose(self) -> ComposeResult:
        """Compose the menu."""
        with Middle():
            with Center():
                with Center(id="menu-container"):
                    if self._pane_type == "geoserver":
                        yield Static(
                            _("GeoServer Actions"),
                            id="menu-title",
                        )
                    else:
                        yield Static(_("File Actions"), id="menu-title")
                    yield OptionList(id="menu-options")

    def on_mount(self) -> None:
        """Populate menu options based on pane type."""
        opts = self.query_one("#menu-options", OptionList)

        if self._pane_type == "geoserver":
            opts.add_option(Option(_("Create Workspace"), id="gs_create_workspace"))
            opts.add_option(Option(_("Create Store"), id="gs_create_store"))
            opts.add_option(Option(_("Refresh Tree"), id="gs_refresh"))
        else:
            opts.add_option(Option(_("Create Directory"), id="local_mkdir"))
            opts.add_option(Option(_("Open Reports Folder"), id="local_open_reports"))

        opts.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        """Handle menu item selection."""
        option = event.option
        if option.id:
            self.dismiss(option.id)

    def action_cancel(self) -> None:
        """Cancel the menu."""
        self.dismiss(None)
