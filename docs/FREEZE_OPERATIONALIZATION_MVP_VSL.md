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

### 7.3 Minimal template

| Concern | Current state | Classification | Code/content reference | Freeze implication |
|---|---|---|---|---|
| Runtime graph / orchestration path | `StateGraph(RuntimeTurnState)` with nodes `interpret_input`, `retrieve_context`, `route_model`, `invoke_model`, `fallback_model`, `package_output`; edges: linear chain through `invoke_model`, conditional to `fallback_model` or `package_output`, then `package_output` → `END`. Entry: `interpret_input`. | partial | [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) (`RuntimeTurnGraphExecutor._build_graph`, L101–L120) | Roadmap turn phases beyond model+RAG require additional orchestration nodes or a parallel engine contract — [NOT DISCERNIBLE] in this file. |
| Runtime state structures | `RuntimeTurnState` (`TypedDict`, `total=False`): `session_id`, `module_id`, `current_scene_id`, `player_input`, `trace_id`, `host_versions`, `active_narrative_threads`, `thread_pressure_summary`, `interpreted_input`, `task_type`, `routing`, `selected_provider`, `selected_timeout`, `retrieval`, `context_text`, `model_prompt`, `generation`, `fallback_needed`, `graph_diagnostics`, `nodes_executed`, `node_outcomes`, `graph_errors`, `capability_audit`. | partial | [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) (`RuntimeTurnState`, L50–L74; `run` initial state L134–L150) | Map to canonical turn schema (§11); explicit commit/validation keys — [NOT DISCERNIBLE] in `RuntimeTurnState`. |
| Turn-related contracts / vocabulary | `AdapterInvocationMode` literals + constants; `ExecutionHealth` literals + `EXECUTION_HEALTH_*`; `EXECUTION_HEALTH_VALUES`; `RAW_FALLBACK_BYPASS_NOTE`. Used in `generation.metadata.adapter_invocation_mode` and `graph_diagnostics.execution_health`. | partial | [`ai_stack/runtime_turn_contracts.py`](../ai_stack/runtime_turn_contracts.py); [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) (`_invoke_model`, `_fallback_model`, `_package_output`) | Scene-function / continuity / visibility vocab — [NOT DISCERNIBLE] in `runtime_turn_contracts.py`. |
| Content/module system (GoC relevance) | `load_builtin_templates()` registers `build_god_of_carnage_solo()` → `ExperienceTemplate` id `god_of_carnage_solo`. Comment: builtins are not primary runtime authority; published feed canonical. `ModuleService` / `ContentModule` types load modules from filesystem root (default `content_modules_root()`). GoC YAML tree — [NOT DISCERNIBLE] from `builtins.py` / `module_models.py` alone (loader schema only). | partial / reusable | [`backend/app/content/builtins.py`](../backend/app/content/builtins.py) (`load_builtin_templates`, `build_god_of_carnage_solo`, L21–L34); [`backend/app/content/module_service.py`](../backend/app/content/module_service.py) (`ModuleService`, `load_and_validate`); [`backend/app/content/module_models.py`](../backend/app/content/module_models.py) (`ContentModule`) | Freeze: which source is authoritative for GoC at runtime — [UNKNOWN] without further call-site inspection. |
| Mock/fallback/test infrastructure (dry-run) | Primary path: `invoke_runtime_adapter_with_langchain` in `invoke_model`. Fallback: `adapters.get("mock")` → `fallback_adapter.generate(...)` in `fallback_model`; metadata includes `ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK`, `RAW_FALLBACK_BYPASS_NOTE`. If mock missing: `graph_errors` append `fallback_adapter_missing:mock`. Dedicated test harness files — [NOT DISCERNIBLE] in the listed files. | partial | [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) (`_invoke_model` L268–L316, `_fallback_model` L321–L357) | Dry-run may reference the fallback path; full test infrastructure — [NOT DISCERNIBLE] here. |
| Diagnostics / logging surfaces | `package_output` sets `graph_diagnostics`: `graph_name`, `graph_version`, `nodes_executed`, `node_outcomes`, `fallback_path_taken`, `execution_health`, `errors`, `capability_audit`, `repro_metadata` (e.g. `ai_stack_semantic_version`, `runtime_turn_graph_version`, `trace_id`, routing/retrieval/model flags, `adapter_invocation_mode`, `graph_path_summary`), `operational_cost_hints`. | partial | [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) (`_package_output`, L359–L428); [`ai_stack/runtime_turn_contracts.py`](../ai_stack/runtime_turn_contracts.py) | Operator logging beyond this dict — [NOT DISCERNIBLE] in the listed files. |

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

