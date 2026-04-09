# Canonical To Repo Mapping Table (Phase 0)

## Scope

This Phase 0 artifact maps canonical objects for the in-scope block only:

- Phase 0 mapping
- G1
- G2
- G3
- G4
- G5
- G6

Out of scope: G7, G8, G9, G9B, G10, aggregation, closure recommendation.

## Section 3.4 Anchor Label Registry

All initial mapping anchors from section 3.4 of `docs/GoC_Gate_Baseline_Audit_Plan.md` are explicitly labeled.

| canonical_name | repo_path | repo_owner_surface | mapping_confidence | notes | evidence_ref |
| --- | --- | --- | --- | --- | --- |
| GoC authored module | `content/modules/god_of_carnage/` | module_substrate_surface | high | Direct GoC authored package anchor. | `content/modules/god_of_carnage/module.yaml` |
| Runtime + scene + turn seams | `ai_stack/` | shared_runtime_surface | medium | Broad tree; canonical sub-ownership must be finalized per object row below. | `ai_stack/langgraph_runtime.py`, `ai_stack/goc_turn_seams.py` |
| Backend runtime and evidence APIs | `backend/app/runtime/` | backend_runtime_surface | high | Direct runtime/evidence contract surface. | `backend/app/runtime/model_routing_contracts.py`, `backend/app/runtime/model_routing_evidence.py` |
| Backend runtime and evidence APIs | `backend/app/services/` | backend_service_surface | medium | Broad services namespace; object-level ownership remains mixed. | `backend/app/services/ai_stack_evidence_service.py` |
| Writers' Room service/API | `writers-room/` | writers_room_surface | high | Direct Writers' Room surface. | `writers-room/app.py` |
| Writers' Room service/API | `backend/app/services/writers_room_service.py` | writers_room_service_surface | high | Direct named Writers' Room service path. | `backend/app/services/writers_room_service.py` |
| Writers' Room service/API | `backend/app/api/v1/writers_room_routes.py` | writers_room_api_surface | high | Direct named Writers' Room API path. | `backend/app/api/v1/writers_room_routes.py` |
| Improvement service/API | `backend/app/services/improvement_service.py` | improvement_service_surface | high | Direct named Improvement service path. | `backend/app/services/improvement_service.py` |
| Improvement service/API | `backend/app/api/v1/improvement_routes.py` | improvement_api_surface | high | Direct named Improvement API path. | `backend/app/api/v1/improvement_routes.py` |
| Admin control surface | `administration-tool/` | admin_control_surface | high | Direct admin UI/control-plane surface. | `administration-tool/app.py` |
| Existing reports | `tests/reports/` | test_report_surface | medium | Broad report area; gate-to-artifact ownership must be selected per gate. | `tests/reports/GOC_PHASE3_EXPERIENCE_RICHNESS_REPORT.md` |
| Roadmap/governance docs | `docs/` | governance_docs_surface | medium | Broad docs area; canonical references mapped per row below. | `docs/ROADMAP_MVP_GoC.md`, `docs/GoC_Gate_Baseline_Audit_Plan.md` |

## Canonical Surface Mapping (Roadmap Section 4)

| canonical_name | repo_path | repo_owner_surface | mapping_confidence | notes | evidence_ref |
| --- | --- | --- | --- | --- | --- |
| Module Substrate Surface | `content/modules/god_of_carnage/` | module_substrate_surface | high | Canonical authored module package exists and is structured. | `docs/ROADMAP_MVP_GoC.md` section 4.1; `content/modules/god_of_carnage/module.yaml` |
| Shared Semantic Surface | `ai_stack/goc_roadmap_semantic_surface.py` + `ai_stack/goc_frozen_vocab.py` | semantic_surface | high | Roadmap §4.2 registry (`TASK_TYPES`, `ROUTING_LABELS`, …) plus slice frozen vocab (`SCENE_FUNCTIONS`, …). Backend parity: `backend/tests/test_goc_semantic_parity.py`. | `docs/ROADMAP_MVP_GoC.md` section 4.2; `ai_stack/goc_roadmap_semantic_surface.py` |
| Capability Surface | `ai_stack/capabilities.py` | capability_surface | high | Capability registry and retrieval trace interfaces exist. | `docs/ROADMAP_MVP_GoC.md` section 4.3; `ai_stack/capabilities.py` |
| Policy Surface | `backend/app/runtime/model_routing_contracts.py` | routing_policy_surface | high | Routing policy enums/contracts are explicit and versionable. | `docs/ROADMAP_MVP_GoC.md` section 4.4; `backend/app/runtime/model_routing_contracts.py` |
| Turn Record Surface | `ai_stack/goc_turn_seams.py` | turn_record_surface | medium | Canonical projection helpers exist; full section-level completeness requires gate-level validation. | `docs/ROADMAP_MVP_GoC.md` section 4.5; `ai_stack/goc_turn_seams.py` |
| Retrieval Governance Surface | `ai_stack/rag.py` | retrieval_governance_surface | high | Explicit lane/visibility/governance structures are present. | `docs/ROADMAP_MVP_GoC.md` section 4.6; `ai_stack/rag.py` |
| Experience Acceptance Surface | `docs/GATE_SCORING_POLICY_GOC.md` | experience_acceptance_surface | medium | Out-of-scope for this block execution, mapped for dependency trace only. | `docs/ROADMAP_MVP_GoC.md` section 4.7; `docs/GATE_SCORING_POLICY_GOC.md` |

