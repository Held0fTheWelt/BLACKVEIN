# V24 GoC Canonical Experience — Wave AK Delta-Focused Reaction Readout Hardening

## Summary

This pass hardens the MVP-v24 authoritative runtime → shell readout so the player can more clearly perceive what changed because of the last act.

The work remains narrow and additive:
- no frontend redesign
- no new internal behavior layer
- no beat/objective hints
- no narrator expansion

## Added readout signals

The authoritative shell readout now carries compact delta-focused signals:
- `reaction_delta_now`
- `carryover_delta_now`
- `pressure_shift_delta_now`
- `hot_surface_delta_now`

These are derived from existing runtime/session truth including:
- current scene / threshold context
- open pressure lines
- last committed consequences
- short-horizon continuity and thread pressure
- responder/social-state asymmetry

## What this improves

The shell is now better at showing:
- what just tightened
- what wound was reactivated now
- how pressure just moved to a new social line
- what object/zone became hot because of the latest act

This is intended to strengthen felt agency without giving visible guidance.

## Validation

Focused validation was rerun across:
- world-engine shell readout logic
- frontend shell render / execute / observe readout transport
- backend bridge continuity
- narrow ai_stack social-state surfaces

See `CURRENT_STATE_VALIDATION_SUMMARY_WAVE_AK.txt` for the command summary.
