# ROADMAP MVP — Semantic Dramatic Planner

**Status:** Proposed MVP architecture and migration roadmap for the next GoC runtime maturity step  
**Scope:** God of Carnage vertical slice first; no cross-module generalization in this phase  
**Audience:** Runtime, AI-stack, backend, and operator-facing architecture work  
**Related repo surfaces:** `ai_stack/langgraph_runtime.py`, `ai_stack/scene_director_goc.py`, `ai_stack/goc_dramatic_alignment.py`, `ai_stack/goc_yaml_authority.py`, `backend/app/runtime/role_contract.py`, `backend/app/runtime/narrative_threads.py`, `docs/VERTICAL_SLICE_CONTRACT_GOC.md`, `docs/technical/architecture/backend-runtime-classification.md`

---

## 1. Purpose

This document defines the next concrete MVP architecture for evolving the current God of Carnage runtime from a deterministic heuristic scene-director implementation into a **bounded semantic dramatic planner**.

The intended upgrade is **not** greater model freedom. The intended upgrade is **more semantic intelligence inside the same truth and validation contracts that already exist**.

The architecture must preserve all of the following:

- a single runtime truth authority,
- explicit validation and commit seams,
- bounded and inspectable planner reasoning,
- truth-aligned visible output,
- and operator-legible diagnostics.

In short:

> AI proposes. Engine validates. Commit authorizes. Visible output remains truth-bound.

That rule remains unchanged.

---

## 2. Current baseline in the repository

The current repo state is already strong in several foundational ways.

### 2.1 Single graph truth surface already exists

The GoC runtime already executes through one named `StateGraph(RuntimeTurnState)` path in `ai_stack/langgraph_runtime.py`, with explicit nodes including:

- `director_assess_scene`
- `director_select_dramatic_parameters`
- `route_model`
- `validate_seam`
- `commit_seam`
- `render_visible`

This means the system already has a stable orchestration surface and does not need a second runtime to evolve.

### 2.2 Canonical content authority already exists

The GoC slice already has a canonical YAML authority through `ai_stack/goc_yaml_authority.py`, and the vertical slice contract already defines YAML-backed slice authority and truth handling.

This is a major strength because the semantic planner can be grounded in authored dramatic structure instead of inventing truth from scratch.

### 2.3 Truth seams already exist

The current vertical slice already has explicit proposal, validation, commit, continuity, and visible render seams.

That means the target architecture should evolve **inside** these seams rather than redesigning them.

### 2.4 Director logic exists, but remains heuristic

`ai_stack/scene_director_goc.py` currently performs scene assessment and dramatic parameter selection through deterministic helper logic. It already works, but its core selection behavior remains largely heuristic and bounded by pattern and tie-break logic rather than explicit semantic scene planning.

### 2.5 Dramatic alignment exists, but remains surface-oriented

`ai_stack/goc_dramatic_alignment.py` already protects the system from fluent but empty output. However, it does so through rule and token checks tied to scene-function support, minimum narrative mass, and banned weak-output patterns.

This is useful, but it is still not a true dramatic-effect evaluator.

### 2.6 Backend role separation exists, but is not yet the runtime semantic core

`backend/app/runtime/role_contract.py` already distinguishes between:

- `interpreter`
- `director`
- `responder`

This is valuable, but in the present system it should be understood as a structured role contract rather than the canonical semantic planning core.

### 2.7 Bounded continuity substrate already exists

`backend/app/runtime/narrative_threads.py` already provides bounded, derived continuity threads. Those threads are explicitly non-authoritative and remain downstream of canonical commit.

This is exactly the right posture. It means the planner can become smarter without moving truth authority away from commit.

### 2.8 Runtime authority is already clearly documented

The repository documentation already states that the **World Engine** remains the authoritative live play host, while backend in-process runtime paths are non-authoritative and transitional.

This boundary must not be weakened by semantic planner work.

---

## 3. Problem statement

