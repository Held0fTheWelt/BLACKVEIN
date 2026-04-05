# AI Story Contract

## Purpose

This document defines the formal contract between the AI story systems and the World Engine. It specifies what AI can propose, what it is forbidden to change, how proposals are structured, how validation works, and the role separation between SLM helpers and the authoritative LLM story model.

---

## Model routing (Tasks 2A / 2B / Task 2E)

The **executable** routing contracts and policy live in `backend/app/runtime/model_routing_contracts.py` and `backend/app/runtime/model_routing.py`, backed by model specs in `adapter_registry`. They implement cross-model LLM/SLM selection by task kind and phase.

**Task 2 (operational inventory)**: Flask `create_app` calls `routing_registry_bootstrap` when **`ROUTING_REGISTRY_BOOTSTRAP`** is true (default on `Config`; **off on `TestingConfig`** for isolated pytest). That registers the real **`MockStoryAIAdapter`** + `AdapterModelSpec` so Runtime `route_model()` without explicit `specs=` sees a non-empty `iter_model_specs()` in normal non-test processes. Writers-Room and Improvement share specs from `writers_room_model_routing` with honest **`revision_synthesis`** coverage and intentional **`degrade_targets`** to `mock`. Details: [LLM / SLM role stratification](./llm_slm_role_stratification.md) and [model inventory seam map](./model_inventory_seam_map.md).

The SLM helper roles described later in this document are **conceptual** narrative roles for the story stack. They are not interchangeable with the **internal** interpreter/director/responder contract in `role_contract.py`, nor with the Task 2A/2B **cross-model** routing layer. See [LLM / SLM role stratification](./llm_slm_role_stratification.md).

**Task 2B / Task 2C / Task 2E / Task 1 (Runtime) integration (current):**

- **Runtime**: The canonical in-process AI path (`execute_turn_with_ai`) runs **Task 1 multi-stage orchestration** by default (`backend/app/runtime/runtime_ai_stages.py`): **preflight** (SLM-first `cheap_preflight`), **signal / consistency** (`repetition_consistency_check` with hints derived deterministically from preflight), then **conditional synthesis** (LLM-class `narrative_formulation` or session override) **only when** the signal output and parse-safety rules require it. Otherwise a deterministic **SLM-only packaging** step builds canonical structured JSON for the existing parse → `execute_turn` pipeline. **Each stage** uses its own `RoutingRequest` (meaningful `workflow_phase` / `task_kind`). **Guards, commit, and reject semantics are unchanged**; models remain advisory. `AIDecisionLog` adds **`runtime_stage_traces`** (per-stage routing, `routing_evidence`, skip reasons, bounded output summaries) and **`runtime_orchestration_summary`** (`stages_executed`, `stages_skipped`, `synthesis_skipped`, `final_path`, etc., plus Task 3 additive keys that separate **packaging** from **no-eligible-adapter** skips). **`model_routing_trace`** is a **rollup** compatible with earlier consumers (synthesis stage when used; signal rollup when synthesis is skipped). **Task 3** adds **`operator_audit`** on `AIDecisionLog` (deterministic timeline/summary from existing evidence). **Supervisor `agent_orchestration` preempts** staged Runtime orchestration (explicit in summary). **`runtime_staged_orchestration: false`** selects the legacy single-pass path. Nested **Task 2C-2** `routing_evidence`, **Task 2D** alignment/deviation, **Task 2E** primary codes, and **Task 2F** compact diagnostics apply per stage trace and/or rollup as implemented.
- **Writers Room**: Same contracts via `route_model` with **preflight** and **synthesis** stages. `model_generation.task_2a_routing` holds per-stage traces; each stage includes **`routing_evidence`** in the same normalized shape as runtime (plus bounded-call / skip fields where applicable). Responses include additive **`operator_audit`** and per-trace **`stage_id`** (alias of **`stage`**).
- **Improvement**: After deterministic sandbox evaluation and recommendation thresholds, the Improvement experiment HTTP path runs **two** bounded routing stages (preflight + synthesis) using the same spec source as Writers Room. The package exposes `task_2a_routing`, `deterministic_recommendation_base`, and `model_assisted_interpretation` (advisory only), plus additive **`operator_audit`** and per-trace **`stage_id`** (alias of **`stage`**). **Model output does not replace** threshold-based recommendation truth; **authoritative truth** stays with deterministic evaluation and engine rules.

