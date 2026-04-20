# Wave AL — In-Situation Turn Framing + Address Pressure Hardening

## Scope
This wave hardens the existing authoritative runtime-to-shell readout so the player can more clearly tell:
- who is effectively pressing them now,
- what kind of social moment the room is in,
- and what sort of response pressure is socially live.

It remains compact, non-directive, and chamber-play appropriate.

## Added player-facing compact fields
- `address_pressure_now`
- `social_moment_now`
- `response_pressure_now`

## Architecture seams used
- authoritative world-engine session state
- existing backend session bridge
- existing frontend play shell

## Validation summary
- world-engine shell readout test: 2 passed
- backend bridge test slice: 1 passed
- frontend shell/readout test slice: 9 passed
- narrow inherited ai_stack GoC tests: 5 passed
