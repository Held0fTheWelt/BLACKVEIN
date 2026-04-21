# FREEZE_OPERATIONALIZATION_MVP_VSL

## 1. Purpose

This document defines how **Phase 0 Freeze** must operate for the World of Shadows MVP vertical slice.

It is a **freeze-bridge and freeze-rule document**.

That means it is not merely loose commentary around the freeze.  
It is normative wherever it defines what the three freeze artifacts must contain, how they must relate to the current codebase, and what must be true before task conversion may begin.

It is not a fourth mandatory freeze artifact.  
The canonical freeze outputs remain exactly:

1. `VERTICAL_SLICE_CONTRACT_GOC.md`
2. `CANONICAL_TURN_CONTRACT_GOC.md`
3. `GATE_SCORING_POLICY_GOC.md`

But this document governs how those three artifacts must be created, how they must stay grounded in the actual codebase, and how freeze readiness is judged.

---

## 2. What this document is and is not

### 2.1 It is

- the operational bridge from MVP target to freeze artifacts
- the rulebook for how Phase 0 Freeze is conducted
- the place where freeze discipline, comparability, and codebase-grounding are fixed
- the document that prevents freeze work from happening in a vacuum

### 2.2 It is not

- a replacement for the MVP roadmap
- a substitute for the three freeze artifacts
- the execution-ready closure task series
- a license to keep iterating planning indefinitely

---

## 3. Freeze outcome

Phase 0 Freeze is complete only when all of the following are true:

1. the slice is concretely bounded
2. the current codebase and the target slice architecture are explicitly bridged
3. the canonical turn contract exists as a starter schema with real field names
4. the proposal / validation / commit / visible-output seams are explicit
5. the scene-director representation choice is explicit
6. the God of Carnage asset state is inventoried
7. the dry-run method is mapped to real existing infrastructure
8. the minimal operating mode for governance/review is concrete and runnable
9. tabletop trace-through demonstrates the frozen semantics survive a real scenario
10. task derivation can trace back to freeze rules, vocabulary, and gate families without semantic drift

If these conditions are not met, freeze is not complete.

---

## 4. Freeze artifact policy

The freeze produces exactly three canonical artifacts:

1. `VERTICAL_SLICE_CONTRACT_GOC.md`
2. `CANONICAL_TURN_CONTRACT_GOC.md`
3. `GATE_SCORING_POLICY_GOC.md`

No additional mandatory freeze document is required.

However, the following sections are mandatory **inside** those artifacts, or explicitly cross-referenced from them:

- Reality Anchor
- Current State vs Target State bridge
- Controlled Vocabulary
- Proposal / Validation / Commit / Visible-Output seams
- Dependency / Escalation Matrix
- Failure Severity / Response mapping
- Diagnostic default and escalation flow
- Minimal operating mode
- Tabletop trace-through evidence section

---

## 4A. Primary section ownership across the three freeze artifacts

To prevent redundant or drifting definitions, each required freeze section must have a **primary artifact owner**.

A concept may be referenced from other artifacts, but it must have exactly one primary normative home.

### 4A.1 Primary ownership map

| Freeze section / concept | Primary artifact owner | Secondary reference policy |
|---|---|---|
| Slice boundaries, scope, out-of-scope behavior, Reality Anchor, Current-vs-Target bridge, God of Carnage asset inventory | `VERTICAL_SLICE_CONTRACT_GOC.md` | May be referenced from the other two artifacts, but not redefined there |
| Canonical turn schema, field ownership, proposal/validation/commit/visible-output seams, scene-director representation decision, state transition doctrine, pattern inventory | `CANONICAL_TURN_CONTRACT_GOC.md` | May be referenced from the slice contract and gate policy, but not redefined there |
| Gate families, scoring rules, review bundles, failure-to-response gate consequences, diagnostic sufficiency requirements, cadence/escalation review rules | `GATE_SCORING_POLICY_GOC.md` | May reference canonical schema/seams/vocabulary, but not redefine them |

### 4A.2 Cross-reference rule

If a section is owned by one artifact and needed by another, the non-owning artifact must:
- reference the owning artifact section,
- summarize only as much as necessary for readability,
- and must not introduce a competing normative version.

### 4A.3 Conflict rule

