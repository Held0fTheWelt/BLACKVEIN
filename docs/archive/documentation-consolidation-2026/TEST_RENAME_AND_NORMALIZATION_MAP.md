# Test rename and normalization map (2026 consolidation)

Maps **former** paths to **current** paths, disposition, and whether references were updated. “Former” names reflect the pre-readability surface; some moves were completed in an earlier chunk of the same program of work.

## Backend runtime suites

| Former path | New path | Disposition | Reason for new name | Split/merge | References updated |
|-------------|----------|-------------|---------------------|-------------|-------------------|
| `backend/tests/runtime/test_area2_convergence_gates.py` | `backend/tests/runtime/test_runtime_operational_bootstrap_and_routing_registry.py` | rename-only | States bootstrap, registry, routing, and operational truth under test. | merge implicit (single owning suite) | Yes (`area2_validation_commands`, imports, docs) |
| `backend/tests/runtime/test_area2_final_closure_gates.py` | `backend/tests/runtime/test_runtime_startup_profiles_operator_truth.py` | rename-only | States startup profiles and operator-truth reproducibility. | merge implicit | Yes |
| `backend/tests/runtime/test_area2_task2_closure_gates.py` | `backend/tests/runtime/test_runtime_routing_registry_composed_proofs.py` | rename-only | Composed proofs over registry/routing authority. | merge implicit | Yes |
| `backend/tests/runtime/test_area2_task3_closure_gates.py` | `backend/tests/runtime/test_runtime_operator_comparison_cross_surface.py` | rename-only | States cross-surface operator comparison contracts. | merge implicit | Yes |
| `backend/tests/runtime/test_area2_task4_closure_gates.py` | `backend/tests/runtime/test_runtime_validation_commands_orchestration.py` | rename-only | Executable orchestration of validation + doc alignment. | merge implicit | Yes |
| `backend/tests/runtime/test_area2_convergence_gates.py` (duplicate listing) | — | — | — | — | — |
| `backend/tests/runtime/test_runtime_ranking_closure_gates.py` | `backend/tests/runtime/test_runtime_model_ranking_synthesis_contracts.py` | rename-only | Ranking stage + synthesis orchestration contracts. | merge implicit | Yes |
| `backend/tests/runtime/test_runtime_task4_hardening.py` | `backend/tests/runtime/test_runtime_ai_turn_degraded_paths_tool_loop.py` | rename-only | Degraded AI-turn paths and tool-loop behavior. | merge implicit | Yes |

## Improvement routing

| Former path | New path | Disposition | Reason | Split/merge | References updated |
|-------------|----------|-------------|--------|-------------|-------------------|
| `backend/tests/improvement/test_improvement_task2a_routing_negative.py` | `backend/tests/improvement/test_improvement_model_routing_denied.py` | rename-only | Negative routing = denied/missing adapter honesty. | merge implicit | Yes |

## Repository root CLI tests

| Former path | New path | Disposition | Reason | Split/merge | References updated |
|-------------|----------|-------------|--------|-------------|-------------------|
| `tests/goc_gates/` | `tests/experience_scoring_cli/` | rename-only | Names the G9 experience score matrix CLI surface. | merge implicit | Yes (CI paths, `docs/testing-setup.md`) |

## AI stack (filename level)

| Former path | New path | Disposition | Reason | Split/merge | References updated |
|-------------|----------|-------------|--------|-------------|-------------------|
| `ai_stack/tests/test_goc_phase2_scenarios.py` | `ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py` | rename-only | Breadth + continuity diagnostics scenarios. | merge implicit | Partial (this pass: `docs/testing-setup.md`, G9 baseline, `g9_level_a_evidence_capture.py`) |
| `ai_stack/tests/test_goc_phase3_experience_richness.py` | `ai_stack/tests/test_goc_multi_turn_experience_quality.py` | rename-only | Multi-turn experience quality. | merge implicit | Partial + S5 anchor rename |
| `ai_stack/tests/test_goc_phase5_final_mvp_closure.py` | `ai_stack/tests/test_goc_mvp_breadth_playability_regression.py` | rename-only | MVP breadth / playability regression. | merge implicit | Partial (`docs/testing-setup.md` automated bundle) |
| `ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py` | `ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py` | rename-only | Long-run operator readiness. | merge implicit | Deferred doc sweep beyond testing-setup |

> Note: Verify exact phase4 target filename on disk if docs still mention the old string; the authoritative list is `ai_stack/tests/*.py`.

## MCP server tests (tools)

| Former path | New path | Disposition | Reason | References updated |
|-------------|----------|-------------|--------|-------------------|
| `tools/mcp_server/tests/test_mcp_m1_gates.py` | `tools/mcp_server/tests/test_mcp_operational_parity_and_registry.py` | rename-only | Operational parity + registry. | Yes (per prior pass) |
| `tools/mcp_server/tests/test_mcp_m2_gates.py` | `tools/mcp_server/tests/test_mcp_runtime_safe_session_surface.py` | rename-only | Safe session surface contracts. | Yes |

## No split required

No mixed-purpose file in this pass required **split** after inspection: orchestration stayed in `test_runtime_validation_commands_orchestration.py`, composed proofs stayed in `test_runtime_routing_registry_composed_proofs.py`.

## Documentation co-renames (not test files)

Updated to embed **exact** `area2_dual_closure_pytest_invocation()` / `area2_task4_full_closure_pytest_invocation()` strings and new module basenames:

- `docs/testing-setup.md`
- `docs/archive/architecture-legacy/area2_dual_workstream_closure_report.md`
- `docs/archive/architecture-legacy/area2_validation_hardening_closure_report.md`
- `docs/archive/architecture-legacy/area2_task4_closure_gates.md`
- `docs/archive/architecture-legacy/area2_runtime_ranking_closure_report.md`
- `docs/technical/ai/llm-slm-role-stratification.md`
- `docs/technical/architecture/ai_story_contract.md`
- `docs/audit/gate_G9_experience_acceptance_baseline.md`
- `.github/workflows/backend-tests.yml`
- `scripts/g9_level_a_evidence_capture.py`
- Selected `outgoing/**/scenario_goc_roadmap_s5_primary_failure_fallback.json` anchor metadata
