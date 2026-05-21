Feature: Context-sensitive F2 Menu
  As a GeoServer administrator
  I want a context-sensitive menu that changes based on active pane
  So that I can quickly access relevant actions

  Scenario: F2 shows GeoServer actions when right pane is active
    Given the application is running
    And the right pane is active
    When I press F2
    Then I should see the GeoServer Actions menu
    And the menu should contain "Create Workspace"
    And the menu should contain "Create Store"
    And the menu should contain "Refresh Tree"

  Scenario: F2 shows File actions when left pane is active
    Given the application is running
    And the left pane is active
    When I press F2
    Then I should see the File Actions menu

  Scenario: Escape closes the menu
    Given the application is running
    When I press F2
    Then I should see a menu
    When I press Escape
    Then the menu should be closed

  Scenario: Create workspace requires active connection
    Given the application is running with no connections
    And the right pane is active
    When I try to create a workspace
    Then I should see a warning about no connection
