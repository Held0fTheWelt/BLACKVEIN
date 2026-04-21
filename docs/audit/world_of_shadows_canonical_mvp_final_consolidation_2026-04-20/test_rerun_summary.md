# Final consolidation pass — direct test rerun summary

## Commands rerun in this pass

| Command | Status | Summary |
|---|---|---|
| python -m pytest -q mvp/reference_scaffold/tests --tb=short | NONZERO | See raw output |
| PYTHONPATH=world-engine:. python -m pytest -q world-engine/tests/test_story_runtime_shell_readout.py --tb=short | PASS | 18 passed, 1 warning |
| PYTHONPATH=world-engine:. python -m pytest -q world-engine/tests/test_story_runtime_narrative_commit.py --tb=short | PASS | 18 passed, 1 warning |
| python -m pytest -q ai_stack/tests/test_goc_scene_identity.py ai_stack/tests/test_social_state_goc.py ai_stack/tests/test_semantic_move_interpretation_goc.py --tb=short | PASS | 10 passed |
| python -m pytest -q ai_stack/tests/test_goc_mvp_breadth_playability_regression.py -rs --tb=short | SKIPPED / ENV-LIMITED | 1 skipped |
| python -m pytest -q backend/tests/test_session_routes.py -k "shell_readout_projection or execute_turn_proxies_to_world_engine" --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' |
| PYTHONPATH=frontend python -m pytest -q frontend/tests/test_routes_extended.py -k "play_shell_frames_latest_transcript_with_runtime_response_prefix" --tb=short | BLOCKED IN THIS CONTAINER | ModuleNotFoundError: No module named 'flask' |

## Reading

These reruns are intentionally narrow.
They refresh the most reachable proof surfaces in this container without pretending that blocked Flask-backed or graph-heavy paths were replayed successfully.

## Raw outputs

All raw outputs are stored under:

`evidence/raw_test_outputs/final_consolidation_2026-04-20/`
