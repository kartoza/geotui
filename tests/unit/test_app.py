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


class TestVaultUnlockPrompt:
    """Regression tests for the master-password re-prompt loop."""

    @pytest.mark.asyncio
    async def test_locked_decrypt_shows_single_unlock(self, tmp_path) -> None:
        """Decrypting many connections while locked shows ONE unlock prompt.

        Previously each connection triggered its own UnlockScreen, stacking
        several identical prompts that felt like the password was being
        rejected in a loop.
        """
        from geotui.config import ConfigManager, Connection
        from geotui.screens.unlock import UnlockScreen

        cm = ConfigManager(config_path=tmp_path / "config.json")
        cm.init_vault("masterpassword")
        vk = cm.unlock("masterpassword")
        for name in ("A", "B", "C"):
            cm.add_connection(
                Connection(
                    name=name,
                    url="http://gs",
                    username="u",
                    password=cm.encrypt_password("s", vk),
                )
            )

        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            app.vault_key = None  # vault locked
            for conn in cm.config.connections:
                app.decrypt_connection(conn)
            await pilot.pause()

            stack = [type(s).__name__ for s in app.screen_stack]
            assert stack.count("UnlockScreen") == 1
            assert isinstance(app.screen, UnlockScreen)

    @pytest.mark.asyncio
    async def test_unlock_clears_guard_for_retry(self, tmp_path) -> None:
        """A successful unlock clears the guard so a later lock re-prompts."""
        from geotui.config import ConfigManager, Connection

        cm = ConfigManager(config_path=tmp_path / "config.json")
        cm.init_vault("masterpassword")
        vk = cm.unlock("masterpassword")
        cm.add_connection(
            Connection(
                name="A",
                url="http://gs",
                username="u",
                password=cm.encrypt_password("s", vk),
            )
        )

        app = GeoTUIApp(config_manager=cm)
        async with app.run_test() as pilot:
            app.vault_key = None
            app.decrypt_connection(cm.config.connections[0])
            await pilot.pause()
            assert app._unlock_active is True

            # Simulate a completed unlock cycle: the screen is dismissed and
            # the guard is cleared (as handle_unlock does on success).
            app._unlock_active = False
            app.vault_key = cm.unlock("masterpassword")
            await app.pop_screen()
            await pilot.pause()

            # A later lock should be able to prompt again (exactly once).
            app.vault_key = None
            app.decrypt_connection(cm.config.connections[0])
            await pilot.pause()
            stack = [type(s).__name__ for s in app.screen_stack]
            assert stack.count("UnlockScreen") == 1
