# World of Shadows MVP v24 Lean Finishable — Comprehensive Audit
**Date:** 2026-04-17  
**Status:** MVP-Ready Foundation Established with Specific Critical Gaps  
**Audit Scope:** Runtime-readiness preparedness across all mandatory source layers

---

## 1. Executive Verdict

**Is the MVP fully prepared as a foundation for runtime-readiness implementation?**

**Verdict: PARTIALLY PREPARED with critical blockers in evidence integration and contract coherence.**

The MVP v24 has achieved:
- ✓ **Canonical runtime authority established** (world-engine as authoritative play service)
- ✓ **God of Carnage vertical slice fully scoped and contractified** (YAML module authority, dramatic vocabulary, turn/validation/commit seams)
- ✓ **FY governance infrastructure in place** (contractify audit reporting 60 contracts, despaghettify structural analysis, docify baseline scans)
- ✓ **Foundation-critical code implemented** (StoryRuntimeManager, RuntimeTurnGraphExecutor, narrative commit resolution, input interpreter)
- ✓ **18/18 GoC structure smoke tests passing**

The MVP v24 remains **NOT FULLY PREPARED** because:
- ✗ **Evidence attachment is incomplete** — Runtime contracts documented and code implemented, but validation links to test surfaces remain thin
- ✗ **FY governance integration is nascent** — Contractify identifies 60 contracts, but enforcement hooks and drift-detection workflows not yet wired into CI/commit gates
- ✗ **Docify attachment is pending** — 1,097 documentation findings across 227 files (4 parse errors, 100+ missing docstrings in FY-suite tools) remain ungoverned
- ✗ **Validation/commit path coverage gaps** — GoC validation and commit seams operationalized but integration with content authority (YAML → runtime) still developing

**Preparedness Level:** ~65% toward full readiness. The MVP is usable as a foundation but requires immediate work on:
1. Evidence integration and validation surface attachment
2. FY governance workflow attachment (CI gates, merge checks)
3. Documentation governance enforcement
4. Content authority integration (YAML → validation → commit → visible)

---

## 2. Total Preparedness Assessment

### By Runtime-Readiness Domain

| Domain | Preparedness | Status | Evidence |
|--------|--------------|--------|----------|
| **Runtime authority** | A → G (Implemented & integrated) | ✓ Complete | ADR-0001, StoryRuntimeManager, world-engine/app/story_runtime/ |
| **Reaction behavior** | C → E (Operationalized, weak evidence) | Partial | Director nodes, scene_assessment, but validation surface thin |
| **Turn processing** | D → E (Implemented, tests emerging) | Partial | RuntimeTurnGraphExecutor, node order stable, but gate scoring CLI missing |
| **Intent interpretation** | D → F (Implemented & tested) | Sufficient | story_runtime_core/input_interpreter.py, tests/test_input_interpreter.py |
| **Scene identity** | C → F (Scoped & partially tested) | Partial | ADR-0003, goc_scene_identity.py, ai_stack tests, but YAML authority integration TBD |
| **Validation seam** | D (Partially implemented) | Partial | validate_seam node exists, GoC rule engine stubbed, no production tests |
| **Commit seam** | D (Partially implemented) | Partial | resolve_narrative_commit in manager.py, narrative_commit_resolution.py split, thin test coverage |
| **Visible output** | D (Implemented, evidence weak) | Partial | render_visible node, visibility_class_markers defined, integration tests missing |
| **Continuity & memory** | C → D (Scoped & partially implemented) | Weak | prior_continuity_impacts bounded carry-forward, narrative_threads structure, untested at scale |
| **Validation/commit commitment** | D (Implemented but gates absent) | Partial | Seams exist, diagnostics recorded, but no enforcement CI gates |
| **Observability** | E (Implemented, evidence emerging) | Sufficient | graph_diagnostics, diagnostics_refs, operator_compact bundle defined |
| **Service integration** | E (Flask ↔ FastAPI proxy operational) | Sufficient | backend/app/services/game_service.py, internal URLs, tests passing |
| **Governance anti-drift** | C → D (FY-suites installed, workflow TBD) | Weak | Contractify audit reports generated, but enforcement hooks not wired |
| **Contract coherence** | E (60 contracts mapped, relations established) | Sufficient | IMPLEMENTATION_RESULT.md shows 310 relations, 6 managed conflicts |
| **Documentation coherence** | D (Baseline scanned, gaps identified) | Partial | Docify audit reports 1,097 findings, 4 parse errors, FY-suite tools lack docstrings |
| **Structural change discipline** | C → D (Despaghettify reports available, workflow TBD) | Weak | AST analysis complete (15,392 functions), but enforcement workflow not wired |

**Summary:** The MVP is **foundation-ready but governance-incomplete**. Code layers are sound; evidence and orchestration layers need strengthening.

---

## 3. Current-State Protocol

### What is Present

**A. Documented Normative Authority**
- ✓ 9 mandatory runtime anchors (ADRs, contracts, policies)
- ✓ God of Carnage vertical slice fully specified (VERTICAL_SLICE_CONTRACT_GOC.md, CANONICAL_TURN_CONTRACT_GOC.md, GATE_SCORING_POLICY_GOC.md)
- ✓ Runtime authority split clearly defined (world-engine owns play, backend owns governance)
- ✓ Canonical turn schema with explicit seams (proposal → validation → commit → visibility)
- ✓ Player input interpretation contract operationalized

**B. Implementation Layer (Code)**
- ✓ StoryRuntimeManager in world-engine (session lifecycle, turn orchestration)
- ✓ RuntimeTurnGraphExecutor (LangGraph-based orchestrator with 10 named nodes)
- ✓ Director nodes for scene assessment and dramatic parameter selection
- ✓ Validation seam (validate_seam → run_validation_seam)
- ✓ Commit seam (commit_seam → resolve_narrative_commit)
- ✓ Visible render seam (render_visible)
- ✓ Input interpreter (story_runtime_core/input_interpreter.py)
- ✓ RAG and context retrieval (ai_stack/rag.py)
- ✓ Backend-to-world-engine proxy (backend/app/services/game_service.py)
- ✓ Content module loader (backend/app/content/module_service.py)
- ✓ God of Carnage YAML module (content/modules/god_of_carnage/) — 8 core files + direction/

**C. Evidence Layer**
- ✓ 18/18 GoC structure smoke tests passing
- ✓ backend/tests/ suite operational
- ✓ world-engine/tests/ suite operational
- ✓ ai_stack/tests/ suite operational
- ✓ story_runtime_core/tests/ suite operational
- ✓ test_reports/ with JUnit XML
- ✗ Production turn validation tests (missing)
- ✗ Production commit integration tests (missing)
- ✗ Gate scoring CLI tests (missing)

**D. Governance Layer (FY-suites)**
- ✓ Contractify: 60 contracts discovered, 310 relations mapped, 5 precedence tiers
- ✓ Contractify audit reports: audit.hermetic-fixture.json, conflicts tracked
- ✓ Despaghettify: AST analysis complete (15,392 functions, nesting/cycle analysis)
- ✓ Docify: baseline scan running (1,097 findings, parse errors identified)
- ✓ Execution governance state tracking (EXECUTION_GOVERNANCE.md, workstream artifacts)
- ✗ CI gates not wired to contractify/docify/despaghettify outputs
- ✗ Merge checks do not enforce contract coherence
- ✗ Drift detection workflow not automated

### What is Documented

- ✓ Architecture decisions (ADR-0001, ADR-0002, ADR-0003)
- ✓ Runtime contracts (7 normative, 23 slice-scoped)
- ✓ API reference (OpenAPI 3, backend REST surface)
- ✓ Implementation guides (technical/runtime/, technical/ai/)
- ✓ Slice roadmap (ROADMAP_MVP_VSL.md)
- ✓ Freeze operationalization (FREEZE_OPERATIONALIZATION_MVP_VSL.md)
- ✓ Governance scope (CONTRACT_GOVERNANCE_SCOPE.md)
- ✗ Validation/commit rule book (rule engine defined informally, not formally documented)
- ✗ Test coverage targets (per-contract validation targets not tracked)
- ✗ Evidence checklist (what audit artifacts must exist before "ready" claim)

### What is Operationalized

- ✓ Runtime turn execution (LangGraph graph builder, node execution, state threading)
- ✓ Proposal generation (model invocation with dramatic parameters)
- ✓ Validation (rule engine stub, return status only)
- ✓ Commit (narrative_commit_resolution with effects application)
- ✓ Visibility (render_visible with visibility_class_markers)
- ✓ Continuity carry-forward (prior_continuity_impacts, narrative_threads)
- ✗ Gate scoring and cadence (operator_compact / dramatic_expanded / freeze_integrity bundles defined, not operationalized in CI)
- ✗ Escape/failure recovery (containment-first policy defined, not integrated in graph)

