# Area 2 — Convergence gates (G-CONV)

Explicit closure gates for routing/registry **operational truth** across Runtime, Writers-Room, and Improvement bounded paths. These gates are **additive** to Task 4 gates ([`task4_hardening_gates.md`](./task4_hardening_gates.md)). They do **not** change `route_model` policy semantics, `StoryAIAdapter`, or guard/commit/reject authority.

| Gate ID | Pass condition | Failure meaning | Test coverage |
|--------|----------------|-----------------|---------------|
| **G-CONV-01** | Importable authority registry lists every canonical seam once; `route_model` is the sole authoritative routing policy entry; `ai_stack` LangGraph `RoutingPolicy` is **not** canonical for Task 2A HTTP paths. | Undocumented competing routing authority for canonical paths. | `backend/tests/runtime/test_area2_convergence_gates.py::test_g_conv_01_single_authority_gate` |
| **G-CONV-02** | Bootstrap registers specs; staged runtime tuples and bounded WR/Improvement spec sets satisfy `validate_surface_coverage`; healthy in-process runtime does not routine-hit `no_eligible_adapter` on routed stages when specs are registered. | Healthy bootstrap still yields empty eligibility or routine no-eligible. | `test_g_conv_02_*`, `test_bounded_specs_cover_writers_room_and_improvement_surfaces` |
| **G-CONV-03** | `Area2OperationalState` classifies explicit fact vectors deterministically (`healthy`, `intentionally_degraded`, `misconfigured`, `test_isolated`). | Ambiguous operational/bootstrap state. | `test_g_conv_03_state_classification_gate_matrix` |
| **G-CONV-04** | `NoEligibleDiscipline` and rollups distinguish setup gap, true no-eligible, intentional degradation flag on no-eligible, test-isolated empty registry, and bounded executor mismatch. | Operators cannot tell misconfiguration from honest exhaustion. | `test_g_conv_04_no_eligible_discipline_gate` |
| **G-CONV-05** | `operator_audit.area2_operator_truth` is present on Runtime, Writers-Room, and Improvement responses with required keys derived from real facts. | Operator truth block missing or incomplete. | `backend/tests/runtime/test_cross_surface_operator_audit_contract.py` (G-CONV-05 assertions) |
| **G-CONV-06** | `TestingConfig` with `ROUTING_REGISTRY_BOOTSTRAP=False` leaves `iter_model_specs()` empty; legacy registration patterns remain covered by existing inventory tests. | Legacy/bootstrap contract regressed. | `test_g_conv_06_legacy_compatibility_gate` + `test_model_inventory_bootstrap.py` |
| **G-CONV-07** | Architecture docs list all G-CONV IDs and reference `area2_routing_authority`. | Documentation drift from code truth. | `test_g_conv_07_documentation_truth_gate` |
| **G-CONV-08** | `area2_operator_truth` exposes the same key set across Runtime, Writers-Room, and Improvement. | Cross-surface operator truth incoherent. | `test_g_conv_08_cross_surface_area2_truth_coherence`, `test_g_conv_08_runtime_truth_keys_match_bounded_http_surface` |

## Authority source of truth (code)

- [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) — `AREA2_AUTHORITY_REGISTRY`

## Operator truth (code)

- [`backend/app/runtime/area2_operator_truth.py`](../../backend/app/runtime/area2_operator_truth.py) — `build_area2_operator_truth`, `enrich_operator_audit_with_area2_truth`

## Operational state (code)

- [`backend/app/runtime/area2_operational_state.py`](../../backend/app/runtime/area2_operational_state.py) — `Area2OperationalState`, `NoEligibleDiscipline`

## Task 2 registry/routing convergence (cross-reference)

Named closure suite **G-T2-01**, **G-T2-02**, **G-T2-03**, **G-T2-04**, **G-T2-05**, **G-T2-06**, **G-T2-07**, **G-T2-08** — [`area2_task2_closure_gates.md`](./area2_task2_closure_gates.md), [`area2_registry_routing_convergence_closure_report.md`](./area2_registry_routing_convergence_closure_report.md), tests `backend/tests/runtime/test_area2_task2_closure_gates.py`. Authority map: [`area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py).
