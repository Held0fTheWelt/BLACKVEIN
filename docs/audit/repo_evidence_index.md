# Repo Evidence Index (All-Gates Baseline + Closure Rerun)

## Purpose

This index enumerates repository evidence used across the gate baseline and all-gates closure rerun:

- Phase 0 mapping and canonical references
- G1-G10 + G9B baseline and aggregation surfaces
- closure rerun evidence and authoritative-preservation records

Each item is tagged by gate relevance and evidence role.

## Evidence Catalog

| repo_path | evidence_role | gates | evidence_type | notes |
| --- | --- | --- | --- | --- |
| `docs/ROADMAP_MVP_GoC.md` | canonical requirements source | Phase0, G1-G6 | doc | Authoritative gate and surface requirements. |
| `docs/GoC_Gate_Baseline_Audit_Plan.md` | baseline audit method source | Phase0, G1-G6 | doc | Command and gate audit framing. |
| `docs/CANONICAL_TURN_CONTRACT_GOC.md` | turn contract definition | G3, G4 | doc | Canonical turn record sections and fields. |
| `docs/rag_retrieval_hardening.md` | retrieval governance requirements | G5 | doc | Retrieval hardening and governance scope. |
| `docs/rag_retrieval_subsystem_closure.md` | retrieval closure guidance | G5 | doc | Retrieval closure evidence framing. |
| `docs/rag_task3_source_governance.md` | source governance contract | G5 | doc | Governance lane and provenance expectations. |
| `docs/rag_task4_evaluation_harness.md` | retrieval evaluation harness reference | G5 | doc | Evaluation harness expectations. |
| `docs/testing-setup.md` | command/cwd conventions | Phase0, G2, G6 | doc | Confirms `cd backend` + `--no-cov` patterns. |
| `content/modules/god_of_carnage/module.yaml` | authored module anchor | Phase0, G1, G5 | artifact | Canonical GoC module package evidence. |
| `ai_stack/goc_frozen_vocab.py` | shared semantic vocabulary implementation | G1 | code | Frozen labels and assertion helpers. |
| `ai_stack/tests/test_goc_frozen_vocab.py` | semantic parity checks | G1 | test | Canonical vocab consistency checks. |
| `ai_stack/mcp_canonical_surface.py` | canonical surface integration | G1 | code | Relevant canonical surface bridge (limited direct evidence found). |
| `backend/app/services/writers_room_model_routing.py` | writer routing consumer surface | G1 | code | Uses runtime routing contracts. |
| `backend/app/services/improvement_task2a_routing.py` | improvement routing consumer surface | G1, G2 | code | Uses runtime routing contracts/evidence. |
| `ai_stack/capabilities.py` | capability surface implementation | G2, G5 | code | Capability access and retrieval traces. |
| `ai_stack/operational_profile.py` | policy/operational profile surface | G2 | code | Operational hints and profile logic. |
| `backend/app/runtime/model_inventory_contract.py` | capability inventory contract | G2 | code | Required routing tuples by surface. |
| `backend/app/runtime/model_routing_contracts.py` | routing policy contract | G2 | code | Bounded enums and request/decision models. |
| `backend/app/runtime/model_routing.py` | runtime routing implementation | G2 | code | Policy decision engine implementation. |
| `backend/app/runtime/model_routing_evidence.py` | routing observation contract | G2 | code | Deterministic evidence payload and diagnostics. |
| `backend/app/runtime/area2_routing_authority.py` | routing authority boundary | G2 | code | Authority scope for routing decisions. |
| `backend/tests/runtime/test_model_routing_evidence.py` | routing observation test evidence | G2 | test | Verifies routing_evidence shape and semantics. |
| `backend/tests/runtime/test_decision_policy.py` | policy validation test evidence | G2 | test | Verifies action policy taxonomy/validation. |
| `ai_stack/goc_turn_seams.py` | turn seam projections | G3, G4 | code | Operator canonical turn projection and seam outputs. |
| `ai_stack/runtime_turn_contracts.py` | runtime turn constants/types | G3 | code | Stable diagnostics vocabulary constants. |
| `ai_stack/langgraph_runtime.py` | runtime turn executor and output packaging | G3, G4, G5 | code | Runtime state, retrieval/routing, graph diagnostics. |
| `backend/app/services/ai_stack_evidence_service.py` | backend evidence aggregation | G3, G5 | code | Session evidence and retrieval influence summary. |
| `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py` | runtime graph seams + diagnostics | G3, G4 | test | Gate-aligned runtime tests (successor to removed `test_goc_phase1_runtime_gate.py`). |
| `ai_stack/scene_director_goc.py` | scene direction control logic | G4 | code | Deterministic selection and bounded modes. |
| `ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py` | breadth / continuity scenario tests | G4 | test | Scenario behavior checks (successor to removed `test_goc_phase2_scenarios.py`). |
| `ai_stack/rag.py` | retrieval governance implementation | G5 | code | Evidence lanes, visibility classes, governance pathing. |
| `ai_stack/tests/test_rag.py` | retrieval test surface | G5 | test | Retrieval behavior checks (not executed here). |
| `ai_stack/tests/retrieval_eval_scenarios.py` | retrieval scenario harness | G5 | test | Retrieval-evaluative scenario coverage surface. |
| `ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py` | retrieval reliability / long-run operator surface | G5 | test | Reliability/breadth checks (successor to removed `test_goc_phase4_reliability_breadth_operator.py`). |
| `administration-tool/app.py` | admin UI/control plane routes | G6 | code | Governance pages and admin management routes. |
| `backend/app/api/v1/ai_stack_governance_routes.py` | admin governance APIs | G6 | code | Moderator/admin evidence APIs. |
| `backend/app/api/v1/improvement_routes.py` | governance-tied improvement APIs | G6 | code | Improvement lifecycle and review state flows. |
| `backend/tests/test_game_admin_routes.py` | admin route governance tests | G6 | test | Publish/review/runtime admin route behavior. |
| `backend/tests/test_admin_security.py` | admin security boundary tests | G6 | test | Role/IP/2FA/rate-limit/security checks. |
| `tests/smoke/test_admin_startup.py` | admin startup smoke surface | G6 | test | Lightweight startup smoke checks. |
| `backend/app/runtime/area2_validation_commands.py` | canonical pytest command pattern | Phase0, G2, G6 | code | Documents backend cwd and `--no-cov` invocation patterns. |
| `ai_stack/goc_roadmap_semantic_surface.py` | roadmap §4.2 label registry | G1, G2 | code | Shared semantic families aligned to routing / decision enums (parity tests). |
| `ai_stack/scene_direction_subdecision_matrix.py` | explicit G4 matrix rows | G4, G10 | code | Machine-readable scene-direction subdecision traceability. |
| `ai_stack/retrieval_governance_summary.py` | turn-level lane / visibility histogram | G5, G10 | code | Operator-visible retrieval governance summary on runtime turns. |
| `backend/app/contracts/writers_room_artifact_class.py` | Writers' Room artifact taxonomy | G7 | code | Roadmap §7.3 `artifact_class` enum. |
| `backend/app/contracts/improvement_entry_class.py` | Improvement typed entry enum | G8 | code | Roadmap §7.5 improvement entry classes. |
| `backend/app/contracts/improvement_operating_loop.py` | Improvement loop stage enum + contract version | G8 | code | Roadmap §6.8 typed loop stages. |
| `docs/goc_evidence_templates/` | G9/G9B human evidence shells + JSON schemas | G9, G9B | doc | G9 matrix, G9B raw/delta/reconciliation templates, manifest, `g9b_level_b_attempt_record.template.json`; `schemas/` (incl. `g9b_level_b_attempt_record.schema.json`); scaffolding only. |
| `scripts/g9_threshold_validator.py` | §6.9 threshold arithmetic helper | G9 | code | Validates filled matrices; does not invent scores. |
| `tests/experience_scoring_cli/test_experience_score_matrix_cli.py` | Validator CLI regression tests | G9 | test | Pytest subprocess coverage for `scripts/g9_threshold_validator.py` with fixtures under `tests/experience_scoring_cli/fixtures/`. |
| `ai_stack/goc_g9_roadmap_scenarios.py` | Frozen §6.9 scenario ids + failure_oriented defaults | G9 | code | Single source with templates and retrieval-heavy test. |
| `ai_stack/goc_s4_misinterpretation_scenario.py` | Canonical §8.2 S4 three-turn chain (misroute / correction / incorporation) | G9 | code | Shared by S4 pytest and capture script. |
| `ai_stack/tests/test_goc_roadmap_s4_misinterpretation_correction.py` | Roadmap S4 automated anchor | G9 | test | `test_roadmap_s4_misinterpretation_correction_chain`; collected by `pytest ai_stack/tests` (see `ai-stack-tests.yml`). |
| `scripts/g9_level_a_evidence_capture.py` | G9 Level A structured evidence dump (graph.run excerpts) | G9 | code | S4 uses `goc_s4_misinterpretation_scenario`; `--evidence-run-scope s4_closure_partial` or `s5_targeted_partial` for partial bundles; full run still emits S1–S6. |
| `tests/reports/evidence/g9_level_a_20260408/` | Partial G9 state (S4 unscored; validator incomplete) | G9, G9B | artifact | Historical; superseded for threshold story by `g9_level_a_fullsix_20260410`. |
| `tests/reports/evidence/g9_level_a_fullsix_20260410/` | Full six-scenario G9 matrix (A), pytest log, scenario JSON, validator output (A); Evaluator B matrix + `g9b_raw_score_sheet_evaluator_b.json` (current B: `evaluator_b_claude_system_20260409`, ingested strict-blind handoff return); `g9b_score_delta_record.json` (full 6×5 `per_cell_delta`, score_a−score_b); G9B manifest `level_b_attempt_insufficient_independence`; `g9b_level_b_attempt_record.json` (`failed_insufficient_independence`, `independence_classification_primary: insufficient_process_separation`); `g9b_evaluator_b_declaration.json` includes `repository_task_b_post_return_bundle_linkage` (repo-only; external return left top-level A/delta refs empty) | G9, G9B | artifact | **Authoritative** evaluative run; G9 §6.9 `pass_all: true` on Evaluator A. See `gate_G9_experience_acceptance_baseline.md` / `gate_G9B_evaluator_independence_baseline.md`. |
| `tests/reports/evidence/g10_backend_e2e_20260409/` | Backend G10 audit-plan pytest trio transcript + `run_metadata.json` | G10 | artifact | **Current** integrated backend E2E witness: 15 passed, `exit_code: 0` (`pytest_g10_backend_trio.txt`). Step 11 of §6.11 remains anchored on `g9_level_a_fullsix_20260410`, not superseded. See `gate_G10_end_to_end_closure_baseline.md`. |
| `tests/reports/evidence/all_gates_closure_20260409/` | Canonical rerun transcript bundle for G1–G8 plus G9/G9B/G10 validation checks and preservation-policy metadata | G1-G10, G9B | artifact | All canonical execution paths that can run in-repo were rerun and archived; G9/G9B/G10 authoritative artifacts were preserved unless contradiction required regeneration. |
| `tests/reports/evidence/g9_level_a_fullsix_20260409/` | Full six-scenario G9 matrix (historical) | G9, G9B | artifact | Complete failed §6.9 run (`pass_all: false`); **historical context only** — superseded by `g9_level_a_fullsix_20260410`. |
| `tests/reports/evidence/g9_s4_closure_20260409/` | S4-only closure partial bundle (`evidence_run_scope: s4_closure_partial`) | G9 | artifact | Scenario JSON + `run_metadata.json` + S4 pytest witness files; not a full six-scenario G9 rerun. |
| `tests/reports/evidence/g9_s5_targeted_20260409/` | S5-only targeted partial bundle (`evidence_run_scope: s5_targeted_partial`) | G9 | artifact | S5 scenario JSON, `run_metadata.json`, `pytest_s5_anchor.txt`, notes, provisional S5-only evaluator row; not a full six-scenario G9 matrix; see `gate_G9_experience_acceptance_baseline.md`. |

## Evidence-Quality Basis Used For This Block

- **High:** direct authoritative docs + direct implementation + direct tests tied to the same gate subject.
- **Medium:** authoritative docs + implementation evidence without runtime execution in this block.
- **Low:** indirect or partial mapping where canonical relevance is plausible but not fully resolved.

## Known Coverage Gaps (Current)

- Level B evaluator independence evidence remains insufficient (`failed_insufficient_independence`); this is an evidential blocker, not a repo-local implementation blocker.
- CI parity remains Python 3.10 while this closure rerun was on Python 3.13.12 (`docs/testing-setup.md`).
