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

# Status pill colours
_STATUS_PILL = {
    "OK": _TEAL,
    "SUCCESS": _TEAL,
    "ERROR": _RED,
    "SKIPPED": _GREY,
    "DRY_RUN": _BLUE,
}

# Table alternating row colours
_ROW_EVEN = (0xFF, 0xFF, 0xFF)
_ROW_ODD = (0xF0, 0xF7, 0xFC)

# Warning box colours
_WARNING_BG = (0xFF, 0xEB, 0xEE)
_WARNING_BORDER = _RED

# Teal accent block background
_TEAL_LIGHT_BG = (0xE0, 0xF7, 0xF8)

# Table border colour
_TABLE_BORDER = (0xE0, 0xE0, 0xE0)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _shorten_error(error: str) -> str:
    """Shorten an error message to a brief summary for the table.

    Full details are in the warnings section above the table.

    Args:
        error: Full error message.

    Returns:
        Short summary like "Missing (shx)" or "HTTP 500".
    """
    if not error:
        return ""
    low = error.lower()
    if "missing" in low:
        # Extract what's missing from "Incomplete bundle ... missing .shx, .dbf"
        if "missing" in error:
            parts = error.split("missing")[-1].strip().rstrip(".")
            return f"Missing ({parts})"
    if "http" in low:
        # "HTTP 500: java.io.IOException" -> "HTTP 500"
        for word in error.split():
            if word.isdigit() and len(word) == 3:
                return f"HTTP {word}"
    if "timeout" in low:
        return "Timeout"
    if "connect" in low:
        return "Connect err"
    if "auth" in low:
        return "Auth failed"
    # Fallback: first 15 chars
    return error[:15]


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

# Column widths for the detail table (mm).  Total ~190mm fits A4 landscape.
_COL_WIDTHS = {
    "#": 8,
    "Layer Name": 40,
    "Source": 42,
    "Action": 16,
    "Status": 18,
    "Size": 16,
    "Time": 14,
    "Error": 36,
}
_TABLE_COLS = list(_COL_WIDTHS.keys())

# Logo path (relative to package)
_LOGO_PATH = (
    Path(__file__).resolve().parent.parent.parent / "resources" / "kartoza-logo.png"
)

# Header bar height
_HEADER_H = 22


