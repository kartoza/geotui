"""Tests for the main GeoTUI application."""

import pytest

from geotui.app import GeoTUIApp


class TestGeoTUIApp:
    """Test suite for GeoTUIApp."""

    @pytest.mark.asyncio
    async def test_app_launches(self) -> None:
        """Test that the application launches without errors."""
        async with GeoTUIApp().run_test() as pilot:
            assert pilot.app.title == "GeoTUI"

    @pytest.mark.asyncio
    async def test_app_has_header(self) -> None:
        """Test that the app displays a header."""
        async with GeoTUIApp().run_test() as pilot:
            from textual.widgets import Header

            header = pilot.app.query_one(Header)
            assert header is not None

    @pytest.mark.asyncio
    async def test_app_has_footer(self) -> None:
        """Test that the app displays a footer."""
        async with GeoTUIApp().run_test() as pilot:
            from textual.widgets import Footer

            footer = pilot.app.query_one(Footer)
            assert footer is not None

    @pytest.mark.asyncio
    async def test_app_has_dual_pane(self) -> None:
        """Test that the app contains a dual pane widget."""
        async with GeoTUIApp().run_test() as pilot:
            from geotui.widgets.dual_pane import DualPane

            dual_pane = pilot.app.query_one(DualPane)
            assert dual_pane is not None

    @pytest.mark.asyncio
    async def test_app_has_status_bar(self) -> None:
        """Test that the app contains a status bar."""
        async with GeoTUIApp().run_test() as pilot:
            from geotui.widgets.status_bar import StatusBar

            status_bar = pilot.app.query_one(StatusBar)
            assert status_bar is not None

    @pytest.mark.asyncio
    async def test_tab_switches_pane(self) -> None:
        """Test that pressing Tab switches the active pane."""
        async with GeoTUIApp().run_test() as pilot:
            from geotui.widgets.dual_pane import DualPane

            dual_pane = pilot.app.query_one(DualPane)
            assert dual_pane.active_pane == "left"
            pilot.app.action_switch_pane()
            await pilot.pause()
            assert dual_pane.active_pane == "right"

    @pytest.mark.asyncio
    async def test_quit_action(self) -> None:
        """Test that pressing q exits the app."""
        async with GeoTUIApp().run_test() as pilot:
            await pilot.press("q")
