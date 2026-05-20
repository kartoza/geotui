"""PDF and JSON report generation for GeoTUI bulk publish operations.

Provides two public functions:
- generate_json_report: write a machine-readable JSON summary.
- generate_pdf_report: write a branded, human-readable PDF summary.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fpdf import FPDF, XPos, YPos

from geotui import __version__
from geotui.publisher import PublishReport

# ---------------------------------------------------------------------------
# Colour constants (RGB tuples matching Kartoza brand palette)
# ---------------------------------------------------------------------------

_BLUE = (0x56, 0x9F, 0xC6)
_AMBER = (0xDF, 0x9E, 0x2F)
_TEAL = (0x06, 0x96, 0x9A)
_GREY = (0x8A, 0x8B, 0x8B)
_RED = (0xCC, 0x04, 0x03)
_DARK = (0x1A, 0x1A, 0x2E)
_WHITE = (0xFF, 0xFF, 0xFF)
_SUCCESS_BG = (0xE8, 0xF5, 0xE9)
_ERROR_BG = (0xFF, 0xEB, 0xEE)
_SKIP_BG = (0xF5, 0xF5, 0xF5)
_DRY_BG = (0xE3, 0xF2, 0xFD)
_BLACK = (0x00, 0x00, 0x00)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_size(num_bytes: int) -> str:
    """Return a human-readable file size string."""
    value: float = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if value < 1024:
            return f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} PB"


def _format_duration(seconds: float) -> str:
    """Return a human-readable duration string."""
    if seconds < 60:
        return f"{seconds:.1f}s"
    total_s = int(seconds)
    minutes = total_s // 60
    secs = total_s % 60
    if minutes < 60:
        return f"{minutes}m {secs:02d}s"
    hours = minutes // 60
    minutes = minutes % 60
    return f"{hours}h {minutes:02d}m {secs:02d}s"


def _compute_summary(report: PublishReport) -> dict[str, Any]:
    """Compute summary counts from raw result data using case-insensitive comparison."""
    total = len(report.results)
    created = sum(
        1
        for r in report.results
        if r.action.upper() == "CREATE" and r.status.upper() == "SUCCESS"
    )
    updated = sum(
        1
        for r in report.results
        if r.action.upper() == "UPDATE" and r.status.upper() == "SUCCESS"
    )
    skipped = sum(
        1 for r in report.results if r.status.upper() in ("SKIPPED", "DRY_RUN")
    )
    failed = sum(1 for r in report.results if r.status.upper() == "ERROR")
    return {
        "total_bundles": total,
        "created": created,
        "updated": updated,
        "skipped": skipped,
        "failed": failed,
        "total_uploaded_bytes": report.total_uploaded_bytes,
        "wall_clock_seconds": report.wall_clock_seconds,
    }


# ---------------------------------------------------------------------------
# JSON report
# ---------------------------------------------------------------------------


def generate_json_report(report: PublishReport, output_path: Path) -> None:
    """Write a machine-readable JSON report to *output_path*.

    The report contains:
    - ``generated``: ISO-8601 timestamp.
    - ``config``: publish configuration (password redacted).
    - ``summary``: aggregate counts and totals.
    - ``warnings``: list of warning strings.
    - ``results``: per-bundle outcome records.

    Args:
        report: The completed publish report.
        output_path: Destination file path (parent must exist or will be created).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cfg = report.config
    config_block: dict[str, Any] = {
        "workspace": cfg.workspace,
        "datastore": cfg.datastore,
        "source_directory": str(cfg.source_directory),
        "naming": cfg.naming.value,
        "prefix": cfg.prefix,
        "recurse": cfg.recurse,
        "concurrency": cfg.concurrency,
        "dry_run": cfg.dry_run,
        "fail_fast": cfg.fail_fast,
        "retry_max_attempts": cfg.retry_max_attempts,
        "geoserver_url": report.geoserver_url,
        "geoserver_version": report.geoserver_version,
        "username": report.username,
        # password intentionally omitted
    }

    results_block = [
        {
            "layer_name": r.layer_name,
            "source_path": str(r.source_path),
            "action": r.action,
            "status": r.status,
            "file_size": r.file_size,
            "file_size_human": _format_size(r.file_size),
            "upload_time": r.upload_time,
            "error": r.error,
        }
        for r in report.results
    ]

    payload: dict[str, Any] = {
        "generated": datetime.now(tz=timezone.utc).isoformat(),
        "geotui_version": __version__,
        "config": config_block,
        "summary": _compute_summary(report),
        "warnings": report.warnings,
        "results": results_block,
    }

    output_path.write_text(json.dumps(payload, indent=2, default=str), encoding="utf-8")