class _PublishPDF(FPDF):
    """Custom FPDF subclass that renders the branded publish report."""

    def __init__(self, report: PublishReport) -> None:
        super().__init__(orientation="L", unit="mm", format="A4")
        self._report = report
        self.set_auto_page_break(auto=True, margin=15)
        self.set_margins(10, 10, 10)
        self.add_page()

    # ------------------------------------------------------------------
    # FPDF hooks
    # ------------------------------------------------------------------

    def header(self) -> None:
        # Dark navy background bar
        self.set_fill_color(*_DARK)
        self.rect(0, 0, self.w, _HEADER_H, style="F")

        # Kartoza logo (left side)
        if _LOGO_PATH.exists():
            self.image(str(_LOGO_PATH), x=10, y=3, h=15)

        # Title in amber, centred
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(*_AMBER)
        title = "GeoTUI Bulk Publish Report"
        title_w = self.get_string_width(title)
        self.set_xy((self.w - title_w) / 2, 5)
        self.cell(title_w, 10, title, new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Version in blue (right side, top)
        self.set_font("Helvetica", "", 9)
        self.set_text_color(*_BLUE)
        version_text = f"v{__version__}"
        self.set_xy(self.w - 40, 4)
        self.cell(30, 5, version_text, align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # kartoza.com in amber italic (right side, below version)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(*_AMBER)
        self.set_xy(self.w - 40, 10)
        self.cell(30, 5, "kartoza.com", align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)

        # Thin amber line under the header bar
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.3)
        self.line(0, _HEADER_H, self.w, _HEADER_H)

        # Move below header
        self.set_y(_HEADER_H + 4)

    def footer(self) -> None:
        self.set_y(-12)
        # Thin grey separator line
        self.set_draw_color(*_GREY)
        self.set_line_width(0.2)
        y_line = self.get_y() - 1
        self.line(self.l_margin, y_line, self.w - self.r_margin, y_line)

        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_GREY)

        # Left: version
        self.cell(
            80,
            8,
            f"GeoTUI v{__version__}",
            align="L",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        # Centre: branding
        self.cell(
            0,
            8,
            "Made with love by Kartoza | kartoza.com",
            align="C",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )
        # Right: page number
        self.set_xy(self.w - 50, self.get_y())
        page_text = f"Page {self.page_no()}/{{nb}}"
        self.cell(40, 8, page_text, align="R", new_x=XPos.RIGHT, new_y=YPos.TOP)

    # ------------------------------------------------------------------
    # Public build entry-point
    # ------------------------------------------------------------------

    def build(self) -> None:
        """Render all report sections."""
        self.alias_nb_pages()
        self._section_job_summary()
        self._section_warnings()
        self._section_detail_table()
        self._section_summary_stats()

    # ------------------------------------------------------------------
    # Section heading helper
    # ------------------------------------------------------------------

    def _section_heading(self, title: str) -> None:
        """Render a section heading with amber underline."""
        self.set_font("Helvetica", "B", 12)
        self.set_text_color(*_DARK)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(*_AMBER)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(3)

    # ------------------------------------------------------------------
    # Section: job summary key-value pairs
    # ------------------------------------------------------------------

    def _section_job_summary(self) -> None:
        report = self._report
        cfg = report.config
        self._section_heading("Job Summary")

        kv_pairs = [
            ("Generated", datetime.now(tz=timezone.utc).strftime("%Y-%m-%d %H:%M UTC")),
            ("GeoServer URL", report.geoserver_url or "N/A"),
            ("Version", report.geoserver_version or "N/A"),
            ("Username", report.username or "N/A"),
            ("Workspace", cfg.workspace),
            ("Source Directory", str(cfg.source_directory)),
            ("Naming Strategy", cfg.naming.value),
            ("Concurrency", str(cfg.concurrency)),
            ("Dry Run", "Yes" if cfg.dry_run else "No"),
        ]

        # Save position for teal accent border
        block_x = self.l_margin
        block_y = self.get_y()

        # Render key-value pairs with teal left accent
        self.set_x(block_x + 4)  # Indent for teal border
        col_label_w = 42
        col_value_w = 100

        self.set_font("Helvetica", "", 9)
        for label, value in kv_pairs:
            self.set_x(block_x + 4)
            self.set_text_color(*_GREY)
            self.cell(col_label_w, 5.5, label + ":", new_x=XPos.RIGHT, new_y=YPos.TOP)
            self.set_text_color(*_DARK)
            self.multi_cell(col_value_w, 5.5, str(value))

        block_end_y = self.get_y()

        # Draw teal left accent border and light background
        self.set_fill_color(*_TEAL_LIGHT_BG)
        self.rect(block_x, block_y, 2, block_end_y - block_y, style="F")

        self.ln(4)

    # ------------------------------------------------------------------
    # Section: warnings
    # ------------------------------------------------------------------

    def _section_warnings(self) -> None:
        report = self._report
        if not report.warnings:
            return

        # Red alert box
        box_x = self.l_margin
        box_y = self.get_y()
        box_w = self.w - self.l_margin - self.r_margin

        # Calculate box height first
        self.set_font("Helvetica", "", 8)
        line_h = 5
        header_h = 7
        content_h = header_h + len(report.warnings) * line_h + 3
        box_h = content_h

        # Check page break
        if self.get_y() + box_h > self.h - self.b_margin:
            self.add_page()
            box_y = self.get_y()

        # Draw light red background
        self.set_fill_color(*_WARNING_BG)
        self.rect(box_x, box_y, box_w, box_h, style="F")

        # Draw thin red border
        self.set_draw_color(*_WARNING_BORDER)
        self.set_line_width(0.3)
        self.rect(box_x, box_y, box_w, box_h, style="D")

        # Warning header
        self.set_xy(box_x + 3, box_y + 1)
        self.set_font("Helvetica", "B", 9)
        self.set_text_color(*_RED)
        self.cell(
            0,
            header_h,
            f"  !   Warnings ({len(report.warnings)})",
            new_x=XPos.LMARGIN,
            new_y=YPos.NEXT,
        )

        # Warning text lines
        self.set_font("Helvetica", "", 8)
        self.set_text_color(*_DARK)
        for w in report.warnings:
            self.set_x(box_x + 10)
            self.cell(0, line_h, w, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

        self.set_y(box_y + box_h + 4)

    # ------------------------------------------------------------------
    # Section: per-bundle detail table
    # ------------------------------------------------------------------

    def _table_header_row(self) -> None:
        """Render a single table header row."""
        self.set_fill_color(*_WHITE)
        self.set_text_color(*_DARK)
        self.set_draw_color(*_TABLE_BORDER)
        self.set_line_width(0.2)
        self.set_font("Helvetica", "B", 8)
        last_col = _TABLE_COLS[-1]
        for col in _TABLE_COLS:
            nx = XPos.LMARGIN if col == last_col else XPos.RIGHT
            ny = YPos.NEXT if col == last_col else YPos.TOP
            self.cell(
                _COL_WIDTHS[col],
                6,
                col,
                border=1,
                fill=True,
                align="C",
                new_x=nx,
                new_y=ny,
            )

    def _status_pill(self, status: str, w: float, h: float) -> None:
        """Render a coloured status pill/badge."""
        status_upper = status.upper()
        pill_color = _STATUS_PILL.get(status_upper, _GREY)

        # Draw pill background
        self.set_fill_color(*pill_color)
        self.set_text_color(*_WHITE)
        self.set_font("Helvetica", "B", 7)
        self.cell(
            w,
            h,
            status,
            border=0,
            fill=True,
            align="C",
            new_x=XPos.RIGHT,
            new_y=YPos.TOP,
        )

    def _section_detail_table(self) -> None:
        if not self._report.results:
            return

        self._section_heading("File Details")
        self._table_header_row()

        row_h = 6
        last_col = _TABLE_COLS[-1]

        for idx, result in enumerate(self._report.results, start=1):
            # Alternating row background
            bg = _ROW_EVEN if idx % 2 == 0 else _ROW_ODD

            # Check if a page break is needed; if so, add header again.
            if self.get_y() + row_h > self.h - self.b_margin - 2:
                self.add_page()
                self._table_header_row()

            self.set_fill_color(*bg)
            self.set_draw_color(*_TABLE_BORDER)
            self.set_line_width(0.2)
            self.set_text_color(*_DARK)
            self.set_font("Helvetica", "", 7)

            cells = {
                "#": str(idx),
                "Layer Name": result.layer_name,
                "Source": Path(str(result.source_path)).name,
                "Action": result.action,
                "Status": result.status,
                "Size": _format_size(result.file_size),
                "Time": f"{result.upload_time:.2f}s",
                "Error": _shorten_error(result.error) if result.error else "",
            }

            for col in _TABLE_COLS:
                nx = XPos.LMARGIN if col == last_col else XPos.RIGHT
                ny = YPos.NEXT if col == last_col else YPos.TOP

                if col == "Status":
                    # Save position and draw bordered cell background first
                    cx = self.get_x()
                    cy = self.get_y()
                    # Draw cell border with row background
                    self.set_fill_color(*bg)
                    self.rect(cx, cy, _COL_WIDTHS[col], row_h, style="FD")
                    # Draw status pill centred within the cell
                    pill_w = _COL_WIDTHS[col] - 2
                    pill_x = cx + 1
                    pill_y = cy + 0.5
                    self.set_xy(pill_x, pill_y)
                    self._status_pill(cells[col], pill_w, row_h - 1)
                    # Reset position for next column
                    self.set_xy(cx + _COL_WIDTHS[col], cy)
                    # Restore text colour and font for subsequent cells
                    self.set_text_color(*_DARK)
                    self.set_font("Helvetica", "", 7)
                    self.set_fill_color(*bg)
                else:
                    self.cell(
                        _COL_WIDTHS[col],
                        row_h,
                        cells[col],
                        border=1,
                        fill=True,
                        new_x=nx,
                        new_y=ny,
                    )

        self.ln(5)

    # ------------------------------------------------------------------
    # Section: summary statistics
    # ------------------------------------------------------------------

    def _section_summary_stats(self) -> None:
        report = self._report
        summary = _compute_summary(report)

        # Check page break - need about 70mm
        if self.get_y() + 70 > self.h - self.b_margin:
            self.add_page()

        self._section_heading("Summary Statistics")

        upload_times = [r.upload_time for r in report.results if r.upload_time > 0]
        avg_time = sum(upload_times) / len(upload_times) if upload_times else 0.0
        min_time = min(upload_times) if upload_times else 0.0
        max_time = max(upload_times) if upload_times else 0.0

        stats = [
            ("Total Bundles", str(summary["total_bundles"]), False),
            ("Created", str(summary["created"]), False),
            ("Updated", str(summary["updated"]), False),
            ("Skipped / Dry-run", str(summary["skipped"]), False),
            ("Failed", str(summary["failed"]), summary["failed"] > 0),
            ("Data Uploaded", _format_size(summary["total_uploaded_bytes"]), False),
            ("Wall Time", _format_duration(summary["wall_clock_seconds"]), False),
            ("Avg Upload Time", _format_duration(avg_time), False),
            ("Min Upload Time", _format_duration(min_time), False),
            ("Max Upload Time", _format_duration(max_time), False),
        ]

        # Render in a 2x5 grid
        block_x = self.l_margin
        block_y = self.get_y()

        col_label_w = 42
        col_value_w = 30
        pair_w = col_label_w + col_value_w
        line_h = 6
        rows_per_col = 5

        self.set_font("Helvetica", "", 9)
        for i, (label, value, is_red) in enumerate(stats):
            col = i // rows_per_col
            row = i % rows_per_col
            x = block_x + 4 + col * (pair_w + 10)
            y = block_y + row * line_h

            self.set_xy(x, y)
            self.set_text_color(*_GREY)
            self.cell(
                col_label_w,
                line_h,
                label + ":",
                new_x=XPos.RIGHT,
                new_y=YPos.TOP,
            )

            if is_red:
                self.set_text_color(*_RED)
                self.set_font("Helvetica", "B", 9)
            else:
                self.set_text_color(*_DARK)
                self.set_font("Helvetica", "", 9)
            self.cell(col_value_w, line_h, value, new_x=XPos.RIGHT, new_y=YPos.TOP)

        block_end_y = block_y + rows_per_col * line_h

        # Draw teal left accent
        self.set_fill_color(*_TEAL_LIGHT_BG)
        self.rect(block_x, block_y, 2, block_end_y - block_y, style="F")

        self.set_y(block_end_y + 6)

        # Branding line at bottom of content
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

    The PDF is A4 landscape and contains four sections:
    1. Job summary (key-value metadata).
    2. Warnings (if any).
    3. Per-bundle detail table (colour-coded status pills).
    4. Aggregate summary statistics.

    Args:
        report: The completed publish report.
        output_path: Destination file path (parent will be created if needed).
    """
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf = _PublishPDF(report)
    pdf.build()
    pdf.output(str(output_path))
