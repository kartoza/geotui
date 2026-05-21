Feature: Store Creation
  As a GeoServer administrator
  I want to create different types of data stores
  So that I can manage geospatial data sources

  Scenario: Create workspace form appears with name field
    Given a connected GeoServer instance
    When I open the create workspace form
    Then I should see a name input field
    And the action panel should be visible

  Scenario: Store type selector shows all supported types
    Given a connected GeoServer instance
    And a workspace is selected in the tree
    When I open the create store form
    Then I should see the store type selector
    And the selector should list vector store types
    And the selector should list raster store types
    And the selector should list WMS store type

  Scenario: PostGIS store form has database fields
    Given a connected GeoServer instance
    When I select PostGIS as the store type
    Then I should see fields for host, port, database, user, password

  Scenario: Cancel hides the action panel
    Given a connected GeoServer instance
    And the action panel is visible
    When I cancel the action
    Then the action panel should be hidden
