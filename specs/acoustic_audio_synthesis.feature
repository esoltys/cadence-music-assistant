@in_order @action_allowed
Feature: Acoustic Audio Synthesis Pipeline
  As a music composition assistant
  I want to compile my active score notes into a concrete piano wav file
  So that I can listen to my compositions

  Scenario: Generate a piano WAV audio export from active score state
    Given an active score state at "skills/score_construction/assets/score_{session_id}.json"
    When the user requests to synthesize the score to a piano WAV file
    Then the agent should call the audio synthesis tool
    And the response should confirm the output audio target path "skills/acoustic_audio_synthesis/assets/score_{session_id}.wav"