The current MVP is strong in contract discipline, graph structure, canonical content authority, and truth-bound output.

Its main remaining weakness is that dramatic direction is still primarily driven by:

- heuristic move classification,
- bounded tie-break logic,
- phrase- and token-sensitive alignment checks,
- and partially implicit character-selection biases.

As a result, the system is still weaker than it should be at:

- understanding indirect player intent,
- tracking social meaning beyond surface wording,
- preserving tactical character identity under pressure,
- sustaining believable longer dramatic runs,
- and distinguishing truly dramatic output from merely fluent output.

The next MVP step is therefore not “more generation.”

It is:

> replace surface-level heuristic dramatic routing with bounded semantic dramatic planning while preserving the same runtime truth seams.

---

## 4. Architectural objective

The target system should become:

> a bounded semantic dramatic runtime that interprets player moves as social actions, selects character-plausible pressure responses, tracks explicit interpersonal scene state, and advances scenes inside the same engine-authorized truth pipeline.

This means the runtime should become better at understanding:

- what the player is socially doing,
- what that move means in the current scene,
- what it changes between the characters,
- what each character would plausibly protect or attack,
- and what kind of scene progression is dramatically justified next.

It does **not** mean:

- free story authorship,
- unconstrained model improvisation,
- second-truth memory systems,
- or LLM sovereignty over runtime state.

---

## 5. Governing principles

### 5.1 Authority rule

The semantic planner remains advisory until validation and commit succeed.

No semantic or planner record may directly mutate canonical runtime truth.

### 5.2 One runtime truth surface

The semantic planner must live inside the existing turn graph, not beside it as a second runtime or secondary decision surface.

### 5.3 Bounded semantics before free intelligence

The system should first gain explicit semantic records and stable planner contracts before any attempt is made to increase inference freedom.

### 5.4 GoC-first implementation

The first semantic planner must be implemented as a GoC-specific runtime maturity step. Generalization to other modules is out of scope for the initial MVP phase.

### 5.5 Diagnostics are derived, not sovereign

Operator and audit views may become richer, but they must remain projections of canonical turn state rather than their own authority surface.

### 5.6 Authored truth remains upstream of runtime interpretation

Canonical YAML and authored slice guidance remain the upstream dramatic source. The planner must use authored constraints to interpret and select, not invent a competing authored truth.

---

## 6. Target architecture layers

## 6.1 Dramatic Source Layer

**Owns:** canonical authored dramatic truth for the GoC slice.

**Current basis:**

- canonical module YAML,
- character YAML,
- character voice YAML,
- scene guidance YAML,
- vertical slice contract.

**Responsibility in the new MVP:**

This layer must remain the source of truth for authored dramatic structure, and it should additionally expose planner-ready authored constraints such as:

- character tactical identity hints,
- scene-specific pressure expectations,
- responder plausibility constraints,
- and phase-sensitive guidance.

This is authored truth, not runtime memory.

---

## 6.2 Retrieval and Context Layer

**Owns:** bounded retrieval, context packing, retrieval governance visibility, and bounded carry-forward continuity inputs.

**Current basis:**

- `ai_stack/rag.py`,
- retrieval governance summary,
- compact context packs,
- active narrative threads,
- thread pressure summary.

**Responsibility in the new MVP:**

This layer may inform semantic planning, but it may not decide truth. It supplies planner inputs such as prior pressure lines and bounded context, but it does not authorize scene state or canonical consequence.

---

## 6.3 Semantic Move Layer

**Owns:** bounded interpretation of the player turn as a dramatic-social move.

**Current status:** missing as a first-class canonical layer.

This layer must become explicit.

It should answer questions such as:

- what social move is being attempted,
- who is being targeted,
- whether the move is direct or indirect,
- whether it attacks, repairs, probes, exposes, deflects, withdraws, or repositions,
- and how much scene risk the move carries.

This is the first major upgrade beyond keyword and surface-pattern routing.

---

## 6.4 Character Mind Layer

