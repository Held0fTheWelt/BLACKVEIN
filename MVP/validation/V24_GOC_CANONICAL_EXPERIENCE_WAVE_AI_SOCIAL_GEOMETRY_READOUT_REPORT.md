# Wave AI — Social-Axis Geometry Readout Hardening

This pass sharpens the existing authoritative runtime/session/shell readout so the player can more clearly perceive how the room is socially arranged against itself.

## Added precision

The shell readout projection now carries these compact geometry-focused fields:
- `host_guest_pressure_now`
- `spouse_axis_now`
- `cross_couple_now`
- `pressure_redistribution_now`

These fields are derived from authoritative runtime/session state already present in the MVP v24 loop, including:
- current scene id
- last open pressures
- last committed consequences
- selected responder set
- social-state diagnostic record
- narrative thread continuity

## What this improves

The shell can now more clearly show:
- whether pressure is sitting with the host side or guest side
- whether embarrassment is living on the spouse axis
- whether the room is tilting into cross-couple strain or temporary coalition logic
- whether the player's recent act redistributed pressure from one axis to another

## Guardrails preserved

- no objective hints
- no beat exposure
- no frontend redesign
- no narrator layer
- compact, non-directive readout only
