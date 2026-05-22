"""Tests for the unlock/vault setup screen."""

import pytest

from geotui.app import GeoTUIApp
from geotui.screens.unlock import UnlockScreen


class TestUnlockScreen:
    """Test suite for UnlockScreen."""

    @pytest.mark.asyncio
    async def test_unlock_screen_renders(self) -> None:
        """Test that the unlock screen renders."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=False))
            await pilot.pause()
            assert isinstance(pilot.app.screen, UnlockScreen)

    @pytest.mark.asyncio
    async def test_setup_mode_renders(self) -> None:
        """Test that setup mode shows create title."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=True))
            await pilot.pause()
            from textual.widgets import Label

            title = pilot.app.screen.query_one("#unlock-title", Label)
            assert title is not None

    @pytest.mark.asyncio
    async def test_setup_has_confirm_field(self) -> None:
        """Test that setup mode has a confirm password field."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=True))
            await pilot.pause()
            from textual.widgets import Input

            confirm = pilot.app.screen.query_one("#unlock-confirm", Input)
            assert confirm is not None

    @pytest.mark.asyncio
    async def test_unlock_mode_no_confirm_field(self) -> None:
        """Test that unlock mode does not have a confirm field."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=False))
            await pilot.pause()
            from textual.css.query import NoMatches
            from textual.widgets import Input

            with pytest.raises(NoMatches):
                pilot.app.screen.query_one("#unlock-confirm", Input)

    @pytest.mark.asyncio
    async def test_empty_password_shows_error(self) -> None:
        """Test that submitting empty password shows error."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=False))
            await pilot.pause()
            # Submit via Enter key on the input field
            await pilot.press("enter")
            await pilot.pause()
            from textual.widgets import Static

            error = pilot.app.screen.query_one("#unlock-error", Static)
            assert error.display is True

    @pytest.mark.asyncio
    async def test_short_password_shows_error(self) -> None:
        """Test that password under 8 chars shows error."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=False))
            await pilot.pause()
            from textual.widgets import Input

            inp = pilot.app.screen.query_one("#unlock-input", Input)
            inp.value = "short"
            await pilot.pause()
            # Submit via Enter
            await pilot.press("enter")
            await pilot.pause()
            from textual.widgets import Static

            error = pilot.app.screen.query_one("#unlock-error", Static)
            assert error.display is True

    @pytest.mark.asyncio
    async def test_valid_password_dismisses(self) -> None:
        """Test that a valid password dismisses the screen."""
        results: list[str | None] = []

        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(
                UnlockScreen(is_setup=False), callback=results.append
            )
            await pilot.pause()
            from textual.widgets import Input

            inp = pilot.app.screen.query_one("#unlock-input", Input)
            inp.value = "mysecretpassword"
            await pilot.pause()
            # Submit via Enter
            await pilot.press("enter")
            await pilot.pause()

        assert results == ["mysecretpassword"]

    @pytest.mark.asyncio
    async def test_setup_mismatched_passwords(self) -> None:
        """Test that mismatched passwords in setup mode shows error."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=True))
            await pilot.pause()
            from textual.widgets import Input

            inp = pilot.app.screen.query_one("#unlock-input", Input)
            inp.value = "mysecretpassword"
            confirm = pilot.app.screen.query_one("#unlock-confirm", Input)
            confirm.value = "different1234567"
            await pilot.pause()
            # Focus confirm and press Enter to submit
            confirm.focus()
            await pilot.press("enter")
            await pilot.pause()
            from textual.widgets import Static

            error = pilot.app.screen.query_one("#unlock-error", Static)
            assert error.display is True

    @pytest.mark.asyncio
    async def test_escape_exits_app(self) -> None:
        """Test that escape on unlock screen triggers app exit."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(UnlockScreen(is_setup=False))
            await pilot.pause()
            # Escape calls action_cancel which calls app.exit()
            await pilot.press("escape")
            await pilot.pause()
