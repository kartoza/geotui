"""Master password unlock screen.

Shown at startup when a vault is configured. The user must enter
their master password to decrypt stored connection credentials.
Also handles first-time vault setup.
"""

from textual.app import ComposeResult
from textual.containers import Center, Middle, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Static

from geotui import __version__
from geotui.i18n import _
from geotui.screens.logo_data import LOGO

_VER = f"v{__version__}"


class UnlockScreen(ModalScreen[str | None]):
    """Master password prompt shown at startup.

    Returns the master password on success, or None if reset/cancelled.
    """

    CSS = """
    UnlockScreen {
        background: #1a1a2e;
        align: center middle;
    }

    UnlockScreen #unlock-container {
        width: auto;
        max-width: 60;
        height: auto;
        background: #1a1a2e;
        padding: 0 1;
    }

    UnlockScreen #unlock-logo {
        width: auto;
        height: auto;
        content-align: center middle;
        text-align: center;
        margin: 0 0 1 0;
    }

    UnlockScreen #unlock-box {
        width: 100%;
        height: auto;
        border: round #569FC6;
        background: #16213e;
        padding: 1 2;
    }

    UnlockScreen #unlock-title {
        width: 100%;
        text-align: center;
        text-style: bold;
        color: #DF9E2F;
        margin: 0 0 1 0;
    }

    UnlockScreen #unlock-subtitle {
        width: 100%;
        text-align: center;
        color: #8A8B8B;
        margin: 0 0 1 0;
    }

    UnlockScreen #unlock-error {
        width: 100%;
        text-align: center;
        color: #CC0403;
        text-style: bold;
        margin: 0 0 1 0;
    }

    UnlockScreen #unlock-input {
        width: 100%;
        margin: 0;
    }

    UnlockScreen #unlock-confirm {
        width: 100%;
        margin: 0;
    }

    UnlockScreen #unlock-buttons {
        width: 100%;
        height: auto;
        align: center middle;
    }

    UnlockScreen #unlock-buttons Button {
        margin: 0 1;
        min-width: 12;
    }

    UnlockScreen .btn-primary {
        background: #06969A;
        color: #1a1a2e;
    }

    UnlockScreen .btn-danger {
        background: #CC0403;
        color: white;
    }

    UnlockScreen #unlock-branding {
        width: 100%;
        text-align: center;
        color: #8A8B8B;
        margin: 1 0 0 0;
    }
    """

    BINDINGS = [
        ("escape", "cancel", _("Cancel")),
    ]

    def __init__(self, *, is_setup: bool = False) -> None:
        """Initialize the unlock screen.

        Args:
            is_setup: True if this is first-time vault setup.
        """
        super().__init__()
        self._is_setup = is_setup
        self._attempts = 0

    def compose(self) -> ComposeResult:
        """Compose the unlock screen."""
        with Middle():
            with Center():
                with Vertical(id="unlock-container"):
                    yield Static(LOGO, id="unlock-logo")
                    with Vertical(id="unlock-box"):
                        if self._is_setup:
                            yield Label(
                                _("Create Master Password"),
                                id="unlock-title",
                            )
                            yield Static(
                                _(
                                    "Set a master password to encrypt your\n"
                                    "GeoServer connection credentials."
                                ),
                                id="unlock-subtitle",
                            )
                        else:
                            yield Label(
                                _("Unlock Vault"),
                                id="unlock-title",
                            )
                            yield Static(
                                _(
                                    "Enter your master password to\n"
                                    "decrypt connection credentials."
                                ),
                                id="unlock-subtitle",
                            )
                        yield Static("", id="unlock-error")
                        yield Input(
                            placeholder=_("Master password"),
                            password=True,
                            id="unlock-input",
                        )
                        if self._is_setup:
                            yield Input(
                                placeholder=_("Confirm password"),
                                password=True,
                                id="unlock-confirm",
                            )
                        from textual.containers import Horizontal

                        with Horizontal(id="unlock-buttons"):
                            yield Button(
                                _("Unlock") if not self._is_setup else _("Create"),
                                id="btn-unlock",
                                classes="btn-primary",
                            )
                            if not self._is_setup:
                                yield Button(
                                    _("Reset Vault"),
                                    id="btn-reset",
                                    classes="btn-danger",
                                )
                    yield Static(
                        f"GeoServer Manager {_VER}",
                        id="unlock-branding",
                    )

    def on_mount(self) -> None:
        """Focus the password input."""
        self.query_one("#unlock-input", Input).focus()
        # Hide error label initially
        self.query_one("#unlock-error", Static).display = False

    def _show_error(self, msg: str) -> None:
        """Display an error message."""
        error = self.query_one("#unlock-error", Static)
        error.update(msg)
        error.display = True

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter key in input fields."""
        if self._is_setup and event.input.id == "unlock-input":
            # Tab to confirm field
            try:
                self.query_one("#unlock-confirm", Input).focus()
            except Exception:  # nosec B110
                pass  # Confirm field may not exist in unlock mode
            return
        self._attempt_unlock()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses."""
        if event.button.id == "btn-unlock":
            self._attempt_unlock()
        elif event.button.id == "btn-reset":
            self._confirm_reset()

    def _attempt_unlock(self) -> None:
        """Attempt to unlock or create the vault."""
        password = self.query_one("#unlock-input", Input).value

        if not password:
            self._show_error(_("Password cannot be empty"))
            return

        if len(password) < 8:
            self._show_error(_("Password must be at least 8 characters"))
            return

        if self._is_setup:
            try:
                confirm = self.query_one("#unlock-confirm", Input).value
            except Exception:
                confirm = ""
            if password != confirm:
                self._show_error(_("Passwords do not match"))
                return
            self.dismiss(password)
        else:
            # Verify against vault - caller handles actual verification
            self._attempts += 1
            self.dismiss(password)

    def _confirm_reset(self) -> None:
        """Show reset confirmation."""
        from geotui.screens.confirm import ConfirmScreen

        def handle_reset(confirmed: bool | None) -> None:
            if confirmed:
                self.dismiss(None)  # None signals vault reset

        self.app.push_screen(
            ConfirmScreen(
                _("Reset Vault"),
                _(
                    "This will DELETE all saved connections.\n"
                    "You will need to set a new master password\n"
                    "and re-enter all your connections.\n\n"
                    "This cannot be undone!"
                ),
            ),
            callback=handle_reset,
        )

    def action_cancel(self) -> None:
        """Cancel - exit the app."""
        self.app.exit()
