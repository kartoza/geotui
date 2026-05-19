"""BDD step definitions for dual pane navigation."""

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from geotui.app import GeoTUIApp
from geotui.widgets.dual_pane import DualPane

scenarios("../features/dual_pane.feature")


@pytest.fixture
def app():
    """Create app fixture."""
    return GeoTUIApp()


@given("the application is running", target_fixture="running_app")
@pytest.mark.asyncio
async def app_is_running(app):
    """Start the application."""
    async with app.run_test() as pilot:
        yield pilot


@given("the left pane is active")
def left_pane_active(running_app):
    """Ensure left pane is active."""
    dual_pane = running_app.app.query_one(DualPane)
    dual_pane.active_pane = "left"


@when("I press the Tab key")
@pytest.mark.asyncio
async def press_tab(running_app):
    """Press the Tab key."""
    await running_app.press("tab")


@then("the left pane should be active")
def check_left_active(running_app):
    """Verify left pane is active."""
    dual_pane = running_app.app.query_one(DualPane)
    assert dual_pane.active_pane == "left"


@then("the right pane should be active")
def check_right_active(running_app):
    """Verify right pane is active."""
    dual_pane = running_app.app.query_one(DualPane)
    assert dual_pane.active_pane == "right"


@then("the left pane should be inactive")
def check_left_inactive(running_app):
    """Verify left pane is inactive."""
    dual_pane = running_app.app.query_one(DualPane)
    assert dual_pane.active_pane != "left"


@then("the right pane should be inactive")
def check_right_inactive(running_app):
    """Verify right pane is inactive."""
    dual_pane = running_app.app.query_one(DualPane)
    assert dual_pane.active_pane != "right"


@then(parsers.parse('I should see a header with "{text}"'))
def check_header(running_app, text):
    """Verify header contains text."""
    assert running_app.app.title == text


@then("I should see a footer with function key bindings")
def check_footer(running_app):
    """Verify footer exists."""
    from textual.widgets import Footer

    footer = running_app.app.query_one(Footer)
    assert footer is not None
