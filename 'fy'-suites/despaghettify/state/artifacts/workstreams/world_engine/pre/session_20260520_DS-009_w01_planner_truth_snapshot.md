# DS-009 w01 pre-snapshot — planner-truth projection

Session: 20260520

Scope:

- DS-009 targets `world-engine/app/story_runtime/commit_models.py` and `world-engine/app/api/story_ws.py`.
- Wave 1 owns `_planner_truth_from_graph_state` only.
- WebSocket stream-loop extraction is reserved for wave 2.

Current hotspot evidence from the latest metrics scan (`2026-05-20T19:32:19Z`):

- `world-engine/app/story_runtime/commit_models.py:_planner_truth_from_graph_state`: 540 AST lines, nesting depth 6.
- `world-engine/app/api/story_ws.py:story_session_stream`: 391 AST lines, nesting depth 8.

Planned change:

- Add a focused planner-truth projection module under `world-engine/app/story_runtime/`.
- Keep `_planner_truth_from_graph_state(...)` in `commit_models.py` as a stable `PlannerTruth` wrapper.
- Preserve the persisted `PlannerTruth` field contract and allow Pydantic to coerce actor-summary dictionaries into `ActorLineSummary`.

Gates for this wave:

- `python -m compileall -q world-engine/app/story_runtime`
- `pytest world-engine/tests/test_planner_truth_and_runtime_surfaces.py world-engine/tests/test_validator_lane_truth.py world-engine/tests/test_story_runtime_narrative_commit.py -q --tb=short`
- `python tests/run_tests.py --suite engine_runtime --quick`