**Operator audit (Task 3)** is derived-only, not an immutable distributed audit platform; routing and authoritative Runtime semantics are unchanged. See [LLM / SLM role stratification](./llm_slm_role_stratification.md) (Task 3 section).

**Not in scope:** separate telemetry pipelines, dashboards, or autonomous multi-turn editorial stacks beyond the **bounded** Task 1 Runtime stages described above.

### Task 4 — Maturity hardening (validation and drift resistance)

Task 4 **does not** change routing policy, `StoryAIAdapter`, or guard/commit/reject authority. It adds **documented validation gates**, **stronger automated tests**, and **cross-surface contract checks** so behavior stays honest and regression-visible.

- **Seam map (what was strong vs weak):** [`task4_validation_seam_map.md`](./task4_validation_seam_map.md)
- **Explicit gate table (reviewable contract):** [`task4_hardening_gates.md`](./task4_hardening_gates.md)
- **Closure report (PASS/FAIL, commands, residual risks):** [`task4_maturity_hardening_closure_report.md`](./task4_maturity_hardening_closure_report.md)

**What tests now prove (high level):** staged Runtime success, SLM-only, degraded skip/parse-forced synthesis, orchestration-preempted audit shape (schema version and preempted timeline entry), legacy single-pass, tool-loop continuation after a staged synthesis tool request, real `create_app` bootstrap-on path, empty-registry / missing-adapter honesty, synthesis stage with `no_eligible_spec_selection` while execution still falls back to the passed adapter, Improvement `_run_routed_bounded_call` skip when provider adapters are absent, shared `operator_audit` / `routing_evidence` key contracts across Runtime, Writers-Room, and Improvement, and bounded drift checks on `audit_schema_version` and stable evidence keys.

**Still not claimed:** God-of-Carnage lifecycle E2E does not assert full staged audit fields by default execution mode; no distributed immutable audit; no new telemetry products.

---

## Authority Rule (Fundamental)

**AI proposes. Engine decides.**

The AI may generate story proposals — scene interpretation, character reactions, conflict progression. The AI may NOT:
- Set canonical state directly
- Override Engine validation
- Define facts outside the content module
- Create new characters, relationships, or scenes
- Claim truth about the game world

**Every AI proposal must pass Engine validation before any state change occurs.**

---

## Structured AI Output

AI story models must return a JSON structure with these mandatory fields:

```json
{
  "scene_interpretation": "string",
  "detected_triggers": ["string"],
  "proposed_state_deltas": { /* see below */ },
  "dialogue_impulses": ["string"],
  "conflict_vector": "string",
  "confidence": "optional float 0–1",
  "uncertainty": "optional string"
}
```

### Field Definitions

**`scene_interpretation`** (required, string)
- What is happening right now in narrative terms
- Examples: "Annette is escalating moral accusations", "Michel is attempting damage control"
- Length: 1–2 sentences
- Constraints: Must reference only characters and facts in session state or event log

**`detected_triggers`** (required, array of strings)
- Which triggers from the module's trigger set are active
- Valid values for God of Carnage: `contradiction`, `exposure`, `relativization`, `apology_offered`, `apology_refused`, `cynicism`, `flight_into_sideplot`
- Constraints: Must be subset of module-defined triggers
- Engine will reject unknown triggers

**`proposed_state_deltas`** (required, object)
- Proposed changes to session state (see Session Runtime Contract)
- Structure: `{ "character_name": { "field": new_value }, ... }`
- Examples:
  - `{ "Véronique": { "emotional_state": 75 } }`
  - `{ "spousal_bond": { "stability": 45 } }`
- Constraints: Must match module state schema; must not create new characters or axes

**`dialogue_impulses`** (required, array of strings)
- Proposed dialogue or action for characters
- Format: `"[CHARACTER]: [dialogue or action]"`
- Examples: `"Annette: 'Your principles are just camouflage for your ego.'"`, `"Michel: [leaves the room]"`
- Constraints: Dialogue must fit character voice; actions must be plausible in scene

**`conflict_vector`** (required, string)
- Current direction/intensity of conflict
- Examples: `"escalating_moral_attack"`, `"defensive_coalition_forming"`, `"de-escalating_with_humor"`
- Used by Engine to assess turn trajectory
- Constraints: Descriptive only; Engine decides if it matches proposed_state_deltas

