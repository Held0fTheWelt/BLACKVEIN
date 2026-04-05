# Area 2 — Final operational closure gates (G-FINAL)

Explicit **final** closure gates for Area 2 operational truth: reproducible bootstrap, healthy canonical paths, authority convergence, no-eligible discipline, operator legibility, cross-surface coherence, legacy compatibility, and documentation truth. These gates **do not** change `route_model` policy semantics, `StoryAIAdapter`, or guard/commit/reject authority.

**Authority source of truth (code):** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) — `AREA2_AUTHORITY_REGISTRY`.

**Prior evolution gates (unchanged, cross-referenced):** G-CONV-01, G-CONV-02, G-CONV-03, G-CONV-04, G-CONV-05, G-CONV-06, G-CONV-07, G-CONV-08 — see [`area2_convergence_gates.md`](./area2_convergence_gates.md).

| Gate ID | Pass condition | Failure meaning | Test proof |
|--------|----------------|-----------------|------------|
| **G-FINAL-01** | Named startup profiles (`production_default`, `testing_isolated`, `testing_bootstrap_on`, plus `production_bootstrap_disabled` for honesty) map deterministically to bootstrap flag, expected global `iter_model_specs()` after `create_app`, and `Area2OperationalState` via shared classification rules. | Bootstrap/registry expectations are ambiguous or untested. | `backend/tests/runtime/test_area2_final_closure_gates.py::test_g_final_01_reproducible_bootstrap_gate`, `test_g_final_01_expected_operational_state_matrix` |
| **G-FINAL-02** | Under `testing_bootstrap_on`, canonical Runtime (staged), Writers-Room HTTP, and Improvement HTTP paths show eligible routing (`route_reason_code` not `no_eligible_adapter`), selected adapter names on bounded stages, and preflight performs a bounded model call when adapters resolve. | Healthy profile still routine-hits `no_eligible_adapter` or routing succeeds only through undocumented skip paths. | `test_g_final_02_healthy_canonical_paths_runtime_bootstrap_on`, `test_g_final_02_healthy_canonical_paths_writers_room_bootstrap_on`, `test_g_final_02_healthy_canonical_paths_improvement_bootstrap_on` |
| **G-FINAL-03** | `AREA2_AUTHORITY_REGISTRY` includes `area2_operator_truth` and `area2_startup_profiles`; `canonical_authority_summary` on operator truth names `route_model` and bounded vs runtime spec sources. | Practical authority story missing from registry or summary. | `test_g_final_03_practical_authority_convergence_gate` |
| **G-FINAL-04** | `NoEligibleDiscipline` distinguishes true no-eligible from test-isolated empty registry; `legibility.route_status` does not read as plain healthy when stages record `no_eligible_adapter` with non-degraded discipline. | No-eligible outcomes are normalized or indistinguishable. | `test_g_final_04_no_eligible_non_normalization_gate` |
| **G-FINAL-05** | `area2_operator_truth.legibility` exposes `authority_source`, `operational_state`, `route_status`, `selected_vs_executed`, `primary_operational_concern`, `startup_profile` — all derived from existing facts. | Operator-facing block incomplete or not directly readable. | `test_g_final_05_operator_legibility_gate` + `assert_area2_truth_shape` (legibility keys) |
| **G-FINAL-06** | Same top-level `area2_operator_truth` key set across Runtime, Writers-Room, and Improvement under `testing_bootstrap_on`. | Cross-surface operator truth diverges. | `test_g_final_06_cross_surface_coherence_bootstrap_on` |
| **G-FINAL-07** | `TestingConfig` with `ROUTING_REGISTRY_BOOTSTRAP=False` yields empty `iter_model_specs()` after `create_app`; legacy inventory/bootstrap tests still pass. | Legacy/test isolation contract regressed. | `test_g_final_07_legacy_compatibility_gate`, `backend/tests/runtime/test_model_inventory_bootstrap.py` |
| **G-FINAL-08** | Architecture docs list G-FINAL-01 … G-FINAL-08 and reference `area2_routing_authority`; this file retains G-CONV cross-reference. | Documentation drift from enforced gates. | `test_g_final_08_documentation_and_closure_truth_gate` |

## Related code

- Startup profiles: [`backend/app/runtime/area2_startup_profiles.py`](../../backend/app/runtime/area2_startup_profiles.py)
- Operator truth / legibility: [`backend/app/runtime/area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py)
- Closure report: [`area2_final_operational_closure_report.md`](./area2_final_operational_closure_report.md)

## Task 2 registry/routing convergence (cross-reference)

Named closure suite **G-T2-01**, **G-T2-02**, **G-T2-03**, **G-T2-04**, **G-T2-05**, **G-T2-06**, **G-T2-07**, **G-T2-08** — [`area2_task2_closure_gates.md`](./area2_task2_closure_gates.md), [`area2_registry_routing_convergence_closure_report.md`](./area2_registry_routing_convergence_closure_report.md), tests `backend/tests/runtime/test_area2_task2_closure_gates.py`. Authority map: [`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py).