### 8.3 Minimal template

| Target concern | Current shape (code) | Target shape (roadmap) | Classification | Justification (code) |
|---|---|---|---|---|
| Canonical turn object | `RuntimeTurnState` returned from `run()` / `invoke`; includes `graph_diagnostics` after `package_output`. | Single canonical turn record (roadmap §8, §11). | partial | TypedDict aggregates turn data but is not named “canonical turn”; no `turn_id` field — [NOT DISCERNIBLE]. |
| Scene assessment | `retrieve_context` builds `model_prompt` from `player_input`, `context_text`, formatted lines from `interpreted_input` (`kind`, `confidence`, `ambiguity`, `intent`, `selected_handling_path`, `runtime_delivery_hint`), optional `active_narrative_threads` / `thread_pressure_summary`. | First-class `scene_assessment` object (roadmap §4.3, §8). | replace | Target schema requires an explicit assessment object; today only text aggregation in `model_prompt` / RAG fields — existing shape should be replaced with a schema-first representation. |
| Responder selection | `_route_model`: `RoutingPolicy.choose(task_type=...)` → `routing` dict with `selected_model`, `selected_provider`, etc.; `task_type` from `_interpret_input`. | Dramatic responder selection (roadmap §3.3, §8). | new | No NPC/actor responder fields in `RuntimeTurnState`; routing is LLM provider/model selection only ([`langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) L251–L266, L152–L158). |
| Scene function | [NOT DISCERNIBLE] in `RuntimeTurnState` / inspected graph nodes. | `selected_scene_function` (roadmap §8, §11). | new | No field or node for scene function in referenced code. |
| Pacing / silence / brevity shaping | [NOT DISCERNIBLE] in `RuntimeTurnState` / inspected graph nodes. | Explicit pacing / silence / brevity (roadmap §8). | new | No such keys in `RuntimeTurnState`; not set in nodes read. |
| Proposed state effects | `generation` dict; `generation.metadata.structured_output` from `parsed_output.model_dump(mode="json")` when LangChain path succeeds; else null / raw fallback path. | `proposed_state_effects` (roadmap §8, §11). | partial | Proposal-like payload only inside `generation`; not normalized to “state effects” type in this file. |
| Validation outcome | [NOT DISCERNIBLE] — no `validation_outcome` or validation node in graph. | `validation_outcome` (roadmap §8, §11). | new | No validation phase in [`langgraph_runtime.py`](../ai_stack/langgraph_runtime.py). |
| Committed result | [NOT DISCERNIBLE] — no `committed_result` in `RuntimeTurnState`. | `committed_result` (roadmap §8, §11). | new | No commit node or committed-state field in referenced code. |
| Visible output bundle | Output carried under `generation` (and metadata); no `visible_output_bundle` key. | Truth-aligned visible bundle (roadmap §9–10). | partial | Structured output exists under `generation.metadata.structured_output`; UI binding — [NOT DISCERNIBLE] in this file. |
| Continuity handling | Optional inputs: `active_narrative_threads`, `thread_pressure_summary` (bounded); forwarded into `model_prompt` in `retrieve_context`. | Continuity carry-forward (roadmap §10). | partial | Snapshot pass-through only; no continuity mutation/commit in graph. |
| Diagnostics / replay surfaces | `graph_diagnostics` + `runtime_turn_contracts` enums; `repro_metadata` includes versions, trace_id, routing/retrieval summary. | Full diagnostic replay (roadmap §7–8). | partial | Replay store / `turn_id` — [NOT DISCERNIBLE] in referenced files. |
| Source-to-game assets | `builtins.build_god_of_carnage_solo` + generic `ContentModule` loader (paths via `ModuleService`); graph receives `module_id` / `current_scene_id` only. | Dramatic source → playable machinery (roadmap §4.1). | reusable | Assets exist outside graph; graph does not load YAML module content in inspected code. |
| Scene-director representation | Graph nodes = interpretation, retrieval, routing, invoke, fallback, package. | Explicit scene director layer (roadmap §5.3). | new | No director object separate from this graph in referenced code. |
| Operator review mode | Diagnostics embedded in `graph_diagnostics` only. | Governance / review mode (roadmap §13 freeze implications). | new | No operator-review API or mode in referenced files — [NOT DISCERNIBLE]. |

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

### 10.2 Minimal seam template

| Seam | Owner | Input | Output | May alter truth? | May alter visibility? |
|---|---|---|---|---|---|
| Proposal | `RuntimeTurnGraphExecutor._invoke_model` → `story_runtime_core` adapter + `invoke_runtime_adapter_with_langchain` from [`ai_stack/langchain_integration/`](../ai_stack/langchain_integration/); fallback: `_fallback_model` → `adapters["mock"].generate` | `player_input`, `interpreted_input`, `context_text`, `model_prompt`, `selected_timeout` (from state after `route_model`) | `generation` with `metadata.structured_output` (LangChain path) or raw fallback metadata (`ADAPTER_INVOCATION_RAW_GRAPH_FALLBACK`, `RAW_FALLBACK_BYPASS_NOTE`) | no | yes, proposal-only; player-facing channel [NOT DISCERNIBLE] in `langgraph_runtime.py` |
| Validation | [NOT DISCERNIBLE] | [UNKNOWN] | [UNKNOWN] | no, shapes only (if present elsewhere) | no direct player output |
| Commit | [NOT DISCERNIBLE] in `langgraph_runtime.py` | [UNKNOWN] | [UNKNOWN] | yes (only if/when an engine commit exists) | indirectly |
| Visible render | [NOT DISCERNIBLE] in `langgraph_runtime.py` | [UNKNOWN] | [UNKNOWN] | no | yes |

**Diagnostics references:** `RuntimeTurnGraphExecutor._package_output` → `graph_diagnostics` (includes `repro_metadata`, `execution_health`, `operational_cost_hints`); optional `capability_audit` from `CapabilityRegistry.invoke` path in `_retrieve_context`.

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
    "turn_id": "[NOT DISCERNIBLE]",
    "session_id": "RuntimeTurnState.session_id",
    "trace_id": "RuntimeTurnState.trace_id",
    "timestamp": "[NOT DISCERNIBLE]",
    "module_id": "RuntimeTurnState.module_id",
    "current_scene_id": "RuntimeTurnState.current_scene_id",
    "host_versions": "RuntimeTurnState.host_versions"
  },
  "interpreted_move": {
    "runtime_field": "RuntimeTurnState.interpreted_input",
    "keys_echoed_into_model_prompt": [
      "kind",
      "confidence",
      "ambiguity",
      "intent",
      "selected_handling_path",
      "runtime_delivery_hint"
    ]
  },
  "scene_assessment": {
    "scene_core": "[NOT DISCERNIBLE]",
    "pressure_state": "[NOT DISCERNIBLE]",
    "runtime_context_only": "RuntimeTurnState.model_prompt, context_text, retrieval, optional active_narrative_threads / thread_pressure_summary"
  },
  "selected_responder_set": [],
  "selected_scene_function": "[NOT DISCERNIBLE]",
  "pacing_mode": "[NOT DISCERNIBLE]",
  "silence_brevity_decision": {
    "mode": "[NOT DISCERNIBLE]",
    "reason": "[NOT DISCERNIBLE]"
  },
  "proposed_state_effects": [
    "model-proposed: RuntimeTurnState.generation.metadata.structured_output (shape [NOT DISCERNIBLE] — produced by parser/adapter outside langgraph_runtime.py)"
  ],
  "validation_outcome": {
    "status": "[NOT DISCERNIBLE]"
  },
  "committed_result": {
    "committed_effects": []
  },
  "visible_output_bundle": {
    "gm_narration": [],
    "spoken_lines": []
  },
  "continuity_impacts": [
    "RuntimeTurnState.active_narrative_threads (bounded snapshot input)",
    "RuntimeTurnState.thread_pressure_summary (bounded snapshot input)"
  ],
  "visibility_class_markers": [
    "[NOT DISCERNIBLE]"
  ],
  "failure_markers": [
    "RuntimeTurnState.graph_errors",
    "RuntimeTurnState.generation.error"
  ],
  "fallback_markers": [
    "RuntimeTurnState.generation.fallback_used",
    "RuntimeTurnState.graph_diagnostics.fallback_path_taken",
    "generation.metadata.adapter_invocation_mode ∈ { langchain_structured_primary, raw_adapter_graph_managed_fallback, degraded_no_fallback_adapter }",
    "generation.metadata.bypass_note → RAW_FALLBACK_BYPASS_NOTE"
  ],
  "diagnostics_refs": [
    "RuntimeTurnState.graph_diagnostics",
    "graph_diagnostics.execution_health ∈ { healthy, graph_error, model_fallback, degraded_generation }",
    "graph_diagnostics nested: graph_name, graph_version, nodes_executed, node_outcomes, fallback_path_taken, execution_health, errors, capability_audit, repro_metadata, operational_cost_hints"
  ]
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

Derived from `RuntimeTurnState` ([`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py) L50–L74). **validation-owned** / **commit-owned**: [NOT DISCERNIBLE] — no keys in state. **player-visible-only**: [NOT DISCERNIBLE] — no dedicated player-visibility field in state.