If two freeze artifacts appear to define the same concept differently, the primary owner artifact wins, and the mismatch must be corrected before freeze completion.

---

## 5. Requirement tiers and decision rule

Freeze work must distinguish three requirement tiers:

- **Freeze-critical**
- **First-cycle mandatory**
- **Later deepening**

### 5.1 Freeze-critical
Must exist in an explicit, reviewable form before task conversion may begin.

### 5.2 First-cycle mandatory
May begin in minimal acceptable form at freeze completion, but must be explicitly scheduled for the first review cycle and may constrain downstream work if weak.

### 5.3 Later deepening
May remain intentionally incomplete at freeze completion if explicitly marked as such and if the omission does not destabilize slice semantics.

### 5.4 Go / No-Go decision rule

Task conversion may start only if:
- all freeze-critical items are present and reviewable
- all first-cycle mandatory items exist in at least minimal acceptable form
- any remaining weakness has an explicit downstream review owner and escalation consequence

If a first-cycle mandatory item is only minimally present and later proves materially weak, its downstream impact must follow the dependency/escalation matrix rather than informal negotiation.

---

## 6. Phase 0 timebox and stop rule

Phase 0 Freeze must not absorb the project indefinitely.

### 6.1 Timebox rule

Freeze should be treated as a short, bounded pre-execution phase.

Because the project may be accelerated through AI-assisted development, this timebox must be treated as **effort-bounded and decision-bounded**, not rigidly calendar-bound.

Phase 0 must still have:
- a declared start
- a declared intended finish condition
- at least one checkpoint for freeze-critical completeness
- and a stop/re-scope decision point

### 6.2 Stop / re-scope rule

If the same freeze-critical gap remains open across repeated review cycles without real closure movement, the team must not continue polishing the freeze indefinitely.

It must explicitly choose one of:
- close the gap now
- reduce slice scope
- downgrade the claim from freeze-critical if justified
- or stop task conversion

This prevents Phase 0 from becoming an endless refinement loop.

### 6.3 Early-operationalization rule

The freeze should begin with a short, code-informed operationalization pass rather than more abstract planning.

A fast AI-assisted workflow may complete this quickly, but it must still happen explicitly.

This pass should at minimum:
- inspect runtime-state surfaces
- inspect content/module surfaces relevant to God of Carnage
- establish the first Reality Anchor rows with actual references
- establish the first Current-vs-Target bridge entries
- draft the starter turn schema against real code assumptions

---

## 7. Reality Anchor

Each freeze artifact set must begin from a **Reality Anchor**.

The Reality Anchor is a short, codebase-aware statement of:

- what already exists
- what exists only partially or implicitly
- what is reusable with reshaping
- what must be built new
- what must be replaced or refactored

### 7.1 Required reality-anchor topics

At minimum:

- current runtime graph / orchestration path
- current runtime state structures
- current turn-related contracts or vocabularies
- current content/module system relevant to God of Carnage
- current mock/fallback/test infrastructure relevant to dry-runs
- current diagnostics/logging surfaces relevant to operator review

### 7.2 Code-surface reference rule

Every Current-vs-Target classification must reference at least one concrete code or content surface where possible.

This is required to stop freeze work from drifting into architecture-only prose.

### 7.3 Reality Anchor (current inspection pass)

