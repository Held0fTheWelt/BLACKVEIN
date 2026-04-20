# Wave AU — Surface Priority Compression

## Result

Wave AU closed.

The real package already proved Wave AT before changes in this pass: domestic surfaces were present in the visible response/output path, the AT report matched the accessible files, and the focused world-engine/backend/frontend proof reran cleanly.

The strongest next unresolved A-line move was therefore not reconciliation but compression:

- the hottest surface was already present,
- but the visible runtime response still spent too many words on explanation,
- and the exchange line still named the hot surface as an additional clause instead of letting that surface become the line's single pressure focus.

Wave AU tightened that visible response path so the room now reads faster as one dominant social surface at a time.

## What changed

### Runtime readout compression

Updated `world-engine/app/story_runtime_shell_readout.py` so the visible response path now compresses surface priority into a single dominant pressure point instead of explaining it twice.

Key changes:

- response surface heat phrases were shortened from `loading the ...` forms to tighter `at/on the ...` forms
- `response_exchange_now` was compressed so it no longer says both:
  - what the live wound is
  - and then again where the pressure is hottest
- carryover exchange phrasing was tightened from `with it still carrying ...` to `still carrying ...`
- response text now prioritizes one dominant surface more sharply:
  - doorway
  - bathroom edge
  - books
  - flowers
  - phone
  - hosting surface

### Focused proof strengthening

Updated focused expectations in:

- `world-engine/tests/test_story_runtime_shell_readout.py`
- `backend/tests/test_session_routes.py`
- `frontend/tests/test_routes_extended.py`

Added a new direct proof case that when both phone and hosting-surface pressure are present, the visible response compresses to the phone as the dominant hot surface rather than diluting focus across both.

## Why this was the strongest next wave

Wave AT was already package-truth-proven.

The remaining highest-leverage visible issue was not missing room anchoring but over-explanation. The response line already knew the apartment surface. The next strongest improvement was making the player feel that the room is reading one pressure point first, without dashboard drift.

That is exactly what AU required.

## Validation

### Pre-change package-truth verification

Executed before changing code:

- `PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short`
- `PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short`
- `PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short`

Observed:

- world-engine focused readout tests: `7 passed, 1 warning in 0.13s`
- backend focused bridge tests: `2 passed, 35 deselected in 8.15s`
- frontend focused session/play tests: `14 passed, 53 deselected in 0.43s`

### Post-change wave proof

Executed after implementation:

- `PYTHONPATH=world-engine /opt/pyvenv/bin/python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short`
- `PYTHONPATH=backend /opt/pyvenv/bin/python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short`
- `PYTHONPATH=frontend /opt/pyvenv/bin/python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_execute_json_merges_runtime_shell_readout_projection or play_shell_frames_latest_transcript_with_runtime_response_address or play_execute_json_prefers_turn_level_addressed_visible_output_bundle or play_execute_json_uses_turn_level_runtime_shell_readout_when_state_missing or play_shell_renders_cached_runtime_shell_readout_fields or play_shell_prefers_compressed_contextual_readout_fields or play_execute_json_returns_authoritative_shell_state_bundle or play_observe_returns_observation_meta or play_shell_embeds_initial_authoritative_shell_state_json or play_observe_returns_observation_source_and_runtime_session_flags or play_execute_json_returns_runtime_ready_and_observation_source or play_execute_json_and_followup_observe_share_coherent_bundle_shape or play_execute_json_prefers_turn_level_addressed_visible_output_bundle_over_hosting_surface' --tb=short`
- `PYTHONPATH=. /opt/pyvenv/bin/python -m pytest -q ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short`

Observed:

- world-engine focused readout tests: `8 passed, 1 warning in 0.13s`
- backend focused bridge tests: `2 passed, 35 deselected in 8.23s`
- frontend focused session/play tests: `14 passed, 53 deselected in 0.40s`
- ai_stack inherited narrow proof: `5 passed in 0.46s`

## Key proof

The visible response/output layer is materially changed, not just shell metadata.

Examples of the new compressed player-facing line shape:

- `Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, still carrying departure shame from the earlier failed exit`
- `Annette, from the guest side across the couples, answers in accusation with cross-couple strain on the books, still carrying the earlier taste-and-status wound`
- `Michel, from the host side, answers in brittle repair with host-side hospitality pressure on the hosting surface, still carrying the earlier hospitality-and-hosting line`

And the compressed exchange explanation now resolves to a single dominant pressure point, for example:

- `Your act drew an accusation answer because your move made the books the live pressure point, still carrying the earlier taste-and-status wound.`
- `Your act drew an evasive pressure answer because your move made the phone the live pressure point, still carrying the earlier humiliation line.`

## Closure position

Wave AU is materially present in the real package state and backed by focused executable proof.

The hottest social surface now reads more quickly and with less explanatory drag in the actual runtime response path.
