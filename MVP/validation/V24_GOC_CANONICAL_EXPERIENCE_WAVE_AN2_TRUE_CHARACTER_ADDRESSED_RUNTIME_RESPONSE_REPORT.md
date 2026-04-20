# V24 GoC Canonical Experience — Wave AN2 True Character-Addressed Runtime Response Report

## Summary

Wave AN2 hardens the actual runtime observation/response layer so the player-facing scene output reads as more clearly answered by specific people and pressure lines.

This wave does **not** primarily solve the problem by adding more shell-only labels.
Instead it:

- derives compact response framing from authoritative runtime/session state,
- uses that framing to produce addressed runtime response bundles,
- and applies that framing in the visible transcript/observation line shown in the real play shell.

## What changed

Runtime-side:
- Added compact response exchange labels and line prefixes in `world-engine/app/story_runtime_shell_readout.py`
- Added `frame_story_runtime_visible_output_bundle(...)` to harden visible runtime output itself
- Added `visible_output_bundle_addressed` and `shell_readout_projection` into the authoritative turn event in `world-engine/app/story_runtime/manager.py`

Frontend/session-flow side:
- Frontend now accepts turn-level shell readout projection as a fallback source when state is not yet populated
- Latest transcript line and transcript preview now prefer the runtime-built response line prefix, making the observation layer itself feel more character-addressed

## What is now proven

- The runtime/session turn output now carries character-addressed response framing
- The visible runtime output bundle can be framed through the active responder and pressure line
- The actual observation/transcript surface shown to the player is more clearly traceable to who is answering and why now
- The improvement remains compact and non-directive
- Previously closed readout surfaces remain intact