# ---------------------------------------------------------------------------
# PDF report
# ---------------------------------------------------------------------------

# Column widths for the detail table (mm).  Total fits within A4 landscape.
_COL_WIDTHS = {
    "#": 8,
    "Layer Name": 38,
    "Source Path": 40,
    "Action": 16,
    "Status": 16,
    "Size": 18,
    "Time": 14,
    "Error": 40,
}
_TABLE_COLS = list(_COL_WIDTHS.keys())


class _PublishPDF(FPDF):  # type: ignore[misc]
    """Custom FPDF subclass that renders the branded publish report."""

    def __init__(self, report: PublishReport) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self._report = report
        self.set_auto_page_break(auto=True, margin=15)
        self.add_page()

    # ------------------------------------------------------------------
    # FPDF hooks
    # ------------------------------------------------------------------

    def header(self) -> None:
        # Dark navy background bar.
        self.set_fill_color(*_DARK)
        self.rect(0, 0, self.w, 18, style="F")

        # Title in amber.
        self.set_xy(8, 4)
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "B", 13)
        self.cell(
            0,
            8,
            "GeoTUI Bulk Publish Report",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )

        # Version in blue, right-aligned.
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_BLUE)
        version_text = f"GeoTUI v{__version__}"
        self.set_xy(self.w - 60, 4)
        self.cell(30, 8, version_text, new_x=XPos.RIGHT, new_y=YPos.TOP)

        # kartoza.com right-aligned.
        self.set_text_color(*_AMBER)
        self.set_font("Helvetica", "I", 9)
        self.set_xy(self.w - 30, 4)
        self.cell(22, 8, "kartoza.com", new_x=XPos.RIGHT, new_y=YPos.TOP)

        self.ln(14)

    def footer(self) -> None:
        self.set_y(-12)
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_GREY)
        self.cell(
            0,
            8,
            f"GeoTUI v{__version__}",
            align="L",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        self.set_y(-12)
        page_text = f"Made with love by Kartoza  |  Page {self.page_no()}/{{nb}}"
        self.cell(0, 8, page_text, align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # ------------------------------------------------------------------
    # Public build entry-point
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Render all report sections."""
        self.alias_nb_pages()
        self._section_job_summary()
        self._section_detail_table()
        self._section_summary_stats()

    # ------------------------------------------------------------------
    # Section: job summary key-value pairs
    # ------------------------------------------------------------------

    def _section_job_summary(self) -> None:
        report = self._report
        cfg = report.config
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_DARK)
        self.cell(0, 7, "Job Summary", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

        kv_pairs = [
            ("Generated", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
            ("GeoServer URL", report.geoserver_url or "N/A"),
            ("GeoServer Version", report.geoserver_version or "N/A"),
            ("Username", report.username or "N/A"),
            ("Workspace", cfg.workspace),
            ("Datastore", cfg.datastore),
            ("Source Directory", str(cfg.source_directory)),
            ("Naming Strategy", cfg.naming.value),
            ("Dry Run", "Yes" if cfg.dry_run else "No"),
            ("Recurse", "Yes" if cfg.recurse else "No"),
            ("Concurrency", str(cfg.concurrency)),
            ("Wall Clock Time", _format_duration(report.wall_clock_seconds)),
        ]

        self.set_font("Helvetica", "", 9)
        col_label_w = 45
        col_value_w = 100
        for label, value in kv_pairs:
            self.set_text_color(*_GREY)
            self.cell(col_label_w, 6, label + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*_DARK)
            self.multi_cell(col_value_w, 6, str(value))

        if report.warnings:
            self.ln(2)
            self.set_font("Helvetica", "B", 9)
            self.set_text_color(*_RED)
            self.cell(
                0,
                6,
                f"Warnings ({len(report.warnings)}):",
                new_x=XPos.LMARGIN,
                new_y=YPos.NEXT,
            )
            self.set_font("Helvetica", "", 8)
            for w in report.warnings:
                self.set_text_color(*_RED)
                self.cell(5, 5, "-", new_x=XPos.RIGHT, new_y=YPos.TOP)
                self.set_text_color(*_DARK)
                self.multi_cell(0, 5, w)

        self.ln(4)

    # ------------------------------------------------------------------
    # Section: per-bundle detail table
    # ------------------------------------------------------------------

    def _table_header_row(self) -> None:
        """Render a single table header row."""
        self.set_fill_color(*_DARK)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 8)
        last_col = _TABLE_COLS[-1]
        for col in _TABLE_COLS:
            nx = XPos.LMARGIN if col == last_col else XPos.RIGHT
            ny = YPos.NEXT if col == last_col else YPos.TOP
            self.cell(_COL_WIDTHS[col], 6, col, border=1, fill=True, new_x=nx, new_y=ny)

    def _section_detail_table(self) -> None:
        if not self._report.results:
            return

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_DARK)
        self.cell(0, 7, "Bundle Detail", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

        self._table_header_row()

        self.set_font("Helvetica", "", 7)
        row_h = 5
        last_col = _TABLE_COLS[-1]

        for idx, result in enumerate(self._report.results, start=1):
            # Choose row background colour by status.
            status_upper = result.status.upper()
            if status_upper in ("SUCCESS", "OK"):
                bg = _SUCCESS_BG
            elif status_upper == "ERROR":
                bg = _ERROR_BG
            elif status_upper == "SKIPPED":
                bg = _SKIP_BG
            elif status_upper == "DRY_RUN":
                bg = _DRY_BG
            else:
                bg = _WHITE

            self.set_fill_color(*bg)
            self.set_text_color(*_DARK)

            # Check if a page break is needed; if so, add header again.
            if self.get_y() + row_h > self.h - self.b_margin - 2:
                self.add_page()
                self._table_header_row()
                self.set_font("Helvetica", "", 7)
                self.set_fill_color(*bg)
                self.set_text_color(*_DARK)

            cells = {
                "#": str(idx),
                "Layer Name": result.layer_name,
                "Source Path": Path(str(result.source_path)).name,
                "Action": result.action,
                "Status": result.status,
                "Size": _format_size(result.file_size),
                "Time": f"{result.upload_time:.2f}s",
                "Error": result.error or "",
            }
            for col in _TABLE_COLS:
                nx = XPos.LMARGIN if col == last_col else XPos.RIGHT
                ny = YPos.NEXT if col == last_col else YPos.TOP
                self.cell(
                    _COL_WIDTHS[col],
                    row_h,
                    cells[col],
                    border=1,
                    fill=True,
                    new_x=nx,
                    new_y=ny,
                )

        self.ln(4)

    # ------------------------------------------------------------------
    # Section: summary statistics
    # ------------------------------------------------------------------

    def _section_summary_stats(self) -> None:
        report = self._report
        summary = _compute_summary(report)

        self.set_font("Helvetica", "B", 11)
        self.set_text_color(*_DARK)
        self.cell(0, 7, "Summary Statistics", new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(2)

        upload_times = [r.upload_time for r in report.results if r.upload_time > 0]
        avg_time = sum(upload_times) / len(upload_times) if upload_times else 0.0
        min_time = min(upload_times) if upload_times else 0.0
        max_time = max(upload_times) if upload_times else 0.0

        stats = [
            ("Total Discovered", str(summary["total_bundles"])),
            ("Created", str(summary["created"])),
            ("Updated", str(summary["updated"])),
            ("Skipped / Dry-run", str(summary["skipped"])),
            ("Failed", str(summary["failed"])),
            ("Data Uploaded", _format_size(summary["total_uploaded_bytes"])),
            ("Wall Time", _format_duration(summary["wall_clock_seconds"])),
            ("Avg Upload Time", _format_duration(avg_time)),
            ("Min Upload Time", _format_duration(min_time)),
            ("Max Upload Time", _format_duration(max_time)),
        ]

        self.set_font("Helvetica", "", 9)
        col_label_w = 45
        col_value_w = 60
        for label, value in stats:
            self.set_text_color(*_GREY)
            self.cell(col_label_w, 6, label + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*_DARK)
            self.cell(col_value_w, 6, value, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.ln(4)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_GREY)
        self.cell(
            0,
            6,
            "Made with love by Kartoza  |  https://kartoza.com",
            align="C",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )


def generate_pdf_report(report: PublishReport, output_path: Path) -> None:
    """Write a branded PDF report to *output_path*.

    The PDF is A4 landscape and contains three sections:
    1. Job summary (key-value metadata).
    2. Per-bundle detail table (colour-coded by status).
    3. Aggregate summary statistics.

    Args:
        report: The completed publish report.
        output_path: Destination file path (parent will be created if needed).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _PublishPDF(report)
    pdf.build()
    pdf.output(str(output_path))
