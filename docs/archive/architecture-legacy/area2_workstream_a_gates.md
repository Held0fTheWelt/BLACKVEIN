# Area 2 — Workstream A practical convergence gates (G-A)

Workstream A closes **operational** convergence for canonical Runtime, Writers-Room, and Improvement paths: one primary routing/spec authority per surface, explicit non-competing auxiliary layers, no practical split-brain, healthy-path coherence, honest no-eligible discipline, operator-readable truth, and documentation parity.

These gates **do not** change `route_model` semantics, `StoryAIAdapter`, or guard/commit/reject authority.

**Binding vocabulary:** [`area2_dual_workstream_binding.md`](./area2_dual_workstream_binding.md)

**Authority map (code):** [`backend/app/runtime/area2_routing_authority.py`](../../backend/app/runtime/area2_routing_authority.py)

| Gate ID | Pass condition | Failure meaning | Test |
|---------|----------------|-----------------|------|
| **G-A-01** | Each canonical surface has registry coverage and non-empty primary spec authority strings; singular Task 2A policy entry. | Missing or competing undocumented authority for a canonical path. | `test_g_a_01_primary_authority_convergence_gate` |
| **G-A-02** | Translation / compatibility / support registry entries are explicit, bounded (scoped or non-canonical), and non-competing with `task2a_route_model`. | Auxiliary layers ambiguous or overlapping authoritative policy. | `test_g_a_02_non_competing_auxiliary_layer_gate` |
| **G-A-03** | Parallel LangGraph / legacy `RoutingPolicy` stacks are **not** canonical for Task 2A HTTP paths; `canonical_authority_summary` states compatibility-only posture. | Practical split-brain between stacks on canonical paths. | `test_g_a_03_canonical_path_coherence_gate` |
| **G-A-04** | Under `testing_bootstrap_on`, Runtime + WR + Improvement healthy paths route without routine `no_eligible_adapter` and retain truth shape on bounded HTTP. | Healthy canonical paths degrade or lose operator truth. | `test_g_a_04_healthy_canonical_path_confidence_gate` |
| **G-A-05** | True NEA is classified distinctly; `route_status` does not normalize NEA as generic healthy success. | Operators cannot tell NEA from healthy routing. | `test_g_a_05_no_eligible_non_normalization_gate` |
| **G-A-06** | `legibility` exposes direct readability fields (derived only). | Operator truth incomplete for convergence reads. | `test_g_a_06_operator_grade_convergence_readability_gate` |
| **G-A-07** | Listed architecture docs reference every **G-A-01** … **G-A-07** and `area2_routing_authority`. | Documentation drift from enforced convergence. | `test_g_a_07_documentation_truth_for_convergence_gate` |

## Related

- Combined closure: [`area2_dual_workstream_closure_report.md`](./area2_dual_workstream_closure_report.md)
- Workstream A report: [`area2_practical_convergence_closure_report.md`](./area2_practical_convergence_closure_report.md)
- Prior suites: **G-CONV-**, **G-FINAL-**, **G-T2-** (composed, not replaced)
