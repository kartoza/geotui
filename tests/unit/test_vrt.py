"""Tests for VRT (GDAL/OGR Virtual Format) parsing and classification."""

from pathlib import Path

import pytest

from geotui.vrt import InvalidVRTError, VRTInfo, parse_vrt

RASTER_VRT = """<VRTDataset rasterXSize="512" rasterYSize="512">
  <SRS>EPSG:4326</SRS>
  <VRTRasterBand dataType="Byte" band="1">
    <SimpleSource>
      <SourceFilename relativeToVRT="1">tiles/a.tif</SourceFilename>
      <SourceBand>1</SourceBand>
    </SimpleSource>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">{abs}</SourceFilename>
      <SourceBand>1</SourceBand>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
"""

VECTOR_VRT = """<OGRVRTDataSource>
  <OGRVRTLayer name="points">
    <SrcDataSource relativeToVRT="1">data/points.csv</SrcDataSource>
    <GeometryType>wkbPoint</GeometryType>
  </OGRVRTLayer>
</OGRVRTDataSource>
"""

DOCTYPE_VRT = """<?xml version="1.0"?>
<!DOCTYPE VRTDataset [ <!ENTITY xxe SYSTEM "file:///etc/passwd"> ]>
<VRTDataset rasterXSize="1" rasterYSize="1">
  <VRTRasterBand dataType="Byte" band="1">
    <SimpleSource>
      <SourceFilename relativeToVRT="1">&xxe;</SourceFilename>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
"""


def _write(dirpath: Path, name: str, content: str) -> Path:
    p = dirpath / name
    p.write_text(content, encoding="utf-8")
    return p


class TestParseRasterVRT:
    def test_classifies_as_raster(self, tmp_path: Path) -> None:
        abs_tile = tmp_path / "b.tif"
        abs_tile.write_bytes(b"II*\x00")
        vrt = _write(tmp_path, "mosaic.vrt", RASTER_VRT.format(abs=abs_tile))
        info = parse_vrt(vrt)
        assert isinstance(info, VRTInfo)
        assert info.kind == "raster"

    def test_enumerates_referenced_files_resolved(self, tmp_path: Path) -> None:
        (tmp_path / "tiles").mkdir()
        rel_tile = _write(tmp_path / "tiles", "a.tif", "x")
        abs_tile = tmp_path / "b.tif"
        abs_tile.write_bytes(b"II*\x00")
        vrt = _write(tmp_path, "mosaic.vrt", RASTER_VRT.format(abs=abs_tile))
        info = parse_vrt(vrt)
        refs = set(info.referenced_files)
        assert rel_tile.resolve() in refs  # relativeToVRT=1 resolved to VRT dir
        assert abs_tile.resolve() in refs  # relativeToVRT=0 absolute path


class TestParseVectorVRT:
    def test_classifies_as_vector(self, tmp_path: Path) -> None:
        (tmp_path / "data").mkdir()
        _write(tmp_path / "data", "points.csv", "x,y\n1,2\n")
        vrt = _write(tmp_path, "points.vrt", VECTOR_VRT)
        info = parse_vrt(vrt)
        assert info.kind == "vector"

    def test_enumerates_srcdatasource(self, tmp_path: Path) -> None:
        (tmp_path / "data").mkdir()
        csv = _write(tmp_path / "data", "points.csv", "x,y\n1,2\n")
        vrt = _write(tmp_path, "points.vrt", VECTOR_VRT)
        info = parse_vrt(vrt)
        assert csv.resolve() in set(info.referenced_files)


class TestReferencedFileExistence:
    def test_missing_source_still_enumerated(self, tmp_path: Path) -> None:
        """Server-path mode needs the declared path even if not present locally."""
        vrt = _write(
            tmp_path, "mosaic.vrt", RASTER_VRT.format(abs="/data/on/server/b.tif")
        )
        info = parse_vrt(vrt)
        assert Path("/data/on/server/b.tif") in set(info.referenced_files)

    def test_missing_files_reported(self, tmp_path: Path) -> None:
        vrt = _write(
            tmp_path, "mosaic.vrt", RASTER_VRT.format(abs="/data/on/server/b.tif")
        )
        info = parse_vrt(vrt)
        # tiles/a.tif and the absolute path are both absent locally
        assert len(info.missing_files) == 2


REMOTE_VRT = """<VRTDataset rasterXSize="4" rasterYSize="4">
  <VRTRasterBand dataType="Byte" band="1">
    <SimpleSource>
      <SourceFilename relativeToVRT="0">/vsis3/my-bucket/path/cog.tif</SourceFilename>
    </SimpleSource>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">/vsicurl/https://ex.com/a/cog.tif</SourceFilename>
    </SimpleSource>
    <SimpleSource>
      <SourceFilename relativeToVRT="0">s3://bucket/key/cog.tif</SourceFilename>
    </SimpleSource>
  </VRTRasterBand>
</VRTDataset>
"""


class TestRemoteSources:
    def test_remote_sources_flagged(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "remote.vrt", REMOTE_VRT)
        info = parse_vrt(vrt)
        assert all(s.remote for s in info.sources)

    def test_remote_urls_not_mangled(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "remote.vrt", REMOTE_VRT)
        info = parse_vrt(vrt)
        raws = [s.raw for s in info.sources]
        # The // in the /vsicurl URL must survive verbatim.
        assert "/vsicurl/https://ex.com/a/cog.tif" in raws
        assert set(info.remote_sources) == set(raws)

    def test_remote_sources_have_no_local_path(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "remote.vrt", REMOTE_VRT)
        info = parse_vrt(vrt)
        assert all(s.resolved is None for s in info.sources)

    def test_remote_sources_not_reported_missing(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "remote.vrt", REMOTE_VRT)
        info = parse_vrt(vrt)
        assert info.missing_files == ()
        assert info.referenced_files == ()

    def test_local_absolute_path_is_not_remote(self, tmp_path: Path) -> None:
        """A plain absolute filesystem path is local (server-path mode), not vsi."""
        vrt = _write(
            tmp_path, "abs.vrt", RASTER_VRT.format(abs="/data/on/server/b.tif")
        )
        info = parse_vrt(vrt)
        assert not any(s.remote for s in info.sources)


class TestSecurityAndValidation:
    def test_doctype_entity_rejected(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "evil.vrt", DOCTYPE_VRT)
        with pytest.raises(InvalidVRTError):
            parse_vrt(vrt)

    def test_non_vrt_xml_rejected(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "nope.vrt", "<Something/>")
        with pytest.raises(InvalidVRTError):
            parse_vrt(vrt)

    def test_malformed_xml_rejected(self, tmp_path: Path) -> None:
        vrt = _write(tmp_path, "bad.vrt", "<VRTDataset><unclosed>")
        with pytest.raises(InvalidVRTError):
            parse_vrt(vrt)
