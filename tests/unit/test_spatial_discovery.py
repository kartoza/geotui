"""Tests for multi-format spatial file discovery."""

from pathlib import Path

import pytest

from geotui.publisher import discover_spatial_files


@pytest.fixture
def mixed_dir(tmp_path: Path) -> Path:
    """Create directory with mixed spatial formats."""
    for ext in (".shp", ".shx", ".dbf", ".prj"):
        (tmp_path / f"roads{ext}").touch()
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"buildings{ext}").touch()
    (tmp_path / "broken.shp").touch()
    (tmp_path / "broken.shx").touch()
    (tmp_path / "parcels.gpkg").touch()
    (tmp_path / "zones.gpkg").touch()
    (tmp_path / "dem.tif").touch()
    (tmp_path / "ortho.tiff").touch()
    (tmp_path / "readme.txt").touch()
    return tmp_path


@pytest.fixture
def shp_only_dir(tmp_path: Path) -> Path:
    """Directory with only shapefiles."""
    for ext in (".shp", ".shx", ".dbf"):
        (tmp_path / f"rivers{ext}").touch()
    return tmp_path


@pytest.fixture
def empty_dir(tmp_path: Path) -> Path:
    """Empty directory."""
    return tmp_path


class TestDiscoverSpatialFiles:
    def test_finds_all_formats(self, mixed_dir: Path) -> None:
        groups, _warnings = discover_spatial_files(mixed_dir)
        format_names = {g.format_type for g in groups}
        assert "shapefile" in format_names
        assert "geopackage" in format_names
        assert "geotiff" in format_names

    def test_shapefile_group_has_bundles(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        shp = next(g for g in groups if g.format_type == "shapefile")
        names = {b.name for b in shp.files}
        assert "roads" in names
        assert "buildings" in names
        assert len(shp.files) == 2

    def test_geopackage_group(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        gpkg = next(g for g in groups if g.format_type == "geopackage")
        names = {f.name for f in gpkg.files}
        assert "parcels" in names
        assert "zones" in names

    def test_geotiff_group(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        tif = next(g for g in groups if g.format_type == "geotiff")
        names = {f.name for f in tif.files}
        assert "dem" in names
        assert "ortho" in names

    def test_incomplete_shapefile_warned(self, mixed_dir: Path) -> None:
        _groups, warnings = discover_spatial_files(mixed_dir)
        assert len(warnings) == 1
        assert "broken" in warnings[0]

    def test_empty_directory(self, empty_dir: Path) -> None:
        groups, warnings = discover_spatial_files(empty_dir)
        assert len(groups) == 0
        assert len(warnings) == 0

    def test_single_format(self, shp_only_dir: Path) -> None:
        groups, _ = discover_spatial_files(shp_only_dir)
        assert len(groups) == 1
        assert groups[0].format_type == "shapefile"

    def test_group_store_type(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        types = {g.format_type: g.store_type for g in groups}
        assert types["shapefile"] == "Directory of spatial files (shapefiles)"
        assert types["geopackage"] == "GeoPackage"
        assert types["geotiff"] == "GeoTIFF"

    def test_group_total_size(self, mixed_dir: Path) -> None:
        groups, _ = discover_spatial_files(mixed_dir)
        for g in groups:
            assert g.total_size >= 0
