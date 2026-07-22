"""Tests for the VRT mode selection modal."""

import pytest
from textual.app import App, ComposeResult
from textual.widgets import Button

from geotui.screens.vrt_mode import VRTModeScreen


class _Host(App[None]):
    def compose(self) -> ComposeResult:
        yield from ()


@pytest.mark.asyncio
async def test_bundle_choice_returns_bundle() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        result: list[str] = []
        app.push_screen(VRTModeScreen(), callback=lambda r: result.append(r))
        await pilot.pause()
        app.screen.query_one("#btn-vrt-bundle", Button).press()
        await pilot.pause()
        assert result == ["bundle"]


@pytest.mark.asyncio
async def test_server_choice_returns_server_path() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        result: list[str] = []
        app.push_screen(VRTModeScreen(), callback=lambda r: result.append(r))
        await pilot.pause()
        app.screen.query_one("#btn-vrt-server", Button).press()
        await pilot.pause()
        assert result == ["server_path"]


@pytest.mark.asyncio
async def test_cancel_returns_empty() -> None:
    app = _Host()
    async with app.run_test() as pilot:
        result: list[str] = []
        app.push_screen(VRTModeScreen(), callback=lambda r: result.append(r))
        await pilot.pause()
        app.screen.query_one("#btn-vrt-cancel", Button).press()
        await pilot.pause()
        assert result == [""]
