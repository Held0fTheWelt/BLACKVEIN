# Workstream: world_engine

## Closed — DS-009 world-engine runtime split (session 20260520)

| Sub-wave | Outcome | Primary files / symbols | Evidence |
|----------|---------|--------------------------|----------|
| w01 | Planner-truth projection moved behind a focused story-runtime projection module. `_planner_truth_from_graph_state(...)` remains as the stable `PlannerTruth` wrapper. | `world-engine/app/story_runtime/commit_models.py`, `world-engine/app/story_runtime/planner_truth_projection.py`; `_planner_truth_from_graph_state`, `build_planner_truth_payload` | Post comparison: `artifacts/workstreams/world_engine/post/session_20260520_DS-009_w01_planner_truth_comparison.*` |
| w02 | WebSocket autonomous follow-up wait/cut-in loop extracted from `story_session_stream(...)` into `_run_autonomous_followup_after_turn(...)`. | `world-engine/app/api/story_ws.py`; `story_session_stream`, `_run_autonomous_followup_after_turn` | Post comparison: `artifacts/workstreams/world_engine/post/session_20260520_DS-009_w02_ws_stream_loop_comparison.*` |

**Plan mirror:** `artifacts/workstreams/world_engine/pre/session_20260520_DS-009_wave_plan.json`

**Current metrics report:** `../reports/latest_check_with_metrics.json` generated `2026-05-20T22:02:19Z`.

## Gates

- `python -m compileall -q world-engine/app/story_runtime world-engine/app/api` — passed.
- `INTERNAL_RUNTIME_CONFIG_TOKEN= pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py::test_planner_truth_populated_from_graph_state world-engine/tests/test_planner_truth_and_runtime_surfaces.py::test_planner_truth_persists_current_npc_agency_closure world-engine/tests/test_validator_lane_truth.py::test_planner_truth_validator_layers_from_live_seam -q --tb=short` — 3 passed.
- Earlier full focused planner/lane/commit gate in this wave: `pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_validator_lane_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q --tb=short` — 33 passed before the final helper compaction.
- `INTERNAL_RUNTIME_CONFIG_TOKEN= pytest world-engine/tests/test_phase2_ws_session_loop_endpoint.py world-engine/tests/test_mvp3_narrative_streaming_endpoint.py -q --tb=short` — 60 passed.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli wave-plan-validate --file "'fy'-suites/despaghettify/state/artifacts/workstreams/world_engine/pre/session_20260520_DS-009_wave_plan.json" --check-primary-paths` — passed.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` — passed.
- `git diff --check` for touched world-engine/state files — passed.

## Caveats

- `python tests/run_tests.py --suite engine_runtime --quick` currently stops on unrelated NLU contract drift in `world-engine/tests/test_story_runtime_api.py::test_story_session_lifecycle_and_nl_interpretation` (`interpreted_input.kind`: expected `mixed`, got `speech`).
- `python tests/run_tests.py --suite engine_http_ws --quick` was stopped as over-broad for DS-009 after a long generic HTTP run; no DS-009 failure had surfaced at the stop point.

## Structural delta

- `_planner_truth_from_graph_state`: 540 AST lines / depth 6 → 9 lines / depth 0 wrapper.
- `build_planner_truth_payload`: 133 lines / depth 1 in the extracted projection module.
- `story_session_stream`: 391 AST lines / depth 8 → 229 lines / depth 5.
- Current full scan: 10747 functions; L50 858; L100 235; D6 24.
- DS-009 symbols no longer appear in the formal top longest/nesting rankings.