## Gate Subject Mapping (Roadmap Section 6.1-6.6)

| canonical_name | repo_path | repo_owner_surface | mapping_confidence | notes | evidence_ref |
| --- | --- | --- | --- | --- | --- |
| G1 Shared Semantic Contract | `ai_stack/goc_roadmap_semantic_surface.py`, `story_runtime_core/model_registry.py`, `ai_stack/langgraph_runtime.py` | semantic_surface | high | Shared enums: registry + `RoutingPolicy` route reasons aligned with `RouteReasonCode`; graph `task_type` uses `TaskKind` strings. | `docs/ROADMAP_MVP_GoC.md` section 6.1; `ai_stack/tests/test_goc_roadmap_semantic_surface.py`, `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py`, `backend/tests/test_goc_semantic_parity.py` |
| G2 Capability/Policy/Observation Separation | `backend/app/runtime/model_routing_contracts.py` | routing_contract_surface | high | Capability/policy/observation structures are explicitly separated in runtime contracts/evidence. | `docs/ROADMAP_MVP_GoC.md` section 6.2; `backend/app/runtime/model_routing_evidence.py` |
| G3 Canonical Dramatic Turn Record | `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `ai_stack/goc_turn_seams.py`, `ai_stack/goc_field_initialization_envelope.py` | turn_contract_surface | high | Operator projection + roadmap §6.3 `dramatic_turn_record`; uninitialized fields use `goc_uninitialized_field_envelope_v1` only. | `docs/CANONICAL_TURN_CONTRACT_GOC.md` §8.1; `ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py` |
| G4 Scene Direction Boundary | `ai_stack/scene_director_goc.py`, `ai_stack/scene_direction_subdecision_matrix.py` | scene_direction_surface | high | Matrix rows include G4 seam columns; director validates labels against matrix. | `docs/ROADMAP_MVP_GoC.md` section 6.4; `ai_stack/tests/test_scene_direction_subdecision_matrix.py` |
| G5 Retrieval Governance | `ai_stack/rag.py` | retrieval_governance_surface | high | Retrieval governance lanes and visibility classes are explicitly implemented. | `docs/ROADMAP_MVP_GoC.md` section 6.5; `docs/rag_task3_source_governance.md` |
| G6 Admin Governance | `administration-tool/app.py` | admin_control_surface | medium | Admin governance/readiness routes exist; semantic-boundary enforcement needs cross-route proof. | `docs/ROADMAP_MVP_GoC.md` section 6.6; `backend/app/api/v1/ai_stack_governance_routes.py` |

## Required Evidence Artifact Mapping (Roadmap Section 13, In-Scope)

| canonical_name | repo_path | repo_owner_surface | mapping_confidence | notes | evidence_ref |
| --- | --- | --- | --- | --- | --- |
| `shared_semantic_contract.*` | `ai_stack/goc_roadmap_semantic_surface.py`, `ai_stack/goc_frozen_vocab.py` | semantic_surface | high | Registry maps roadmap set names to code; slice vocab in frozen module. | `docs/ROADMAP_MVP_GoC.md` section 13; `ai_stack/tests/test_goc_roadmap_semantic_surface.py` |
| `capability_contract.*` | `ai_stack/capabilities.py` | capability_surface | high | Capability helper and trace semantics are present. | `docs/ROADMAP_MVP_GoC.md` section 13; `ai_stack/capabilities.py` |
| `routing_policy_contract.*` | `backend/app/runtime/model_routing_contracts.py` | routing_policy_surface | high | Policy enums/records are explicit and bounded. | `backend/app/runtime/model_routing_contracts.py` |
| `routing_observation_contract.*` | `backend/app/runtime/model_routing_evidence.py` | routing_observation_surface | high | Routing observation evidence includes route reason and diagnostics shape. | `backend/tests/runtime/test_model_routing_evidence.py` |
| `dramatic_turn_record_contract.*` | `docs/CANONICAL_TURN_CONTRACT_GOC.md` | turn_contract_surface | high | §8.1 defines uninitialized envelope; `build_operator_canonical_turn_record` emits `dramatic_turn_record`. | `docs/CANONICAL_TURN_CONTRACT_GOC.md`; `ai_stack/goc_turn_seams.py` |
| `scene_direction_subdecision_matrix.*` | `ai_stack/scene_direction_subdecision_matrix.py` | scene_direction_surface | high | `SCENE_DIRECTION_SUBDECISION_ROWS` with G4 columns; bound in `scene_director_goc`. | `docs/ROADMAP_MVP_GoC.md` section 6.4; `ai_stack/scene_direction_subdecision_matrix.py` |
| `retrieval_governance_contract.*` | `ai_stack/rag.py` | retrieval_governance_surface | high | Governance lanes and visibility classification are explicit. | `ai_stack/rag.py`; `docs/rag_task3_source_governance.md` |
| `gate_results_report.*` (G1-G6 scope) | `docs/audit/` | audit_output_surface | high | This block produces per-gate baseline reports for G1-G6 only. | current execution block output set |

## Command Candidate Classification (G1-G6)

All command candidates are classified as required by Phase 0.

| gate | command_candidate | status | notes | evidence_ref |
| --- | --- | --- | --- | --- |
| G1 | `python -m pytest ai_stack/tests/test_goc_frozen_vocab.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; execution not finalized in this block due no test run and unresolved cross-surface equality proof. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G1 | semantic reference grep patterns | `pending-finalization-after-phase-0` | Exact pattern set not frozen as canonical command set. | `docs/GoC_Gate_Baseline_Audit_Plan.md` section 4 G1.F |
| G2 | `cd backend && python -m pytest tests/runtime/test_model_routing_evidence.py -q --tb=short --no-cov` | `repo-verified` | Path exists; backend cwd + `--no-cov` pattern is documented. | `docs/testing-setup.md`; `backend/app/runtime/area2_validation_commands.py` |
| G2 | `cd backend && python -m pytest tests/runtime/test_decision_policy.py -q --tb=short --no-cov` | `repo-verified` | Path exists; backend cwd + `--no-cov` pattern is documented. | `docs/testing-setup.md`; `backend/app/runtime/area2_validation_commands.py` |
| G3 | `python -m pytest ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; full runtime turn-contract evidence mix unresolved in this block. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G3 | additional turn-record module selection | `pending-finalization-after-phase-0` | Module subset not frozen. | `docs/GoC_Gate_Baseline_Audit_Plan.md` section 4 G3.F |
| G4 | `python -m pytest ai_stack/tests/test_goc_runtime_graph_seams_and_diagnostics.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; no runtime execution in this block. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G4 | `python -m pytest ai_stack/tests/test_goc_runtime_breadth_continuity_diagnostics.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; evaluative scenario overlap deferred. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G5 | `python -m pytest ai_stack/tests/test_rag.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; retrieval runtime execution not run in this block. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G5 | `python -m pytest ai_stack/tests/test_goc_reliability_longrun_operator_readiness.py -q --tb=short` | `pending-finalization-after-phase-0` | Path exists; runtime proof deferred. | `docs/GoC_Gate_Baseline_Audit_Plan.md` Appendix A |
| G5 | retrieval scenario module checks | `pending-finalization-after-phase-0` | Scope not frozen. | `docs/GoC_Gate_Baseline_Audit_Plan.md` section 4 G5.F |
| G6 | `python -m pytest tests/smoke/test_admin_startup.py -v --tb=short` | `pending-finalization-after-phase-0` | Path exists; smoke test quality is lightweight and environment-sensitive. | `tests/smoke/test_admin_startup.py` |
| G6 | `cd backend && python -m pytest tests/test_game_admin_routes.py tests/test_admin_security.py -q --tb=short --no-cov` | `repo-verified` | Paths exist; backend command pattern and flags are documented. | `docs/testing-setup.md`; `backend/app/runtime/area2_validation_commands.py` |

## Unresolved Mapping Conflicts / Risks

- G1 roadmap semantic set names (`task_types`, `model_roles`, `fallback_classes`, `decision_classes`) do not map one-to-one to current frozen-vocab symbol names without a translation layer.
- G3 canonical turn record section names exist in docs, but runtime projection surfaces require deeper field-by-field parity proof.
- G4 subdecision matrix artifact is not found as a standalone explicit matrix file; behavior is implemented but matrix traceability remains partial.
- G6 includes both governance-read APIs and broader game-admin operations; strict "policy not semantic authorship" boundaries need cross-route assertion evidence.

## Phase 0 Completion Check

Phase 0 completion conditions for this block are met:

- canonical-to-repo mapping table completed for in-scope objects
- section 3.4 anchors fully labeled
- command candidates classified as `repo-verified` or `pending-finalization-after-phase-0`
- unresolved conflicts explicitly recorded
- no unlabeled anchors remain for G1-G6 execution
