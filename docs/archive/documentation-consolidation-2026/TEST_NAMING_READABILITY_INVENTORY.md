# Test naming readability inventory (2026 consolidation)

This inventory records **active** test-surface naming issues that were addressed in the readability pass, plus items **explicitly deferred** (see justification column). Paths are relative to the repository root unless noted.

## Classification legend

| Class | Meaning |
|-------|---------|
| `historical_task_marker` | Name encodes a task/wave ID rather than behavior. |
| `historical_area_marker` | Name encodes legacy “Area 2” suite fragmentation. |
| `historical_phase_marker` | Name encodes roadmap phase vocabulary in filenames or test ids. |
| `historical_closure_marker` | “closure gates” style filename with no behavior description. |
| `vague_behavior_name` | File or test name does not state expected outcome. |
| `vague_scope_name` | Scope (what subsystem) is unclear from the name. |
| `acronym_without_context` | Acronym without domain anchor (e.g. unexplained “g9” in a test module). |
| `mixed_purpose_suite_name` | Single file name suggests unrelated purposes (if not split). |
| `historical_internal_label` | Internal gate id (`G-T4-01`) used as the **only** function name. |
| `misleading_fixture_or_helper_name` | Fixture/helper implies wrong scope or era. |

## Backend — `backend/tests/runtime/`

| Current path | Irregularity classes | Why not self-explanatory | Provisional disposition | Priority |
|--------------|----------------------|---------------------------|------------------------|----------|
| `test_runtime_validation_commands_orchestration.py` | (post-rename) `historical_internal_label` partially mitigated | Orchestrator still references documented gate ids in docstrings (intentional traceability). | **retain** filename; normalize **internal** `test_g_t4_*` → `test_full_validation_*` (done). | P0 |
| `test_runtime_operational_bootstrap_and_routing_registry.py` | (post-rename) | Replaces `test_area2_convergence_gates.py`. | **retain** (rename-only from prior step). | P0 |
| `test_runtime_startup_profiles_operator_truth.py` | (post-rename) | Replaces `test_area2_final_closure_gates.py`. | **retain** (rename-only). | P0 |
| `test_runtime_routing_registry_composed_proofs.py` | (post-rename) | Replaces `test_area2_task2_closure_gates.py`. | **retain** (rename-only). | P0 |
| `test_runtime_operator_comparison_cross_surface.py` | (post-rename) `historical_internal_label` | Replaces `test_area2_task3_closure_gates.py`; internal `test_g_t3_*` renamed to `test_operator_comparison_*`. | **internal-name cleanup** (done). | P0 |
| `test_runtime_model_ranking_synthesis_contracts.py` | (post-rename) `historical_internal_label` | Replaces `test_runtime_ranking_closure_gates.py`; internal `test_g_canon_rank_*` renamed to `test_runtime_ranking_*`. | **internal-name cleanup** (done). | P0 |
| `test_runtime_ai_turn_degraded_paths_tool_loop.py` | (post-rename) | Replaces `test_runtime_task4_hardening.py`. | **retain** (rename-only). | P0 |
| `test_cross_surface_operator_audit_contract.py` | `historical_internal_label` | Contained `test_g_conv_08_*`; renamed to `test_operator_truth_*` / `test_runtime_operator_truth_*`. | **internal-name cleanup** (done). | P0 |

## Backend — `backend/tests/improvement/`

| Current path | Irregularity classes | Why not self-explanatory | Provisional disposition | Priority |
|--------------|----------------------|---------------------------|------------------------|----------|
| `test_improvement_model_routing_denied.py` | (post-rename) | Replaces `test_improvement_task2a_routing_negative.py`. | **retain** (rename-only). | P1 |

## Repository root — `tests/`

| Current path | Irregularity classes | Why not self-explanatory | Provisional disposition | Priority |
|--------------|----------------------|---------------------------|------------------------|----------|
| `tests/experience_scoring_cli/` | `vague_scope_name` (prior: `goc_gates`) | Old directory suggested “gates” generically; new name states CLI/matrix validation scope. | **rename directory** (done). | P1 |

## AI stack — `ai_stack/tests/`

| Current path | Irregularity classes | Why not self-explanatory | Provisional disposition | Priority |
|--------------|----------------------|---------------------------|------------------------|----------|
| `test_goc_multi_turn_experience_quality.py` | `historical_phase_marker` (partial) | Replaces `test_goc_phase3_experience_richness.py`; **internal** `test_phase3_run_c_*` anchor renamed for S5 evidence alignment. | **internal-name cleanup** for anchor (done); remaining `test_phase3_*` / `test_phase4_*` / `test_phase5_*` in other modules **deferred** (see validation report). | P1 |
| `test_goc_runtime_breadth_continuity_diagnostics.py` | (post-rename) | Replaces phase-2 scenario filename. | **retain** (rename-only from prior step). | P2 |
| `test_goc_mvp_breadth_playability_regression.py` | `historical_phase_marker` | Still contains `test_phase5_*` function names. | **deferred** internal rename (large dependent doc surface). | P2 |
| `test_goc_reliability_longrun_operator_readiness.py` | `historical_phase_marker` | Still contains `test_phase4_*` function names. | **deferred** internal rename. | P2 |

## MCP / tools (if present in tree)

Prior pass renamed `test_mcp_m1_gates.py` → `test_mcp_operational_parity_and_registry.py`, `test_mcp_m2_gates.py` → `test_mcp_runtime_safe_session_surface.py` (inventory carried forward from earlier rename map).

## Revalidation note

Earlier consolidation notes referenced **deleted** module paths (`test_area2_*`, `test_goc_phase*_*.py`). This inventory was **revalidated** against the current tree (2026-04-10): those paths no longer exist as filenames; remaining risk is **stale markdown outside** `docs/testing-setup.md` and gate baselines—spot-fix as discovered.
