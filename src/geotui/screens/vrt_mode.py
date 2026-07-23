"""Modal prompt for choosing how VRT source files are handled on publish."""

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Middle
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from geotui.i18n import _


class VRTModeScreen(ModalScreen[str]):
    """Ask the user how to handle a VRT's referenced source files.

    Dismisses with ``"bundle"`` (upload the ``.vrt`` and its sources into the
    GeoServer data directory), ``"server_path"`` (the referenced data already
    lives on the server filesystem), or ``""`` if cancelled.
    """

    CSS = """
    VRTModeScreen {
        align: center middle;
    }

    VRTModeScreen #vrt-mode-container {
        width: 66;
        height: auto;
        border: round #569FC6;
        background: #16213e;
        padding: 1 2;
    }

    VRTModeScreen #vrt-mode-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: #DF9E2F;
        margin: 0 0 1 0;
    }

    VRTModeScreen #vrt-mode-message {
        width: 100%;
        color: #8A8B8B;
        margin: 0 0 1 0;
    }

    VRTModeScreen #vrt-mode-buttons {
        width: 100%;
        align: center middle;
        height: auto;
    }

    VRTModeScreen #vrt-mode-buttons Button {
        margin: 0 1;
    }

    VRTModeScreen .btn-primary {
        background: #569FC6;
        color: #1a1a2e;
    }

    VRTModeScreen .btn-success {
        background: #06969A;
        color: #1a1a2e;
    }

    VRTModeScreen .btn-default {
        background: #8A8B8B;
        color: #1a1a2e;
    }
    """

    BINDINGS = [
        ("escape", "cancel", _("Cancel")),
    ]

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Middle():
            with Center():
                with Center(id="vrt-mode-container"):
                    yield Label(_("Publish VRT"), id="vrt-mode-title")
                    yield Static(
                        _(
                            "A VRT references other datasets. How should GeoTUI "
                            "handle them?\n\n"
                            "Bundle & upload: send the .vrt and its referenced "
                            "source files to the GeoServer data directory.\n"
                            "Server paths: the referenced data already exists on "
                            "the GeoServer filesystem."
                        ),
                        id="vrt-mode-message",
                    )
                    with Horizontal(id="vrt-mode-buttons"):
                        yield Button(
                            _("Bundle & upload"),
                            id="btn-vrt-bundle",
                            classes="btn-success",
                        )
                        yield Button(
                            _("Server paths"),
                            id="btn-vrt-server",
                            classes="btn-primary",
                        )
                        yield Button(
                            _("Cancel"),
                            id="btn-vrt-cancel",
                            classes="btn-default",
                        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-vrt-bundle":
            self.dismiss("bundle")
        elif event.button.id == "btn-vrt-server":
            self.dismiss("server_path")
        else:
            self.dismiss("")

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss("")