| Concern | Current state | Classification | Code/content reference | Freeze implication |
|---|---|---|---|---|
| Runtime graph / orchestration path | `StateGraph(RuntimeTurnState)` with nodes `interpret_input`, `retrieve_context`, `route_model`, `invoke_model`, `fallback_model`, `package_output`; edges: linear chain through `invoke_model`, conditional to `fallback_model` or `package_output`, then `package_output` → `END`. Entry: `interpret_input`. | partial | `ai_stack/langgraph_runtime.py` (`RuntimeTurnGraphExecutor._build_graph`) | Roadmap turn phases beyond model+RAG require additional orchestration nodes or a parallel engine contract. |
| Runtime state structures | `RuntimeTurnState` (`TypedDict`, `total=False`): `session_id`, `module_id`, `current_scene_id`, `player_input`, `trace_id`, `host_versions`, `active_narrative_threads`, `thread_pressure_summary`, `interpreted_input`, `task_type`, `routing`, `selected_provider`, `selected_timeout`, `retrieval`, `context_text`, `model_prompt`, `generation`, `fallback_needed`, `graph_diagnostics`, `nodes_executed`, `node_outcomes`, `graph_errors`, `capability_audit`. | partial | `ai_stack/langgraph_runtime.py` (`RuntimeTurnState`; `run` initial state) | Must be mapped to the canonical turn schema; explicit commit/validation keys are not visible in this state shape. |
| Turn-related contracts / vocabulary | `AdapterInvocationMode` literals + constants; `ExecutionHealth` literals + constants; execution-health values; raw fallback bypass note. Used in `generation.metadata.adapter_invocation_mode` and `graph_diagnostics.execution_health`. | partial | `ai_stack/runtime_turn_contracts.py`; `ai_stack/langgraph_runtime.py` (`_invoke_model`, `_fallback_model`, `_package_output`) | Scene-function / continuity / visibility vocabulary does not currently live here. |
| Content/module system (GoC relevance) | `load_builtin_templates()` registers `build_god_of_carnage_solo()` → `ExperienceTemplate` id `god_of_carnage_solo`. Builtins are explicitly described as not primary runtime authority. `ModuleService` / `ContentModule` load modules from filesystem content root. | partial / reusable | `backend/app/content/builtins.py`; `backend/app/content/module_service.py`; `backend/app/content/module_models.py` | Freeze must choose which GoC source is canonical for the slice and how the other shapes relate to it. |
| Mock/fallback/test infrastructure (dry-run) | Primary path uses LangChain/runtime adapter invocation in `_invoke_model`. Fallback path uses `adapters.get("mock")` in `_fallback_model`; metadata marks managed fallback or degraded missing-fallback mode. | partial | `ai_stack/langgraph_runtime.py` (`_invoke_model`, `_fallback_model`) | Dry-run should build on this existing path rather than inventing an abstract separate concept. |
| Diagnostics / logging surfaces | `package_output` sets `graph_diagnostics`: graph name/version, nodes executed, node outcomes, fallback path taken, execution health, errors, capability audit, repro metadata, operational cost hints. | partial | `ai_stack/langgraph_runtime.py` (`_package_output`) | Strong starting point for operator-facing diagnostics, but not yet the full dramatic replay surface required by the target slice. |

---

## 8. Current State vs Target State bridge

The freeze must include a compact bridge from the actual codebase to the target slice architecture.

### 8.1 Required classifications

Each major target concern must be classified as one of:

- already implemented
- partially / implicitly present
- reusable with reshaping
- must be built new
- must replace an existing shape
- intentionally deferred

### 8.2 Mandatory target concerns

At minimum:

- canonical turn object
- scene assessment
- responder selection
- scene function
- pacing / silence / brevity shaping
- proposed state effects
- validation outcome
- committed result
- visible output bundle
- continuity handling
- diagnostics / replay surfaces
- source-to-game assets
- scene-director representation
- operator review mode

### 8.3 Current-vs-Target bridge (current inspection pass)