**Owns:** stable tactical identity of active characters under pressure.

**Current status:** partial and implicit only.

Today, pieces of this behavior are scattered across authored voice, director defaults, responder bias, and continuity handling. That is useful, but too implicit.

This layer must become first-class and bounded.

It should model, in authored or authored-derived form:

- what a character protects,
- what they cannot openly admit,
- how they usually attack,
- how they attempt repair,
- what they do under humiliation,
- how they deflect under stress,
- when they escalate,
- and how they retreat, freeze, or collapse.

This is not free psychology generation. It is a bounded tactical character contract.

---

## 6.5 Social State Layer

**Owns:** explicit bounded interpersonal scene state.

**Current status:** partial only.

Today, the system already exposes bounded continuity impacts and derived narrative threads, but there is no explicit scene-social state record that the planner can reason over as a compact canonical input.

This layer should track bounded dramatic-social conditions such as:

- blame pressure,
- dignity injury,
- alliance tendency,
- exposure pressure,
- repair opportunity,
- conversational control,
- and escalation stage.

This layer is planner-facing and derived. It is not the same as canonical world truth.

---

## 6.6 Scene Planning Layer

**Owns:** short-horizon dramatic direction for the current turn and immediate scene progression.

**Current basis:** `ai_stack/scene_director_goc.py`

**New MVP responsibility:**

This layer becomes the actual semantic dramatic planner. It combines:

- semantic move interpretation,
- character tactical identity,
- bounded social state,
- authored scene constraints,
- and continuity pressure.

It must produce bounded, inspectable scene-direction outputs such as:

- responder selection,
- scene function,
- pacing,
- silence or brevity posture,
- pressure target,
- continuity obligation,
- and immediate dramatic-beat intent.

This layer selects direction. It does not commit truth.

---

## 6.7 Model Realization Layer

**Owns:** wording, bounded proposal generation, and model execution under planner-selected parameters.

**Current basis:** existing routing and model invocation path.

**New MVP responsibility:**

The model realization layer remains responsible for transforming planner-bounded direction into a structured proposal. It must not gain authority over:

- scene legality,
- truth commitment,
- social-state commitment,
- or runtime consequence authorization.

The model is a realization engine for a planner-shaped decision, not the owner of dramatic truth.

---

## 6.8 World Truth Layer

**Owns:** validation, canonical consequence approval, commit application, bounded continuity effects, and truth-aligned visible output.

**Current basis:** validation seam, commit seam, continuity impacts, visible output bundle.

**MVP rule:**

This remains the non-negotiable authority layer.

No semantic planner phase may bypass or dilute validation and commit. Any output that reaches the player as runtime truth must still flow through the existing truth seams.

---

## 6.9 Operator and Diagnostics Layer

**Owns:** explainability, replayability, governance evidence, and compact operator-facing runtime truth.

**Current basis:** graph tracking, route diagnostics, governance evidence, role-structured outputs, and bounded runtime diagnostics.

**New MVP responsibility:**

This layer should expose semantic-planner-visible records, including:

- interpreted social move,
- social-state snapshot,
- character-mind selection basis,
- scene-plan summary,
- dramatic-effect gate outcome,
- and graph/route evidence.

This remains a derived diagnostic projection, never a second runtime authority surface.

---

## 7. Canonical contracts

## 7.1 Authority Contract

1. The World Engine remains the authoritative live runtime.
2. Semantic planning is advisory until validation and commit succeed.
3. Backend non-authoritative runtime paths must not become a second live play surface.
4. No planner output may directly mutate canonical runtime truth.
5. Visible player-facing truth remains downstream of validation and commit.

---

## 7.2 Semantic Move Contract

Introduce a canonical `SemanticMoveRecord`.

This record should be schema-first, serializable, and bounded. It should describe the interpreted dramatic-social move without inventing open-ended world truth.

Suggested fields:

