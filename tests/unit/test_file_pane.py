"""Tests for FilePane widget."""

from pathlib import Path

import pytest

from geotui.app import GeoTUIApp
from geotui.config import ConfigManager
from geotui.widgets.file_pane import FilePane


@pytest.fixture
def config_manager(tmp_path: Path) -> ConfigManager:
    """Create a ConfigManager with temporary storage."""
    return ConfigManager(config_path=tmp_path / "config.json")


class TestFilePane:
    @pytest.mark.asyncio
    async def test_get_selected_path_returns_path(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that get_selected_path returns a Path object."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            path = pane.get_selected_path()
            assert isinstance(path, Path)

    @pytest.mark.asyncio
    async def test_get_selected_path_is_directory(
        self, config_manager: ConfigManager
    ) -> None:
        """Test that get_selected_path returns a real directory."""
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            path = pane.get_selected_path()
            assert path.exists()


class TestCursorTargetAndSelection:
    """F5 selection semantics: cursor target and Space multi-select."""

    async def _navigate_to_entry(self, pane, target: Path, pilot) -> None:
        """Move the tree cursor onto *target* (bounded search)."""
        from geotui.widgets.file_pane import MCDirectoryTree

        tree = pane.query_one(MCDirectoryTree)
        tree.focus()
        pane.navigate_to(target.parent)
        await pilot.pause()
        for _ in range(12):
            if pane.get_cursor_target() == target:
                return
            await pilot.press("down")
            await pilot.pause()

    @pytest.mark.asyncio
    async def test_cursor_target_on_file_returns_file(
        self, config_manager: ConfigManager, tmp_path: Path
    ) -> None:
        f = tmp_path / "only.tif"
        f.write_bytes(b"II*\x00")
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            await self._navigate_to_entry(pane, f, pilot)
            target = pane.get_cursor_target()
            assert target == f
            assert target.is_file()

    @pytest.mark.asyncio
    async def test_cursor_target_on_folder_returns_folder(
        self, config_manager: ConfigManager, tmp_path: Path
    ) -> None:
        sub = tmp_path / "sub"
        sub.mkdir()
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            await self._navigate_to_entry(pane, sub, pilot)
            target = pane.get_cursor_target()
            assert target == sub
            assert target.is_dir()

    @pytest.mark.asyncio
    async def test_space_tags_file(
        self, config_manager: ConfigManager, tmp_path: Path
    ) -> None:
        f = tmp_path / "only.tif"
        f.write_bytes(b"II*\x00")
        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            await self._navigate_to_entry(pane, f, pilot)
            await pilot.press("space")
            await pilot.pause()
            assert f in pane.get_selected_files()


class TestArrowExpandCollapse:
    """Right arrow expands a folder in place; left collapses it."""

    @pytest.mark.asyncio
    async def test_right_expands_left_collapses(
        self, config_manager: ConfigManager, tmp_path: Path
    ) -> None:
        from geotui.widgets.file_pane import MCDirectoryTree

        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "child.tif").write_bytes(b"II*\x00")

        app = GeoTUIApp(config_manager=config_manager)
        async with app.run_test() as pilot:
            pane = pilot.app.query_one("#left-pane", FilePane)
            tree = pane.query_one(MCDirectoryTree)
            tree.focus()
            pane.navigate_to(tmp_path)
            await pilot.pause()

            # Move onto the "sub" folder node.
            for _ in range(12):
                if pane.get_cursor_target() == sub:
                    break
                await pilot.press("down")
                await pilot.pause()
            assert pane.get_cursor_target() == sub

            node = tree.cursor_node
            assert node.allow_expand
            await pilot.press("right")
            await pilot.pause()
            assert node.is_expanded is True

            await pilot.press("left")
            await pilot.pause()
            assert node.is_expanded is False
