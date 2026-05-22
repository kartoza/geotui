Feature: Multi-Connection Tree
  As a GeoServer administrator
  I want to see all my GeoServer connections in one tree
  So that I can manage multiple servers from one interface

  Scenario: All connections shown on startup
    Given I have 3 saved GeoServer connections
    When the application starts
    Then I should see 3 connection nodes in the tree

  Scenario: Expanding connection triggers lazy load
    Given I have a saved GeoServer connection
    When I expand the connection node
    Then a connection attempt is made
    And workspaces appear if successful

  Scenario: Failed connection shown in red
    Given I have a connection to an unreachable server
    When I expand the connection node
    Then the node should be shown in red
    And an error message should appear as a child node

  Scenario: R key retries failed connection
    Given I have a failed connection node
    When I press R on the failed node
    Then a new connection attempt is made

  Scenario: F5 targets highlighted connection
    Given I have two connected GeoServer instances
    And I am highlighting a workspace in the second connection
    When I press F5
    Then files are published to the second connection

  Scenario: No connections shows help message
    Given I have no saved connections
    When the application starts
    Then I should see a message about configuring connections
