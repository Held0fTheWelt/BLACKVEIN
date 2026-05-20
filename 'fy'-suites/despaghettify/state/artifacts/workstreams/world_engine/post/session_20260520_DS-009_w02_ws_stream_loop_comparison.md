# DS-009 w02 post-comparison — WebSocket stream-loop follow-up extraction

Session: 20260520

Pre:

- `story_session_stream` in `world-engine/app/api/story_ws.py` carried session-loop orchestration plus the autonomous follow-up pause loop.
- Baseline hotspot: 391 AST lines, nesting depth 8.

Post:

- Added `_run_autonomous_followup_after_turn(...)` to hold the autonomous follow-up wait/cut-in loop.
- `story_session_stream(...)` now delegates that section and keeps the endpoint/session orchestration surface stable.
- Removed the stale `autonomous_cut_in_interrupted` local.
- Local AST check after the wave: `story_session_stream` 229 lines / nesting depth 5; `_run_autonomous_followup_after_turn` 181 lines / nesting depth 6.
- Formal `check --with-metrics` no longer lists `story_session_stream` in the top longest/nesting rankings.
- Formal scan after DS-009: 10747 functions, 858 functions over 50 lines, 235 functions over 100 lines, 24 functions at nesting depth >= 6.

Gates:

- `python -m compileall -q world-engine/app/story_runtime world-engine/app/api` — passed.
- `INTERNAL_RUNTIME_CONFIG_TOKEN= pytest world-engine/tests/test_phase2_ws_session_loop_endpoint.py world-engine/tests/test_mvp3_narrative_streaming_endpoint.py -q --tb=short` — 60 passed.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli wave-plan-validate --file "'fy'-suites/despaghettify/state/artifacts/workstreams/world_engine/pre/session_20260520_DS-009_wave_plan.json" --check-primary-paths` — passed.
- `PYTHONPATH="'fy'-suites" DESPAG_SKIP_ARCHIVE_SYNC=1 python -m despaghettify.tools.hub_cli check --with-metrics --out "'fy'-suites/despaghettify/reports/latest_check_with_metrics.json"` — passed; report `2026-05-20T22:02:19Z`.
- `git diff --check -- world-engine/app/api/story_ws.py world-engine/app/story_runtime/planner_truth_projection.py world-engine/app/story_runtime/manager/recoverable_aspect_ledger.py world-engine/app/story_runtime/manager/external_imports_core.py world-engine/app/story_runtime/manager/_imports_00.py world-engine/tests/test_mvp3_narrative_streaming_endpoint.py world-engine/tests/test_mvp3_narrative_agent_orchestration.py world-engine/tests/test_mvp3_complete_integration.py` — passed.

Broad-suite caveat:

- `python tests/run_tests.py --suite engine_http_ws --quick` was stopped as over-broad for this wave after a long run through generic HTTP coverage; no DS-009 failure had surfaced at the stop point.
