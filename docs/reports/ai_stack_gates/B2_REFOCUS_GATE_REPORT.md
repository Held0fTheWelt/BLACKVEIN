# B2 REFOCUS Gate Report — Harden LangGraph Runtime Truthfulness

**Date:** 2026-04-04
**Status:** PASS

## Gap Addressed

`build_seed_writers_room_graph()` and `build_seed_improvement_graph()` (lines 315-348 in
`wos_ai_stack/langgraph_runtime.py`) are single-node stub graphs that return trivial state
transitions. They are not used in actual multi-stage workflows. Without explicit documentation,
readers could overestimate their maturity.

The existing test `test_seed_graphs_for_writers_room_and_improvement_are_operational` verified
that the graphs ran and returned expected keys, but did not document the stub-only nature or
assert absence of real workflow stages.

## Work Done

Added two new tests to `wos_ai_stack/tests/test_langgraph_runtime.py`:

- `test_seed_writers_room_graph_is_minimal_stub`: asserts `workflow == "writers_room_review_seed"`
  and `status == "ready"`, then explicitly asserts that real stage keys (`retrieval`, `generation`,
  `review`, `revision`) are absent from the result.

- `test_seed_improvement_graph_is_minimal_stub`: same pattern for `improvement_eval_seed`,
  asserting absence of `retrieval`, `generation`, `evaluation`, `recommendation` keys.

These tests function as honest documentation: they will catch any future accidental promotion of
the stubs to multi-stage graphs without updating the tests.

## Test Results

```
collected 6 items
test_runtime_turn_graph_propagates_trace_and_host_versions  PASSED
test_runtime_turn_graph_executes_nodes_and_emits_trace      PASSED
test_seed_graphs_for_writers_room_and_improvement_are_operational PASSED
test_seed_writers_room_graph_is_minimal_stub                PASSED
test_seed_improvement_graph_is_minimal_stub                 PASSED
test_langgraph_missing_dependency_raises_honest_runtime_error PASSED
6 passed in 0.46s
```

## Verdict

**PASS** — Stub status is now explicitly documented and enforced via tests. No production code
was changed; only the test file was extended.