| `RuntimeTurnState` field | Category |
|---|---|
| `session_id` | deterministic |
| `module_id` | deterministic |
| `current_scene_id` | deterministic |
| `player_input` | deterministic |
| `trace_id` | deterministic |
| `host_versions` | deterministic |
| `active_narrative_threads` | deterministic |
| `thread_pressure_summary` | deterministic |
| `interpreted_input` | deterministic / model-proposed (payload from injected `interpreter`; schema [NOT DISCERNIBLE] outside this file) |
| `task_type` | deterministic |
| `routing` | deterministic |
| `selected_provider` | deterministic |
| `selected_timeout` | deterministic |
| `retrieval` | deterministic |
| `context_text` | deterministic |
| `model_prompt` | deterministic |
| `generation` | model-proposed |
| `fallback_needed` | deterministic |
| `graph_diagnostics` | diagnostics-only |
| `nodes_executed` | diagnostics-only |
| `node_outcomes` | diagnostics-only |
| `graph_errors` | diagnostics-only |
| `capability_audit` | diagnostics-only |

| Starter schema group (§11.1) | Nearest `RuntimeTurnState` / contract | Category |
|---|---|---|
| `interpreted_move` | `interpreted_input` | see `interpreted_input` |
| `selected_responder_set` | [NOT DISCERNIBLE] | — |
| `committed_result` | [NOT DISCERNIBLE] | — |
| `visible_output_bundle` | `generation` (e.g. `metadata.structured_output`) | model-proposed |
| `diagnostics_refs` | `graph_diagnostics` (+ `generation.metadata.adapter_invocation_mode` from [`runtime_turn_contracts`](../ai_stack/runtime_turn_contracts.py)) | diagnostics-only |

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