| Target concern | Current shape | Target shape | Classification | Reuse / replace / build note |
|---|---|---|---|---|
| Canonical turn object | `RuntimeTurnState` returned from graph execution; includes `graph_diagnostics` after `package_output`. | Single canonical dramatic turn record. | partial | Useful as starting surface, but not yet a canonical dramatic turn object. |
| Scene assessment | `retrieve_context` builds `model_prompt` from `player_input`, `context_text`, formatted `interpreted_input`, optional `active_narrative_threads` / `thread_pressure_summary`. | First-class `scene_assessment` object. | replace | Current shape is text aggregation, not schema-first dramatic assessment. |
| Responder selection | `_route_model` chooses provider/model via routing policy and task type. | Dramatic responder selection. | new | Current routing is infrastructure/model selection, not actor-level responder choice. |
| Scene function | Not discernible in inspected runtime state / graph nodes. | `selected_scene_function`. | new | Must be introduced explicitly. |
| Pacing / silence / brevity shaping | Not discernible in inspected runtime state / graph nodes. | Explicit pacing and silence/brevity decisions. | new | Must be introduced explicitly. |
| Proposed state effects | Proposal-like payload may exist inside `generation.metadata.structured_output`. | `proposed_state_effects`. | partial | Proposal content exists only indirectly and is not normalized to state-effect semantics. |
| Validation outcome | No validation field or validation node visible in inspected graph. | `validation_outcome`. | new | Must be introduced explicitly. |
| Committed result | No `committed_result` visible in inspected runtime state. | `committed_result`. | new | Must be introduced explicitly. |
| Visible output bundle | Output currently carried under `generation` / metadata rather than dedicated visible-output field. | Truth-aligned visible bundle. | partial | Existing generation output is reusable, but the target bundle shape is new. |
| Continuity handling | Optional inputs: `active_narrative_threads`, `thread_pressure_summary`; currently passed into prompt path. | Continuity carry-forward and continuity impacts. | partial | Continuity snapshot exists, but continuity mutation / commit semantics are not explicit. |
| Diagnostics / replay surfaces | `graph_diagnostics` + execution-health / adapter-invocation vocabulary. | Full diagnostic replayability. | partial | Strong base exists, but replay identity and dramatic answerability are not yet complete. |
| Source-to-game assets | Builtins template plus content-module loader/model surfaces. | Dramatic source transformed into playable slice machinery. | reusable | Existing content surfaces should be classified and reconciled, not ignored. |
| Scene-director representation | Graph currently focuses on interpretation, retrieval, routing, invoke, fallback, package. | Explicit scene-director responsibility. | new | Requires a deliberate representation decision rather than accidental emergence. |
| Operator review mode | Diagnostics currently embedded in runtime output only. | Review/governance mode. | new | Must be made explicit. |

---

## 9. Controlled vocabulary

Freeze must define a controlled vocabulary for core semantic labels.

At minimum this covers:

- scene functions
- continuity classes
- visibility classes
- failure classes
- transition patterns
- gate/review family labels where relevant

### 9.1 Amendment, alias, and cutover rule

Each vocabulary change must specify:

- current canonical label
- temporary alias if allowed
- whether parallel use is allowed
- cutover point
- deprecation condition
- when use of the old label becomes an error in tasks, diagnostics, or replay labels

Tasks and diagnostics must not silently mix old and new labels.

### 9.2 Minimal template

| Semantic area | Canonical label | Temporary alias allowed? | Cutover rule | Deprecation rule |
|---|---|---|---|---|
| Scene function | | yes/no | | |
| Continuity class | | yes/no | | |
| Failure class | | yes/no | | |

---

## 10. Proposal / validation / commit / visible-output seams

Freeze must define the runtime seams explicitly.

At minimum it must state:

- where AI proposal ends
- where validation begins
- where commit authorizes canonical truth
- where visible rendering begins
- which layer owns diagnostics references

This seam definition must be explicit enough that no later execution task can blur proposal and truth.

### 10.1 Seam rule

Nothing player-visible may outrun committed truth, except where explicitly permitted by visibility doctrine as non-factual staging, implied affect, or bounded ambiguity.

### 10.2 Seam template (current inspection anchor)

| Seam | Owner | Input | Output | May alter truth? | May alter visibility? |
|---|---|---|---|---|---|
| Proposal | Runtime graph invocation path (`_invoke_model`; fallback `_fallback_model`) | interpreted input, context text, model prompt, routing / timeout data | `generation` payload, structured output if available, fallback metadata if not | no | yes, proposal only |
| Validation | not yet explicit in inspected path | unknown | unknown | no, shapes only | no direct player output |
| Commit | not yet explicit in inspected path | unknown | unknown | yes | indirectly |
| Visible render | not yet explicit in inspected path | unknown | unknown | no | yes |

Diagnostics references are currently owned by `graph_diagnostics` packaging and related metadata surfaces.

---

## 11. Starter canonical turn schema

Freeze must define a **starter canonical turn schema**.

This is not yet final production implementation, but it must be near enough to implementation that multiple developers would not invent incompatible versions.

### 11.1 Minimum field groups

The starter schema must include concrete field names for at least:

- `turn_metadata`
- `interpreted_move`
- `scene_assessment`
- `selected_responder_set`
- `selected_scene_function`
- `pacing_mode`
- `silence_brevity_decision`
- `proposed_state_effects`
- `validation_outcome`
- `committed_result`
- `visible_output_bundle`
- `continuity_impacts`
- `visibility_class_markers`
- `failure_markers`
- `fallback_markers`
- `diagnostics_refs`

