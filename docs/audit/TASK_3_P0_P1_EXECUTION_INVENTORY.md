# Task 3 — P0/P1 Execution Inventory and Disposition Map

**Execution status (integrated run, 2026-04-09):** P0/P1 items in this inventory were **applied in the repository** (merge/split/rename/smoke relocation + non-GoC moves). Evidence: `docs/audit/TASK_3_VALIDATION_REPORT.md` § *Integrated-run verification*.

**Repository-truth amendment (2026-04-10):** Several paths named in the **markdown table below** are **historical** (2026-04-09 snapshot) and no longer exist on disk as written—especially `backend/tests/runtime/test_area2_*_closure_gates.py`, `ai_stack/tests/test_goc_phase*.py`, `tests/goc_gates/*`, and `tools/mcp_server/tests/test_mcp_m1_gates.py`. For **machine-checkable, current suite paths**, use [`docs/audit/task3_retained_gate_suites.json`](task3_retained_gate_suites.json) **version `task3-v2`** and [`docs/archive/documentation-consolidation-2026/TEST_RENAME_AND_NORMALIZATION_MAP.md`](../archive/documentation-consolidation-2026/TEST_RENAME_AND_NORMALIZATION_MAP.md).

## Scope lock

This document operationalizes Task 3 for:
- test naming cleanup,
- test suite structure cleanup,
- sidecar ownership/consolidation planning,
- non-GoC placement cleanup planning.

Out of scope:
- GoC namespace relocation,
- documentation rewrite programs,
- deep cross-stack closure.

## Disposition priority (enforced)

1. Merge into owning suite.
2. Split mixed-purpose suite.
3. Retain as justified gate/acceptance suite.
4. Remove as redundant.
5. Rename-only.
6. Absorb sidecars into self.

No lower-priority choice is permitted when a higher-priority option is still applicable, unless explicit justification is recorded.

## P0/P1 Active Test Inventory

Canonical paths below were refreshed **2026-04-10** to match files that exist on disk (see amendment note above for why earlier rows referenced removed names).

| Path | Current classification | Inclusion reason | Priority | Downstream task relevance | Chosen disposition | Disposition justification |
|---|---|---|---|---|---|---|
| `backend/tests/runtime/test_runtime_validation_commands_orchestration.py` | Mixed gate/meta orchestrator suite | Doc/command orchestration + closure alignment | P0 | Controls validation-command integrity | Retain as justified gate/acceptance suite | Successor surface for former `test_area2_task4_closure_gates.py`. |
| `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` | Runtime gate suite | Bootstrap + registry + routing operational proofs | P0 | Core retained-gate criteria anchor | Retain as justified gate/acceptance suite | Successor surface for former `test_area2_convergence_gates.py`. |
| `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` | Runtime final gate suite | Startup profiles + operator-truth reproducibility | P0 | Gate retention and naming normalization | Retain as justified gate/acceptance suite | Successor surface for former `test_area2_final_closure_gates.py`. |
| `backend/tests/test_authorization_boundaries.py` | Split contract suite | Successor module after omnibus split | P0 | Split rules proof point | Retain | Part of the seven-way split that replaced `test_coverage_expansion.py` (removed). Siblings: `test_constraint_validation.py`, `test_state_transition_rules.py`, `test_activity_logging_audit.py`, `test_error_response_contracts.py`, `test_bulk_operation_contracts.py`, `test_service_layer_edge_cases.py`. |
| `ai_stack/tests/test_goc_mvp_breadth_playability_regression.py` | Acceptance/gate suite | MVP breadth / playability regression anchor | P0 | Gate retention policy | Retain as justified gate/acceptance suite | Renamed from `test_goc_phase5_final_mvp_closure.py`. |
| `tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py` | MCP gate suite | Explicit gate contracts + report coupling | P0 | Gate rationale coverage and sidecar coupling | Retain as justified gate/acceptance suite | Renamed from `test_mcp_m1_gates.py`; same gate role. |
| `tests/experience_scoring_cli/test_experience_score_matrix_cli.py` | CLI gate/acceptance suite | Sidecar-heavy gate semantics | P0 | Sidecar ownership and gate retention | Retain as justified gate/acceptance suite | G9 threshold validator subprocess tests; fixtures under `tests/experience_scoring_cli/fixtures/`. |
| `backend/tests/runtime/test_runtime_model_ranking_synthesis_contracts.py` | Gate-style runtime suite | Ranking + synthesis orchestration contracts | P1 | Naming + retained gate scope | Retain as justified gate/acceptance suite | Renamed from `test_runtime_ranking_closure_gates.py`. |
| `backend/tests/runtime/test_runtime_drift_resistance.py` | Behavior suite | Drift-resistance regression surface | P1 | Naming normalization (done) | Retain | Renamed from `test_task4_drift_resistance.py`. |
| `backend/tests/runtime/test_narrative_continuity.py` | Behavior suite | Narrative continuity | P1 | Naming normalization (done) | Retain | Renamed from `test_task_1c_continuity.py`. |
| `backend/tests/runtime/test_narrative_thread_progression.py` | Behavior suite | Thread progression | P1 | Naming normalization (done) | Retain | Renamed from `test_task_1d_narrative_threads.py`. |
| `backend/tests/test_session_api_contracts.py` | Session API contract suite | Session API behavior and diagnostics contracts | P1 | Gate-vs-non-gate naming separation (done) | Retain | Renamed from `test_session_api_closure.py`. |
| `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py` | Acceptance/gate suite | Runtime graph seams + diagnostics | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Renamed from `test_goc_phase1_runtime_gate.py`. |
| `ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py` | Acceptance/gate suite | Breadth + continuity diagnostics | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Renamed from `test_goc_phase2_scenarios.py`. |
| `ai_stack/tests/test_goc_multi_turn_experience_quality.py` | Acceptance/gate suite | Multi-turn experience quality | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Renamed from `test_goc_phase3_experience_richness.py`. |
| `ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py` | Acceptance/gate suite | Long-run operator readiness | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Renamed from `test_goc_phase4_reliability_breadth_operator.py`. |
| `tools/mcp_server/tests/test_mcp_runtime_safe_session_surface.py` | MCP gate suite | Runtime-safe session surface | P1 | Naming + gate retention | Retain as justified gate/acceptance suite | Renamed from `test_mcp_m2_gates.py`. |
| `tests/smoke/test_smoke_contracts.py` | Smoke contract suite | Root smoke anti-drift | P1 | Naming normalization at root smoke surface (done) | Retain | Renamed from `test_w0_contracts.py`. |
| `tests/smoke/test_goc_module_structure_smoke.py` | Smoke structure suite | Module-structure smoke | P1 | Naming normalization at root smoke surface (done) | Retain | Renamed from `test_w1_module.py`. |