### What is Implemented

**Code:** StoryRuntimeManager, RuntimeTurnGraphExecutor, director nodes, seam functions, input interpreter, RAG, module loader, narrative threads.

**Tests:** 18 GoC structure tests, input interpreter tests, scene identity tests, session route tests, story runtime API tests.

**Missing implementation:**
- Production validation rule engine (rule logic, not just status framework)
- Production commit validation (effects consistency checks)
- Gate scoring automation (score matrix evaluation)
- Escape/containment behavior (scope breach handling)
- Continuity inconsistency detection
- Fallback policy integration

### What is Evidenced

**Passing:** GoC structure, input parsing, scene identity, session routes, story API endpoints.

**Missing evidence:**
- Turn execution under production conditions (not mocked)
- Validation outcomes across rule variants
- Commit consistency across concurrent/sequential scenes
- Continuity carry-forward at scale (multi-turn sessions)
- Gate scoring against tabletop scenarios
- Failure recovery behavior (containment, silence, withholding)

### What is Governed

**Contractify:** 60 contracts, 5 precedence tiers, 310 relations, confidence 0.85–0.98 on anchors.

**Not yet governed:**
- Per-contract test coverage requirements
- CI enforcement of contract coherence
- Documentation drift detection
- Code structure limits (AST findings not tied to governance)

### What is Missing, Contradictory, or Too Vague

1. **Validation rule engine specificity** — Documented as "rule-based GoC validator" but actual rule logic not formalized. GATE_SCORING_POLICY_GOC.md §5.2–5.3 define mandatory diagnostic questions but not scoring algorithm.

2. **Commit effects consistency** — Seam exists, but rules for detecting/preventing conflicting continuity impacts not documented.

3. **Escape / containment behavior** — Policy defined (GATE_SCORING_POLICY_GOC.md §6.1), but integration into graph nodes TBD. No explicit containment-first branch in validation path.

4. **Content authority integration** — YAML module authority documented in VERTICAL_SLICE_CONTRACT_GOC.md §6.1, but runtime loading and authority-conflict resolution not shown in graph. "Detect builtin/YAML conflict" mentioned, not operationalized.

5. **FY-governance enforcement workflow** — Contractify reports exist, but CI merge gates that enforce them do not. No automated drift alerting.

6. **Multi-intent handling** — Scene director selects single `selected_scene_function` via priority rule (CANONICAL_TURN_CONTRACT_GOC.md §3.5), but competing simultaneous pressure lines only defined in §5 (pacing_mode: multi_pressure). Interaction untested.

7. **Bounded reasoning scope** — Model prompt shaping documented implicitly (context synthesis, responder set), but exact guardrails against open-world elaboration not formalized.

---

## 4. Work-Field Maturity Review

### 4.1 Runtime Authority and Session Lifecycle

**Maturity:** F (Implemented and evidenced)  
**Implementation Status:** Complete in world-engine/app/story_runtime/manager.py; StoryRuntimeManager holds in-memory sessions, executes turns via graph, manages narrative commit.  
**Evidence Status:** ADRs documented, tests passing (story_runtime_api tests, session_routes tests).  
**Governance Status:** Contractify records CTR-ADR-0001-RUNTIME-AUTHORITY, CTR-RUNTIME-AUTHORITY-STATE-FLOW with high confidence (0.95+).  
**Strengths:**
- Clear separation: world-engine owns play, backend owns governance.
- ADRs explicit about consequences (proxy/secret config required, transitional backend paths must be labeled).
- Code anchors unambiguous (StoryRuntimeManager is the sole in-memory session authority).

**Blockers:** None. Authority is established and evidenced.

**Drift Risks:** Backend session_store.py is transitional and non-durable; drift risk if new features silently add duplicate session logic. Mitigated by ADR-0002 quarantine policy and backend-runtime-classification docs.

**End-State Relevance:** Critical. Runtime authority is foundational for everything downstream.

---

### 4.2 Player Input Interpretation

**Maturity:** F (Implemented and evidenced)  
**Implementation Status:** story_runtime_core/input_interpreter.py complete; returns structured object with kind, confidence, intent, entities, selected_handling_path.  
**Evidence Status:** Test suite story_runtime_core/tests/test_input_interpreter.py operational; covers speech, action, reaction, mixed, ambiguous categories.  
**Governance Status:** Contractify records CTR-PLAYER-INPUT-INTERPRETATION with confidence 0.93; implemented_by and validated_by links established.  
**Strengths:**
- Contract is explicit: natural language is primary, explicit commands secondary.
- Interpreter is shared across backend (preview) and world-engine (authoritative).
- Ambiguity is honest (confidence, ambiguity_reason, conservative hints).

**Blockers:** None. Input interpretation is ready for production.

**Drift Risks:** Backend may expose `backend_interpretation_preview` as a second truth surface. Mitigated by contract statement: "not a second runtime truth."

**End-State Relevance:** Critical. Input interpretation drives turn graph routing and model prompt shaping.

---

### 4.3 Scene Identity and Dramatic Direction

**Maturity:** E (Implemented but weakly evidenced)  
**Implementation Status:** 
- ai_stack/goc_scene_identity.py implements scene assessment and responder set selection.
- ai_stack/goc_yaml_authority.py handles canonical YAML loading.
- director_assess_scene and director_select_dramatic_parameters nodes in graph.
- Controlled vocabulary operationalized (scene_function, pacing_mode, silence_brevity_decision).

**Evidence Status:** 
- ai_stack/tests/test_goc_scene_identity.py operational but coverage thin.
- Smoke test for scene guidance file structure passing.
- No production tests of director decisions under multi-pressure or scope-breach conditions.

**Governance Status:** Contractify records CTR-ADR-0003-SCENE-IDENTITY (confidence 0.93), CTR-GOC-VERTICAL-SLICE, CTR-GOC-CANONICAL-TURN; vocabulary mapped.

**Strengths:**
- Scene assessment deterministic (rule-based, not model-based, before proposal generation).
- Responder asymmetry is checked (relationships, attitudes, baseline roles).
- Single selected_scene_function rule (priority: revealed_fact > dignity_injury > alliance_shift ...) explicit.
- Controlled vocabulary frozen for MVP (8 scene functions, 5 pacing modes, 4 silence modes).

**Blockers:**
- Content authority integration incomplete. "goc_resolve_canonical_content" node placeholder; actual YAML → scene assessment integration not fully wired.
- Director nodes have no formal test coverage of conflict resolution (e.g., pacing_mode multi_pressure with competing scene functions).
- Fallback behavior when scene assessment cannot resolve (e.g., new character not in relationships YAML) not formalized.

**Drift Risks:**
- Silent merging of builtins and YAML authority. Mitigated by VERTICAL_SLICE_CONTRACT_GOC.md §6.1 rule: "YAML wins; builtins may only mirror YAML or remain explicitly non-authoritative."
- Director node overwrites of proposal fields. Mitigated by CANONICAL_TURN_CONTRACT_GOC.md §3.6: "Silent overwrite from raw model output is forbidden."

**End-State Relevance:** High. Scene identity is central to GoC's dramatic integrity and validation decisions.

---

### 4.4 Proposal Generation and Model Invocation

**Maturity:** E (Implemented, weak evidence)  
**Implementation Status:** 
- _invoke_model node orchestrates LangChain adapter invocation.
- proposal_normalize node maps model output to proposed_state_effects.
- Fallback path via _fallback_model with adapters.get("mock").

**Evidence Status:** 
- Adapter tests exist but limited scope.
- Mock/fallback tested in isolation, not in turn context.
- No production tests of generation under tight dramatic constraints.

**Governance Status:** Contractify records CTR-PLAYER-INPUT-INTERPRETATION (model prompt shaping documented), but generation seam itself not separately governed.

**Strengths:**
- Model prompts include interpreted input summary (discrete hints to constrain generation).
- Fallback path is explicit and diagnostic (metadata marks managed fallback vs degraded).
- Proposal is clearly non-authoritative (CANONICAL_TURN_CONTRACT_GOC.md §2.1: proposal produces candidate material only).

**Blockers:**
- Model guardrails against open-world elaboration not formalized. Prompt engineering documented implicitly.
- Bounded meta-strategy (preventing model from "stepping outside" slice) not specified in code.
- Generation cost tracking and optimization not documented.

**Drift Risks:**
- Model invocation becoming the truth authority instead of proposal-only. Mitigated by visible rendering seam (render_visible only outputs committed truth).
- Proposal field overwrites. Mitigated by director node protection (§3.6 above).

**End-State Relevance:** High. Generation quality drives dramatic satisfaction.

---

### 4.5 Validation Seam

**Maturity:** D (Partially implemented)  
**Implementation Status:** 
- validate_seam node exists in graph.
- run_validation_seam function called but logic stubbed (returns approved status).
- validation_outcome structure defined (status: approved/rejected/waived, reason, validator_lane).