### 11.2 Required schema decisions

For each relevant field or group, freeze must state:

- ownership
- cardinality
- optionality
- phase ownership:
  - deterministic pre-model
  - model-proposed
  - validation-shaped
  - commit-owned
  - visible-output-only
  - diagnostics-only

### 11.3 Minimal example skeleton

```json
{
  "turn_metadata": {
    "turn_id": "placeholder-turn-id",
    "session_id": "placeholder-session-id",
    "trace_id": "placeholder-trace-id",
    "module_id": "god_of_carnage",
    "current_scene_id": "placeholder-scene-id"
  },
  "interpreted_move": {
    "player_intent": "placeholder",
    "move_class": "placeholder"
  },
  "scene_assessment": {
    "scene_core": "placeholder",
    "pressure_state": "placeholder"
  },
  "selected_responder_set": [
    {
      "actor_id": "placeholder",
      "reason": "placeholder"
    }
  ],
  "selected_scene_function": "placeholder",
  "pacing_mode": "placeholder",
  "silence_brevity_decision": {
    "mode": "placeholder",
    "reason": "placeholder"
  },
  "proposed_state_effects": [],
  "validation_outcome": {
    "status": "placeholder"
  },
  "committed_result": {
    "committed_effects": []
  },
  "visible_output_bundle": {
    "gm_narration": [],
    "spoken_lines": []
  },
  "continuity_impacts": [],
  "visibility_class_markers": [],
  "failure_markers": [],
  "fallback_markers": [],
  "diagnostics_refs": []
}
```

This skeleton is illustrative but mandatory in structure.  
The freeze artifacts must refine it, not ignore it.

---

## 12. Field ownership table

Freeze must include a field ownership table.

This table must explicitly distinguish:

- deterministic runtime-owned fields
- model-proposed fields
- validation-owned fields
- commit-owned fields
- player-visible-only fields
- diagnostics-only fields

### 12.1 Minimal template

| Field / group | Owner | Phase | Optional? | Cardinality | Notes |
|---|---|---|---|---|---|
| interpreted_move | | | | | |
| selected_responder_set | | | | | |
| committed_result | | | | | |
| visible_output_bundle | | | | | |
| diagnostics_refs | | | | | |

---

## 13. Scene Director representation decision

Freeze must not leave scene-direction representation ambiguous.

### 13.1 Required decision

Freeze must explicitly choose or constrain the allowed representation pattern for scene direction, such as:

- graph-node decomposition
- deterministic orchestration layer plus bounded generative realization
- director object with bounded sub-decisions
- hybrid deterministic selection plus generative realization

### 13.2 Required justification

Freeze must define:

- allowed pattern(s)
- selection criteria
- why the chosen pattern fits the current stack
- how the design avoids a scene-director god object
- how decision boundaries remain testable and inspectable

### 13.3 Mandatory sub-decisions

At minimum:

- responder selection
- scene-function selection
- pacing selection
- silence / brevity selection
- visibility shaping
- fallback shaping

---

## 14. State transition doctrine and decision grammar

Freeze must operationalize the state transition doctrine.

### 14.1 It must distinguish

- hard transitions
- soft markings
- continuity carry-forward markers
- diagnostics-only observations

### 14.2 It must define

- what can be committed per turn
- what is only derived
- what remains diagnostics-only
- what kinds of events typically trigger which class of state consequence

### 14.3 Decision grammar / pattern inventory

Freeze must include a compact reusable **pattern inventory**, not just loose example pairs.

The pattern inventory is part of **binding freeze semantics** for turn and transition meaning.
It is not merely explanatory review material.

Its normative purpose is to ensure that:
- transition language is stable,
- later task derivation does not invent incompatible transition meanings,
- and diagnostics can refer back to recognizable transition patterns.

The primary normative home for the pattern inventory is `CANONICAL_TURN_CONTRACT_GOC.md`.

### 14.4 Minimal template

| Event / trigger class | Transition pattern | Consequence class | Commitment type | Diagnostics marker |
|---|---|---|---|---|
| | | | hard / soft / carry-forward / diagnostics-only | |

This template is intentionally minimal in **format**, but not optional in semantic force.  
Its purpose is to force comparable structure without inflating freeze work into a large taxonomy exercise.

