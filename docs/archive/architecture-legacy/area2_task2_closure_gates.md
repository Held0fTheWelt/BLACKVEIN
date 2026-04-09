# Area 2 — Task 2 registry/routing convergence gates (G-T2)

Explicit **Task 2** closure gates: registry/routing convergence across canonical Runtime, Writers-Room, and Improvement paths. These gates **compose** existing G-CONV / G-FINAL proofs in [`backend/tests/runtime/test_area2_task2_closure_gates.py`](../../backend/tests/runtime/test_area2_task2_closure_gates.py). They do **not** change `route_model` policy semantics, `StoryAIAdapter`, or guard/commit/reject authority.

**Authority source of truth (code):** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py) — `AREA2_AUTHORITY_REGISTRY`.

**Binding interpretation (minimal, mirrored in code docstring):** One **primary operational authority** per canonical path; **translation**, **compatibility**, and **support** layers remain only when **explicit, bounded, and non-competing** with that primary line.

| Gate ID | Pass condition | Failure meaning | Test coverage |
|--------|----------------|-----------------|---------------|
| **G-T2-01** | Singular primary Task 2A routing policy per surface; registry and `canonical_authority_summary` reflect non-competing layers. | Undocumented competing authority for canonical paths. | `test_g_t2_01_authority_convergence_gate` |
| **G-T2-02** | Named startup profiles map deterministically to bootstrap and `Area2OperationalState` inputs. | Ambiguous bootstrap truth. | `test_g_t2_02_startup_bootstrap_truth_gate` |
| **G-T2-03** | Under healthy profile, Runtime and bounded HTTP paths are routeable without routine `no_eligible_adapter`. | Healthy path still degrades to NEA or lacks coverage. | `test_g_t2_03_healthy_canonical_path_gate_runtime`, `test_g_t2_03_healthy_canonical_path_gate_bounded_http` |
| **G-T2-04** | `NoEligibleDiscipline` and `route_status` distinguish true NEA, setup gaps, degradation, and test isolation. | Operators cannot read honest discipline. | `test_g_t2_04_no_eligible_discipline_gate` |
| **G-T2-05** | `area2_operator_truth` / `legibility` is present and shape-valid on representative bounded HTTP plus derived legibility fields. | Operator truth missing or incomplete. | `test_g_t2_05_operator_truth_gate` |
| **G-T2-06** | Inventory surfaces satisfied by bootstrap + `build_writers_room_model_route_specs` coverage checks. | Contract/coverage drift. | `test_g_t2_06_inventory_coverage_truth_gate` |
| **G-T2-07** | Bootstrap-off test isolation and legacy registry expectations unchanged. | Legacy compatibility regressed. | `test_g_t2_07_legacy_compatibility_gate` |
| **G-T2-08** | Architecture docs list **G-T2-01** … **G-T2-08** and reference `area2_routing_authority`. | Documentation drift from enforced Task 2 closure. | `test_g_t2_08_documentation_truth_gate` |

## Related documents

- Closure report (PASS/FAIL, tests run): [`area2_registry_routing_convergence_closure_report.md`](./area2_registry_routing_convergence_closure_report.md)
- Prior gates: [`area2_convergence_gates.md`](./area2_convergence_gates.md), [`area2_final_closure_gates.md`](./area2_final_closure_gates.md)
