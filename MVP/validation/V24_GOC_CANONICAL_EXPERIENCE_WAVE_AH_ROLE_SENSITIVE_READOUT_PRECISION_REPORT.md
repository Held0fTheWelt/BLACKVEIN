# Wave AH — Role-Sensitive Consequence Readout Precision Hardening

This pass sharpens the existing authoritative runtime/session/shell readout so the player can more clearly perceive not just that pressure exists, but what kind of social reading is currently dominating the room.

## Added precision

The shell readout now carries compact additional fields:
- `dominant_social_reading_now`
- `social_axis_now`
- `object_social_reading_now`
- `callback_role_frame_now`

These fields are derived from authoritative runtime/session state already present in the MVP v24 loop, including:
- current scene id
- last open pressures
- last committed consequences
- selected responder set
- social-state diagnostic record
- narrative thread continuity

## What this improves

The shell can now more clearly show:
- whether an act landed as judgment, overfamiliarity, failed repair, humiliation, or care mixed with exposure
- whether host-side, guest-side, spouse-axis, or cross-couple strain is carrying the pressure
- how a callback is being socially reused
- how an object is currently being socially read, not just that it is salient

## Guardrails preserved

- no objective hints
- no beat exposure
- no frontend redesign
- no narrator layer
- compact, non-directive readout only
