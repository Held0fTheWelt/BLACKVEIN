# Task 3 — P0/P1 Execution Inventory and Disposition Map

**Execution status (integrated run, 2026-04-09):** P0/P1 items in this inventory were **applied in the repository** (merge/split/rename/smoke relocation + non-GoC moves). Evidence: `docs/audit/TASK_3_VALIDATION_REPORT.md` § *Integrated-run verification*.

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

Canonical paths below reflect the **post-execution** tree (2026-04-09). Removed predecessors are recorded only in the executed maps below.

| Path | Current classification | Inclusion reason | Priority | Downstream task relevance | Chosen disposition | Disposition justification |
|---|---|---|---|---|---|---|
| `backend/tests/runtime/test_area2_task4_closure_gates.py` | Mixed gate/meta orchestrator suite | High ownership ambiguity and broad orchestration behavior | P0 | Controls split-vs-retain gate logic | Retain as justified gate/acceptance suite | Suite acts as cross-surface gate orchestrator; merge/split would hide gate role and evidence intent. |
| `backend/tests/runtime/test_area2_convergence_gates.py` | Runtime gate suite | Historical naming + cross-doc assertions; hosts merged former workstream A gate block | P0 | Core retained-gate criteria anchor | Retain as justified gate/acceptance suite | Cross-surface authority/routing contract validation is non-redundant. |
| `backend/tests/runtime/test_area2_final_closure_gates.py` | Runtime final gate suite | Historical naming + adjacency to convergence gates; hosts merged former workstream B gate block | P0 | Gate retention and naming normalization | Retain as justified gate/acceptance suite | Distinct end-state gate semantics and acceptance role. |
| `backend/tests/test_authorization_boundaries.py` | Split contract suite | Successor module after omnibus split | P0 | Split rules proof point | Retain | Part of the seven-way split that replaced `test_coverage_expansion.py` (removed). Siblings: `test_constraint_validation.py`, `test_state_transition_rules.py`, `test_activity_logging_audit.py`, `test_error_response_contracts.py`, `test_bulk_operation_contracts.py`, `test_service_layer_edge_cases.py`. |
| `ai_stack/tests/test_goc_phase5_final_mvp_closure.py` | Acceptance/gate suite | High-visibility historical naming + broad acceptance role | P0 | Gate retention policy | Retain as justified gate/acceptance suite | Provides explicit acceptance breadth semantics not reducible to unit-level suites. |
| `tools/mcp_server/tests/test_mcp_m1_gates.py` | MCP gate suite | Explicit gate contracts + report coupling | P0 | Gate rationale coverage and sidecar coupling | Retain as justified gate/acceptance suite | Distinct MCP governance/contract gate role; non-redundant. |
| `tests/goc_gates/test_g9_threshold_validator.py` | CLI gate/acceptance suite | Sidecar-heavy gate semantics | P0 | Sidecar ownership and gate retention | Retain as justified gate/acceptance suite | Validates threshold acceptance contract through CLI path; must remain explicit. |
| `backend/tests/runtime/test_runtime_ranking_closure_gates.py` | Gate-style runtime suite | Historical naming but coherent role | P1 | Naming + retained gate scope | Retain as justified gate/acceptance suite | Ranking closure contract is cross-stage and non-redundant. |
| `backend/tests/runtime/test_runtime_drift_resistance.py` | Behavior suite | Drift-resistance regression surface | P1 | Naming normalization (done) | Retain | Renamed from `test_task4_drift_resistance.py`. |
| `backend/tests/runtime/test_narrative_continuity.py` | Behavior suite | Narrative continuity | P1 | Naming normalization (done) | Retain | Renamed from `test_task_1c_continuity.py`. |
| `backend/tests/runtime/test_narrative_thread_progression.py` | Behavior suite | Thread progression | P1 | Naming normalization (done) | Retain | Renamed from `test_task_1d_narrative_threads.py`. |
| `backend/tests/test_session_api_contracts.py` | Session API contract suite | Session API behavior and diagnostics contracts | P1 | Gate-vs-non-gate naming separation (done) | Retain | Renamed from `test_session_api_closure.py`. |
| `ai_stack/tests/test_goc_phase1_runtime_gate.py` | Acceptance/gate suite | Phase marker + gate semantics | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Distinct runtime gate role with acceptance semantics. |
| `ai_stack/tests/test_goc_phase2_scenarios.py` | Acceptance/gate suite | Phase marker + scenario acceptance role | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Non-redundant phase-scenario acceptance surface. |
| `ai_stack/tests/test_goc_phase3_experience_richness.py` | Acceptance/gate suite | Phase marker + quality acceptance role | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Experience-quality acceptance cannot be reduced to one lower suite. |
| `ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py` | Acceptance/gate suite | Phase marker + reliability breadth role | P1 | Gate retention policy | Retain as justified gate/acceptance suite | Cross-cutting reliability acceptance role is distinct. |
| `tools/mcp_server/tests/test_mcp_m2_gates.py` | MCP gate suite | Milestone-coded naming | P1 | Naming + gate retention | Retain as justified gate/acceptance suite | M2 gate validates expanded MCP contract closure. |
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
| `backend/tests/runtime/test_area2_workstream_a_closure_gates.py` | `backend/tests/runtime/test_area2_convergence_gates.py` | Workstream A is gate fragment with owner semantics already present in convergence gate. |
| `backend/tests/runtime/test_area2_workstream_b_closure_gates.py` | `backend/tests/runtime/test_area2_final_closure_gates.py` | Workstream B is gate fragment better represented under final gate ownership. |

## Internal naming cleanup scope (material only)

Affected files for internal normalization during execution:
- `backend/tests/runtime/test_area2_convergence_gates.py`
- `backend/tests/runtime/test_area2_final_closure_gates.py`
- `backend/tests/runtime/test_area2_task4_closure_gates.py`
- `ai_stack/tests/test_goc_phase5_final_mvp_closure.py`
- `tools/mcp_server/tests/test_mcp_m1_gates.py`
- `tools/mcp_server/tests/test_mcp_m2_gates.py`
- `backend/tests/test_authorization_boundaries.py` and the other six split successors of removed `test_coverage_expansion.py` (see Split-Suite Map above)

Internal cleanup targets:
- Test function names that still encode historical process labels without technical meaning.
- Helper/fixture names that obscure owner role.
- Assertion labels/comments carrying stale phase/task execution language.

## Remainder summary

Additional historically named candidates outside P0/P1 remain in scope after this control surface is executed with the same decision rules and disposition-priority enforcement.