- `move_type`
- `surface_mode`
- `target_character_ids`
- `explicit_intent`
- `hidden_intent_hypothesis`
- `pressure_tactic`
- `repair_vs_attack`
- `directness`
- `sincerity_estimate`
- `scene_risk`
- `confidence`

This record becomes the semantic replacement for overly shallow move classification.

---

## 7.3 Character Mind Contract

Introduce a canonical `CharacterMindRecord`.

This record should describe authored or authored-derived tactical identity for active characters and remain bounded, stable, and explainable.

Suggested fields:

- `character_id`
- `protects`
- `cannot_admit`
- `default_attack_modes`
- `default_repair_modes`
- `stress_deflection_pattern`
- `escalation_threshold`
- `humiliation_trigger`
- `collapse_or_withdrawal_pattern`
- `alliance_bias`

This record must not be unconstrained free-generation per turn.

### 7.3.1 Character mind provenance and canonicalization

`CharacterMindRecord` must not be invented freely per turn.

Its allowed provenance is strictly limited to the following sources, in descending order of authority:

1. explicit authored character-mind fields in canonical GoC YAML or adjacent canonical authored assets;
2. deterministic authored-derived projection from canonical character definition, voice, scene-role, and pressure-specific authored constraints;
3. bounded fallback defaults defined in code for fields that are intentionally optional.

The runtime must not generate new long-lived character tactical identity from unconstrained model inference.

### Canonicalization rule

If `CharacterMindRecord` is authored-derived rather than explicitly authored, the derivation must be:

- deterministic,
- reproducible,
- schema-bounded,
- and implemented in canonical code rather than delegated to a model.

### Operational rule

The derivation path from authored source to `CharacterMindRecord` must be inspectable in diagnostics.

Diagnostics should make it clear whether a field is:

- explicitly authored,
- authored-derived,
- or fallback-defaulted.

### Future authoring rule

If a derived field proves consistently necessary and stable across GoC use, it may later be promoted into explicit authored source fields.
That promotion is an authoring evolution step, not a runtime inference privilege.

---

## 7.4 Social State Contract

Introduce a canonical `SocialStateRecord`.

This record should express the bounded interpersonal condition of the current scene from the planner’s point of view.

Suggested fields:

- `blame_pressure`
- `dignity_injury`
- `alliance_shift`
- `repair_window`
- `exposure_pressure`
- `conversation_control`
- `escalation_stage`

This record is planner-facing only. It does not itself commit world truth.

---

## 7.5 Scene Plan Contract

Introduce a canonical `ScenePlanRecord`.

This record becomes the planner’s authoritative output inside the runtime turn graph.

Suggested fields:

- `selected_responder_set`
- `selected_scene_function`
- `pacing_mode`
- `silence_brevity_decision`
- `pressure_target`
- `dramatic_beats`
- `continuity_obligation`
- `expected_transition_pattern`
- `rationale_codes`

This record does not authorize commit. It authorizes the shape of the bounded proposal request to the model layer.

---

## 7.6 Model Response Contract

The model-facing structured proposal contract may continue to use the current bounded proposal pattern.

If the backend `AIRoleContract` remains in use, its future semantic role should be treated as a projection of canonical planner state:

- `interpreter` = semantic move and scene reading
- `director` = scene-plan explanation
- `responder` = runtime-relevant proposal candidate

That means the role contract becomes a transport and explanation structure, not the root authority of dramatic planning.

---

## 7.7 Dramatic Effect Gate Contract

Introduce a stronger `DramaticEffectGateOutcome`.

This gate should evaluate whether a proposal:

- supports the selected scene function,
- plausibly follows from the selected character mind,
- sustains or changes the current social state,
- continues an existing pressure line,
- and is dramatically effective rather than merely fluent.

This gate may begin as deterministic, but it should be architected so that it can become richer without becoming opaque or unbounded.

---

## 8. Graph integration rule

The semantic planner must not become a second service or a parallel runtime.

It should be integrated into the existing single graph truth surface.

### 8.1 Current graph posture

