"""BDD step definitions for dual pane navigation.

Since Textual's run_test() is an async context manager, we test BDD scenarios
as self-contained async tests that verify the full scenario inline.
"""

import pytest

from geotui.app import GeoTUIApp
from geotui.widgets.dual_pane import DualPane


class TestDualPaneBDD:
    """BDD-style tests for dual pane navigation scenarios."""

    @pytest.mark.asyncio
    async def test_application_starts_with_left_pane_active(self) -> None:
        """Scenario: Application starts with left pane active.

        Given the application is running
        Then the left pane should be active
        And the right pane should be inactive
        """
        async with GeoTUIApp().run_test() as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            assert dual_pane.active_pane == "left"
            assert dual_pane.active_pane != "right"

    @pytest.mark.asyncio
    async def test_switch_panes_with_tab_key(self) -> None:
        """Scenario: Switch panes with Tab key.

        Given the application is running
        And the left pane is active
        When I press the Tab key
        Then the right pane should be active
        And the left pane should be inactive
        """
        async with GeoTUIApp().run_test() as pilot:
            dual_pane = pilot.app.query_one(DualPane)
            assert dual_pane.active_pane == "left"
            pilot.app.action_switch_pane()
            await pilot.pause()
            assert dual_pane.active_pane == "right"
            assert dual_pane.active_pane != "left"

    @pytest.mark.asyncio
    async def test_application_displays_header_and_footer(self) -> None:
        """Scenario: Application displays header and footer.

        Given the application is running
        Then I should see a header with "GeoTUI"
        And I should see a footer with function key bindings
        """
        async with GeoTUIApp().run_test() as pilot:
            from textual.widgets import Footer

            assert pilot.app.title == "GeoTUI"
            footer = pilot.app.query_one(Footer)
            assert footer is not None
