# Task 4 — Retrieval evaluation harness

## Purpose

Named, deterministic scenarios live in [`ai_stack/tests/retrieval_eval_scenarios.py`](../ai_stack/tests/retrieval_eval_scenarios.py). They are **test-only** (not imported by production code) and document what “good” means for regression detection across domains.

## Scenario coverage

| Scenario id | Domain / profile | What it proves |
|-------------|------------------|----------------|
| `runtime_canonical_over_draft_when_both_in_pool` | Runtime | Published canonical is the top anchor when both draft and published exist for the same module; pack shows “Canonical evidence”; trace lane mix is canonical-heavy. |
| `runtime_hides_evaluative_artifacts` | Runtime | Evaluation/report content is not in runtime hits when published anchor exists. |
| `writers_room_sees_review_notes` | Writers-Room | `review_note` content is visible; pack includes “Review context”. |
| `improvement_surfaces_evaluative_lane` | Improvement | Evaluation artifacts surface with evaluative lane; pack includes “Evaluative evidence”; lane mix is evaluative-present or evaluative-mixed. |
| `duplicate_suppression_improvement` | Improvement | Near-duplicate chunks collapse; `dup_suppressed` in ranking notes; trace `dedup_shaped_selection` is true. |
| `sparse_route_recorded_for_operators` | Runtime | Sparse path records `retrieval_route=sparse_fallback` in notes and payload. |
| `runtime_hard_exclusion_when_published_canonical_present` | Runtime | Task 3 hard gate removes same-module draft when published canonical is in pool; trace `policy_outcome_hint` is `hard_pool_exclusions_applied`. |

## Running tests

```bash
pytest ai_stack/tests/test_rag.py::test_retrieval_eval_named_scenario -q
```

The harness uses `assert_scenario`, which builds a capability-shaped retrieval dict and runs `build_retrieval_trace` for trace expectations.

## Intentionally out of scope

- Large benchmark suites or external golden datasets
- Non-deterministic or score-only assertions (prefer path, lane, pack role, and trace fields)
