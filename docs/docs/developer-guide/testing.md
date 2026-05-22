# Testing

## Approach

GeoTUI uses a combination of TDD (Test-Driven Development) and BDD (Behaviour-Driven Development) with a minimum coverage target of 80%.

## Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=geotui --cov-report=html

# Run only unit tests
pytest tests/unit/

# Run only BDD tests
pytest tests/bdd/

# Run a specific test
pytest tests/unit/test_app.py::TestGeoTUIApp::test_launch -v
```

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── test_app.py          # App launch and interaction tests
│   ├── test_client.py       # GeoServer client tests
│   ├── test_config.py       # Configuration and encryption tests
│   ├── test_i18n.py         # Internationalisation tests
│   ├── test_publisher.py    # Publisher tests
│   ├── test_report.py       # PDF report tests
│   └── test_theme.py        # Theme and colour tests
├── bdd/                     # BDD tests
│   ├── features/            # Gherkin feature files
│   └── step_defs/           # Step definitions
└── conftest.py              # Shared fixtures
```

## Writing Unit Tests

Use `pytest` with async support via `pytest-asyncio`. Textual provides `AppTest` for testing TUI interactions:

```python
import pytest
from textual.testing import AppTest
from geotui.app import GeoTUIApp


class TestMyFeature:
    @pytest.mark.asyncio
    async def test_feature_works(self) -> None:
        app = GeoTUIApp()
        async with AppTest.run_test(app) as pilot:
            # Interact with the app
            await pilot.press("f9")
            # Assert on app state
            assert pilot.app.screen.name == "settings"
```

## Writing BDD Tests

Feature files use Gherkin syntax in `tests/bdd/features/`:

```gherkin
Feature: Connection Management
  As a GeoServer administrator
  I want to manage my server connections
  So that I can work with multiple GeoServer instances

  Scenario: Add a new connection
    Given the application is running
    And the settings screen is open
    When I click the Add button
    And I fill in the connection details
    And I click Save
    Then the connection appears in the list
```

Step definitions go in `tests/bdd/step_defs/`:

```python
from pytest_bdd import given, when, then, scenario

@scenario("../features/connections.feature", "Add a new connection")
def test_add_connection():
    pass

@given("the application is running")
def app_running(app):
    assert app.is_running
```

## Testing the GeoServer Client

Use `httpx`'s mock transport or `respx` for mocking HTTP responses:

```python
import respx
from httpx import Response
from geotui.client import GeoServerClient

@respx.mock
async def test_list_workspaces():
    respx.get("https://example.com/geoserver/rest/workspaces").mock(
        return_value=Response(200, json={
            "workspaces": {"workspace": [{"name": "test"}]}
        })
    )
    client = GeoServerClient("https://example.com", "admin", "pass")
    workspaces = await client.list_workspaces()
    assert workspaces == [{"name": "test"}]
```

## Coverage

View the HTML coverage report after running tests with `--cov-report=html`:

```bash
pytest --cov=geotui --cov-report=html
open htmlcov/index.html
```

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
