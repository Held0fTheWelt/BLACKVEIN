# V24 GoC Canonical Experience — Wave AP Exchange-Type Differentiation + Response-Cause Compression

## Scope

This wave hardens the actual runtime observation/response layer so the visible response feels more clearly like a specific kind of social exchange.

It does **not** redesign the architecture.
It does **not** add broad frontend work.
It does **not** rely on shell metadata alone.

## What changed

The runtime-side shell readout builder now derives a tighter response framing around:

- exchange type
- response cause compression
- side/pair/pressure-line voice framing
- compact addressed response line prefixes

The frontend execute/readout flow now also prefers a turn-level `visible_output_bundle_addressed` line when present, so the actual runtime response can surface immediately in the shell response instead of relying only on later transcript refresh.

## Main effects

The response/output layer now reads more like:

- host-side failed repair
- guest-side accusation
- containment under exposure
- evasive pressure
- blame transfer

instead of a more generic pressure summary.

## Files in scope

- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/tests/test_story_runtime_shell_readout.py`
- `frontend/app/routes.py`
- `frontend/tests/test_routes_extended.py`
- `backend/tests/test_session_routes.py`

## Validation

Focused validation was rerun against the reconciled package state and passed.