**`confidence`** (optional, float)
- Model's confidence in this proposal (0–1)
- Used by Engine and router SLM to decide retry/fallback strategy
- If absent: assume 0.7 (default)

**`uncertainty`** (optional, string)
- Model's expression of doubt or alternative interpretations
- Examples: `"Michel's intentions are unclear; could be protecting spouse or himself"`, `"Trigger detection uncertain; could be 'exposure' or 'relativization'"`
- Helps Engine and guard_precheck assess proposal robustness

---

## Allowed Action Types

AI may propose state changes only to these fields (per-character and per-relationship):

### Per-Character Fields
- `emotional_state` (0–100: neutral → angry)
- `escalation_level` (0–100: calm → furious)
- `engagement` (0–100: withdrawn → fully invested)
- `moral_defense` (0–100: confident → shattered)

### Per-Relationship/Axis Fields
- `stability` (0–100: aligned → hostile)
- `dominance_shift` (integer: -5 to +5, representing who gains influence)

### Dialogue & Actions
- Character dialogue (must be in character voice)
- Character actions (must be plausible in scene)

**Constraints**:
- State values must stay within defined bounds (0–100)
- New facts may not be added to the module
- New characters may not be created
- Scene transitions are Engine-only (not AI)

---

## Forbidden Changes

AI may NOT propose:

- ❌ New characters or NPCs
- ❌ New relationships or axes beyond the module definition
- ❌ New facts about the game world (e.g., "Alain is secretly the town's mayor")
- ❌ Direct scene transitions (only Engine can call scene changes)
- ❌ Module changes (e.g., adding triggers, redefining characters)
- ❌ Overwriting the event log or session metadata
- ❌ Accessing information not in content module or event log
- ❌ Generating dialogue for players (only NPCs)
- ❌ Making strategic decisions (only Engine decides turn outcome)

---

## Validation Rules

The Engine's guard layer validates every AI proposal:

### Schema Validation
- ✅ Output is valid JSON
- ✅ All mandatory fields present
- ✅ Field types correct (string, array, object)

### Semantic Validation
- ✅ `detected_triggers` contains only module-defined triggers
- ✅ `proposed_state_deltas` references only defined characters/axes
- ✅ State values within bounds (0–100, or defined range)
- ✅ `dialogue_impulses` reference only available characters (NPCs or player)

### Constraint Validation
- ✅ No new facts introduced
- ✅ No forbidden changes attempted
- ✅ Scene_interpretation is coherent with proposed deltas
- ✅ Dialogue impulses match character voice (guard_precheck compares to character_voice.yaml)

### Coherence Validation
- ✅ `conflict_vector` matches emotional trajectory of proposed deltas
- ✅ Detected triggers justify proposed state changes
- ✅ No contradictions within the proposal (e.g., "de-escalating" but proposing max emotional_state)

---

## SLM Helper Roles

Five specialized SLM roles assist the story LLM and Engine:

### 1. `context_packer`

**Input**:
- Full session state (all characters, axes, current scene)
- Event log (all turns so far)
- Active relationship metadata

**Output**:
- Compressed story context (typically <2000 tokens)
- Priority ranking: what the story LLM must know first

**Task**:
- Extract the most recent and relevant facts
- Compress multi-turn conversations into key decision points
- Preserve all character emotional states and axis values
- Flag escalation moments and turning points

**Constraints**:
- May not add facts
- May not alter state values
- Must preserve all quantitative data (emotional_state, stability, etc.)

### 2. `trigger_extractor`

**Input**:
- Most recent turn's player/NPC dialogue
- Module's trigger set definition
- Current scene state

**Output**:
- List of detected triggers from the trigger set
- Confidence per trigger (optional)

**Task**:
- Identify which trigger types are present in the turn
- Note which character is responding
- Flag uncertain trigger detections

**Constraints**:
- May only output module-defined triggers
- Must work for any module (generic role)

### 3. `delta_normalizer`

**Input**:
- Raw AI story output JSON (possibly malformed or inconsistent)
- Module state schema

**Output**:
- Normalized `proposed_state_deltas` object
- Cleanup notes (optional)

**Task**:
- Fix minor JSON formatting issues
- Ensure all state changes fit module schema
- Validate data types and bounds
- Flag data that cannot be normalized

**Constraints**:
- May not invent new state changes
- May not alter meaning of proposal
- Must preserve all values or flag for rejection

### 4. `guard_precheck`

