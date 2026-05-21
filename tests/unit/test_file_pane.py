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
