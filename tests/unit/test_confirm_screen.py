"""Tests for the confirmation dialog screen."""

import pytest

from geotui.app import GeoTUIApp
from geotui.screens.confirm import ConfirmScreen


class TestConfirmScreen:
    """Test suite for ConfirmScreen."""

    @pytest.mark.asyncio
    async def test_confirm_screen_renders(self) -> None:
        """Test that the confirm screen renders with title and message."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(ConfirmScreen("Delete?", "Are you sure?"))
            await pilot.pause()
            screen = pilot.app.screen
            assert isinstance(screen, ConfirmScreen)

    @pytest.mark.asyncio
    async def test_confirm_shows_title(self) -> None:
        """Test that the title label exists."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(ConfirmScreen("Delete Item", "This is permanent."))
            await pilot.pause()
            from textual.widgets import Label

            title = pilot.app.screen.query_one("#confirm-title", Label)
            assert title is not None

    @pytest.mark.asyncio
    async def test_confirm_cancel_via_escape(self) -> None:
        """Test that escape key cancels the dialog."""
        results: list[bool] = []

        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(
                ConfirmScreen("Test", "msg"), callback=results.append
            )
            await pilot.pause()
            await pilot.press("escape")
            await pilot.pause()

        assert results == [False]

    @pytest.mark.asyncio
    async def test_confirm_with_require_name(self) -> None:
        """Test that delete button is disabled when name is required."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(
                ConfirmScreen("Delete", "Sure?", require_name="my_workspace")
            )
            await pilot.pause()
            from textual.widgets import Button

            btn = pilot.app.screen.query_one("#btn-confirm", Button)
            assert btn.disabled is True

    @pytest.mark.asyncio
    async def test_confirm_name_enables_button(self) -> None:
        """Test that typing the correct name enables the delete button."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(
                ConfirmScreen("Delete", "Sure?", require_name="ws1")
            )
            await pilot.pause()
            from textual.widgets import Button, Input

            inp = pilot.app.screen.query_one("#confirm-name-input", Input)
            inp.value = "ws1"
            await pilot.pause()
            btn = pilot.app.screen.query_one("#btn-confirm", Button)
            assert btn.disabled is False

    @pytest.mark.asyncio
    async def test_confirm_wrong_name_keeps_disabled(self) -> None:
        """Test that wrong name keeps button disabled."""
        async with GeoTUIApp().run_test() as pilot:
            pilot.app.push_screen(
                ConfirmScreen("Delete", "Sure?", require_name="ws1")
            )
            await pilot.pause()
            from textual.widgets import Button, Input

            inp = pilot.app.screen.query_one("#confirm-name-input", Input)
            inp.value = "wrong"
            await pilot.pause()
            btn = pilot.app.screen.query_one("#btn-confirm", Button)
            assert btn.disabled is True
