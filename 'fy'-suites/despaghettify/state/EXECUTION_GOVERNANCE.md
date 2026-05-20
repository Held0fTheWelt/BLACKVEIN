# Execution governance (despaghettify)

## Completion gate (every sub-wave)

1. **Pre** artefacts under `artifacts/workstreams/<slug>/pre/` (human-readable + optional JSON).
2. Implementation with behaviour unchanged.
3. **Post** artefacts under `…/post/` with pre→post comparison.
4. Gates from wave plan / input list **note** column — all green or hard stop.
5. Update `WORKSTREAM_*_STATE.md` and [`despaghettification_implementation_input.md`](../despaghettification_implementation_input.md).

## Contradiction stop

Missing wave plan, missing pre/post, or gate regression without recorded reason → stop; do not claim DS closure.