The current graph already has the correct overall shape:

`interpret_input -> retrieve_context -> goc_resolve_canonical_content -> director_assess_scene -> director_select_dramatic_parameters -> route_model -> invoke_model -> proposal_normalize -> validate_seam -> commit_seam -> render_visible -> package_output`

### 8.2 Migration rule

The graph should remain structurally recognizable.

Recommended evolution:

- `director_assess_scene` becomes the wrapper that produces semantic move interpretation and bounded social-state assessment.
- `director_select_dramatic_parameters` becomes the wrapper that produces character-mind selection and scene-plan output.
- `validate_seam` gains dramatic-effect evaluation as an additional truth-bound guard.

This preserves graph identity, diagnostic continuity, and testability.

---

## 9. Non-goals

This architecture explicitly does **not** aim to create:

- a free-form world AI,
- a second truth surface,
- LLM-led runtime authority,
- unconstrained persistent memory as scene truth,
- a generic chatbot with better dramatic prose,
- module-general semantic abstraction before GoC is stable,
- or opaque planner logic that operators cannot inspect.

The goal is not “more freedom.”

The goal is:

> more semantic precision, stronger social-state modeling, better character-plausible selection, and better dramatic effect evaluation under the same bounded contracts.

---

## 10. Expansion phases

## Phase 0 — Contract extraction without semantic freedom

**Goal:** introduce explicit semantic and planner records while preserving current runtime behavior.

**Deliverables:**

- `SemanticMoveRecord`
- `CharacterMindRecord`
- `SocialStateRecord`
- `ScenePlanRecord`
- operator-visible projections
- regression tests proving parity with current runtime behavior where intended

This phase should change structure more than behavior.

---

## Phase 1 — Semantic move interpretation

**Goal:** replace shallow surface-driven move interpretation with bounded dramatic-social move inference.

**Expected gain:**

- better handling of indirect player input,
- less phrase brittleness,
- better operator visibility into what the runtime thinks the move means.

---

## Phase 2 — Character mind formalization

**Goal:** convert implicit responder bias and authored voice hints into explicit bounded tactical character records.

**Expected gain:**

- more stable character identity,
- more plausible pressure-specific reactions,
- less arbitrary responder behavior.

---

## Phase 3 — Explicit social state

**Goal:** unify continuity impacts, thread pressure, and scene pressure into one bounded social-state layer.

**Expected gain:**

- stronger multi-turn coherence,
- clearer blame, alliance, and repair dynamics,
- reduced turn-local amnesia.

---

## Phase 4 — Semantic scene planner

**Goal:** upgrade the current director from heuristic routing to bounded short-horizon dramatic planning.

**Expected gain:**

- better responder choice,
- more believable scene progression,
- stronger handling of exposure, failed repair, alliance movement, pressure shifts, and temporary freezes.

---

## Phase 5 — Dramatic effect gate

**Goal:** replace primarily phrase- and token-level anti-seductive checks with a stronger dramatic effectiveness evaluator.

**Expected gain:**

- fewer fluent-but-empty turns,
- better continuation of scene pressure,
- stronger consequence density and scene usefulness.

---

## Phase 6 — Controlled generalization

**Goal:** only after GoC stabilizes, abstract the contracts for wider module reuse.

**Expected gain:**

- shared semantic planner interfaces,
- module-specific authored tactical mappings,
- preserved truth-bound runtime discipline outside GoC.

This phase is explicitly post-MVP.

---

## 11. Suggested file/module placement

Recommended new modules:

- `ai_stack/semantic_move_contract.py`
- `ai_stack/character_mind_contract.py`
- `ai_stack/social_state_contract.py`
- `ai_stack/scene_plan_contract.py`
- `ai_stack/semantic_scene_planner.py`
- `ai_stack/dramatic_effect_gate.py`

Recommended migration posture:

- keep `ai_stack/scene_director_goc.py` as a façade during migration,
- move existing heuristics behind explicit contracts step by step,
- do not break existing operator or closure surfaces in one jump.

