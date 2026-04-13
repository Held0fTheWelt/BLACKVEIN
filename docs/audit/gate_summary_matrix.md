# Gate Summary Matrix (GoC Baseline Audit)

Dual-status model per `docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_GoC.md` §11.1 and `docs/GoC_Gate_Baseline_Audit_Plan.md`: each gate has **structural_status** and **closure_level_status**. This matrix summarizes the baseline captured in per-gate reports under `docs/audit/`.

| Gate | structural_status | closure_level_status | evidence_quality | Per-gate report |
|------|-------------------|----------------------|------------------|-----------------|
| G1 Shared Semantic Contract | `green` | `level_a_capable` | `high` | [gate_G1_semantic_contract_baseline.md](gate_G1_semantic_contract_baseline.md) |
| G2 Capability / Policy / Observation | `green` | `level_a_capable` | `high` | [gate_G2_capability_policy_observation_baseline.md](gate_G2_capability_policy_observation_baseline.md) |
| G3 Canonical Dramatic Turn Record | `green` | `level_a_capable` | `high` | [gate_G3_turn_record_baseline.md](gate_G3_turn_record_baseline.md) |
| G4 Scene Direction Boundary | `green` | `level_a_capable` | `high` | [gate_G4_scene_direction_boundary_baseline.md](gate_G4_scene_direction_boundary_baseline.md) |
| G5 Retrieval Governance | `green` | `level_a_capable` | `high` | [gate_G5_retrieval_governance_baseline.md](gate_G5_retrieval_governance_baseline.md) |
| G6 Admin Governance | `green` | `level_a_capable` | `high` | [gate_G6_admin_governance_baseline.md](gate_G6_admin_governance_baseline.md) |
| G7 Writers' Room Operating | `green` | `level_a_capable` | `high` | [gate_G7_writers_room_operating_baseline.md](gate_G7_writers_room_operating_baseline.md) |
| G8 Improvement Path Operating | `green` | `level_a_capable` | `high` | [gate_G8_improvement_operating_baseline.md](gate_G8_improvement_operating_baseline.md) |
| G9 Experience Acceptance | `green` | `level_a_capable` | `high` | [gate_G9_experience_acceptance_baseline.md](gate_G9_experience_acceptance_baseline.md) |
| G9B Evaluator Independence | `green` | `level_a_capable` | `high` | [gate_G9B_evaluator_independence_baseline.md](gate_G9B_evaluator_independence_baseline.md) |
| G10 End-to-End Closure | `green` | `level_a_capable` | `high` | [gate_G10_end_to_end_closure_baseline.md](gate_G10_end_to_end_closure_baseline.md) |

## Notes

- **Clone reproducibility:** `.gitignore` lists `/tests/reports`; only intentionally tracked files under `tests/reports/` (e.g. the MCP M1 closure Markdown reports) ship with every clone. Paths such as `tests/reports/evidence/...` cited below are **machine-local capture trees** unless explicitly listed by `git ls-files`—regenerate them with the suites/commands in the per-gate baselines and [Testing](../../README.md#testing). Policy detail: [TASK_1A_REPOSITORY_BASELINE.md](TASK_1A_REPOSITORY_BASELINE.md) Appendix B.
- **Task 4 closure controls:** Final validation and closure decisions for cleanup program status are tracked in [TASK_4_FINAL_VALIDATION_COMMAND_SET.md](TASK_4_FINAL_VALIDATION_COMMAND_SET.md) and [TASK_4_FINAL_CLEANUP_CLOSURE_REPORT.md](TASK_4_FINAL_CLEANUP_CLOSURE_REPORT.md).
- **Structural `green`:** G1–G10 and G9B are structural `green` on canonical execution evidence. G1–G8 promotion evidence is archived in `tests/reports/evidence/all_gates_closure_20260409/`; G9/G9B authoritative evaluative bundle remains `g9_level_a_fullsix_20260410`; G10 authoritative trio remains `g10_backend_e2e_20260409` and was revalidated by `all_gates_closure_20260409/g10_backend_trio_rerun.txt`.
- **`closure_level_status` and program closure:** G10 is now `level_a_capable` with prerequisite gate health satisfied (G1–G8 structural green) and authoritative G9/G9B alignment. Program-level Level B remains blocked by G9B independence evidence (`failed_insufficient_independence`), so no `level_b_capable` upgrade is made.
- **G9B** is listed after G9; ordering follows audit dependency (`docs/GoC_Gate_Baseline_Audit_Plan.md` §5).
- Operational gates G7/G8 use `structural_status` for operational sufficiency per their baseline notes—not G1–G6 static-only semantics.
