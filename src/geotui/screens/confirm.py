"""Confirmation dialog for destructive actions."""

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Middle
from textual.screen import ModalScreen
from textual.widgets import Button, Label, Static

from geotui.i18n import _


class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog.

    Returns True if confirmed, False if cancelled.
    """

    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen #confirm-container {
        width: 50;
        height: auto;
        border: round #CC0403;
        background: #16213e;
        padding: 1 2;
    }

    ConfirmScreen #confirm-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: #CC0403;
        margin: 0 0 1 0;
    }

    ConfirmScreen #confirm-message {
        width: 100%;
        color: #8A8B8B;
        margin: 0 0 1 0;
    }

    ConfirmScreen #confirm-buttons {
        width: 100%;
        align: center middle;
        height: auto;
    }

    ConfirmScreen #confirm-buttons Button {
        margin: 0 1;
    }

    ConfirmScreen .btn-danger {
        background: #CC0403;
        color: white;
    }

    ConfirmScreen .btn-default {
        background: #8A8B8B;
        color: #1a1a2e;
    }
    """

    BINDINGS = [
        ("escape", "cancel", _("Cancel")),
    ]

    def __init__(self, title: str, message: str) -> None:
        """Initialize confirmation dialog.

        Args:
            title: Dialog title.
            message: Confirmation message.
        """
        super().__init__()
        self._title = title
        self._message = message

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Middle():
            with Center():
                with Center(id="confirm-container"):
                    yield Label(self._title, id="confirm-title")
                    yield Static(self._message, id="confirm-message")
                    with Horizontal(id="confirm-buttons"):
                        yield Button(
                            _("Delete"),
                            id="btn-confirm",
                            classes="btn-danger",
                        )
                        yield Button(
                            _("Cancel"),
                            id="btn-cancel-confirm",
                            classes="btn-default",
                        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(False)
