@in_order
Feature: Score Construction Score Management
  As a music composition assistant
  I want to initialize a score and append note tokens sequentially
  So that the localized score state file is correctly mutated

  Scenario: Initialize a blank score and add a note
    Given a clean score state
    When the user requests to initialize a blank score with time signature "4/4"
    Then the score should contain a blank note stream with signature "4/4"
    When the user requests to add note "C4" with duration "quarter"
    Then the score state file should contain a note token with pitch "C4" and duration "quarter"