Minimal structure must not be misread as illustrative-only status.  
The freeze artifacts must treat this inventory as a binding semantic reference for transition interpretation.

---

## 15. God of Carnage asset inventory

Freeze must include a concrete God of Carnage asset inventory.

This inventory must be written **after** the initial Reality Anchor / code-surface inspection has established what content and content-adjacent structures actually exist today.

At minimum it must classify relevant slice material into:

- authored static assets
- derived static assets
- loose source material
- runtime-usable assets already present
- assets missing for the MVP slice

### 15.1 Ordering rule

The asset inventory must not classify slice material as missing, reusable, or newly required before the Reality Anchor and Current-vs-Target bridge have been populated with actual code/content references.

In practice, this means:
1. inspect relevant content/runtime surfaces,
2. populate the first Reality Anchor rows,
3. populate the first Current-vs-Target rows,
4. then classify God of Carnage slice assets.

### 15.2 God of Carnage asset inventory (current inspection pass)

| Asset / content surface | Type | Present today? | Slice relevance | Action needed |
|---|---|---|---|---|
| Builtins `god_of_carnage_solo` template | authored + runtime-usable | yes | High | Decide whether this remains a convenience/testing surface or becomes slice-canonical. |
| Content-module YAML tree under `content/modules/god_of_carnage/` | authored / structured module source | yes | High | Determine whether this is the canonical slice source and how it maps to runtime loading. |
| Writers-room markdown under `writers-room/.../god_of_carnage/` | seed / loose source / implementation notes | yes | Medium | Treat as non-canonical unless explicitly promoted or derived. |
| Derived dramatic slice assets as a dedicated canonical corpus | derived | not explicit | High | Must be either generated and versioned, or replaced by a clearly declared canonical source shape. |

### 15.3 Authoring-cost lens

The inventory must include a short note on whether the slice already appears to demand disproportionate manual authoring effort.

This is not a freeze blocker by default, but it must not remain invisible.

Current risk note: God of Carnage material exists in at least three parallel shapes today (YAML module tree, builtins template, writers-room markdown). Until freeze chooses a single canonical authority and relation rules for the other two, maintenance cost and semantic drift risk are likely disproportionate.

---

## 16. Dry-run operationalization

Freeze must define the **non-productive dry-run** concretely.

### 16.1 The dry-run must state

- which existing infrastructure it uses
- what it proves
- what it does not yet prove
- how it differs from the productive runtime path
- how its outputs are inspected

### 16.2 It may use

- existing mock adapters
- fixtures
- deterministic driver logic
- replay-like harnesses
- manual tabletop overlays where necessary

### 16.3 It must not be

- purely aspirational review
- a disguised production path
- or a substitute for later productive integration evidence

---

## 17. Minimal operating mode and cadence

Freeze must define the smallest **real** governance/review mode the team can sustain.

### 17.1 The minimal mode must specify

- which routine bundle families are mandatory
- who owns them
- how often they run
- how many anchor scenarios are required for routine review
- when escalation to expanded review is mandatory
- when a bundle is too broad and must be split

### 17.2 Default practical guidance

Unless the team has a clearly justified alternative, the minimal operating mode should assume:

- 1 routine owner per bundle family
- 2 anchor scenarios as the default minimum for routine review
- compact operator-first review as the standard default
- escalation to expanded review whenever compact mode cannot answer the required operator/reviewer questions
- bundle splitting if a routine bundle is repeatedly skipped, delayed, or judged too broad to execute in normal practice

These are defaults, not universal absolutes, but freeze must replace them only with an equally concrete alternative.

### 17.3 Minimal cadence table

| Routine bundle | Typical owner | Cadence | Minimum scenarios | Escalation trigger |
|---|---|---|---|---|
| | | | | |

### 17.4 Governance reality rule

If the defined minimal mode is routinely skipped, delayed, or selectively bypassed, that is a governance failure, not a reviewer preference.

---

## 18. Diagnostics data basis and reading modes

Freeze must define diagnostics as a **shared data basis** with explicit reading modes.

### 18.1 Required minimum

- one compact operator-first mode
- one expanded dramatic review mode

### 18.2 Freeze must define

- the shared data basis
- which mode is default
- when escalation is automatic
- what conditions make compact mode insufficient
- whether the reading modes are filtered views over the same base data or separately assembled summaries

