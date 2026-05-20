# W5 actor situation — parallel track (ADR-0063)

**Date:** 2026-05-20  
**Status:** In flight (does not block Phase-1 closure)

## Scope

Optional enrichment of `actor_locations` for `compute_gathering_state` via W5 snapshot projection.

## Anchors

- `ai_stack/actor_tracking/projection.py` — `build_w5_projection_for_narrator`, `build_w5_projection_for_director`
- `complete_actor_locations_for_gathering_with_optional_w5_projection` — `ai_stack/tests/test_phase1_live_wiring.py`
- `world-engine/tests/test_story_runtime_w5_narrator_projection.py`

## Consumer rule

When W5 flag disabled, gathering pause uses legacy `actor_locations` only — no regression.
