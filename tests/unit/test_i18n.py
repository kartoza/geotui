"""Tests for internationalization support."""

from unittest.mock import patch

from geotui.i18n import (
    SUPPORTED_LANGUAGES,
    _,
    _detect_language,
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

    def test_detect_language_from_geotui_lang(self) -> None:
        """Test GEOTUI_LANG env var takes priority."""
        with patch.dict("os.environ", {"GEOTUI_LANG": "es"}):
            assert _detect_language() == "es"

    def test_detect_language_from_system_locale(self) -> None:
        """Test system locale detection when GEOTUI_LANG is unset."""
        with patch.dict("os.environ", {"GEOTUI_LANG": "", "LANG": "pt_BR.UTF-8"}):
            with patch("locale.getlocale", return_value=("pt_BR", "UTF-8")):
                assert _detect_language() == "pt"

    def test_detect_language_falls_back_to_english(self) -> None:
        """Test fallback to English for unsupported locale."""
        with patch.dict("os.environ", {"GEOTUI_LANG": "", "LANG": "zh_CN.UTF-8"}):
            with patch("locale.getlocale", return_value=("zh_CN", "UTF-8")):
                assert _detect_language() == "en"

    def test_detect_language_handles_empty_locale(self) -> None:
        """Test fallback when no locale is set."""
        with patch.dict("os.environ", {"GEOTUI_LANG": "", "LANG": ""}, clear=False):
            with patch("locale.getlocale", return_value=(None, None)):
                assert _detect_language() == "en"

    def test_translations_load_spanish(self) -> None:
        """Test that Spanish translations actually load from .mo files."""
        set_language("es")
        assert _("Help") == "Ayuda"
        assert _("Quit") == "Salir"
        set_language("en")

    def test_translations_load_portuguese(self) -> None:
        """Test that Portuguese translations actually load from .mo files."""
        set_language("pt")
        assert _("Help") == "Ajuda"
        assert _("Quit") == "Sair"
        set_language("en")
