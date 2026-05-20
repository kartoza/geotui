Feature: Publish Report Generation
  As a GeoServer administrator
  I want a detailed PDF report after publishing
  So that I have an audit trail of what was uploaded

  Scenario: PDF report is generated after publish
    Given a completed publish run with results
    When I generate the PDF report
    Then a PDF file should be created
    And it should contain the job summary
    And it should contain the file detail table

  Scenario: JSON report contains same data as PDF
    Given a completed publish run with results
    When I generate the JSON report
    Then the JSON should contain all bundle results
    And the JSON should contain summary statistics
