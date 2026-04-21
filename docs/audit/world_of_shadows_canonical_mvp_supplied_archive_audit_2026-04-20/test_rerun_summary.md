# Direct test rerun summary

These reruns were executed against the extracted `world_of_shadows_mvp_v24_f_line_closed_FULL_MVP_DIRECTORY` archive during this preservation audit.

| Command | Result |
|---|---|
| `python -m pytest -q mvp/reference_scaffold/tests --tb=short` | PASS |
| `python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short` | PASS |
| `python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py --tb=short` | PASS |
| `python -m pytest -q ai_stack/tests/test_goc_scene_identity.py ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short` | PASS |
| `python -m pytest -q ai_stack/tests/test_goc_mvp_breadth_playability_regression.py -rs --tb=short` | SKIPPED: LangGraph/LangChain stack required for GoC runtime graph tests |
| `python -m pytest -q backend/tests/test_session_routes.py -k 'shell_readout_projection or execute_turn_proxies_to_world_engine' --tb=short` | BLOCKED: missing Flask |
| `PYTHONPATH=frontend python -m pytest -q frontend/tests/test_routes_extended.py -k 'play_shell_frames_latest_transcript_with_runtime_response_prefix' --tb=short` | BLOCKED: missing Flask |

## Honest reading

The direct reruns in this audit keep the active-slice proof posture strong, but they do not justify pretending that every higher-level service route proof was freshly replayed here.