Recommended tests:

- `ai_stack/tests/test_semantic_move_contract.py`
- `ai_stack/tests/test_character_mind_contract.py`
- `ai_stack/tests/test_social_state_contract.py`
- `ai_stack/tests/test_scene_plan_contract.py`
- `ai_stack/tests/test_dramatic_effect_gate.py`
- graph-level regression tests ensuring no second truth surface appears

---

## 12. Acceptance posture

This architecture is only considered correctly implemented when each phase satisfies both structural and behavioral acceptance criteria appropriate to its scope.

### 12.1 General rule

Earlier phases are primarily contract and migration phases.
Later phases are controlled behavior-improvement phases.

A phase is complete only when:

- all required new contracts exist in canonical code,
- all required graph integrations are present,
- all explicitly required tests pass,
- no second runtime truth surface is introduced,
- and no protected authority seam is weakened.

### 12.2 Phase 0 acceptance criteria

Phase 0 is a contract-extraction phase.
It must change structure more than behavior.

Phase 0 passes only if all of the following are true:

1. `SemanticMoveRecord`, `CharacterMindRecord`, `SocialStateRecord`, and `ScenePlanRecord` exist as canonical serializable runtime contracts.
2. Existing director nodes continue to operate on the same single LangGraph path; no parallel planner graph is introduced.
3. Existing validation, commit, and visible render seams remain authoritative and unchanged in authority semantics.
4. Existing GoC regression suites continue to pass without requiring broader behavioral re-baselining.
5. New diagnostics may expose the new contracts, but visible runtime truth and committed outcomes remain sourced from the existing authority seams.
6. For a fixed golden set of representative GoC turns, responder selection, scene-function class, and validation and commit outcome do not regress beyond explicitly approved tolerances.

### 12.3 Phase 0 regression posture

Phase 0 is not required to improve dramatic quality.
It is required to preserve current runtime behavior while making planner state explicit.

Any material drift in committed outcome shape, authority boundaries, or graph truth routing is a failure for Phase 0.

### 12.4 Later-phase posture

Phases 1 through 5 may change behavior, but only in ways that are:

- explainable through the new planner contracts,
- bounded by authored dramatic constraints,
- and validated by targeted phase-specific test suites.

### 12.5 Stability and explainability posture

Later phases may claim improved stability, explainability, or dramatic quality only when those claims are backed by explicit evidence such as:

- golden-turn comparison suites,
- planner-state diagnostics proving why a move was interpreted and selected a certain way,
- and targeted tests showing that authored constraints remain the dominant source of tactical identity.

Qualitative improvement language is acceptable in design discussion, but not sufficient for closure.

---

## 13. Phase dependency matrix

The phases in this document are not independent.

### 13.1 Hard dependencies

- Phase 0 is required before all later phases.
- Phase 1 depends on Phase 0.
- Phase 2 depends on Phase 0 and should precede Phase 4.
- Phase 3 depends on Phase 0 and should not be treated as semantically complete without Phase 2.
- Phase 4 depends on Phases 1, 2, and 3.
- Phase 5 depends on Phase 4 and the existence of stable planner-state diagnostics.
- Phase 6 depends on successful GoC-local closure of Phases 0 through 5.

### 13.2 Execution meaning

The system must not attempt full semantic scene planning before:

- semantic move interpretation is explicit,
- character tactical identity is explicit,
- and bounded social scene state is explicit.

Any implementation that jumps directly from heuristic director logic to a combined semantic planner without these prior contracts is considered architecturally non-compliant.

---

## 14. Final architectural statement

The next MVP should not try to become a freer storyteller.

It should become:

> a bounded semantic dramatic planner that interprets player moves as social actions, selects character-plausible pressure responses, tracks explicit interpersonal scene state, and advances scene direction inside the same engine-authorized truth pipeline.

That is the correct next architecture step for the current repository state.
