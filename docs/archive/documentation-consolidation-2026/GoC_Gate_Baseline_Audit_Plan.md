# GoC Gate Baseline Audit Plan

## 1. Executive audit intent

This document defines **how** to run a baseline audit of the current repository against `docs/ROADMAP_MVP_GoC.md`.

Baseline means: a repository-state snapshot that determines, per gate, what is currently evidenced, what is missing, and what is not yet auditable without additional mapping or execution setup.

This baseline audit answers two distinct questions for each gate:

1. **Structural status**: `green`, `yellow`, `red`, or `not_auditable_yet`
2. **Closure-level status**: `none`, `level_a_capable`, or `level_b_capable`

The audit does **not**:

- execute closure remediation work
- modify code/tests/configuration
- claim closure completion

The audit does:

- produce an evidence-backed gate-by-gate baseline
- identify exact gaps to move gates to green
- classify whether current evidence supports Level A or Level B capability

Why baseline first: roadmap closure requires strict gate logic, implementation order, and evidence artifacts. Baseline prevents closure work from starting with unresolved mapping ambiguity or hidden evidence gaps.

## 2. Audit execution model

Audit execution should follow these phases:

1. **Phase 0: canonical-to-repo mapping**
2. **Phase 1: structural gates** (G1-G6)
3. **Phase 2: operational gates** (G7, G8, G10 prechecks)
4. **Phase 3: evaluative gate G9** (scenario + score evidence)
5. **Phase 4: evaluative gate G9B** (evaluator mode and independence over G9 evidence)
6. **Phase 5: final G10 end-to-end closure baseline**
7. **Phase 6: aggregation and reporting**

Execution ordering rules:

- Structural gates are audited before evaluative gates.
- G9 evidence must exist before concluding G9B (`docs/ROADMAP_MVP_GoC.md`, section 11.2A).
- G10 is concluded only after all prerequisite gate evidence is assembled.

Method selection rules:

- **Static-only**: when gate checks file-level contracts, schema, imports, and mappings.
- **Runtime required**: when gate checks turn emission, routing observation, fallback behavior, or audit traces.
- **Scenario required**: when gate checks user-facing dramatic quality or multi-turn continuity.
- **Evaluator scoring required**: for G9 (scores) and G9B (independence of score process).

Level support rules:

- For many structural gates, `level_a_capable` should be interpreted as **non-blocking for a Level A closure path**, not as a standalone closure determination.
- `level_b_capable` requires valid G9 + G9B evidence and global aggregation through G10.

## 2A. Roadmap-term consistency check

The roadmap explicitly names and governs the audit terms used here:

- `canonical-to-repo mapping` (`docs/ROADMAP_MVP_GoC.md`, Terminology note and section 10)
- `dual-status reporting` (section 11.1)
- `qualitative gate handling` (sections 5 and 11.3)
- `closure-level classification` (section 2 and section 11)

Result: no term is introduced as independent architecture. This plan uses roadmap terminology as written and operationalizes it into audit steps only.

## 3. Phase 0 - Canonical-to-repo mapping

### 3.1 Purpose

Map roadmap canonical names and artifacts to real repository paths before gate-level command finalization.

No gate can be concluded as `green` until mapped objects are tied to real repository evidence targets.

### 3.2 Required mapping artifact

Output table: `audit_phase0_canonical_to_repo_mapping.md` with at least:

- `canonical_name`
- `repo_path`
- `repo_owner_surface`
- `mapping_confidence`
- `notes`
- `evidence_ref`

### 3.3 Mandatory mapping scope

Phase 0 must map:

- canonical surfaces from roadmap section 4
- gate subjects from roadmap section 6
- required evidence artifacts from roadmap section 13
- known GoC contract and score artifacts already present in repo

### 3.4 Initial repository mapping anchors (from current repo)

- GoC authored module: `content/modules/god_of_carnage/` (`pending-finalization-after-phase-0`)
- Runtime + scene + turn seams: `ai_stack/` (`pending-finalization-after-phase-0`)
- Backend runtime and evidence APIs: `backend/app/runtime/`, `backend/app/services/` (`pending-finalization-after-phase-0`)
- Writers' Room service/API: `writers-room/`, `backend/app/services/writers_room_service.py`, `backend/app/api/v1/writers_room_routes.py` (`pending-finalization-after-phase-0`)
- Improvement service/API: `backend/app/services/improvement_service.py`, `backend/app/api/v1/improvement_routes.py` (`pending-finalization-after-phase-0`)
- Admin control surface: `administration-tool/` (`pending-finalization-after-phase-0`)
- Existing reports: `tests/reports/` (`pending-finalization-after-phase-0`)
- Roadmap/governance docs: `docs/` (`pending-finalization-after-phase-0`)

### 3.5 Command finalization gate

All gate commands are either:

- `repo-verified` (existing and validated from repository docs/scripts/tests), or
- `pending-finalization-after-phase-0` (allowed command type known, exact path selection deferred)

