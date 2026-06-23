---
name: rendering-visual-notation
description: Converts active canvas JSON state file coordinates into inline graphs or static plot files using matplotlib configurations.
permission_tier: Read-Only
allowed-tools:
  - render_notation
---

# rendering-visual-notation

## Focus & Capabilities
This skill handles rendering symbolic music notation states into visual representations:
- Reading the active localized canvas state file coordinates from JSON.
- Generating static plot files or inline graphics (e.g., piano roll or note plots) using `matplotlib` configurations.
- Confirming target image paths.

## Triggers
- "Render the active score canvas to an image."
- "Show a visualization of the canvas."
- "Graph the current notes."

## Non-Capabilities
- This skill does not modify the canvas state file.
- This skill does not synthesize audio or MIDI playback.
