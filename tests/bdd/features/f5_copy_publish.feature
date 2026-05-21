Feature: F5 Copy to Publish
  As a GeoServer administrator
  I want to press F5 to copy spatial files from my local folder
  to a GeoServer workspace
  So that I can publish data using the familiar MC workflow

  Scenario: F5 with no connection shows error
    Given the application is running with no connections
    When I press F5
    Then I should see an error about connecting first

  Scenario: F5 discovers multiple formats
    Given a folder with shapefiles, GeoPackage, and GeoTIFF files
    When I run spatial file discovery
    Then groups for shapefile, geopackage, and geotiff are found

  Scenario: F5 auto-creates stores per format
    Given a connected GeoServer instance
    And a folder with shapefiles and GeoTIFF files
    When I press F5 with a workspace selected
    Then a shapefile store and a GeoTIFF store are created

  Scenario: Bulk Publish removed from F2 menu
    Given the application is running with a connection
    When I open the F2 GeoServer menu
    Then Bulk Publish Shapefiles should not be listed
