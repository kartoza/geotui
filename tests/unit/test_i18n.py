"""Tests for internationalization support."""

from geotui.i18n import (
    SUPPORTED_LANGUAGES,
    _,
    cycle_language,
    get_current_language,
    set_language,
)


class TestI18n:
    """Test suite for i18n functionality."""

    def test_default_language_is_english(self) -> None:
        """Test that English is the default language."""
        set_language("en")
        assert get_current_language() == "en"

    def test_supported_languages(self) -> None:
        """Test that all required languages are supported."""
        assert "en" in SUPPORTED_LANGUAGES
        assert "pt" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES

    def test_set_language_english(self) -> None:
        """Test setting language to English."""
        set_language("en")
        assert get_current_language() == "en"

    def test_set_language_portuguese(self) -> None:
        """Test setting language to Portuguese."""
        set_language("pt")
        assert get_current_language() == "pt"
        set_language("en")

    def test_set_language_spanish(self) -> None:
        """Test setting language to Spanish."""
        set_language("es")
        assert get_current_language() == "es"
        set_language("en")

    def test_invalid_language_falls_back(self) -> None:
        """Test that invalid language codes fall back to English."""
        set_language("xx")
        assert get_current_language() == "en"

    def test_cycle_language(self) -> None:
        """Test cycling through languages."""
        set_language("en")
        cycle_language()
        assert get_current_language() == "pt"
        cycle_language()
        assert get_current_language() == "es"
        cycle_language()
        assert get_current_language() == "en"

    def test_english_translation_passthrough(self) -> None:
        """Test that English returns the original string."""
        set_language("en")
        assert _("Quit") == "Quit"
        assert _("Help") == "Help"

    def test_three_languages_exist(self) -> None:
        """Test that exactly 3 languages are supported."""
        assert len(SUPPORTED_LANGUAGES) == 3