No unverified command may be treated as canonical execution until Phase 0 mapping is complete.

## 4. Gate-by-gate audit plans

### G1 - Shared Semantic Contract Gate

#### A. Gate summary

- Gate name: G1 Shared Semantic Contract
- Gate class: structural
- Purpose: enforce one shared semantic vocabulary across runtime, Writers' Room, Improvement, Admin, AI stack
- Closure relevance: prevents semantic forked truths

#### B. Audit subject

Canonical semantic vocabulary ownership, import usage, and redefinition prevention.

#### C. Repository inspection targets

- `docs/ROADMAP_MVP_GoC.md`
- `ai_stack/goc_frozen_vocab.py`
- `ai_stack/mcp_canonical_surface.py`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/langgraph_runtime.py`
- `ai_stack/tests/test_goc_frozen_vocab.py`
- `backend/app/services/writers_room_model_routing.py`
- `backend/app/services/improvement_task2a_routing.py`

#### D. Required evidence

- canonical semantic artifact(s)
- semantic import/reference traces from runtime/writers-room/improvement/admin paths
- equality checks for required enum sets
- tests proving no productive local override

#### E. Audit methods

- static contract inspection
- import/reference tracing
- equality-set comparison
- targeted test execution

#### F. Commands and checks

- `python -m pytest ai_stack/tests/test_goc_frozen_vocab.py -q --tb=short` (`pending-finalization-after-phase-0`)
- semantic reference grep patterns (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: canonical semantic source mapped; all required sets equal; no productive overrides
- `yellow`: canonical source exists but some consuming paths are unmapped or equality incomplete
- `red`: conflicting productive semantic definitions or unknown semantic labels found
- `not_auditable_yet`: canonical semantic source unresolved in Phase 0 mapping

#### H. Closure-level status logic

- `none`: structural red or not auditable
- `level_a_capable`: structural green/yellow and non-blocking for a Level A path (semantic fork risk controlled)
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G1 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G1_semantic_contract_baseline.md`

---

### G2 - Capability / Policy / Observation Separation Gate

#### A. Gate summary

- Gate name: G2 Capability/Policy/Observation Separation
- Gate class: structural
- Purpose: ensure capability truth, policy truth, and runtime observation are separated
- Closure relevance: prevents policy drift and false routing truth

#### B. Audit subject

Presence and usage of separate capability, policy, and observation records in runtime and admin surfaces.

#### C. Repository inspection targets

- `ai_stack/capabilities.py`
- `ai_stack/operational_profile.py`
- `backend/app/runtime/model_inventory_contract.py`
- `backend/app/runtime/model_routing_contracts.py`
- `backend/app/runtime/model_routing.py`
- `backend/app/runtime/model_routing_evidence.py`
- `backend/app/runtime/area2_routing_authority.py`
- `backend/tests/runtime/test_model_routing_evidence.py`
- `backend/tests/runtime/test_decision_policy.py`

#### D. Required evidence

- distinct structures for capability, policy, observation
- routing records containing policy identity and version
- fallback-chain and route-reason visibility
- tests proving no observation->policy overwrite path

#### E. Audit methods

- static structure review
- runtime evidence contract review
- targeted runtime tests

#### F. Commands and checks

- `cd backend && python -m pytest tests/runtime/test_model_routing_evidence.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`; command pattern is documented, final module scope still maps in Phase 0)
- `cd backend && python -m pytest tests/runtime/test_decision_policy.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`, cwd and flags are repo-verified)

#### G. Structural status logic

- `green`: separated records are structurally present and runtime-visible with required fields
- `yellow`: separation mostly present but some references/fields incomplete
- `red`: mixed authoritative structures or silent observation->policy promotion
- `not_auditable_yet`: record mapping unresolved

#### H. Closure-level status logic

- `none`: structural red/not auditable
- `level_a_capable`: structural green/yellow and non-blocking for Level A (no separation-breaking defects)
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G2 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G2_capability_policy_observation_baseline.md`

---

### G3 - Canonical Dramatic Turn Record Gate

#### A. Gate summary

- Gate name: G3 Canonical Dramatic Turn Record
- Gate class: structural
- Purpose: one canonical per-turn record with required sections and fields
- Closure relevance: single diagnostics truth for runtime and review surfaces

#### B. Audit subject

Turn record schema/field completeness and projection discipline (no parallel truth surfaces).

#### C. Repository inspection targets

- `docs/CANONICAL_TURN_CONTRACT_GOC.md`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/runtime_turn_contracts.py`
- `ai_stack/langgraph_runtime.py`
- `backend/app/services/ai_stack_evidence_service.py`
- `ai_stack/tests/test_goc_phase1_runtime_gate.py`

#### D. Required evidence

- canonical turn record contract
- emitted runtime records containing required groups and fields
- proof that compact/expanded views project from the same canonical source
- test assertions over emitted records

