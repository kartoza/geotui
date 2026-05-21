"""Tests for CLI subcommands."""

from pathlib import Path

import pytest
from click.testing import CliRunner

from geotui.cli import cli


@pytest.fixture
def runner() -> CliRunner:
    """Create a Click test runner."""
    return CliRunner()


@pytest.fixture
def shapefile_dir(tmp_path: Path) -> Path:
    """Create a directory with a test shapefile bundle."""
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"test{ext}").touch()
    return tmp_path


class TestCLI:
    def test_publish_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["publish", "--help"])
        assert result.exit_code == 0
        assert "publish" in result.output.lower()

    def test_export_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["export", "--help"])
        assert result.exit_code == 0

    def test_import_config_help(self, runner: CliRunner) -> None:
        result = runner.invoke(cli, ["import-config", "--help"])
        assert result.exit_code == 0

    def test_publish_requires_connection(
        self, runner: CliRunner, shapefile_dir: Path, tmp_path: Path
    ) -> None:
        cfg_path = tmp_path / "config.json"
        cfg_path.write_text('{"theme":"dark","language":"en","connections":[]}')
        result = runner.invoke(
            cli,
            [
                "publish",
                "--connection",
                "NonExistent",
                "--workspace",
                "ws",
                "--datastore",
                "ds",
                "--source",
                str(shapefile_dir),
                "--config-path",
                str(cfg_path),
            ],
        )
        assert result.exit_code != 0
        assert "not found" in result.output.lower()
