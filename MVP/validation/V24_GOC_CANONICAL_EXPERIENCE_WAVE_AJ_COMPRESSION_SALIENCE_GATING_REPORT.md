# V24 GoC Canonical Experience — Wave AJ Contextual Readout Compression + Salience Gating

## Summary

Wave AJ hardens the MVP-v24 player shell by keeping the authoritative runtime/session readout rich while compressing the player-facing surfacing into a smaller, more contextual set of lines.

The runtime/session state still carries the detailed shell-readout fields. The shell now prioritizes five compact player-facing lines:

- `social_weather_now`
- `live_surface_now`
- `carryover_now`
- `social_geometry_now`
- `situational_freedom_now`

These lines are derived from real runtime/session state and are surfaced through the existing world-engine -> backend -> frontend shell path.

## Why this pass was needed

Earlier readout hardening waves improved precision, role sensitivity, and social-geometry readability, but the visible shell had become too dashboard-like by presenting many neighboring interpretive lines at once.

This pass keeps the richer authoritative state while presenting a more chamber-play-appropriate player readout.

## What changed

- Added compressed contextual readout fields in `world-engine/app/story_runtime_shell_readout.py`
- Passed those fields through the existing frontend route merge layer
- Updated the shell template and JS to show the compressed contextual lines by default
- Added focused tests proving:
  - the new fields exist
  - the shell prefers the compressed contextual readout by default
  - existing closed surfaces remain intact

## Validation summary

- world-engine shell-readout tests: 2 passed
- backend shell-readout bridge test: 1 passed
- frontend shell/readout focused tests: 9 passed
- inherited ai_stack focused tests: 5 passed
