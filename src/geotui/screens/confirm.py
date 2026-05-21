"""Confirmation dialog for destructive actions."""

from textual.app import ComposeResult
from textual.containers import Center, Horizontal, Middle
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from geotui.i18n import _


class ConfirmScreen(ModalScreen[bool]):
    """Modal confirmation dialog.

    Returns True if confirmed, False if cancelled.
    When require_name is set, the user must type the exact resource
    name before the Delete button becomes active.
    """

    CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen #confirm-container {
        width: 60;
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

    ConfirmScreen #confirm-name-prompt {
        width: 100%;
        color: #DF9E2F;
        margin: 0 0 0 0;
    }

    ConfirmScreen #confirm-name-input {
        width: 100%;
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

    ConfirmScreen .btn-danger.-disabled {
        background: #4a4a4a;
        color: #8A8B8B;
    }

    ConfirmScreen .btn-default {
        background: #8A8B8B;
        color: #1a1a2e;
    }
    """

    BINDINGS = [
        ("escape", "cancel", _("Cancel")),
    ]

    def __init__(
        self, title: str, message: str, *, require_name: str | None = None
    ) -> None:
        """Initialize confirmation dialog.

        Args:
            title: Dialog title.
            message: Confirmation message.
            require_name: If set, user must type this name to confirm.
        """
        super().__init__()
        self._title = title
        self._message = message
        self._require_name = require_name

    def compose(self) -> ComposeResult:
        """Compose the dialog."""
        with Middle():
            with Center():
                with Center(id="confirm-container"):
                    yield Label(self._title, id="confirm-title")
                    yield Static(self._message, id="confirm-message")
                    if self._require_name:
                        yield Static(
                            _("Type '{}' to confirm:").format(
                                self._require_name
                            ),
                            id="confirm-name-prompt",
                        )
                        yield Input(
                            placeholder=self._require_name,
                            id="confirm-name-input",
                        )
                    with Horizontal(id="confirm-buttons"):
                        yield Button(
                            _("Delete"),
                            id="btn-confirm",
                            classes="btn-danger",
                            disabled=self._require_name is not None,
                        )
                        yield Button(
                            _("Cancel"),
                            id="btn-cancel-confirm",
                            classes="btn-default",
                        )

    def on_input_changed(self, event: Input.Changed) -> None:
        """Enable Delete button only when typed name matches."""
        btn = self.query_one("#btn-confirm", Button)
        btn.disabled = event.value != self._require_name

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-confirm":
            self.dismiss(True)
        else:
            self.dismiss(False)

    def action_cancel(self) -> None:
        """Cancel the dialog."""
        self.dismiss(False)
