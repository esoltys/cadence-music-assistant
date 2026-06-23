@in_order
Feature: Score Construction Canvas Management
  As a music composition assistant
  I want to initialize a canvas and append note tokens sequentially
  So that the localized score state file is correctly mutated

  Scenario: Initialize a blank canvas and add a note
    Given a clean canvas state
    When the user requests to initialize a blank canvas with time signature "4/4"
    Then the canvas should contain a blank note stream with signature "4/4"
    When the user requests to add note "C4" with duration "quarter"
    Then the canvas state file should contain a note token with pitch "C4" and duration "quarter"
