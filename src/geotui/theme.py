"""Kartoza brand theme for GeoTUI."""

from textual.design import ColorSystem

KARTOZA_COLORS = {
    "highlight1": "#DF9E2F",  # yellow/orange
    "highlight2": "#569FC6",  # blue
    "highlight3": "#8A8B8B",  # grey
    "highlight4": "#06969A",  # teal
    "alert": "#CC0403",  # red
}

KARTOZA_DARK = ColorSystem(
    primary=KARTOZA_COLORS["highlight2"],
    secondary=KARTOZA_COLORS["highlight4"],
    warning=KARTOZA_COLORS["highlight1"],
    error=KARTOZA_COLORS["alert"],
    accent=KARTOZA_COLORS["highlight1"],
    background="#1a1a2e",
    surface="#16213e",
    panel="#0f3460",
    boost="#1a1a2e",
    dark=True,
)

KARTOZA_LIGHT = ColorSystem(
    primary=KARTOZA_COLORS["highlight2"],
    secondary=KARTOZA_COLORS["highlight4"],
    warning=KARTOZA_COLORS["highlight1"],
    error=KARTOZA_COLORS["alert"],
    accent=KARTOZA_COLORS["highlight1"],
    background="#f5f5f5",
    surface="#ffffff",
    panel="#e8e8e8",
    boost="#f5f5f5",
    dark=False,
)
