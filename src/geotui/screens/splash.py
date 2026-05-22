"""Splash screen displaying the Kartoza logo on startup.

The logo is generated from the Kartoza SVG using half-block
character rendering (similar to catimg/term2alpha approach
used in timlinux/nix-vim). Regenerate with:

    magick resources/KartozaSymbolCMYK.svg -resize 200x200 \\
        -background '#1a1a2e' -flatten resources/kartoza-logo.png
    python scripts/logo_to_rich.py 36 > src/geotui/screens/logo_data.py
"""

from textual.app import ComposeResult
from textual.containers import Center, Middle
from textual.screen import Screen
from textual.widgets import Static

from geotui import __version__
from geotui.screens.logo_data import LOGO

_VER = f"v{__version__}"
_TITLE = "G e o T U I"
_SUB = f"GeoServer Manager {_VER}"
# Box inner width = 34 (36 total with border chars)
_W = 34
_T_PAD = (_W - len(_TITLE)) // 2
_S_PAD = (_W - len(_SUB)) // 2

SPLASH_TEXT = (
    f"{LOGO}\n"
    f"\n"
    f"[bold #569FC6]╭{'─' * _W}╮[/]\n"
    f"[bold #569FC6]│[/]"
    f"{' ' * _T_PAD}[bold #DF9E2F]{_TITLE}[/]"
    f"{' ' * (_W - _T_PAD - len(_TITLE))}"
    f"[bold #569FC6]│[/]\n"
    f"[bold #569FC6]│[/]"
    f"{' ' * _S_PAD}[#8A8B8B]{_SUB}[/]"
    f"{' ' * (_W - _S_PAD - len(_SUB))}"
    f"[bold #569FC6]│[/]\n"
    f"[bold #569FC6]╰{'─' * _W}╯[/]\n"
    f"\n"
    f"[#8A8B8B]Made with [#CC0403]\u2764[/#CC0403]"
    f" by [bold #569FC6]Kartoza[/bold #569FC6][/]"
)


class SplashScreen(Screen[None]):
    """Splash screen with Kartoza logo shown on startup."""

    CSS = """
    SplashScreen {
        background: #1a1a2e;
        align: center middle;
    }

    SplashScreen #splash-content {
        width: auto;
        height: auto;
        content-align: center middle;
        text-align: center;
    }
    """

    def compose(self) -> ComposeResult:
        """Compose the splash screen."""
        with Middle():
            with Center():
                yield Static(SPLASH_TEXT, id="splash-content")

    def on_mount(self) -> None:
        """Auto-dismiss after 2 seconds."""
        self.set_timer(2.0, self._dismiss)

    def on_key(self) -> None:
        """Dismiss on any key press."""
        self._dismiss()

    def on_click(self) -> None:
        """Dismiss on mouse click."""
        self._dismiss()

    def _dismiss(self) -> None:
        """Close the splash screen."""
        if self.is_current:
            self.dismiss(None)
