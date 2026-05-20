"""Internationalization support for GeoTUI.

Supports English (default), Portuguese, and Spanish with runtime switching.
"""

import gettext
import os
from pathlib import Path

SUPPORTED_LANGUAGES = {
    "en": "English",
    "pt": "Portuguese",
    "es": "Spanish",
}

_LOCALE_DIR = Path(__file__).parent / "locales"
_current_language = "en"
_translations: gettext.GNUTranslations | gettext.NullTranslations = (
    gettext.NullTranslations()
)


def set_language(lang: str) -> None:
    """Set the active language.

    Args:
        lang: Language code (en, pt, es).
    """
    global _current_language, _translations

    if lang not in SUPPORTED_LANGUAGES:
        lang = "en"

    _current_language = lang

    if lang == "en":
        _translations = gettext.NullTranslations()
    else:
        try:
            _translations = gettext.translation(
                "geotui",
                localedir=str(_LOCALE_DIR),
                languages=[lang],
            )
        except FileNotFoundError:
            _translations = gettext.NullTranslations()


def get_current_language() -> str:
    """Get the current language code.

    Returns:
        Current language code.
    """
    return _current_language


def cycle_language() -> str:
    """Cycle to the next available language.

    Returns:
        New language code.
    """
    langs = list(SUPPORTED_LANGUAGES.keys())
    idx = langs.index(_current_language)
    next_lang = langs[(idx + 1) % len(langs)]
    set_language(next_lang)
    return next_lang


def _(message: str) -> str:
    """Translate a message string.

    Args:
        message: The message to translate.

    Returns:
        Translated message string.
    """
    return _translations.gettext(message)


# Initialize from environment or default
_env_lang = os.environ.get("GEOTUI_LANG", "en")[:2].lower()
set_language(_env_lang)
