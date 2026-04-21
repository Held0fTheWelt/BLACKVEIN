# Direct test rerun summary

These reruns were executed against the extracted `world_of_shadows_mvp_v24_f_line_closed_FULL_MVP_DIRECTORY` archive during this re-audit.

| Command | Result |
|---|---|
| `python -m pytest -q mvp/reference_scaffold/tests --tb=short` | PASS |
| `python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short` | PASS |
| `python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py --tb=short` | PASS |
| `python -m pytest -q ai_stack/tests/test_goc_scene_identity.py ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short` | PASS |
| `python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short` | BLOCKED: missing Flask |
| `PYTHONPATH=frontend python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_shell_frames_latest_transcript_with_runtime_response_prefix' --tb=short` | BLOCKED: missing Flask |

The raw outputs are included alongside this report under `evidence/raw_test_outputs/`.
