"""Shared test configuration and fixtures."""

import pytest

from geotui.config import Connection


@pytest.fixture(autouse=True)
def reset_i18n():
    """Reset language to English before each test."""
    from geotui.i18n import set_language

    set_language("en")
    yield
    set_language("en")


@pytest.fixture
def unreachable_conn() -> Connection:
    """Return a Connection pointing at an unreachable address for isolation."""
    return Connection(
        name="Test",
        url="https://192.0.2.1:9999",
        username="admin",
        password="pass",
    )
