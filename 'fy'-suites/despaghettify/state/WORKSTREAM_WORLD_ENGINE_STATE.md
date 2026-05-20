# Workstream: world_engine

## In flight — DS-009 wave plan (session 20260520)

| Sub-wave | Goal | Primary files / symbols | Gate |
|----------|------|--------------------------|------|
| 1 | Extract planner-truth projection assembly from commit models into a focused world-engine story-runtime module while preserving the PlannerTruth contract. | `world-engine/app/story_runtime/commit_models.py`, `world-engine/app/story_runtime/planner_truth_projection.py`; `_planner_truth_from_graph_state` | `python -m compileall -q world-engine/app/story_runtime`; `pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_validator_lane_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q --tb=short`; `python tests/run_tests.py --suite engine_runtime --quick` |
| 2 | Extract WebSocket stream-loop phases from story_ws into focused helpers without changing session-loop messages or cut-in semantics. | `world-engine/app/api/story_ws.py`; `story_session_stream` | `python -m compileall -q world-engine/app/api world-engine/app/story_runtime`; `pytest world-engine/tests/test_phase2_ws_session_loop_endpoint.py world-engine/tests/test_mvp3_narrative_streaming_endpoint.py -q --tb=short`; `python tests/run_tests.py --suite engine_http_ws engine_runtime --quick`; `check --with-metrics` |

**Plan mirror:** `artifacts/workstreams/world_engine/pre/session_20260520_DS-009_wave_plan.json`
