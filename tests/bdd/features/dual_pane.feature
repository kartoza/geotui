Feature: Dual Pane Navigation
  As a geospatial server administrator
  I want a Midnight Commander-style dual pane interface
  So that I can efficiently manage files and resources

  Scenario: Application starts with left pane active
    Given the application is running
    Then the left pane should be active
    And the right pane should be inactive

  Scenario: Switch panes with Tab key
    Given the application is running
    And the left pane is active
    When I press the Tab key
    Then the right pane should be active
    And the left pane should be inactive

  Scenario: Application displays header and footer
    Given the application is running
    Then I should see a header with "GeoTUI"
    And I should see a footer with function key bindings
