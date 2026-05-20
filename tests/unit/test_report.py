"""Tests for PDF and JSON report generation."""

import json
from pathlib import Path

import pytest

from geotui.publisher import BundleResult, PublishConfig, PublishReport
from geotui.report import generate_json_report, generate_pdf_report


@pytest.fixture
def sample_report() -> PublishReport:
    """Create a sample report with mixed results."""
    cfg = PublishConfig(
        workspace="test_ws",
        datastore="test_ds",
        source_directory=Path("/data/shapes"),
    )
    return PublishReport(
        config=cfg,
        geoserver_url="https://geo.example.com/geoserver",
        geoserver_version="2.24.2",
        username="admin",
        wall_clock_seconds=125.7,
        warnings=["Incomplete bundle 'broken' in /data/shapes"],
        results=[
            BundleResult(
                layer_name="roads",
                source_path="roads.shp",
                action="CREATE",
                status="SUCCESS",
                file_size=1024000,
                upload_time=1.23,
            ),
            BundleResult(
                layer_name="buildings",
                source_path="buildings.shp",
                action="UPDATE",
                status="SUCCESS",
                file_size=2048000,
                upload_time=2.45,
            ),
            BundleResult(
                layer_name="rivers",
                source_path="rivers.shp",
                action="CREATE",
                status="ERROR",
                file_size=512000,
                upload_time=5.0,
                error="HTTP 500 Internal Server Error",
            ),
        ],
    )


class TestJsonReport:
    def test_generates_valid_json(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["summary"]["total_bundles"] == 3
        assert data["summary"]["created"] == 1
        assert data["summary"]["failed"] == 1

    def test_json_contains_all_results(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        data = json.loads(path.read_text())
        assert len(data["results"]) == 3

    def test_json_contains_config(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        data = json.loads(path.read_text())
        assert data["config"]["workspace"] == "test_ws"
        assert data["config"]["geoserver_url"] == "https://geo.example.com/geoserver"

    def test_json_redacts_password(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.json"
        generate_json_report(sample_report, path)
        content = path.read_text()
        assert "password" not in content.lower() or "***" in content


class TestPdfReport:
    def test_generates_pdf_file(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.pdf"
        generate_pdf_report(sample_report, path)
        assert path.exists()
        assert path.stat().st_size > 0

    def test_pdf_starts_with_header(
        self, sample_report: PublishReport, tmp_path: Path
    ) -> None:  # noqa: E501
        path = tmp_path / "report.pdf"
        generate_pdf_report(sample_report, path)
        content = path.read_bytes()
        assert content[:5] == b"%PDF-"

    def test_pdf_with_empty_results(self, tmp_path: Path) -> None:
        cfg = PublishConfig(
            workspace="ws", datastore="ds", source_directory=Path("/empty")
        )  # noqa: E501
        report = PublishReport(config=cfg)
        path = tmp_path / "report.pdf"
        generate_pdf_report(report, path)
        assert path.exists()
