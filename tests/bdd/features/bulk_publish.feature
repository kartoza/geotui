Feature: Bulk Shapefile Publishing
  As a GeoServer administrator
  I want to bulk publish shapefiles to GeoServer
  So that I can quickly set up large datasets

  Scenario: Discover shapefile bundles in a directory
    Given a directory with 3 complete shapefile bundles
    And 1 incomplete bundle missing .dbf
    When I run shapefile discovery
    Then 3 bundles should be found
    And 1 warning should be reported

  Scenario: Dry run validates without uploading
    Given a directory with shapefile bundles
    And a publish configuration with dry_run enabled
    When I run the publisher
    Then all results should have status DRY_RUN
    And no data should be uploaded to GeoServer

  Scenario: Name collision detection
    Given a directory with duplicate shapefile names in subdirectories
    When I resolve names with basename strategy
    Then a collision error should be raised
