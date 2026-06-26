---
name: building-symbolic-scores
description: Manages step-by-step state manipulation of a localized structural JSON file tracking active note/rest token streams.
permission_tier: Draft-Only
allowed-tools:
  - score_manager
---

# building-symbolic-scores

## Focus & Capabilities
This skill manages the sequential creation and mutation of a symbolic musical score. It represents notes, durations, and rests inside a localized JSON structural file representing the score state.
- Initializing a blank score with specific time and key signatures.
- Appending note tokens (pitch and duration) to the active score stream.
- Modifying or clearing elements of the score.

## Triggers
This skill is triggered when the user requests to build, modify, or add notes to a score, including:
- "Initialize a blank 4/4 score."
- "Add a quarter note C4 to the score."
- "Write a scale/melody to the score."

## Non-Capabilities
- This skill does NOT perform music theory calculations (handled by `querying-music-theory`).
- This skill does NOT play or synthesize audio files.
- This skill does NOT read raw MIDI input files directly.
