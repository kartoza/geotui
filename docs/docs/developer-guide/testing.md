# Testing

## Approach

GeoTUI uses a combination of TDD (Test-Driven Development) and BDD (Behavior-Driven Development) with a minimum coverage target of 80%.

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
```

## Test Structure

```
tests/
    unit/              # Unit tests
        test_app.py    # App launch and interaction tests
        test_i18n.py   # Internationalization tests
        test_theme.py  # Theme and color tests
    bdd/               # BDD tests
        features/      # Gherkin feature files
        step_defs/     # Step definitions
```

## Writing Tests

### Unit Tests

```python
class TestMyFeature:
    @pytest.mark.asyncio
    async def test_feature_works(self) -> None:
        app = GeoTUIApp()
        async with AppTest.run_test(app) as pilot:
            # Test interactions
            assert pilot.app.title == "GeoTUI"
```

### BDD Features

```gherkin
Feature: My Feature
  Scenario: Something happens
    Given the application is running
    When I do something
    Then I see the result
```

---

Made with :heart: by [Kartoza](https://kartoza.com) | [Donate!](https://github.com/sponsors/kartoza) | [GitHub](https://github.com/kartoza/geotui)