### 18.3 Diagnostic answerability rule

Freeze must state the minimum questions diagnostics must answer for:
- a technical operator
- a dramatic reviewer

---

## 19. Failure-to-response mapping

Freeze must map failure and scope-breach classes to:

- visible behavior
- diagnostic marking
- gate consequence

### 19.1 It must include

- a qualitative severity ladder
- default safe-failure style
- out-of-scope grace behavior
- containment-first cases
- review-first cases
- closure-impacting cases

### 19.2 Minimal template

| Failure class | Typical severity | Visible response style | Diagnostic marking | Gate impact |
|---|---|---|---|---|
| | containment-first / review-first / closure-impacting | | | |

---

## 20. Dependency and escalation matrix

Freeze must include a compact dependency/escalation matrix.

### 20.1 It must answer

- which work blocks depend on which frozen guarantees
- what happens if a freeze-critical item is missing
- what happens if a first-cycle mandatory item is only minimally present
- which downstream work may continue conditionally
- which downstream work must stop

### 20.2 Minimal template

| Upstream freeze item | Affected work block(s) | Missing / weak consequence | Allowed continuation? | Escalation action |
|---|---|---|---|---|
| | | | yes/no/conditional | |

---

## 21. Tabletop trace-through

Before task conversion, freeze must be stress-tested with a tabletop trace-through.

### 21.1 Required scenario mix

At minimum:

- standard representative scenario(s)
- thin-edge scenario(s)
- out-of-scope / scope-breach scenario(s)
- anti-seductive scenario(s)
- at least one scenario with multiple active pressure / continuity lines

### 21.2 What it must prove

- freeze rules are usable
- controlled vocabulary is sufficient
- the starter turn schema can represent the turn cleanly
- priority legibility survives competing pressures
- diagnostics remain answerable
- task derivation has a trace path

### 21.3 Trace-through rule

At least one tabletop scenario must be traced through all of:

- freeze rule
- vocabulary
- gate family
- diagnostics
- derived task implication

---

## 22. Ready-to-freeze check

Before declaring Phase 0 ready for task conversion, the answer to all of the following must be “yes”:

1. Is the slice concretely bounded?
2. Is there a Reality Anchor grounded in actual code/content surfaces?
3. Does the Current-vs-Target bridge classify reuse, replacement, and new work explicitly?
4. Does the starter canonical turn schema exist with real field names?
5. Are proposal / validation / commit / visible-output seams explicit?
6. Is the scene-director representation decision explicit?
7. Does the God of Carnage asset inventory exist?
8. Is the non-productive dry-run mapped to real infrastructure?
9. Is the minimal operating mode concrete and runnable?
10. Is the diagnostics default flow fixed?
11. Does the failure-to-response mapping exist?
12. Does the dependency/escalation matrix exist?
13. Does controlled vocabulary include cutover/deprecation rules?
14. Has tabletop trace-through been completed?
15. Is there no unresolved semantic-drift issue that would materially change task meaning?

If any answer is “no”, freeze is not ready for task conversion.

---

## 23. What freeze must not try to do

Freeze must not:

- finish implementation
- optimize broad multi-module generalization
- replace later execution evidence
- invent a second competing runtime truth
- absorb the project indefinitely
- hide weak seams behind good prose

---

## 24. Recommended immediate next sequence

1. inspect runtime-state surfaces relevant to the slice
2. inspect content/module surfaces relevant to God of Carnage
3. fill the first Reality Anchor and Current-vs-Target rows with actual references
4. draft the starter canonical turn schema against real code assumptions
5. finalize the three freeze artifacts using the templates in this document
6. perform the tabletop trace-through
7. correct any real break revealed by the tabletop
8. derive the execution-ready closure task series
9. perform a traceability check from tasks back to freeze rules, vocabulary, and gate families

This sequence is intentionally concrete so that freeze begins from code and content reality rather than from another abstract planning loop.

---

## 25. Practical conclusion

The MVP target is already strong enough.

What remains is not another broad vision loop.  
What remains is a disciplined, codebase-aware conversion of that target into:

- freeze-ready contracts,
- explicit seams,
- asset and runtime inventories,
- and execution-ready task derivation.

That is the purpose of Phase 0 Freeze.