## Renamed-Test Map (executed, 2026-04-09)

| Former path | Current path | Why |
|---|---|---|
| `backend/tests/runtime/test_task4_drift_resistance.py` | `backend/tests/runtime/test_runtime_drift_resistance.py` | Remove historical task token; keep behavior meaning. |
| `backend/tests/runtime/test_task_1c_continuity.py` | `backend/tests/runtime/test_narrative_continuity.py` | Replace task code with behavior-readable intent. |
| `backend/tests/runtime/test_task_1d_narrative_threads.py` | `backend/tests/runtime/test_narrative_thread_progression.py` | Replace task code with explicit behavior. |
| `backend/tests/test_session_api_closure.py` | `backend/tests/test_session_api_contracts.py` | Remove opaque closure label; express contract role. |
| `tests/smoke/test_w0_contracts.py` | `tests/smoke/test_smoke_contracts.py` | Remove wave token from active smoke entrypoint. |
| `tests/smoke/test_w1_module.py` | `tests/smoke/test_goc_module_structure_smoke.py` | Replace wave token with explicit subject/intent. |

## Split-Suite Map (executed, 2026-04-09)

| Former source suite (removed) | Target suites | Split rationale |
|---|---|---|
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_authorization_boundaries.py` | Separate auth/permission boundaries from unrelated concerns. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_constraint_validation.py` | Separate validation/constraint behavior. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_state_transition_rules.py` | Separate state transition semantics. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_activity_logging_audit.py` | Separate audit/logging assertions. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_error_response_contracts.py` | Separate response-shape/status behavior. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_bulk_operation_contracts.py` | Separate bulk-operation behavior. |
| `backend/tests/test_coverage_expansion.py` | `backend/tests/test_service_layer_edge_cases.py` | Keep edge-case domain scoped and readable. |

## Merge-into-Owning-Suite Map (executed, 2026-04-09)

| Former source suite (removed) | Owning suite target | Merge rationale |
|---|---|---|
| `backend/tests/runtime/test_area2_workstream_a_closure_gates.py` | `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` | Intermediate merge target `test_area2_convergence_gates.py` was itself renamed; current owner is the operational bootstrap/registry suite. |
| `backend/tests/runtime/test_area2_workstream_b_closure_gates.py` | `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` | Intermediate merge target `test_area2_final_closure_gates.py` was itself renamed; current owner is the startup profiles / operator-truth suite. |

## Internal naming cleanup scope (material only)

Affected files for internal normalization during execution (current names):
- `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py`
- `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py`
- `backend/tests/runtime/test_runtime_validation_commands_orchestration.py`
- `ai_stack/tests/test_goc_mvp_breadth_playability_regression.py`
- `tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py`
- `tools/mcp_server/tests/test_mcp_runtime_safe_session_surface.py`
- `backend/tests/test_authorization_boundaries.py` and the other six split successors of removed `test_coverage_expansion.py` (see Split-Suite Map above)

Internal cleanup targets:
- Test function names that still encode historical process labels without technical meaning.
- Helper/fixture names that obscure owner role.
- Assertion labels/comments carrying stale phase/task execution language.

## Remainder summary

Additional historically named candidates outside P0/P1 remain in scope after this control surface is executed with the same decision rules and disposition-priority enforcement.
