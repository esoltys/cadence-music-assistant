---
name: synthesizing-acoustic-audio
description: Commits system mutations by compiling note sequences into concrete wav audio files on disk using the FluidR3_GM acoustic_grand_piano json database.
permission_tier: Action-Allowed
allowed-tools:
  - synthesize_score
---

# synthesizing-acoustic-audio

## Focus & Capabilities
This skill compiles note sequences from our score state file into actual acoustic WAV audio files:
- Synthesizing piano score note events using FluidSynth or simple waveform generator with a target SoundFont (FluidR3_GM piano).
- Exporting concrete WAV audio files on disk.

## Triggers
- "Synthesize the current score to audio."
- "Convert the active score notes into a piano wav file."
- "Render the score as audio."

## Non-Capabilities
- This skill does not modify note coordinates or time signatures.
- This skill does not visualize notations.