#### E. Audit methods

- contract inspection
- runtime output inspection
- projection consistency checks
- targeted phase tests

#### F. Commands and checks

- `python -m pytest ai_stack/tests/test_goc_phase1_runtime_gate.py -q --tb=short` (`pending-finalization-after-phase-0`)
- additional turn-record tests by module selection (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: exactly one canonical record path evidenced with all required groups
- `yellow`: canonical path present but some required fields/groups missing in sampled outputs
- `red`: multiple authoritative diagnostics records or missing major sections
- `not_auditable_yet`: no mapped runtime evidence path for turn records

#### H. Closure-level status logic

- `none`: structural red/not auditable
- `level_a_capable`: structural green/yellow and non-blocking for Level A (no parallel-truth blocker)
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G3 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G3_turn_record_baseline.md`

---

### G4 - Scene Direction Boundary Gate

#### A. Gate summary

- Gate name: G4 Scene Direction Boundary
- Gate class: structural
- Purpose: deterministic-first bounded scene-direction architecture
- Closure relevance: prevents unbounded narrative generation and truth mutation

#### B. Audit subject

Scene-direction subdecision matrix coverage, seam ownership, and forbidden-behavior absence.

#### C. Repository inspection targets

- `ai_stack/scene_director_goc.py`
- `ai_stack/goc_turn_seams.py`
- `ai_stack/langgraph_runtime.py`
- `docs/CANONICAL_TURN_CONTRACT_GOC.md`
- `ai_stack/tests/test_goc_phase1_runtime_gate.py`
- `ai_stack/tests/test_goc_phase2_scenarios.py`

#### D. Required evidence

- mapped subdecision matrix fields
- deterministic and bounded seams before/around model proposals
- anti-overwrite safeguards for director-selected fields
- tests proving bounded behavior

#### E. Audit methods

- static seam analysis
- matrix/contract comparison
- targeted scenario tests

#### F. Commands and checks

- `python -m pytest ai_stack/tests/test_goc_phase1_runtime_gate.py -q --tb=short` (`pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase2_scenarios.py -q --tb=short` (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: all required subdecision metadata mapped and enforced; no forbidden behavior paths found
- `yellow`: matrix mostly present but incomplete seam classification or weak enforcement evidence
- `red`: unclassified or unbounded scene-direction decisions in productive path
- `not_auditable_yet`: subdecision matrix mapping unresolved

#### H. Closure-level status logic

- `none`: structural red/not auditable
- `level_a_capable`: structural green/yellow and non-blocking for Level A
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G4 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G4_scene_direction_boundary_baseline.md`

---

### G5 - Retrieval Governance Gate

#### A. Gate summary

- Gate name: G5 Retrieval Governance
- Gate class: structural
- Purpose: retrieval augments authored truth without redefining it
- Closure relevance: prevents retrieval-time canonical truth drift

#### B. Audit subject

Authored-vs-derived distinction, retrieval lane governance, and turn-record retrieval visibility.

#### C. Repository inspection targets

- `ai_stack/rag.py`
- `docs/rag_retrieval_hardening.md`
- `docs/rag_retrieval_subsystem_closure.md`
- `docs/rag_task3_source_governance.md`
- `docs/rag_task4_evaluation_harness.md`
- `ai_stack/tests/test_rag.py`
- `ai_stack/tests/retrieval_eval_scenarios.py`
- `ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py`

#### D. Required evidence

- explicit authored truth references
- explicit derived retrieval substrate references
- retrieval output source-class metadata
- lane/visibility governance metadata
- runtime turn retrieval traces

#### E. Audit methods

- retrieval contract inspection
- runtime retrieval trace inspection
- retrieval test execution

#### F. Commands and checks

- `python -m pytest ai_stack/tests/test_rag.py -q --tb=short` (`pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py -q --tb=short` (`pending-finalization-after-phase-0`)
- retrieval scenario module checks (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: authored/derived separation and governance lanes are explicit and runtime-visible
- `yellow`: separation exists but provenance/lane visibility incomplete
- `red`: retrieval can redefine authored truth or runtime provenance is missing
- `not_auditable_yet`: retrieval contract-to-runtime mapping incomplete

#### H. Closure-level status logic

- `none`: structural red/not auditable
- `level_a_capable`: structural green/yellow and non-blocking for Level A
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G5 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G5_retrieval_governance_baseline.md`

---

### G6 - Admin Governance Gate

#### A. Gate summary

- Gate name: G6 Admin Governance
- Gate class: structural
- Purpose: admin is control plane, not semantic author
- Closure relevance: prevents semantic drift by admin state alone

#### B. Audit subject

Admin authority boundaries, edit scopes, and review/version visibility.

#### C. Repository inspection targets

- `administration-tool/app.py`
- `backend/app/api/v1/ai_stack_governance_routes.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/test_game_admin_routes.py`
- `backend/tests/test_admin_security.py`
- `tests/smoke/test_admin_startup.py`

#### D. Required evidence

- admin-manageable policy surfaces
- prevention of admin semantic-authoring operations
- versioned/review-visible change traces
- route-level authorization checks

#### E. Audit methods

- static route/surface inspection
- policy-vs-semantic authority checks
- security/admin test execution

#### F. Commands and checks

- `python -m pytest tests/smoke/test_admin_startup.py -v --tb=short` (`pending-finalization-after-phase-0`)
- `cd backend && python -m pytest tests/test_game_admin_routes.py tests/test_admin_security.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: admin can manage policy/runtime controls but cannot introduce semantic truth
- `yellow`: boundaries present but incomplete review/version traceability
- `red`: admin can create productive semantic drift or bypass semantic governance
- `not_auditable_yet`: admin-governance path mapping unresolved

#### H. Closure-level status logic

- `none`: structural red/not auditable
- `level_a_capable`: structural green/yellow and non-blocking for Level A
- `level_b_capable`: usually not meaningful at this gate; record as `n/a` unless explicitly needed for global aggregation through G9, G9B, and G10

#### H2. Evidence quality recording

Every G6 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact, trace, test, or runtime evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G6_admin_governance_baseline.md`

---

### G7 - Writers' Room Operating Contract Gate

#### A. Gate summary

- Gate name: G7 Writers' Room Operating Contract
- Gate class: operational
- Purpose: Writers' Room is bounded, useful, and semantically aligned
- Closure relevance: required operating subsystem, not conceptual placeholder

#### B. Audit subject

Writers' Room functions, artifact classes, and inability to mutate runtime truth directly.

#### C. Repository inspection targets

- `writers-room/app.py`
- `writers-room/app/models/`
- `writers-room/app/models/implementations/god_of_carnage/`
- `backend/app/services/writers_room_service.py`
- `backend/app/services/writers_room_model_routing.py`
- `backend/app/api/v1/writers_room_routes.py`
- `backend/tests/writers_room/test_writers_room_routes.py`
- `backend/tests/writers_room/test_writers_room_model_routing.py`
- `backend/tests/writers_room/test_writers_room_unit.py`

#### D. Required evidence

- analysis/proposal/authoring-support functional paths
- bounded output classing
- approval boundaries preventing direct runtime truth mutation
- semantic alignment checks with shared vocabulary
- operational trace evidence showing that Writers' Room outputs are consumed in bounded workflows (not only emitted by endpoints)

#### E. Audit methods

- static API/service contract review
- artifact-flow inspection
- operational route/unit tests

#### F. Commands and checks

- `cd backend && python -m pytest tests/writers_room/test_writers_room_routes.py tests/writers_room/test_writers_room_model_routing.py tests/writers_room/test_writers_room_unit.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`)
- `python -m pytest tests/reports/` is not a valid target for this gate (no direct report execution command in repo) (`repo-verified exclusion`)

#### G. Structural status logic

- `green`: bounded utility is evidenced in operation (artifact flow + approval behavior + consumption traces), and artifact classes/approval boundaries enforce no second runtime truth surface
- `yellow`: routes/services/files exist, but bounded utility evidence is partial (for example, artifact typing exists without clear approval/use traces)
- `red`: thin concept only, or direct truth mutation path exists
- `not_auditable_yet`: no mapped operational evidence path

#### H. Closure-level status logic

- `none`: red/not auditable
- `level_a_capable`: green/yellow and non-blocking for Level A only when bounded utility is evidenced beyond endpoint existence
- `level_b_capable`: depends on global aggregation; G7 alone does not imply Level B

#### H2. Evidence quality recording

Every G7 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact flow, approval behavior, operational traces, and tests) collected for this gate.

#### I. Output artifact(s)

- `gate_G7_writers_room_operating_baseline.md`

---

### G8 - Improvement Path Operating Gate

#### A. Gate summary

- Gate name: G8 Improvement Path Operating
- Gate class: operational
- Purpose: typed, bounded improvement loop with evidence and review
- Closure relevance: converts runtime/quality gaps into governed improvement flow

#### B. Audit subject

Improvement classes, output classes, and full loop (selection to post-change verification).

#### C. Repository inspection targets

- `backend/app/services/improvement_service.py`
- `backend/app/services/improvement_task2a_routing.py`
- `backend/app/api/v1/improvement_routes.py`
- `backend/tests/improvement/test_improvement_routes.py`
- `backend/tests/improvement/test_improvement_unit.py`
- `backend/tests/improvement/test_improvement_task2a_routing_positive.py`
- `backend/tests/improvement/test_improvement_task2a_routing_negative.py`
- `tests/reports/pytest_improvement_*.xml`

#### D. Required evidence

- typed improvement entry classes
- bounded proposal and approval/rejection handling
- publication and post-change verification traces
- route/service/test evidence for loop steps
- operational trace evidence that typed improvements are actually progressed through the loop, not merely accepted by route handlers

#### E. Audit methods

- static service/route inspection
- operational test execution
- report artifact inspection

#### F. Commands and checks

- `cd backend && python -m pytest tests/improvement/test_improvement_routes.py tests/improvement/test_improvement_unit.py tests/improvement/test_improvement_task2a_routing_positive.py tests/improvement/test_improvement_task2a_routing_negative.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: typed and bounded loop is evidenced end-to-end via artifact flow, approval/rejection behavior, publication handling, and post-change verification traces
- `yellow`: routes/services/files exist, but one or more loop stages lack operational evidence
- `red`: untyped/unbounded improvement behavior
- `not_auditable_yet`: mapped improvement artifacts/tests missing

#### H. Closure-level status logic

- `none`: red/not auditable
- `level_a_capable`: green/yellow and non-blocking for Level A only when typed-loop usefulness is evidenced beyond endpoint existence
- `level_b_capable`: depends on global aggregation; G8 alone does not imply Level B

#### H2. Evidence quality recording

Every G8 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (artifact flow, loop-stage traces, approval behavior, and tests) collected for this gate.

#### I. Output artifact(s)

- `gate_G8_improvement_operating_baseline.md`

---

### G9 - User-Facing Experience Acceptance Gate

#### A. Gate summary

- Gate name: G9 User-Facing Experience Acceptance
- Gate class: evaluative
- Purpose: verify dramatic quality using required scenario set and scoring thresholds
- Closure relevance: technical correctness alone is insufficient

#### B. Audit subject

Scenario execution evidence, score sheets, threshold compliance, and quality rationale.

#### C. Repository inspection targets

- `docs/ROADMAP_MVP_GoC.md` (sections 6.9 and 8)
- `docs/GATE_SCORING_POLICY_GOC.md`
- `ai_stack/tests/test_goc_phase2_scenarios.py`
- `ai_stack/tests/test_goc_phase3_experience_richness.py`
- `ai_stack/tests/test_goc_phase5_final_mvp_closure.py`
- `tests/reports/GOC_PHASE2_MATURITY_BREADTH_QUALITY_REPORT.md`
- `tests/reports/GOC_PHASE3_EXPERIENCE_RICHNESS_REPORT.md`
- `tests/reports/GOC_PHASE5_FINAL_MVP_CLOSURE_REPORT.md`

#### D. Required evidence

- fixed required scenario set coverage
- per-scenario and per-criterion scores (1-5)
- threshold calculations
- transcript excerpts and turn record references
- route/fallback/retrieval evidence where applicable

#### E. Audit methods

- scenario evidence inspection
- score/rubric validation
- runtime-test execution for scenario reproducibility
- threshold recomputation

#### F. Commands and checks

- `python -m pytest ai_stack/tests/test_goc_phase2_scenarios.py -q --tb=short` (`pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase3_experience_richness.py -q --tb=short` (`pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase5_final_mvp_closure.py -q --tb=short` (`pending-finalization-after-phase-0`)
- report generation command surface for markdown score reports (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: scenario set executed with complete score evidence and threshold pass checks
- `yellow`: scenario evidence exists but incomplete scoring, incomplete rationale, or threshold math gaps
- `red`: missing required scenarios, missing score sheets, or threshold failures
- `not_auditable_yet`: scenario execution/reporting surface not mapped

#### H. Closure-level status logic

- `none`: red/not auditable
- `level_a_capable`: G9 meets thresholds with declared evaluator mode ready for Level A path
- `level_b_capable`: only provisional here; final Level B requires G9B and global aggregation

#### H2. Evidence quality recording

Every G9 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (scenario traces, score sheets, threshold calculations, and runtime artifacts) collected for this gate.

#### I. Output artifact(s)

- `gate_G9_experience_acceptance_baseline.md`

---

### G9B - Evaluator Independence Gate

#### A. Gate summary

- Gate name: G9B Evaluator Independence
- Gate class: evaluative
- Purpose: classify evaluator mode and validate independence evidence for Level B
- Closure relevance: distinguishes Level A known limitation vs Level B independence

#### B. Audit subject

Evaluator mode declaration, raw score separation, delta preservation, and reconciliation handling.

#### C. Repository inspection targets

- `docs/ROADMAP_MVP_GoC.md` (sections 2, 6.10, 11.2A, 11.2B)
- `docs/GATE_SCORING_POLICY_GOC.md`
- G9 scenario/score artifacts produced in same audit run
- evaluator score sheets and reconciliation sheets (expected in audit artifact set; location finalizes in Phase 0)

#### D. Required evidence

- explicit evaluator mode declaration (Level A single evaluator or Level B independent evaluators)
- raw per-evaluator score sheets
- score delta records
- reconciled summary that does not overwrite raw evidence

#### E. Audit methods

- evidence package inspection
- evaluator-independence validation checklist
- consistency checks against G9 score set

#### F. Commands and checks

- no standalone runtime command should conclude G9B before G9 evidence exists (`repo-verified rule from roadmap section 11.2A`)
- artifact validation commands for score-sheet presence/checksum/format (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: evaluator mode declared and evidence package complete for claimed mode
- `yellow`: mode declared but raw/delta/reconciliation evidence incomplete
- `red`: undeclared mode, missing raw evidence, or Level B claim without independence evidence
- `not_auditable_yet`: G9 evidence unavailable

#### H. Closure-level status logic

- `none`: red/not auditable
- `level_a_capable`: single-evaluator mode explicitly declared as known limitation and evidenced
- `level_b_capable`: two independent evaluators evidenced with separate raw scores and deltas

#### H2. Evidence quality recording

Every G9B baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (evaluator-mode declaration, raw sheets, deltas, and reconciliation artifacts) collected for this gate.

#### I. Output artifact(s)

- `gate_G9B_evaluator_independence_baseline.md`

---

### G10 - End-to-End Closure Gate

#### A. Gate summary

- Gate name: G10 End-to-End Closure
- Gate class: operational (per roadmap taxonomy)
- Purpose: verify full GoC stack chain works as one system
- Closure relevance: final integrative closure gate

#### B. Audit subject

The full 11-step end-to-end chain listed in roadmap section 6.11.

#### C. Repository inspection targets

- runtime executors: `ai_stack/langgraph_runtime.py`, `backend/app/runtime/ai_turn_executor.py`, `backend/app/runtime/turn_dispatcher.py`
- module load surfaces: `content/modules/god_of_carnage/`, `backend/app/content/builtins.py`, `world-engine/app/content/builtins.py`
- routing/fallback evidence: `backend/app/runtime/model_routing_evidence.py`, `backend/app/services/ai_stack_evidence_service.py`
- end-to-end tests: `backend/tests/test_e2e_god_of_carnage_full_lifecycle.py`, `backend/tests/test_bootstrap_staged_runtime_integration.py`, `backend/tests/runtime/test_area2_task4_closure_gates.py`
- smoke entrance: `run-smoke-tests.bat`, `run-smoke-tests.sh`, `tests/smoke/`

#### D. Required evidence

- complete chain evidence from module load to experience acceptance
- fallback correctness under degraded path
- operator-visible routing truth
- compatibility of Writers' Room semantics with runtime closure chain
- validated dependency on G1-G9/G9B outcomes

#### E. Audit methods

- end-to-end test execution
- chain trace inspection from runtime diagnostics
- dependency confirmation against prior gate reports

#### F. Commands and checks

- `python -m pytest tests/smoke/ -v --tb=short` (`repo-verified`)
- `run-smoke-tests.bat` or `./run-smoke-tests.sh` (`repo-verified`)
- `cd backend && python -m pytest tests/test_e2e_god_of_carnage_full_lifecycle.py tests/test_bootstrap_staged_runtime_integration.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`)
- `cd backend && python -m pytest tests/runtime/test_area2_task4_closure_gates.py -q --tb=short --no-cov` (`pending-finalization-after-phase-0`)

#### G. Structural status logic

- `green`: all end-to-end chain stages evidenced together with no isolated-only pass illusion
- `yellow`: major chain present but one or more stages only partially evidenced
- `red`: chain broken or only isolated layers green
- `not_auditable_yet`: required upstream gate evidence missing

#### H. Closure-level status logic

- `none`: red/not auditable
- `level_a_capable`: G10 chain is green with Level A-compatible G9/G9B context
- `level_b_capable`: only when G10 is green and global aggregation confirms G9 + G9B Level B conditions

#### H2. Evidence quality recording

Every G10 baseline report must include an `evidence_quality` field with value `high`, `medium`, or `low`, plus a short justification tied to the actual evidence mix (end-to-end traces, runtime diagnostics, scenario evidence, and dependency gate evidence) collected for this gate.

#### I. Output artifact(s)

- `gate_G10_end_to_end_closure_baseline.md`

## 5. Cross-gate dependency map

- G1 is foundational for all semantic interpretation and gate language.
- G2 and G3 are coupled: routing observation fields must project into canonical turn records.
- G4 depends on G1 and G3: scene direction labels and turn-record visibility must share semantics.
- G5 depends on authored-vs-derived distinctions established in module/retrieval contracts and observable in G3.
- G6 supports G7 and G8 by preventing admin semantic bypass.
- G7 and G8 both depend on G1 semantic consistency and G6 governance boundaries.
- G9 depends on prior structural/operational gates to avoid scoring unstable architecture.
- G9B depends on completed G9 scenario/score evidence.
- G10 depends on all prior gates for a valid end-to-end closure baseline.

## 6. Mandatory implementation-order mapping

| Roadmap step | Primary gates enabled/materially affected | Audit implication |
|---|---|---|
| 1. Shared semantic contract binding | G1, G4, G7, G8 | Audit G1 before semantic-sensitive operational/evaluative gates |
| 2. Canonical module package contract | G1, G3, G5, G10 | Validate module load and authored truth anchors early |
| 3. Separate capability/policy/observation | G2, G3, G6, G10 | Confirm structure split before routing/e2e claims |
| 4. Scene-direction subdecision matrix | G4, G3, G10 | Bound scene-direction checks before scenario quality scoring |
| 5. Canonical dramatic turn record emission | G3, G5, G9, G10 | Turn-record evidence is required for runtime and evaluative gates |
| 6. Retrieval governance lanes + visibility | G5, G3, G9, G10 | Retrieval checks need lane/source visibility in runtime artifacts |
| 7. Admin governance boundaries | G6, G7, G8 | Operational workflows must run under governance constraints |
| 8. Writers' Room operating contract | G7, G10 | Verify bounded utility before final end-to-end baseline |
| 9. Improvement path operating contract | G8, G10 | Verify typed improvement loop before final aggregation |
| 10. Experience scenarios + score layer | G9, G9B, G10 | G9 evidence required before G9B and final level aggregation |
| 11. Run gates + collect evidence | G1-G10, G9B | Baseline execution/reporting phase itself |

## 7. Required evidence-artifact mapping

| Required artifact (roadmap section 13) | Gates | Audit phase(s) | Repository inspection targets |
|---|---|---|---|
| `shared_semantic_contract.*` | G1, G4, G7, G8 | 0, 1 | `ai_stack/goc_frozen_vocab.py`, `docs/ROADMAP_MVP_GoC.md` |
| `module_package_contract.*` | G1, G5, G10 | 0, 1, 5 | `content/modules/god_of_carnage/`, `docs/architecture/god_of_carnage_module_contract.md` |
| `capability_contract.*` | G2, G10 | 0, 1 | `ai_stack/capabilities.py`, `backend/app/runtime/model_inventory_contract.py` |
| `routing_policy_contract.*` | G2, G6, G10 | 0, 1 | `backend/app/runtime/model_routing_contracts.py`, `backend/app/runtime/decision_policy.py` |
| `routing_observation_contract.*` | G2, G3, G10 | 0, 1 | `backend/app/runtime/model_routing_evidence.py`, `backend/app/services/ai_stack_evidence_service.py` |
| `dramatic_turn_record_contract.*` | G3, G4, G5, G9, G10 | 0, 1, 3, 5 | `docs/CANONICAL_TURN_CONTRACT_GOC.md`, `ai_stack/goc_turn_seams.py` |
| `scene_direction_subdecision_matrix.*` | G4, G10 | 0, 1, 5 | `ai_stack/scene_director_goc.py`, `docs/CANONICAL_TURN_CONTRACT_GOC.md` |
| `retrieval_governance_contract.*` | G5, G9, G10 | 0, 1, 3, 5 | `ai_stack/rag.py`, `docs/rag_task3_source_governance.md` |
| `writers_room_operating_contract.*` | G7, G10 | 0, 2, 5 | `writers-room/`, `backend/app/services/writers_room_service.py` |
| `improvement_operating_contract.*` | G8, G10 | 0, 2, 5 | `backend/app/services/improvement_service.py`, `backend/app/api/v1/improvement_routes.py` |
| `experience_acceptance_matrix.*` | G9, G9B, G10 | 3, 4, 5 | `docs/GATE_SCORING_POLICY_GOC.md`, `tests/reports/GOC_PHASE*_REPORT.md` |
| `gate_results_report.*` | G1-G10, G9B | 6 | All per-gate outputs from this plan |
| `final_closure_report.*` | G10, global Level A/B classification | 6 | Master baseline report + closure-level summary |

## 7A. Closure-level aggregation rule

Closure-level status is a global aggregation result, not independent per-gate precision for every gate.

Interpretation note for structural gates (G1-G6): per-gate `level_a_capable` usually means "currently non-blocking for Level A if aggregated prerequisites remain satisfied," not "Level A closure achieved at this gate."

Aggregation rules:

1. Evaluate structural status and closure-level status per gate.
2. Do not infer Level B from structural gates that do not materially distinguish Level A vs B.
3. Aggregate Level A/B through combined outcomes of G9, G9B, and G10, with prerequisite gate health from G1-G8.
4. If G9 passes but G9B only supports single-evaluator mode, classify as `level_a_capable` (not Level B).
5. Only classify `level_b_capable` when G9 quality thresholds, G9B independence evidence, and G10 end-to-end integration are all satisfied.

## 8. Baseline scoring rules

Global baseline interpretation:

- `green`: full gate requirements evidenced for current baseline scope
- `yellow`: partial evidence, not closure-ready
- `red`: missing or structurally broken requirements
- `not_auditable_yet`: gate cannot be assessed due to unresolved mapping/prerequisites

Closure impact:

- `yellow`, `red`, and `not_auditable_yet` all block closure claims.
- In baseline mode, these statuses are recorded as remediation inputs, not closure failures in isolation.

Evidence quality recording:

- `high`: direct artifact + direct test/scenario/runtime evidence
- `medium`: direct artifact + partial runtime/test evidence
- `low`: indirect references only (must trigger remediation)
- every per-gate report must include `evidence_quality` using only these values and must include a one-paragraph justification

Uncertainty recording:

- uncertainty must be explicit, tied to missing artifacts/commands/paths
- uncertainty cannot be expressed with vague compliance language
- unresolved uncertainty should push status to `yellow` or `not_auditable_yet`, not `green`

## 9. Qualitative-gate handling rule

G7, G8, G9, and G9B are audited with mixed evidence, not static checks only.

Required handling:

- **Structural evidence**: route/service/contract presence and boundaries
- **Operational/evaluative evidence**: actual flow outputs, scenario traces, score sheets, evaluator records
- **Scenario requirements**: enforce G9 required scenario set and threshold logic
- **Rubric requirements**: enforce 1-5 scoring dimensions and threshold calculations
- **Evaluator requirements**: explicit mode declaration for G9B and independence validation for Level B

Missing evaluative evidence effect:

- structural checks may still be `green`/`yellow` for G7/G8
- closure-level remains `none` or `level_a_capable` pending for G9/G9B
- no gate receives Level B capability from static artifacts alone

## 10. Expected audit deliverables

The later audit execution must produce:

1. `master_goc_baseline_audit_report.md`
2. Per-gate reports:
   - `gate_G1_semantic_contract_baseline.md`
   - `gate_G2_capability_policy_observation_baseline.md`
   - `gate_G3_turn_record_baseline.md`
   - `gate_G4_scene_direction_boundary_baseline.md`
   - `gate_G5_retrieval_governance_baseline.md`
   - `gate_G6_admin_governance_baseline.md`
   - `gate_G7_writers_room_operating_baseline.md`
   - `gate_G8_improvement_operating_baseline.md`
   - `gate_G9_experience_acceptance_baseline.md`
   - `gate_G9B_evaluator_independence_baseline.md`
   - `gate_G10_end_to_end_closure_baseline.md`
   - each per-gate report must include a required `evidence_quality` field (`high` / `medium` / `low`) with justification
3. `gate_summary_matrix.md`
4. `canonical_to_repo_mapping_table.md`
5. `implementation_order_mapping_table.md`
6. `evidence_artifact_mapping_table.md`
7. `repo_evidence_index.md`
8. `red_yellow_remediation_list.md`
9. `closure_level_classification_summary.md`
10. `transition_recommendation_ready_or_not_ready.md`

Transition recommendation rule:

- recommendation may state `ready for implementation closure work` or `not ready`
- this recommendation is strictly transitional and is **not** a closure claim

## 11. Post-audit transition rule

After baseline audit:

1. Convert each `yellow`, `red`, and `not_auditable_yet` finding into bounded implementation work items.
2. Group work by gate dependencies and implementation order (roadmap section 12).
3. Preserve roadmap semantics and gate logic; no redesign via remediation backlog.
4. Re-audit sequence after remediation:
   - rerun impacted structural gates first
   - rerun impacted operational gates
   - rerun G9 then G9B if evaluative evidence changed
   - rerun G10 and global aggregation
5. If baseline reaches Level A but not Level B:
   - schedule explicit evaluator-independence remediation package for G9B
   - define second-evaluator sourcing and independent prompt/rubric controls
   - rerun G9 evidence consistency checks and G9B independence checks before any Level B recommendation

---

## Appendix A - Current command-surface snapshot (verified at plan-authoring time)

- `python -m pytest tests/smoke/ -v --tb=short` (root)
- `run-smoke-tests.bat` (Windows)
- `./run-smoke-tests.sh` (POSIX)
- `python -m pytest ai_stack/tests/test_goc_frozen_vocab.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase1_runtime_gate.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase2_scenarios.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase3_experience_richness.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase4_reliability_breadth_operator.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_goc_phase5_final_mvp_closure.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `python -m pytest ai_stack/tests/test_rag.py -q --tb=short` (path exists; execution remains `pending-finalization-after-phase-0`)
- `cd backend && python -m pytest ... --no-cov` pattern is verified from `docs/testing-setup.md` and `backend/app/runtime/area2_validation_commands.py`; exact module lists remain `pending-finalization-after-phase-0`.

Snapshot scope note: this appendix captures command discoverability and documented command patterns at plan-authoring time, not immutable command truth for all later repository states.

## Appendix B - Pending-finalization-after-phase-0 policy

Any command marked `pending-finalization-after-phase-0` must be finalized only after:

1. canonical object mapping is complete
2. target module/test ownership is confirmed
3. command cwd and flags are validated against local `pytest.ini` or script docs
4. the finalized command is added to the gate report before execution

