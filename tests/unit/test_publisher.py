"""Tests for the bulk shapefile publisher engine."""

from pathlib import Path

import pytest

from geotui.publisher import (
    NamingStrategy,
    PublishConfig,
    discover_bundles,
    resolve_layer_names,
)


@pytest.fixture
def shapefile_dir(tmp_path: Path) -> Path:
    """Create a directory with test shapefile bundles."""
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        (tmp_path / f"roads{ext}").touch()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"buildings{ext}").touch()
    (tmp_path / "broken.shp").touch()
    (tmp_path / "broken.shx").touch()
    (tmp_path / "readme.txt").touch()
    return tmp_path


@pytest.fixture
def nested_dir(tmp_path: Path) -> Path:
    """Create nested directories with shapefiles."""
    sub = tmp_path / "subdir"
    sub.mkdir()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"rivers{ext}").touch()
        (sub / f"rivers{ext}").touch()
    return tmp_path


class TestDiscoverBundles:
    def test_finds_complete_bundles(self, shapefile_dir: Path) -> None:
        bundles, _warnings = discover_bundles(shapefile_dir, recurse=False)
        names = {b.name for b in bundles}
        assert "roads" in names
        assert "buildings" in names
        assert len(bundles) == 2

    def test_reports_incomplete_bundles(self, shapefile_dir: Path) -> None:
        _bundles, warnings = discover_bundles(shapefile_dir, recurse=False)
        assert len(warnings) == 1
        assert "broken" in warnings[0]

    def test_recurse_finds_subdirectories(self, nested_dir: Path) -> None:
        bundles, _warnings = discover_bundles(nested_dir, recurse=True)
        assert len(bundles) == 2

    def test_no_recurse_skips_subdirs(self, nested_dir: Path) -> None:
        bundles, _warnings = discover_bundles(nested_dir, recurse=False)
        assert len(bundles) == 1

    def test_bundle_calculates_total_size(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        for b in bundles:
            assert b.total_size >= 0

    def test_bundle_lists_all_components(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        roads = next(b for b in bundles if b.name == "roads")
        extensions = {f.suffix for f in roads.files}
        assert ".shp" in extensions
        assert ".prj" in extensions


class TestNaming:
    def test_basename_strategy(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        names = resolve_layer_names(bundles, shapefile_dir, NamingStrategy.BASENAME)
        assert "roads" in names.values()

    def test_path_slug_avoids_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        names = resolve_layer_names(bundles, nested_dir, NamingStrategy.PATH_SLUG)
        values = list(names.values())
        assert len(values) == len(set(values))

    def test_basename_detects_collision(self, nested_dir: Path) -> None:
        bundles, _ = discover_bundles(nested_dir, recurse=True)
        with pytest.raises(ValueError, match="collision"):
            resolve_layer_names(bundles, nested_dir, NamingStrategy.BASENAME)

    def test_prefixed_basename(self, shapefile_dir: Path) -> None:
        bundles, _ = discover_bundles(shapefile_dir, recurse=False)
        names = resolve_layer_names(
            bundles,
            shapefile_dir,
            NamingStrategy.PREFIXED_BASENAME,
            prefix="geo_",
        )
        assert all(v.startswith("geo_") for v in names.values())


class TestPublishConfig:
    def test_defaults(self) -> None:
        cfg = PublishConfig(
            workspace="ws",
            datastore="ds",
            source_directory=Path("/data"),
        )
        assert cfg.concurrency == 4
        assert cfg.dry_run is False
        assert cfg.naming == NamingStrategy.BASENAME
        assert cfg.retry_max_attempts == 3
