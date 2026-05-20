# DS-009 w01 post-comparison — planner-truth projection split

Session: 20260520

Pre:

- `_planner_truth_from_graph_state` lived in `world-engine/app/story_runtime/commit_models.py`.
- Baseline hotspot: 540 AST lines, nesting depth 6.
- Baseline scan before DS-009: 10731 functions, 857 functions over 50 lines, 235 functions over 100 lines, 25 functions at nesting depth >= 6.

Post:

- Added `world-engine/app/story_runtime/planner_truth_projection.py` as the focused planner-truth projection module.
- Kept `_planner_truth_from_graph_state(...)` in `commit_models.py` as a stable wrapper returning `PlannerTruth`.
- `build_planner_truth_payload(...)` now orchestrates named projection helpers instead of carrying the whole field assembly inline.
- Local AST check after the wave: `_planner_truth_from_graph_state` 9 lines / nesting depth 0; `build_planner_truth_payload` 133 lines / nesting depth 1.
- Formal `check --with-metrics` no longer lists `_planner_truth_from_graph_state` or `build_planner_truth_payload` in the top longest/nesting rankings.
- Formal scan after DS-009: 10747 functions, 858 functions over 50 lines, 235 functions over 100 lines, 24 functions at nesting depth >= 6.

Gates:

- `python -m compileall -q world-engine/app/story_runtime world-engine/app/api` — passed.
- `INTERNAL_RUNTIME_CONFIG_TOKEN= pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py::test_planner_truth_populated_from_graph_state world-engine/tests/test_planner_truth_and_runtime_surfaces.py::test_planner_truth_persists_current_npc_agency_closure world-engine/tests/test_validator_lane_truth.py::test_planner_truth_validator_layers_from_live_seam -q --tb=short` — 3 passed.
- Earlier full focused planner/lane/commit gate in this wave: `pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_validator_lane_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q --tb=short` — 33 passed before the final helper compaction.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` — passed; report `2026-05-20T22:02:19Z`.

Broad-suite caveat:

- `python tests/run_tests.py --suite engine_runtime --quick` is blocked by unrelated NLU contract drift in `world-engine/tests/test_story_runtime_api.py::test_story_session_lifecycle_and_nl_interpretation` (`interpreted_input.kind`: expected `mixed`, got `speech`).
