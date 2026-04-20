# Wave AT — Domestic Surface Heat Prioritization + Side/Pair/Object Interplay Hardening

## Result

Wave AT closed.

The runtime response layer now expresses the hottest current domestic surface more explicitly in the visible response/output path, while preserving prior side/pair differentiation, exchange-type differentiation, carryover-aware response, and prior-line reuse framing.

## What changed

- Hardened `world-engine/app/story_runtime_shell_readout.py` so response framing now carries compact domestic-surface heat interplay such as:
  - host-side spouse embarrassment loading the doorway
  - cross-couple strain loading the books
  - host-side manners pressure loading the flowers
  - host-side hospitality pressure loading the hosting surface
  - guest-side exposure pressure loading the bathroom edge
- Updated focused tests in:
  - `world-engine/tests/test_story_runtime_shell_readout.py`
  - `frontend/tests/test_routes_extended.py`
  - `backend/tests/test_session_routes.py`

## Validation

Executed:

- `PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short`
- `PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short`
- `PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short`
- `PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short`

## Key proof

- world-engine focused readout tests: `7 passed`
- backend focused bridge tests: `2 passed, 35 deselected`
- frontend focused session/play tests: `14 passed, 53 deselected`
- ai_stack narrow inherited tests: `5 passed`

## Closure position

Wave AT is now materially present in the real package state and is backed by focused executable proof.
