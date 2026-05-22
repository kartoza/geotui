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


def _detect_language() -> str:
    """Detect the best language from environment or system locale.

    Priority: GEOTUI_LANG env var > system locale > English fallback.

    Returns:
        Two-letter language code.
    """
    # Explicit override takes priority
    env_lang = os.environ.get("GEOTUI_LANG", "").strip()
    if env_lang:
        return env_lang[:2].lower()

    # Fall back to system locale
    import locale

    try:
        loc = locale.getlocale()[0] or ""
    except (ValueError, locale.Error):
        loc = ""
    if not loc:
        loc = os.environ.get("LANG", "")
    # Extract language code (e.g. "pt_BR.UTF-8" -> "pt")
    lang_code = loc.split("_")[0].split(".")[0].lower()
    if lang_code in SUPPORTED_LANGUAGES:
        return lang_code

    return "en"


# Initialize from env / system locale
set_language(_detect_language())