**Evidence Status:** 
- No production tests of validation rule engine.
- Gate policy documents mandatory diagnostic questions (§5.2–5.3) but rule logic not formalized.

**Governance Status:** Contractify records validation seam in CTR-GOC-CANONICAL-TURN (implemented_by list includes validate_seam), but rule engine itself not governed.

**Strengths:**
- Seam is explicit in turn contract and turn state.
- Three outcome modes (approved/rejected/waived) match freeze policy.
- Validation outcome is never silent (even waived must be recorded).

**Blockers:**
- **Critical:** Rule engine not operationalized. GATE_SCORING_POLICY_GOC.md §1.2 mentions "rule-based GoC validator; not a second LLM judge" but actual rules not coded.
- No logic for detecting proposed_state_effects conflicts with existing scene/continuity.
- No fallback when validation is absent (marked as failure_class missing_validation_path, but no automatic downgrade).

**Drift Risks:**
- Validation becoming a second model review. Mitigated by policy: must be rule-based, not model-based.
- Validation path being silently skipped. Mitigated by GATE_SCORING_POLICY_GOC.md §6.2: experiment_preview must be recorded if validation absent.

**End-State Relevance:** Critical. Validation is the gate between proposal and commit; without formalized rules, no integrity claim is possible.

---

### 4.6 Commit Seam and Narrative Authority

**Maturity:** E (Implemented, weak evidence)  
**Implementation Status:** 
- commit_seam node exists in graph.
- run_commit_seam function calls resolve_narrative_commit (world-engine/app/story_runtime/commit_models.py, DS-012 split completed 2026-04-10).
- committed_result structure defined (commit_applied: bool, committed_effects: list, commit_lane).
- Narrative threads updated on commit (StoryNarrativeThreadSet, update_narrative_threads).

**Evidence Status:** 
- Session route tests verify commit surface exists.
- No integration tests of commit under multi-effect or continuity-conflict scenarios.
- narrative_commit_resolution.py is newly split (DS-012, post-artifact: session_20260410_DS-012_narrative_commit_post.md); integration untested at scale.

**Governance Status:** Contractify records commit seam in CTR-GOC-CANONICAL-TURN; commit semantics documented in CANONICAL_TURN_CONTRACT_GOC.md §2.1.

**Strengths:**
- Commit is sole source of world truth (GATE_SCORING_POLICY_GOC.md §6.3: "no factual claims without committed_result").
- Narrative threads carry forward bounded continuity (not unbounded memory).
- Commit only runs when validation_outcome.status == approved (or waived).

**Blockers:**
- **Critical:** No formal consistency checking for commit effects. No detection of conflicting continuity impacts (e.g., both "dignity_injury" and "repair_attempt" in same turn).
- narrative_commit_resolution.py is newly split but integration with full turn graph untested.
- Failure recovery (rollback, partial commit) not specified.

**Drift Risks:**
- Commit being skipped or silently failing. Mitigated by diagnostics: failed commits are marked in failure_markers.
- Continuity impacts being lost. Mitigated by bounded carry-forward (prior_continuity_impacts list, not unbounded memory).

**End-State Relevance:** Critical. Commit is the authoritative narrative decision point.

---

### 4.7 Visible Output and Rendering

**Maturity:** D (Implemented, weak evidence)  
**Implementation Status:** 
- render_visible node exists in graph.
- run_visible_render function generates visible_output_bundle (gm_narration, spoken_lines).
- visibility_class_markers populated (truth_aligned, bounded_ambiguity, non_factual_staging).
- Fallback-marking when commit absent (non_factual_staging used for preview-class output).

**Evidence Status:** 
- No end-to-end tests of visible output under various visibility classes.
- No tests of staging behavior when validation/commit absent.

**Governance Status:** Contractify records visibility seam in CTR-GOC-CANONICAL-TURN; visibility doctrine documented in VERTICAL_SLICE_CONTRACT_GOC.md §5 and GATE_SCORING_POLICY_GOC.md §6.3.

**Strengths:**
- Visibility classes are explicit (truth_aligned = committed truth; bounded_ambiguity = intentional ambiguity; non_factual_staging = proposal-only without claim).
- Staging behavior is defined for preview mode (no pretense of validation/commit).
- Seam is last before player sees output (integrity checkpoint).

**Blockers:**
- No formal rules for when to use which visibility class. Policy exists (§6.3: "staging when no commit"), but decision logic not coded.
- No fallback when render_visible fails (e.g., model generates incomprehensible output).

**Drift Risks:**
- Factual claims appearing in non_factual_staging mode. Mitigated by gate policy: turn_integrity fails if visible output implies validation/commit when paths absent.
- Visibility classes used as labels without actual effect. Mitigated by test coverage TBD.

**End-State Relevance:** High. Visible output is the player-facing truth; accuracy here is critical.

---

### 4.8 Continuity and Memory

**Maturity:** D (Partially implemented)  
**Implementation Status:** 
- prior_continuity_impacts field carries forward bounded continuity class from prior turn.
- narrative_threads structure holds StoryNarrativeThreadSet (character threads, relationship threads).
- ThreadUpdateTrace tracks updates across turns.
- goc_prior_continuity_for_graph and goc_append_continuity_impacts module hooks.

**Evidence Status:** 
- No tests of multi-turn continuity carry-forward.
- No tests of continuity inconsistency detection (contradicting effects).
- narrative_threads not tested at scale.

**Governance Status:** Contractify records continuity in CTR-GOC-CANONICAL-TURN (continuity_impacts field); continuity classes in VERTICAL_SLICE_CONTRACT_GOC.md §5.

**Strengths:**
- Continuity is bounded (not unbounded memory). Prior impacts carry forward as a list, not a growing monolith.
- Continuity classes are frozen (8 labels: situational_pressure, dignity_injury, alliance_shift, revealed_fact, refused_cooperation, blame_pressure, repair_attempt, silent_carry).
- Narrative threads are structured (character vs relationship thread types).

**Blockers:**
- **Critical:** No detection of continuity inconsistency. GATE_SCORING_POLICY_GOC.md §6.4 mentions failure_class continuity_inconsistency, but no logic to detect it.
- No priority rule when multiple continuity effects compete (unlike scene function priority rule in §3.5).
- Narrative thread merging logic untested (what happens when two turns update the same character thread?).

**Drift Risks:**
- Continuity expanding unbounded. Mitigated by bounded prior_continuity_impacts list and narrative_threads structure.
- Conflicting continuity effects silently co-existing. Not mitigated; this is the missing validation rule.

**End-State Relevance:** High. Continuity is the backbone of multi-turn dramatic coherence.

---

### 4.9 Validation and Commit Discipline (Seams Coherence)

**Maturity:** D (Documented policy, weak enforcement)  
**Implementation Status:** 
- Seams are implemented as named graph nodes.
- Validation (proposed_state_effects → validation_outcome) and commit (validation_outcome + proposed_state_effects → committed_result) are operationalized.
- Semantics documented in CANONICAL_TURN_CONTRACT_GOC.md §2.2–2.3: proposal ≠ validation ≠ commit ≠ visibility.

**Evidence Status:** 
- Smoke tests pass (GoC structure).
- No gate scoring tests (bundled evaluation against anchor scenarios missing).
- No tabletop trace-through evidence (GATE_SCORING_POLICY_GOC.md §8 defines requirement, not evidence).

**Governance Status:** Contractify records CTR-GOC-CANONICAL-TURN, CTR-GOC-GATE-SCORING; policy detailed in three turn contracts.

**Strengths:**
- Single writer per seam (each node has one responsibility).
- Seam closure rules are explicit (§2.3: if validation absent, no committed truth claimed; if commit absent, no factual claims; if visibility absent, staging only).
- Diagram shows seam boundaries (proposal → validation → commit → visible).

