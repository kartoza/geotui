"""Tests for Kartoza theme."""

from geotui.theme import KARTOZA_COLORS, KARTOZA_DARK, KARTOZA_LIGHT


class TestKartozaTheme:
    """Test suite for Kartoza brand theme."""

    def test_kartoza_colors_defined(self) -> None:
        """Test all Kartoza brand colors are defined."""
        assert "highlight1" in KARTOZA_COLORS
        assert "highlight2" in KARTOZA_COLORS
        assert "highlight3" in KARTOZA_COLORS
        assert "highlight4" in KARTOZA_COLORS
        assert "alert" in KARTOZA_COLORS

    def test_highlight1_is_yellow_orange(self) -> None:
        """Test highlight1 matches Kartoza yellow/orange."""
        assert KARTOZA_COLORS["highlight1"] == "#DF9E2F"

    def test_highlight2_is_blue(self) -> None:
        """Test highlight2 matches Kartoza blue."""
        assert KARTOZA_COLORS["highlight2"] == "#569FC6"

    def test_highlight4_is_teal(self) -> None:
        """Test highlight4 matches Kartoza teal."""
        assert KARTOZA_COLORS["highlight4"] == "#06969A"

    def test_alert_is_red(self) -> None:
        """Test alert matches Kartoza red."""
        assert KARTOZA_COLORS["alert"] == "#CC0403"

    def test_dark_theme_exists(self) -> None:
        """Test dark theme color system is defined."""
        assert KARTOZA_DARK is not None
        assert KARTOZA_DARK.dark is True

    def test_light_theme_exists(self) -> None:
        """Test light theme color system is defined."""
        assert KARTOZA_LIGHT is not None
        assert KARTOZA_LIGHT.dark is False