**Input**:
- Structured AI output (post-delta_normalizer)
- Module definition and character_voice.yaml
- Current session state

**Output**:
- List of potential violations or risks
- Severity per violation (hard reject / warning / info)

**Task**:
- Check for forbidden mutations (new characters, facts, module changes)
- Verify character dialogue matches voice
- Flag contradictions between `scene_interpretation` and proposed deltas
- Identify confidence thresholds for retry/fallback

**Constraints**:
- May not reject proposals outright (Engine decides)
- Must list violations clearly so Engine can act
- May not alter the proposal

### 5. `router`

**Input**:
- Task description (e.g., "generate next turn for scene")
- Session history and complexity metrics
- Last turn's result (success, guard precheck warnings, etc.)
- Model performance history (last N turns)

**Output**:
- Routing decision: `full_llm_call`, `reduced_context_llm_call`, `fallback_mode`, `safe_no_op`

**Task**:
- Decide whether a full story LLM call is needed
- Suggest reduced context if complexity is high
- Recommend fallback mode if last turn had errors
- Preserve session stability

**Constraints**:
- Decision is advisory (Engine enforces final routing)
- Must not skip validation steps

---

## LLM Story Model Roles

The story LLM holds three internal roles that work together:

### Interpreter
**Task**: Analyze the current scene state and situation
- What is happening narratively?
- Which characters are in tension?
- What triggered this moment?

### Director
**Task**: Determine which conflict movement or response is dramaturgically appropriate
- Should escalation continue or reverse?
- Which character should drive the next moment?
- What emotional dynamic should shift?

### Responder
**Task**: Generate the concrete narrative response
- What dialogue or action follows?
- How do characters react to the tension?
- What are the immediate consequences?

**Constraint**: All three roles must work within the module's defined constraints (God of Carnage scenes, characters, triggers, escalation logic).

---

## Guard Behavior

The guard layer operates as a series of checks before any state change:

### Check 1: Schema
Does the output conform to mandatory structure? (Handled by delta_normalizer)

### Check 2: Semantic
Do all references (characters, triggers, axes) exist in the module?

### Check 3: Constraints
Are forbidden changes attempted? (Hard reject if yes)

### Check 4: Coherence
Does the interpretation match the proposed changes?

### Check 5: Confidence
Is the model confident in this proposal? (High confidence: accept if guards pass; low confidence: flag for manual review or fallback)

### Outcome
- ✅ **Accept**: All checks pass → Engine applies state deltas
- ⚠️ **Warning**: Minor issues detected → Engine may apply with notation or request retry
- ❌ **Reject**: Critical issues detected → Engine falls back to safe no-op or retry with reduced context

---

## W0 Error Classes

The following error classes are named and handled in W0:

1. **`schema_invalid`** — Output is not valid JSON or missing mandatory fields
2. **`forbidden_mutation`** — Attempt to change something that is read-only (module definition, player character)
3. **`unknown_reference`** — Reference to undefined character, trigger, or axis
4. **`illegal_scene_jump`** — Attempt to transition scenes (Engine-only)
5. **`unsupported_trigger`** — Trigger not in module trigger set
6. **`canon_conflict`** — Proposed state contradicts event log or session state
7. **`partial_output`** — Mandatory field is missing or malformed
8. **`empty_response`** — AI returned null or empty output
9. **`timeout_backend_failure`** — AI call failed to complete
10. **`slm_normalization_failure`** — delta_normalizer could not normalize output
11. **`slm_routing_mismatch`** — router recommendation contradicted by Engine constraints
12. **`precheck_warning_overflow`** — guard_precheck identified too many issues (>threshold)

---

## Architecture Axiom

**"SLMs prepare the canon flow; they do not lead it."**

This means:
- SLMs compress, extract, normalize, and pre-check
- SLMs do not generate story
- SLMs do not make canonical decisions
- The story LLM generates proposals
- The Engine commits canonical state
- SLMs answer "Is this proposal structurally valid?"
- The Engine answers "Is this state change permitted?"

---

## Related Documents

- [MVP Definition](./mvp_definition.md) — Authority model and SLM/LLM distinction
- [God of Carnage Module Contract](./god_of_carnage_module_contract.md) — Module-specific validation rules
- [Session Runtime Contract](./session_runtime_contract.md) — How Engine applies and logs AI proposals

---

**Version**: W0 (2026-03-26)