**Concrete ordering (this freeze pass, code/content-anchored):**

1. **Runtime / turn surfaces inspected:** [`ai_stack/langgraph_runtime.py`](../ai_stack/langgraph_runtime.py), [`ai_stack/runtime_turn_contracts.py`](../ai_stack/runtime_turn_contracts.py) — used for §7.3 / §8.3 / §10.2 / §12.1.
2. **Reality Anchor populated:** §7.3 rows reference the above + GoC content roots.
3. **Current-vs-Target bridge populated:** §8.3 rows map roadmap targets to those surfaces.
4. **Asset inventory classified below (§15.2):** only after steps 1–3.

In practice, this means:
1. inspect relevant content/runtime surfaces,
2. populate the first Reality Anchor rows,
3. populate the first Current-vs-Target rows,
4. then classify God of Carnage slice assets.

**Phase 0 — GoC material visible only in `builtins.py` + `module_models.py` (no other files evaluated in this row):**

| Material | Type | Evidence in code | Missing from these files |
|---|---|---|---|
| `god_of_carnage_solo` `ExperienceTemplate` | authored + runtime-usable | [`backend/app/content/builtins.py`](../backend/app/content/builtins.py) `build_god_of_carnage_solo`, `id="god_of_carnage_solo"`; registered in `load_builtin_templates()` | YAML module tree, direction files, writers-room — [NOT DISCERNIBLE] here |
| Builtins note “not primary runtime authority” | seed (policy text) | Comment in `load_builtin_templates()` L22–L23 | Which feed is “canonical” — [NOT DISCERNIBLE] from these two files alone |
| `ContentModule`, `ModuleMetadata`, `CharacterDefinition`, phase/trigger models | runtime-usable (generic) | [`backend/app/content/module_models.py`](../backend/app/content/module_models.py) — Pydantic schema for arbitrary modules | GoC-specific types or constants — [NOT DISCERNIBLE] (generic classes only) |
| Derived / imported dramaturgy from primary source | derived | [NOT DISCERNIBLE] in `builtins.py` / `module_models.py` | Explicit derived asset |
| Full MVP slice truth in turn graph | — | [NOT DISCERNIBLE] in `builtins.py` / `module_models.py` | Binding to `RuntimeTurnState` / commit — [NOT DISCERNIBLE] here |

