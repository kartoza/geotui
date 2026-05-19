"""Shared test configuration and fixtures."""

import pytest


@pytest.fixture(autouse=True)
def reset_i18n():
    """Reset language to English before each test."""
    from geotui.i18n import set_language

    set_language("en")
    yield
    set_language("en")
