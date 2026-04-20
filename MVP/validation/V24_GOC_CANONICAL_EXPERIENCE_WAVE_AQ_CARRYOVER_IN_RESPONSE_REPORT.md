# Wave AQ — Carryover-in-Response Hardening

## Scope

This wave hardens the actual runtime observation/response layer so visible response output more clearly carries forward prior pressure, failed repair, embarrassment, and object-linked wounds.

This wave does **not** redesign architecture, add broad memory systems, or solve the problem through shell-only metadata expansion.

## Real integration seams used

- `world-engine/app/story_runtime_shell_readout.py`
- `world-engine/app/story_runtime/manager.py` (already emitting addressed runtime bundle and shell readout projection)
- `frontend/app/routes.py`
- `frontend/tests/test_routes_extended.py`
- `backend/tests/test_session_routes.py`

## What changed

The runtime response framing now compresses carryover into the visible response/output layer itself.

Key changes:

- runtime response framing now derives carryover-aware phrases from active pressure, consequences, social-state continuity classes, and thread continuity
- `response_exchange_now` now reflects when the current answer is still carrying an earlier wound
- `response_line_prefix_now` now includes compact carryover phrasing when appropriate
- visible addressed output therefore reads less like an isolated fresh answer and more like a socially continuous answer
- frontend execute/observation flow continues to prefer turn-level addressed visible output and now benefits from the richer runtime framing without a shell redesign

## What was validated

Focused validation was rerun against the reconciled MVP-v24 package:

1. `world-engine/tests/test_story_runtime_shell_readout.py`
2. `backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine'`
3. `frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_carries_prior_wound'`
4. `ai_stack/tests/test_social_state_goc.py`
5. `ai_stack/tests/test_semantic_move_interpretation_goc.py`

## Closure judgment

Wave AQ is closed.

The improvement is real in the runtime response layer itself:

- prior pressure/wounds are more legible in visible response output
- delayed/indirect reaction feels stronger in transcript-facing output
- pair/side differentiation and exchange-type differentiation remain intact
- the shell remains compact and non-directive
- canon corridor integrity remains intact
