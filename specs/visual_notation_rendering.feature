Feature: Visual Notation Rendering Pipeline
  As a music assistant user
  I want to visualize my current score canvas
  So that I can see the graphical representation of the notes

  @any_order
  Scenario: Render active score canvas to a visual plot
    Given an active score canvas state at "skills/score_construction/assets/canvas_state.json"
    When the user requests to render the active score notation
    Then the agent should call the notation rendering tool
    And the response should contain the piano roll image path "skills/visual_notation_rendering/assets/piano_roll.png"
    And the response should contain the MusicXML path "skills/visual_notation_rendering/assets/score.musicxml"