### 15.2 Minimal template

| Asset / content surface | Type | Present today? | Slice relevance | Action needed |
|---|---|---|---|---|
| Character material | authored (YAML) + runtime-usable (builtins template) | partial | High — defines cast, voice hints, baseline attitudes | Reconcile **two shapes**: formal module [`content/modules/god_of_carnage/characters.yaml`](../content/modules/god_of_carnage/characters.yaml) vs solo template roles in [`backend/app/content/builtins.py`](../backend/app/content/builtins.py) (`veronique`/`michel`/… vs module IDs); decide canonical naming and which runtime loads which. |
| Scene material | authored (YAML phases) + runtime-usable (builtins rooms/beats) | partial | High — scene progression and pressure | Map module `scene_phases` in [`content/modules/god_of_carnage/scenes.yaml`](../content/modules/god_of_carnage/scenes.yaml) to builtins beat graph (`courtesy`, `first_fracture`, …); **[UNKNOWN]** whether the engine merges both ([NOT DISCERNIBLE] without further integration inspection). |
| Relationship material | authored | yes (files present) | High — fault lines / axes | Use [`content/modules/god_of_carnage/relationships.yaml`](../content/modules/god_of_carnage/relationships.yaml) (+ `escalation_axes.yaml`) as structured relationship source; wire into runtime truth / turn schema — **[NOT DISCERNIBLE]** whether already consumed on the production path (loader models only in [`backend/app/content/module_models.py`](../backend/app/content/module_models.py)). |
| Triggers / transitions / endings | authored | yes (listed in `module.yaml`) | High — formal dramatic machinery per module contract | Files: `triggers.yaml`, `transitions.yaml`, `endings.yaml` under [`content/modules/god_of_carnage/`](../content/modules/god_of_carnage/); freeze should require engine adherence or mark gap if only documentary today. |
| Direction (LLM) | authored | yes | Medium–high — steering and voice | [`content/modules/god_of_carnage/direction/system_prompt.md`](../content/modules/god_of_carnage/direction/system_prompt.md), `scene_guidance.yaml`, `character_voice.yaml` per `module.yaml` `files` list. |
| Module shell / loader contract | runtime-usable (schema + service) | yes | High — how content enters the system | [`backend/app/content/module_service.py`](../backend/app/content/module_service.py) (`load_and_validate`, `content_modules_root` default beside `backend/`), [`backend/app/content/module_models.py`](../backend/app/content/module_models.py) (`ContentModule`, phases, triggers). |
| Writers-room prose implementations | seed / loose source | yes | Medium — design aid, not identical to YAML module | Directory `writers-room/app/models/implementations/god_of_carnage/`; treat as **not automatically runtime-canonical** unless explicitly ingested. |

### 15.3 Authoring-cost lens

The inventory must include a short note on whether the slice already appears to demand disproportionate manual authoring effort.

This is not a freeze blocker by default, but it must not remain invisible.

**Authoring-cost note (evidence-based):** God of Carnage material exists in **at least three parallel shapes** today: (1) the formal YAML module tree [`content/modules/god_of_carnage/`](../content/modules/god_of_carnage/) (multi-file, high structure), (2) the built-in `ExperienceTemplate` in [`backend/app/content/builtins.py`](../backend/app/content/builtins.py) (`build_god_of_carnage_solo`, large inline authoring), and (3) extensive markdown under `writers-room/app/models/implementations/god_of_carnage/`. **Derived static assets** from primary script text are **not discernible** as a dedicated, versioned corpus in this inspection pass. Until freeze picks a **single canonical authority** and cutover rules, maintenance cost risks being **disproportionate** (duplicate edits, drift).

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