**Blockers:**
- **Critical:** Enforcement gates are absent. No CI check that validates each seam's invariants.
- No test coverage of seam boundaries (e.g., model overwriting director decisions, validation being skipped, commit claiming effects it shouldn't).
- No dynamic enforcement (e.g., runtime check that validation_outcome exists before commit).

**Drift Risks:**
- Silent seam skipping. Mitigated by diagnostics: missing seams are marked in failure_markers.
- Seam overwriting. Mitigated by node protection rules (§3.6), but no runtime enforcement.

**End-State Relevance:** Critical. Seam coherence is the entire narrative integrity contract.

---

### 4.10 Observability and Diagnostics

**Maturity:** E (Implemented, weak evidence integration)  
**Implementation Status:** 
- graph_diagnostics populated by _package_output: graph_name, graph_version, nodes_executed, node_outcomes, fallback_path_taken, execution_health, errors, capability_audit, repro_metadata, operational_cost_hints.
- diagnostics_refs collected (operator_compact bundle, dramatic_review, transition_pattern).
- build_operator_canonical_turn_record creates stable operator JSON view.

**Evidence Status:** 
- Diagnostics structure tested in isolation (test_goc_scene_identity.py checks graph_diagnostics fields).
- No end-to-end tests of diagnostics completeness under failure scenarios.
- Mandatory questions (GATE_SCORING_POLICY_GOC.md §5.2–5.3) not verified by test assertions.

**Governance Status:** Contractify records diagnostic surfaces in CTR-GOC-CANONICAL-TURN, CTR-GOC-GATE-SCORING (mandatory questions defined).

**Strengths:**
- Diagnostics are comprehensive (graph execution trace, fallback markers, repro hints, cost context).
- Multiple read modes (operator_compact, dramatic_expanded) defined without creating second truth.
- Mandatory questions are explicit and testable.

**Blockers:**
- **Critical:** Mandatory diagnostic questions are not tested. No CI gate verifies that questions 1–8 (§5.2) are answerable from returned diagnostics.
- repro_metadata format and completeness not validated.
- operator_compact bundle not tested as a deliverable artifact.

**Drift Risks:**
- Diagnostics becoming complete but unverified (looks good, fails under review). Mitigated by mandatory questions once gated.
- Missing repro hints. Mitigated by CI gate (planned).

**End-State Relevance:** High. Diagnostics enable operational review and are required for gate scoring.

---

### 4.11 Service Integration and Backend Proxy

**Maturity:** E (Implemented and partially evidenced)  
**Implementation Status:** 
- backend/app/services/game_service.py proxies turn execution to world-engine.
- Internal URLs (PLAY_SERVICE_INTERNAL_URL) configured.
- Session routes (backend/app/api/v1/session_routes.py) implement turn endpoint.
- Session service (backend/app/services/session_service.py) creates/manages backend session objects.

**Evidence Status:** 
- Session route tests passing.
- world-engine API tests passing.
- No end-to-end tests of backend → world-engine → diagnostics → backend return path.

**Governance Status:** Contractify records CTR-ADR-0002-BACKEND-SESSION-QUARANTINE (backend transitional surfaces documented); backend-runtime-classification documents quarantine boundaries.

**Strengths:**
- Backend is cleanly quarantined from play runtime (ADR-0002).
- Proxy is stateless (backend does not maintain play state).
- Session routes are explicit about boundaries (create, execute, read, delete).

**Blockers:**
- No test of full round-trip (player input → backend → world-engine → response → backend → player).
- Error handling under service unavailability not specified.

**Drift Risks:**
- Backend adding new session mutation logic. Mitigated by backend-runtime-classification docs: forbidden surfaces listed.
- Proxy logic becoming complex. Mitigated by architectural clarity (backend as governance layer, not play layer).

**End-State Relevance:** High. Backend integration is how players interact with the runtime.

---

### 4.12 Governance and Anti-Drift Control

**Maturity:** D (FY-suites installed, workflow TBD)  
**Implementation Status:** 
- Contractify: 60 contracts discovered, audit reports generated (audit.hermetic-fixture.json, CANONICAL_REPO_ROOT_AUDIT.md).
- Despaghettify: AST analysis complete (15,392 functions, nesting/cycles reported).
- Docify: baseline scan running (1,097 findings, parse errors identified).
- Execution governance state tracking (EXECUTION_GOVERNANCE.md, workstream state docs).

**Evidence Status:** 
- Contractify audit JSON reports exist (committed to repo).
- Despaghettify metrics reports exist.
- Docify findings reports exist.
- No CI integration of these reports.
- No enforcement gates (merge blocks, contract drift alerts).

**Governance Status:** Contractify reports 60 contracts; despaghettify reports structural findings; docify scans docstring coverage. None are wired to CI.

**Strengths:**
- FY-suite infrastructure is in place and operational.
- Discovery is working (contracts found, relations mapped, conflicts identified).
- State tracking is disciplined (workstream artifacts, pre/post comparison).

**Blockers:**
- **Critical:** Enforcement workflow not implemented. Contractify reports exist but no CI job enforces contract coherence.
- FY-suite outputs not integrated into merge gates.
- Drift detection is manual (reports exist, but no alerting).
- Docify findings (1,097 missing docstrings) not addressed; FY-suite tools themselves lack docstrings.

**Drift Risks:**
- Contracts discovered but never enforced, leading to silent drift.
- Despaghettify and docify reports accumulating without action.
- New code bypassing governance because enforcement gates are absent.

**End-State Relevance:** Critical. Without governance workflow, drift will accumulate.

---

### 4.13 Contract Coherence

**Maturity:** E (60 contracts mapped, relations established, some coherence gaps)  
**Implementation Status:** 
- Contractify audit completed (60 contracts, 310 relations, 5 precedence tiers).
- 9 mandatory runtime anchors promoted to first-class records with relations.
- 3 intentional conflicts documented (runtime spine retirement, evidence baseline clone reproducibility, writers-room/RAG overlap).

**Evidence Status:** 
- Contract records include confidence scores (0.85–0.98).
- Relations documented with edge types (depends_on, refines, derives_from, implements, validates, operationalizes).
- IMPLEMENTATION_RESULT.md provides detailed evidence of attachment.

**Governance Status:** Contractify audit reports 6 conflict records (5 documented + 3 intentional); precedence tier system in place.

**Strengths:**
- Contracts are well-mapped (60 distinct records, not a monolithic list).
- Relations are explicitly typed (not just "related to").
- Conflicts are acknowledged and documented (not hidden).
- Precedence tier system allows deterministic resolution of clashes.

**Blockers:**
- Runtime spine retirement timeline unresolved (CNF-RUNTIME-SPINE-TRANSITIONAL-RETIREMENT). Quarantine policy documented, but backward-compatibility constraints not finalized.
- Writers-room/RAG overlap marked as `overlaps_with` but future write-back flows not addressed.
- Some contracts lack explicit implementation_by or validated_by links (need curator review to confirm).

**Drift Risks:**
- New contracts added without relating to existing ones (discovery non-deterministic).
- Contracts drifting from code without enforcement gates.
- Precedence tier system not enforced in CI.

**End-State Relevance:** High. Contract coherence is the foundation for governance.

---

### 4.14 Documentation Coherence

**Maturity:** D (Baseline scanned, gaps identified, governance TBD)  
**Implementation Status:** 
- Docify baseline scan complete: 1,097 findings across 227 files.
- Parse errors identified (4: BOM issues in 4 files).
- Missing docstring audit: 100+ missing docstrings in FY-suite tools.

**Evidence Status:** 
- Docify audit reports exist.
- Missing docstrings documented but not systematically remediated.

**Governance Status:** Docify scans identified, no enforcement gates in place.

**Strengths:**
- Baseline is established (1,097 findings cataloged).
- Parse errors are explicit (BOM cleanup in 4 files will fix).

**Blockers:**
- **Critical:** FY-suite tools themselves lack docstrings (contractify/tools/adr_governance.py, audit_pipeline.py, hub_cli.py, etc.). This undermines governance credibility.
- No remediation plan for 100+ missing docstrings.
- Docify enforcement not integrated into CI.

**Drift Risks:**
- Documentation gaps accumulating without tracking.
- FY-suite tools becoming unmaintainable without docs.

**End-State Relevance:** Medium. Documentation coherence is important for maintenance, less critical for runtime readiness.

---

### 4.15 Structural Change Discipline

**Maturity:** C → D (Despaghettify analysis complete, workflow TBD)  
**Implementation Status:** 
- Despaghettify AST analysis: 15,392 functions across 1,418 Python files analyzed.
- Metrics: 192 files over 100 lines, 734 files with nesting ≥ 3, 34 with nesting ≥ 6, 5.4% in import cycles.
- Top 12 longest functions identified (largest: 381 lines in migration script).

**Evidence Status:** 
- Despaghettify metrics reports exist.
- No concrete "too long/too nested" enforcement rules documented.

**Governance Status:** Despaghettify reports generated, no CI enforcement.

**Strengths:**
- AST analysis is comprehensive (imports, nesting, length, magic literals all tracked).
- Import cycle detection is working (5.4% of files flagged).
- Longest functions are identified (largest 12 visible).

**Blockers:**
- No enforcement rules ("too long" = ? lines; "too nested" = ? depth).
- No automated refactoring guidance.
- Despaghettify workflow not wired to CI.

**Drift Risks:**
- Structural complexity expanding without bounds.
- Long functions becoming longer.
- Import cycles accumulating.

**End-State Relevance:** Medium. Structural discipline helps maintenance; less critical for MVP runtime readiness.

---

## 5. MVP Contract-and-Governance Inventory

### What Should Be Contractified

**In scope:**
- ✓ Runtime authority contracts (ADR-0001, ADR-0002, ADR-0003)
- ✓ Slice contracts (vertical slice, turn, gate scoring)
- ✓ API contracts (OpenAPI, REST surface)
- ✓ Interpretation contract (input handling)
- ✓ Validation/commit contracts (seam semantics)
- ✓ Content authority contract (YAML module truth)
- ✓ Service boundaries (backend quarantine, world-engine authority)
- ✓ Narrative governance contracts (publishing, RAG)
- ✗ Validation rule engine specification (currently implicit)
- ✗ Commit consistency checking rules (currently implicit)
- ✗ Fallback/escape policy operationalization (currently implicit)

### What Should Be Despaghettified

**In scope:**
- ✓ Structural analysis (completed)
- ✗ Enforcement rules (not defined)
- ✗ Refactoring guidance (not generated)
- ✗ Import cycle resolution (not automated)

### What Should Be Doc-Governed

**In scope:**
- ✓ Normative documentation (contracts, ADRs, architecture)
- ✓ Baseline findings (1,097 documented)
- ✗ FY-suite docstrings (100+ missing, should be remediable)
- ✗ Implementation guide docstrings (should be comprehensive)

### What Is Already Governed

**Contractify:**
- ✓ 60 contracts discovered and recorded
- ✓ 310 relations mapped
- ✓ 5 precedence tiers in place
- ✓ 6 conflicts documented (3 intentional unresolved)
- ✓ Implementation_by and validated_by links (high confidence for major contracts)
- ✓ Discovery audit running (audit.hermetic-fixture.json)

**Despaghettify:**
- ✓ AST analysis complete
- ✓ Metrics reports generated
- ✓ Top 12 longest functions identified
- ✓ Import cycle detection working

**Docify:**
- ✓ Baseline scan complete
- ✓ 1,097 findings documented
- ✓ Parse errors identified

**Execution Governance:**
- ✓ Workstream state tracking (EXECUTION_GOVERNANCE.md)
- ✓ Pre/post artifact structure in place
- ✓ DS-012 (narrative commit split) completed with evidence

### What Is Not Yet Properly Governed

1. **Validation rule engine** — Implicit in run_validation_seam, not contractified as "validate GoC effects against scene/continuity rules."

2. **Commit consistency** — No contract specifying "detect conflicting continuity impacts."

3. **Fallback/escape behavior** — Policy defined, not operationalized in graph.

4. **Content authority integration** — Documented, but "goc_resolve_canonical_content" is a placeholder.

5. **Gate scoring cadence and delegation** — Policy defined (GATE_SCORING_POLICY_GOC.md §4), no enforcement mechanism.

6. **FY-suite enforcement workflow** — Contractify reports exist, no CI gates.

7. **Docstring coverage** — Baseline identified, no remediation plan.

---

## 6. Prior Cycle Comparison

**Prior audit instruction:** Task_Implementation.md (executed 2026-04-16)  
**Prior selected target:** Contractify runtime/MVP contract spine attachment with full evidence recording  
**Expected change:** Promote 9 mandatory anchors to first-class records, establish relations, attach implementation/validation links

### Actual Returned Change

✓ **SUCCESS.** The implementation AI successfully:
- Promoted 9 mandatory anchors to first-class Contractify records (CTR-ADR-0001, CTR-RUNTIME-AUTHORITY-STATE-FLOW, CTR-GOC-VERTICAL-SLICE, CTR-GOC-CANONICAL-TURN, CTR-GOC-GATE-SCORING, CTR-PLAYER-INPUT-INTERPRETATION, CTR-BACKEND-RUNTIME-CLASSIFICATION, CTR-CANONICAL-RUNTIME-CONTRACT, CTR-WRITERS-ROOM-PUBLISHING-FLOW, CTR-RAG-GOVERNANCE).
- Mapped 310 relations across 60 total contracts (up from discovered baseline).
- Established 5 precedence tiers (runtime_authority, slice_normative, implementation_evidence, verification_evidence, projection_low).
- Attached implementation_by links (16 contracts with code surfaces).
- Attached validated_by links (27 contracts with test surfaces).
- Documented 6 conflicts explicitly (5 documented + 3 intentional unresolved).
- Evidence recorded in IMPLEMENTATION_RESULT.md with detailed metrics.

### Success / Partial / Failure Judgment

**SUCCESS.** The prior audit's target was achieved. Contractify output went from discovery-only to governance-ready with explicit relations, precedence, and conflict documentation.

### Drift or Overreach Judgment

**No drift detected.** Implementation AI did not:
- Overreach into code rewriting or architectural changes.
- Flatten conflicts or hide complexity.
- Create fake completeness (correctly identified 6 conflicts as intentional/unresolved).

**No overreach detected.** Work remained scoped to governance layer; no feature implementation.

### Improvement of Total Preparedness

**Preparedness improved by ~20%** on governance dimension:
- Before: Contracts discovered but not formally related or weighted.
- After: Contracts now queryable, relations explicit, precedence deterministic.

**Remaining blockers unchanged:**
- Validation rule engine still implicit.
- Commit consistency checking still absent.
- FY-suite enforcement workflow still unwired.

**Implication:** MVP governance layer is now **governable** (60 contracts, relations explicit, precedence clear), but **not yet enforced** (no CI gates, no drift alerts).

---

## 7. Full-Gap Analysis

### Exact Missing Work

1. **Validation rule engine operationalization**
   - Current: run_validation_seam returns approved status.
   - Required: Formal rule engine that checks proposed_state_effects against scene/continuity constraints.
   - Scope: ai_stack/goc_validation_rules.py (new).
   - Tests: ai_stack/tests/test_goc_validation_rules.py (comprehensive rule variants).

2. **Commit consistency checking**
   - Current: resolve_narrative_commit applies effects.
   - Required: Check for conflicting continuity impacts (both "dignity_injury" and "repair_attempt" in same turn).
   - Scope: world-engine/app/story_runtime/commit_models.py (enhance).
   - Tests: world-engine/tests/test_commit_consistency.py (multi-effect scenarios).

3. **Content authority integration (YAML → validation → commit)**
   - Current: goc_resolve_canonical_content is a placeholder; YAML loading not fully wired.
   - Required: Runtime loads canonical YAML, scene director uses it, validation checks against it, commit applies it.
   - Scope: ai_stack/goc_yaml_authority.py (enhance), langgraph_runtime.py (wire goc_resolve_canonical_content).
   - Tests: ai_stack/tests/test_goc_yaml_authority.py (authority conflict resolution).

4. **Fallback/escape behavior operationalization**
   - Current: Fallback path exists, escape policy documented.
   - Required: Graph nodes for scope-breach containment, silence/withholding decisions, and graceful degradation.
   - Scope: ai_stack/goc_fallback_and_escape.py (new or enhance existing).
   - Tests: Tests for containment behavior, silent carry, withheld output.

5. **Gate scoring automation and CI integration**
   - Current: Bundles defined (operator_compact, dramatic_expanded, freeze_integrity), no automation.
   - Required: CLI or API to run bundles, score scenarios, report against mandatory questions.
   - Scope: 'fy'-suites/despaghettify/tools/gate_score_matrix_cli.py (enhance/create).
   - Tests: tests/experience_scoring_cli/ (tabletop scenarios).

6. **FY-governance enforcement workflow**
   - Current: Contractify reports generated, no CI gates.
   - Required: CI job that fails merge if contractify audit detects new drift, docify finds gaps in contracts, despaghettify flags complexity increase.
   - Scope: .github/workflows/fy-governance-gates.yml (new) + contractify/tools/ci_enforcement.py (new).
   - Tests: CI gate behavior tests (mock drift, verify blocking).

7. **Mandatory diagnostic questions validation**
   - Current: Questions defined in GATE_SCORING_POLICY_GOC.md §5.2–5.3.
   - Required: Test suite that verifies all 8 questions answerable from returned diagnostics.
   - Scope: tests/gate_scoring/test_diagnostic_completeness.py (new).
   - Tests: Run sample turns, check all questions answerable.

8. **Documentation governance enforcement**
   - Current: Docify scans 1,097 findings, FY-suite tools lack docstrings.
   - Required: Remediate 4 parse errors (BOM cleanup), add ~100 missing docstrings, wire docify to CI.
   - Scope: FY-suite tools (contractify/, despaghettify/, docify/) docstring additions.
   - Tests: CI gate for docstring coverage.

9. **Tabletop trace-through evidence**
   - Current: Policy defined, no evidence collected.
   - Required: Run 5 anchor scenarios (standard, thin-edge, out-of-scope, anti-seductive, multi-pressure) through full turn graph, collect evidence.
   - Scope: tests/gate_scoring/tabletop_trace_through.py (new).
   - Tests: 5 scenarios with full diagnostic output.

10. **Continuity inconsistency detection**
    - Current: failure_class continuity_inconsistency defined, no logic.
    - Required: Validator rule that detects contradicting continuity effects.
    - Scope: ai_stack/goc_validation_rules.py (rule: check prior_continuity_impacts + proposed_continuity_impacts for conflicts).

### Under-Constrained Work

- **Model guardrails against open-world elaboration** — Prompt shaping documented implicitly; no formal specification of bounded reasoning scope.
- **Multi-intent handling priority rules** — Scene function priority rule documented (§3.5), but interaction with pacing_mode multi_pressure untested.
- **Narrative thread merging logic** — What happens when two concurrent updates hit the same thread? Undefined.

### Architecture-to-Code Gaps

- **goc_resolve_canonical_content placeholder** — Expected to wire YAML authority into graph; currently a no-op.
- **Validation rule engine implicit** — Documented as "rule-based," not formalized.
- **Escape branch missing** — Containment-first policy defined, not in graph nodes.

### Service Integration Gaps

- **End-to-end backend → world-engine → response path untested** — Round-trip integration test missing.
- **Error handling under service unavailability** — Fallback behavior when world-engine is down not specified.

### Proof Gaps

- **No gate scoring tests** — Mandatory questions not verified in CI.
- **No multi-turn continuity tests** — Carry-forward and conflict detection untested.
- **No commitment under conflict tests** — What happens when validated effects conflict with existing continuity?

### Contract-Governance Gaps

- **FY-enforcement workflow unwired** — Reports generated, no merge gates.
- **Precedence tier system not enforced in CI** — Contracts have tiers, but no automation uses tiers to resolve conflicts.
- **Drift detection manual** — No alerting when code or contracts diverge.

### Structural-Governance Gaps

- **Despaghettify enforcement rules undefined** — Metrics collected, no "too long" or "too nested" thresholds.
- **Import cycle resolution not automated** — Cycles flagged, no guidance to fix them.

### Documentation-Governance Gaps

- **FY-suite tools lack docstrings** — ~100 missing docstrings in contractify/, despaghettify/, docify/ tools.
- **Docify enforcement not in CI** — Scans run locally, no merge gate.

### End-State Coverage Gaps

- **Tabletop trace-through** — GATE_SCORING_POLICY_GOC.md §8 defines requirement; no evidence collected.
- **Scenario anchors** — 5 minimum scenarios mentioned (standard, thin-edge, out-of-scope, anti-seductive, multi-pressure); no evidence of running them.

### Drift Risks

- **Validation rule engine becoming opaque** — Rules embedded in code without formal spec; drift likely.
- **Content authority integration incomplete** — YAML authority claimed, but integration points unclear; silent divergence possible.
- **Escape behavior informally handled** — Policy documented, not in graph; ad-hoc implementations possible.
- **FY-governance outputs accumulating unused** — Reports generated but not enforced; reports ignored → governance debt.

---

## 8. Next-Target Decision

### Apparent / Default Target

Based on chronological order and prior work, the default target would be:
**Validation rule engine operationalization** — Continue down the seam path (after contractify, now validate seams themselves).

### Test of Default Target Sensibility

**Is this target actually the best move?**

**Analysis:**

The validation rule engine is **necessary but not sufficient** for immediate MVP readiness:
- ✓ **Unblocks:** Validation seam becomes enforceable (currently stubbed).
- ✓ **Operationalizes:** Rules can be tested and reviewed.
- ✓ **Evidence:** Tests will show validation decisions are correct.

**But:**
- ✗ **Doesn't unblock commitment:** Even with validation rules, commit consistency checking is still absent.
- ✗ **Doesn't address governance workflow:** Enforcement gates still missing; rules will exist in code but not be gated.
- ✗ **Doesn't close FY-governance loop:** Contractify reports still not wired to CI.
- ✗ **Doesn't prove readiness:** Even with validation rules, no tabletop trace-through evidence exists to show the rules work under realistic scenarios.

**Risk of choosing validation rules alone:**
- New rule code goes into production untested against real scenarios.
- Rules are locally correct but don't integrate with the broader governance loop.
- Validation "works" locally; still no proof that full turn graph respects the rules.

### Better Alternative Targets

**Option A: FY-governance enforcement workflow (higher unblock value)**

**Target:** Wire contractify/despaghettify/docify outputs to CI merge gates.

**Why superior:**
- ✓ Unblocks all downstream work (validation, commit, docs) by putting governance enforcement in place first.
- ✓ Prevents drift in real time (new code/contracts must pass governance gates).
- ✓ Establishes feedback loop (broken gate → dev fixes issue → resubmit).
- ✓ Closes the FY-suite loop (reports are now actionable, not just informative).
- ✓ Improves MVP preparedness more broadly (governance, not just validation logic).

**Trade-off:** More infrastructure work; less direct feature progress.

**Option B: Tabletop trace-through evidence (higher proof value)**

**Target:** Run 5 anchor scenarios through full turn graph, collect diagnostic evidence.

**Why superior:**
- ✓ Generates proof that the MVP works end-to-end.
- ✓ Identifies actual gaps (rules missing, seams broken) before they hit production.
- ✓ Provides evidence for "ready" claims (mandatory questions answerable, scenarios pass gates).
- ✓ Guides validation rule implementation (tabletop scenarios drive rule specification).
- ✓ Improves MVP preparedness by establishing ground truth.

**Trade-off:** More testing/evidence work; requires good test infrastructure first.

**Option C: Content authority integration (higher architectural completeness)**

**Target:** Complete YAML → scene → validation → commit → visible path.

**Why superior:**
- ✓ Closes a critical architectural seam (YAML authority currently documented but not wired).
- ✓ Unblocks content/scenario testing (cannot test scenarios without YAML properly integrated).
- ✓ Prevents the silent drift between claimed authority (YAML wins) and actual behavior.
- ✓ Required before validation/commit rules can be tested meaningfully.

**Trade-off:** Requires understanding of module loading and scene director integration.

### Selected Next Target

**FY-Governance Enforcement Workflow** (Option A).

**Why it is superior:**

1. **Highest unblock value:** FY-governance workflow is the multiplier. Without it:
   - Validation rules will be code-only, not enforced.
   - Documentation gaps will keep accumulating.
   - Contracts will drift from code without detection.
   - Every future change will need manual review.

2. **Multiplier effect:** Once governance gates are in place:
   - Validation rule implementation becomes continuous (rules added, gates check them).
   - Documentation governance becomes automatic (docs gaps detected at PR time).
   - Contract coherence is maintained (new contracts must relate to existing ones).
   - Drift is caught immediately (structural complexity, contract violations blocked at merge).

3. **Correctness leverage:** With enforcement in place, future work on validation rules, commit consistency, and escape behavior will be **continuously validated** rather than ad-hoc.

4. **MVP closure path:** The path to "fully prepared" becomes:
   - Enforce governance (gates, this target).
   - Implement validation rules (gated by enforcement).
   - Prove tabletop scenarios (gated by governance + rules).
   - Claim readiness (with evidence, not hope).

5. **Fits the "single next best target" rule:** This target is:
   - Architecturally correct (governance layer should be first, not last).
   - Durable (enforcement mechanisms don't become obsolete).
   - Foundational (enables all downstream work).
   - Not cosmetic (directly improves preparedness).

### Why Other Targets Are Less Suitable (Right Now)

- **Validation rules alone:** Necessary but insufficient; rules without enforcement are ignored or diverge over time.
- **Tabletop scenarios alone:** Important but comes *after* governance is wired (scenarios will guide rules, but rules need enforcement to matter).
- **Content authority integration alone:** Critical but should follow governance enforcement (YAML authority needs to be governable once wired in).
- **Documentation governance alone:** Important but lower priority than runtime enforcement gates.

---

## 9. Implementation Master Prompt (for Separate AI)

You are tasked with implementing the **FY-Governance Enforcement Workflow** for World of Shadows MVP v24. Your role is to wire contractify, despaghettify, and docify outputs into CI merge gates so that drift is detected and blocked in real time.

### Scope (In-Scope Items)

1. **Contractify enforcement gate**
   - Create `.github/workflows/fy-contractify-gate.yml` (new GitHub Actions workflow).
   - Gate logic: Run `python -m contractify.tools audit --json` on PR branch, compare to baseline (committed audit snapshot), fail if:
     - New contracts added without relating to existing contracts.
     - Precedence tier assignments change without justification.
     - Confidence scores drop below 0.85 on runtime_authority tier contracts.
     - Named conflicts are removed without resolving them (not allowed; must escalate or document).
   - Baseline: Use `'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md` as authoritative snapshot.
   - Output: Pass/fail message to PR, link to full audit JSON for review.

2. **Docify enforcement gate**
   - Create `.github/workflows/fy-docify-gate.yml` (new GitHub Actions workflow).
   - Gate logic: Run `python -m docify.tools audit` on PR branch, check for:
     - New missing docstrings in contractify/, despaghettify/, docify/, ai_stack/, story_runtime_core/, world-engine/.
     - Parse errors (BOM, syntax) in tracked modules.
     - Degradation of docstring coverage (must not decrease from baseline).
   - Baseline: Establish current docstring coverage from docify audit.
   - Output: Pass/fail message, list of new missing docstrings, link to full audit.

3. **Despaghettify enforcement gate** (optional, lower priority)
   - Create `.github/workflows/fy-despaghettify-gate.yml` (new GitHub Actions workflow).
   - Gate logic: Run `python -m despaghettify.tools check --with-metrics`, check for:
     - New functions over 200 lines (flag for review).
     - Nesting depth increase beyond baseline (e.g., new functions with nesting ≥ 6).
     - Import cycle count increase (cycles flagged but not blocked by default; allow with justification).
   - Baseline: Establish from current despaghettify metrics.
   - Output: Pass/fail message, list of flagged functions.

4. **Enforcement configuration**
   - Create `'fy'-suites/fy_governance_enforcement.yaml` (central config for all gates).
   - Declare:
     - Which gates are mandatory (block merge).
     - Which are advisory (warn but allow merge).
     - Baseline paths (contractify snapshot, docify baseline, despaghettify baseline).
     - Severity thresholds (e.g., confidence < 0.85 on runtime_authority = mandatory block).

5. **Baseline snapshot creation**
   - If not already present, run all audits locally and commit baseline snapshots:
     - `'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md` (already present).
     - `'fy'-suites/docify/baseline_docstring_coverage.json` (create).
     - `'fy'-suites/despaghettify/baseline_metrics.json` (create).

### Scope (Out-of-Scope Items)

- **Do NOT implement validation rules themselves.** The enforcement workflow enforces *existing* rules/audits; it does not define new rules.
- **Do NOT change or enhance contractify/despaghettify/docify tools.** Use them as-is.
- **Do NOT modify code behavior or architecture.** Enforcement gates are metadata/reporting only.
- **Do NOT create new CI jobs for unrelated systems** (e.g., performance testing). Scope is strictly FY-governance gates.
- **Do NOT merge two gates into one.** Each gate (contractify, docify, despaghettify) remains independent; they are listed separately in `fy_governance_enforcement.yaml` but never flattened.

### Required FY-Suite Usage

- **Contractify:** Use `python -m contractify.tools audit --json` to generate audit JSON; compare against baseline using `contractify/tools/ci_drift_check.py` (new, simple diff tool).
- **Docify:** Use `python -m docify.tools audit` to scan docstring coverage; compare against baseline using `docify/tools/ci_coverage_check.py` (new, simple diff tool).
- **Despaghettify:** Use `python -m despaghettify.tools check --with-metrics` to generate metrics; compare against baseline using `despaghettify/tools/ci_metrics_check.py` (new, simple diff tool).

### Required Governance Entries or Mappings

- Update `'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md` to add section: "CI enforcement thresholds and gate policies" (normative for automated decisions).
- Update `'fy'-suites/docify/README.md` to add: "Docstring coverage is enforced at merge time by docify-gate workflow."
- Update `'fy'-suites/despaghettify/spaghetti-setup.md` to add: "Structural metrics are monitored at merge time by despaghettify-gate workflow."

### Required Evidence to Add

- Evidence artifacts per gate:
  - Contractify: `'fy'-suites/contractify/reports/ci_gate_evidence/` (sample pass/fail logs).
  - Docify: `'fy'-suites/docify/reports/ci_gate_evidence/` (sample audit outputs).
  - Despaghettify: `'fy'-suites/despaghettify/reports/ci_gate_evidence/` (sample metrics comparisons).
- Update `'fy'-suites/despaghettify/state/WORKSTREAM_DOCUMENTATION_STATE.md` with note: "FY-governance enforcement gates implemented [date]; gates are now active on merge."

### Forbidden Drift Patterns

- **Do NOT** allow gates to be silently bypassed (e.g., `--no-verify` or `force-push` to main). Enforce at branch protection level.
- **Do NOT** create new contracts without relating them. Contractify gate blocks PRs that add contracts without edges to existing ones.
- **Do NOT** allow docstring coverage to decrease. Docify gate blocks PRs that reduce coverage on tracked modules.
- **Do NOT** allow functions to grow indefinitely. Despaghettify gate flags new long functions for review (advisory first, may become mandatory).
- **Do NOT** silently accept all findings. Gates must have explicit pass/fail logic; "no enforcement" is not an option once gates are wired.

### What the Re-Audit Must Verify

When the implementation AI returns this work, the next audit must check:

1. **Contractify gate is wired and working:**
   - `.github/workflows/fy-contractify-gate.yml` exists and is syntactically valid.
   - Gate runs `contractify audit --json` on PR branch.
   - Gate compares output to baseline using a deterministic diff.
   - Gate fails when new contracts lack relations or confidence drops.
   - Evidence: PR merge check shows "contractify-gate" in status; sample PR shows gate passing/failing correctly.

2. **Docify gate is wired and working:**
   - `.github/workflows/fy-docify-gate.yml` exists and is syntactically valid.
   - Gate runs `docify audit` on PR branch.
   - Gate tracks baseline docstring coverage.
   - Gate fails when coverage decreases on tracked modules.
   - Evidence: PR merge check shows "docify-gate" in status; sample PR shows gate catching new missing docstrings.

3. **Despaghettify gate is wired and working** (advisory; may warn but not block):
   - `.github/workflows/fy-despaghettify-gate.yml` exists and is syntactically valid.
   - Gate runs `despaghettify check --with-metrics`.
   - Gate compares metrics to baseline.
   - Gate warns on new long functions or nesting increases.
   - Evidence: PR shows despaghettify gate in checks (may be advisory).

4. **Enforcement configuration is documented:**
   - `'fy'-suites/fy_governance_enforcement.yaml` exists and lists all gates.
   - Contract governance scope and docify/despaghettify READMEs are updated with gate references.

5. **Baseline snapshots are committed:**
   - Baselines are in repo and stable (not ephemeral).
   - Gates reference baselines by committed path, not local env vars.

6. **No drift or overreach:**
   - Gates do not modify code or create new features.
   - Gates do not bypass FY-suite tools (they use contractify/docify/despaghettify as-is).
   - Gates do not flatten the three independent audits into one (all three remain separate).

---

## 10. Re-Audit Protocol

When the implementation AI returns the FY-governance enforcement workflow, execute this re-audit protocol to verify success and detect drift.

### Immediate Checks (Within 5 Minutes of Return)

1. **Workflow files exist:**
   ```bash
   ls -la .github/workflows/fy-*.yml
   ```
   Expected: fy-contractify-gate.yml, fy-docify-gate.yml, (fy-despaghettify-gate.yml optional).

2. **Enforcement config exists:**
   ```bash
   ls -la 'fy'-suites/fy_governance_enforcement.yaml
   ```
   Expected: file present, < 100 lines, declarative (not executable).

3. **Baseline snapshots exist:**
   ```bash
   ls -la 'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md
   ls -la 'fy'-suites/docify/baseline_docstring_coverage.json
   ls -la 'fy'-suites/despaghettify/baseline_metrics.json
   ```
   Expected: All three files present (even if baseline_*.json are newly created).

4. **Workflows are syntactically valid:**
   ```bash
   python -c "import yaml; yaml.safe_load(open('.github/workflows/fy-contractify-gate.yml'))"
   ```
   Expected: No parse errors.

### Short Verification (Within 30 Minutes)

5. **Contractify gate logic is correct:**
   - Open `.github/workflows/fy-contractify-gate.yml`.
   - Verify it calls `python -m contractify.tools audit --json`.
   - Verify it compares output to `'fy'-suites/contractify/reports/CANONICAL_REPO_ROOT_AUDIT.md`.
   - Verify it fails on: new contracts without relations, confidence drop, named conflict removal.
   - Verify it does NOT: modify code, run contractify discovery, create new contracts.

6. **Docify gate logic is correct:**
   - Open `.github/workflows/fy-docify-gate.yml`.
   - Verify it calls `python -m docify.tools audit`.
   - Verify it compares to baseline docstring coverage.
   - Verify it fails when coverage decreases on tracked modules.
   - Verify it does NOT: add docstrings itself, modify code beyond metrics.

7. **Despaghettify gate logic is correct** (if present):
   - Open `.github/workflows/fy-despaghettify-gate.yml`.
   - Verify it calls `python -m despaghettify.tools check --with-metrics`.
   - Verify it compares to baseline metrics.
   - Verify it warns (not blocks) on new long functions.
   - Verify it does NOT: refactor code, modify function definitions.

8. **Enforcement config is readable:**
   - Open `'fy'-suites/fy_governance_enforcement.yaml`.
   - Verify it declares all three gates (contractify, docify, despaghettify).
   - Verify it specifies mandatory vs advisory (e.g., contractify: mandatory, despaghettify: advisory).
   - Verify it references baseline paths.

9. **Documentation is updated:**
   - Check `'fy'-suites/contractify/CONTRACT_GOVERNANCE_SCOPE.md`: contains section on CI enforcement thresholds.
   - Check `'fy'-suites/docify/README.md`: mentions docify-gate workflow.
   - Check `'fy'-suites/despaghettify/spaghetti-setup.md`: mentions despaghettify-gate workflow.

### Functional Verification (1–2 Hours)

10. **Test contractify gate on a sample change:**
    - Create a test branch.
    - Add a new contract to `docs/dev/contracts/normative-contracts-index.md` without relating it to existing contracts.
    - Commit and push to PR.
    - **Expected:** Contractify gate fails with clear message about missing relations.
    - Revert change, gate should pass.

11. **Test docify gate on a sample change:**
    - Create a test branch.
    - Remove a docstring from a tracked module (e.g., a function in contractify/tools/).
    - Commit and push to PR.
    - **Expected:** Docify gate fails with message about reduced coverage.
    - Restore docstring, gate should pass.

12. **Test despaghettify gate on a sample change** (if present):
    - Create a test branch.
    - Add a function over 200 lines to a tracked module.
    - Commit and push to PR.
    - **Expected:** Despaghettify gate warns (or fails if mandatory) with message about long function.
    - Remove function, gate should pass.

### Depth Verification (2–4 Hours)

13. **Verify gates do not bypass FY-suite tools:**
    - Contractify gate must use `python -m contractify.tools audit --json`, not a custom audit.
    - Docify gate must use `python -m docify.tools audit`, not a custom scanner.
    - Despaghettify gate must use `python -m despaghettify.tools check --with-metrics`, not a custom linter.

14. **Verify baseline stability:**
    - Run `python -m contractify.tools audit --json --out /tmp/test.json` on main branch.
    - Compare `/tmp/test.json` to baseline in repo.
    - **Expected:** They should match (or be very close; allow for timestamp/UUID diffs).
    - If baseline is stale, this will surface the need to refresh it (and gate will detect stale baseline on next PR).

15. **Verify no code drift:**
    - Check git diff between before and after the implementation.
    - Expected code changes: workflows only (no changes to main codebase, ai_stack, world-engine, backend).
    - Expected config changes: `fy_governance_enforcement.yaml` and README updates only.
    - Forbidden: Any changes to validation logic, commit seams, or runtime code.

### Success Criteria

**All of the following must be true:**

- ✓ Workflows exist and are syntactically valid.
- ✓ Baseline snapshots are committed and stable.
- ✓ Enforcement config declares all gates and thresholds.
- ✓ Documentation is updated with gate references.
- ✓ Contractify gate runs and fails on new contracts without relations.
- ✓ Docify gate runs and fails when coverage decreases.
- ✓ Despaghettify gate runs and warns on new long functions (or fails if mandatory).
- ✓ Gates use FY-suite tools as-is (no custom implementations).
- ✓ No code drift or overreach.
- ✓ Baselines are stable when run on main branch.

### Partial-Completion Criteria

**Work is partially complete if:**

- One of three gates is complete but not all three (e.g., contractify works, docify and despaghettify TBD).
- Workflows exist but one or more gates are not wired into branch protection (they exist but don't block merges).
- Enforcement config exists but is incomplete (missing threshold declarations).

**Action on partial completion:** Re-audit should identify which gates are missing or incomplete, and the next audit cycle must prioritize finishing the incomplete gates.

### Failure Criteria

**Work has failed if:**

- Workflows do not exist or fail to parse.
- Gates do not call FY-suite tools (custom implementations instead).
- Gates modify code or create new features (not allowed).
- Baselines are not committed or are ephemeral (not stable).
- Documentation is not updated.
- Gates can be silently bypassed (no branch protection wired).

### Drift Criteria

**Drift is detected if:**

- Contractify gate discovers new contracts that were not documented/related (implies drift in contract inventory).
- Docify gate detects new missing docstrings (implies drift in documentation coverage).
- Despaghettify gate flags new long functions (implies drift in structural complexity).
- Any gate is added/removed without updating `fy_governance_enforcement.yaml` (config drift).
- Baselines are stale (audit output differs from baseline; signals that audit results have changed, requiring baseline refresh or gate investigation).

### Verification Handoff Notes

After re-audit completes, record in the next audit cycle:

1. **Which gates are working:** List any gates that passed functional verification.
2. **Which gates are incomplete:** List any gates that exist but are not fully wired.
3. **Baseline stability:** Note whether baselines needed refresh or if audit outputs match.
4. **Next immediate priority:** If gates are working, the next target is validation rule engine operationalization (informed by gate enforcement). If gates are incomplete, finish gate implementation first.

---

## 11. Delta Continuity Note

**Implementation AI is being asked to:**

Design, implement, and wire three independent CI merge gates (contractify-gate, docify-gate, despaghettify-gate) that enforce FY-governance audit outputs in real time on pull requests, preventing drift by blocking merges when:
- Contractify detects new contracts without relations or confidence drops.
- Docify detects decreased docstring coverage.
- Despaghettify detects structural complexity increases.

**Outputs expected:**
- Three GitHub Actions workflows (`.github/workflows/fy-*.yml`).
- Central enforcement configuration (`'fy'-suites/fy_governance_enforcement.yaml`).
- Simple diff tools for baseline comparison (contractify/tools/ci_drift_check.py, docify/tools/ci_coverage_check.py, despaghettify/tools/ci_metrics_check.py).
- Baseline snapshots (committed to repo).
- Documentation updates in three FY-suite READMEs.
- Evidence artifacts showing gate behavior on sample changes.

**What the next audit must detect:**

1. Workflows exist and are functionally correct.
2. Gates enforce FY-suite outputs (not custom implementations).
3. Baselines are committed and stable.
4. Enforcement config is complete.
5. Documentation references the gates.
6. No code drift in main codebase.
7. Sample test changes cause expected gate pass/fail behavior.

**Expected improvement in total MVP preparedness:**

Moving from ~65% to ~75% (governance layer now enforced in real time; drift detection automated; enforcement feedback loop wired).

**Dependencies for next target (validation rules):**

Validation rule implementation will be gated by contractify-enforcement; new rule code must pass merge checks. This ensures rules are continuously validated as they are added.

---

## 12. Executive Summary and Conclusion

**MVP v24 Status:**

✓ **Runtime foundation:** Complete and integrated (StoryRuntimeManager, RuntimeTurnGraphExecutor, turn seams, input interpretation).

✓ **Slice specification:** Complete and contractified (God of Carnage vertical slice, 3 normative contracts, 8 scene functions, 5 pacing modes, controlled vocabulary).

✓ **Governance infrastructure:** Installed but not enforced (Contractify reports 60 contracts, Despaghettify analyzes 15k functions, Docify scans 1k findings—all reports exist, no CI gates wired).

✗ **Evidence integration:** Partial (tests passing, but validation rules implicit, commit consistency unchecked, gate scoring untested).

✗ **Enforcement workflow:** Missing (no CI gates, drift detection manual, FY-suite outputs not actionable in merge).

**Next single best target: FY-Governance Enforcement Workflow**

This target multiplies the value of all downstream work (validation rules, commit checking, documentation) by putting governance enforcement in place first. Without enforcement, the MVP remains "prepared on paper" but not "prepared in practice." With enforcement, future work automatically feeds into a governance loop that prevents drift.

**Path to full readiness:**

1. Implement FY-governance enforcement workflow (this target) → ~75% preparedness.
2. Implement validation rule engine (informed by enforcement) → ~80% preparedness.
3. Implement commit consistency checking → ~85% preparedness.
4. Complete content authority integration (YAML → validation → commit) → ~90% preparedness.
5. Collect tabletop trace-through evidence (5 anchor scenarios) → 95% preparedness.
6. Resolve remaining conflicts (retirement timeline, writers-room/RAG overlap) → ~100% preparedness (fully ready).

The MVP is **architecturally sound** and **foundation-complete**. It is not yet **fully prepared** because **governance enforcement is absent**, allowing drift. This target closes that loop.

---

**Report prepared by:** Audit Intelligence (Runtime-Readiness Auditor)  
**Date:** 2026-04-17  
**Scope:** World of Shadows MVP v24 Lean Finishable  
**Method:** Task_Audit.md protocol, mandatory source layers, maturity model, gap analysis, prior cycle comparison, target sanity testing, handoff block  
**Next step:** Present selected target and implementation master prompt to Implementation Agent.
