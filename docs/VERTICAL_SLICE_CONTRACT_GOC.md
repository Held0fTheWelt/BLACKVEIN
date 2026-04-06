# VERTICAL_SLICE_CONTRACT_GOC.md

Contractual frame for the MVP vertical slice **God of Carnage (GoC)** under Phase 0 Freeze. Normative process rules live in `docs/FREEZE_OPERATIONALIZATION_MVP_VSL.md`; product intent in `docs/ROADMAP_MVP_VSL.md`. Other freeze artifacts may reference this document; they must not redefine the same concepts in conflicting terms.

---

## 1. Purpose and scope

This document binds the slice **in content and architecture**: what belongs in the MVP, what is out of scope, how **current code** relates to the **target architecture** in the roadmap, and which **GoC assets** exist today. The goal is a guided interactive dramatic runtime cut (Roadmap §2–§7), not a generic chatbot or text toy.

---

## 2. Slice boundaries

### 2.1 In scope (MVP GoC)

- **Module / narrative space:** **God of Carnage** only as the first MVP vertical slice (Roadmap §6).
- **Player experience:** free input, scene-grounded interpretation, responder and scene-function selection, bounded model proposal, **validation and commit as target**, truth-aligned visible output, continuity across turns (Roadmap §5, §7, §8).
- **Technical baseline:** continue from the existing **LangGraph runtime** and documented **runtime turn state** (see Reality Anchor); extensions must align with the freeze, not introduce a second runtime truth (Roadmap §4.5, FREEZE §23).

### 2.2 Explicitly out of scope

- Full script coverage, multi-module generalization, open-world improvisation, unconstrained roleplay, broad MCP write surfaces before the runtime is dependable (Roadmap §12, §14).
- **Generic** chatbot quality or “strong model + nice prompt” without scene function and truth alignment (Roadmap §11, §12).

### 2.3 Scope violation behavior

For input or situations outside the GoC slice: prefer **containing, scene-coherent** handling (Roadmap §9); do not extend canonical truth beyond the slice. Concrete visible and diagnostic responses are anchored in `docs/GATE_SCORING_POLICY_GOC.md` (Failure-to-Response).

---

## 3. Reality Anchor

Code- and content-facing snapshot: what exists, what is partial, what is reusable. *(From FREEZE §7.3 — Inspection Pass.)*

| Concern | Current state | Classification | Code/content reference | Freeze implication |
|---|---|---|---|---|
| Runtime graph / orchestration path | `StateGraph(RuntimeTurnState)` with nodes `interpret_input`, `retrieve_context`, `route_model`, `invoke_model`, `fallback_model`, `package_output`; edges: linear chain through `invoke_model`, conditional to `fallback_model` or `package_output`, then `package_output` → `END`. Entry: `interpret_input`. | partial | `ai_stack/langgraph_runtime.py` (`RuntimeTurnGraphExecutor._build_graph`) | Roadmap turn phases beyond model+RAG require additional orchestration nodes or a parallel engine contract. |
| Runtime state structures | `RuntimeTurnState` (`TypedDict`, `total=False`): `session_id`, `module_id`, `current_scene_id`, `player_input`, `trace_id`, `host_versions`, `active_narrative_threads`, `thread_pressure_summary`, `interpreted_input`, `task_type`, `routing`, `selected_provider`, `selected_timeout`, `retrieval`, `context_text`, `model_prompt`, `generation`, `fallback_needed`, `graph_diagnostics`, `nodes_executed`, `node_outcomes`, `graph_errors`, `capability_audit`. | partial | `ai_stack/langgraph_runtime.py` (`RuntimeTurnState`; `run` initial state) | Must be mapped to the canonical turn schema; explicit commit/validation keys are not visible in this state shape. |
| Turn-related contracts / vocabulary | `AdapterInvocationMode` literals + constants; `ExecutionHealth` literals + constants; execution-health values; raw fallback bypass note. Used in `generation.metadata.adapter_invocation_mode` and `graph_diagnostics.execution_health`. | partial | `ai_stack/runtime_turn_contracts.py`; `ai_stack/langgraph_runtime.py` (`_invoke_model`, `_fallback_model`, `_package_output`) | Scene-function / continuity / visibility vocabulary does not currently live here. |
| Content/module system (GoC relevance) | `load_builtin_templates()` registers `build_god_of_carnage_solo()` → `ExperienceTemplate` id `god_of_carnage_solo`. `ModuleService` / `ContentModule` load modules from filesystem content root. **Binding:** canonical slice source is the YAML module tree (§6); builtins are secondary (§6). | partial / reusable | `backend/app/content/builtins.py`; `backend/app/content/module_service.py`; `backend/app/content/module_models.py` | Runtime must load dramatic truth for the slice from the canonical YAML authority; builtins must not silently override YAML (§6). |
| Mock/fallback/test infrastructure (dry-run) | Primary path uses LangChain/runtime adapter invocation in `_invoke_model`. Fallback path uses `adapters.get("mock")` in `_fallback_model`; metadata marks managed fallback or degraded missing-fallback mode. | partial | `ai_stack/langgraph_runtime.py` (`_invoke_model`, `_fallback_model`) | Dry-run should build on this existing path rather than inventing an abstract separate concept. |
| Diagnostics / logging surfaces | `package_output` sets `graph_diagnostics`: graph name/version, nodes executed, node outcomes, fallback path taken, execution health, errors, capability audit, repro metadata, operational cost hints. | partial | `ai_stack/langgraph_runtime.py` (`_package_output`) | Strong starting point for operator-facing diagnostics, but not yet the full dramatic replay surface required by the target slice. |

---

## 4. Current state vs target state bridge

Compact classification of roadmap targets vs inspected current shape. *(From FREEZE §8.3 — Inspection Pass.)*

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
| Source-to-game assets | Builtins template plus content-module loader/model surfaces. | Dramatic source transformed into playable slice machinery. | reusable | Canonical YAML + secondary surfaces reconciled per §6 — not ignored. |
| Scene-director representation | Graph currently focuses on interpretation, retrieval, routing, invoke, fallback, package. | Explicit scene-director responsibility. | new | **Resolved** in `docs/CANONICAL_TURN_CONTRACT_GOC.md` §3 (graph-node decomposition). |
| Operator review mode | Diagnostics currently embedded in runtime output only. | Review/governance mode. | new | Must be made explicit. |

---

## 5. Controlled vocabulary (slice authority)

Canonical labels for scene functions, pacing, silence/brevity, continuity, visibility, failure, and transition patterns are **identical** across all three freeze artifacts; alignment and alias rules follow FREEZE §9.1. **This section is the primary normative home** for semantic areas in slice context; `CANONICAL_TURN_CONTRACT_GOC.md` and `GATE_SCORING_POLICY_GOC.md` use the same strings by reference.

**Binding (MVP GoC, Phase 0 Freeze):** The label sets below are **approved for the first implementation cycle**. New canonical labels require a freeze amendment or an explicit task with a migration plan.

| Semantic area | Canonical labels | Temporary alias allowed? | Cutover rule | Deprecation rule |
|---|---|---|---|---|
| Scene function | `establish_pressure`, `escalate_conflict`, `probe_motive`, `repair_or_stabilize`, `withhold_or_evade`, `reveal_surface`, `redirect_blame`, `scene_pivot` | yes, max one release cycle, documented in `fallback_markers.legacy_scene_function` | New label only via freeze amendment or explicit migration task | After cutover, old labels in tasks/diagnostics = error |
| Pacing (`pacing_mode`) | `standard`, `compressed`, `thin_edge`, `containment`, `multi_pressure` | no | Change only via freeze patch | Stale values fail `turn_integrity` when enforced |
| Silence / brevity (`silence_brevity_decision.mode`) | `normal`, `brief`, `withheld`, `expanded` | no | Change only via freeze patch | Stale values fail `turn_integrity` when enforced |
| Continuity class | `situational_pressure`, `dignity_injury`, `alliance_shift`, `revealed_fact`, `refused_cooperation`, `blame_pressure`, `repair_attempt`, `silent_carry` | yes, with published mapping table next review cycle | Parallel only if mapping published | After cutover, aliases not allowed in `continuity_impacts` |
| Visibility class | `truth_aligned`, `bounded_ambiguity`, `non_factual_staging` | no for productive player turns | Change only via freeze patch | Stale values block gate `turn_integrity` |
| Failure class | `scope_breach`, `validation_reject`, `model_fallback`, `graph_error`, `missing_scene_director`, `missing_validation_path`, `missing_commit_path`, `continuity_inconsistency` | yes for raw diagnostic strings (`errors[]`) with `failure_class` field | Runtime maps raw errors to failure class by next minor release | Raw strings without class after cutover = diagnostics-only |
| Transition pattern | `hard`, `soft`, `carry_forward`, `diagnostics_only` | no | Change only jointly with `CANONICAL_TURN_CONTRACT_GOC.md` pattern inventory | Old pattern labels in new tasks = error |

**Pacing semantics (normative):**

- `standard` — Normal scene rhythm; full dramatic bandwidth within policy.
- `compressed` — Tighter beat; less digression; same truth constraints.
- `thin_edge` — Minimal dramatic substance by design; stronger expectation for diagnostic review.
- `containment` — Out-of-scope or scope-breach containment; no new world facts beyond containment copy.
- `multi_pressure` — Multiple simultaneous pressure lines; **single `selected_scene_function` priority rule** in `docs/CANONICAL_TURN_CONTRACT_GOC.md` §3.3 applies.

**Silence / brevity semantics (normative):**

- `normal` — Default verbal density.
- `brief` — Shorter lines; same truth and visibility doctrine.
- `withheld` — Deliberate under-response / silence as a dramatic move.
- `expanded` — More explicit rendering; still truth-safe unless visibility classes allow otherwise.

**Stability for tasks and diagnostics:** Scene function, pacing, silence/brevity, continuity class, and visibility class values appear in structured canonical turn fields and are stable enough for automated gates. Failure class must be recoverable from `failure_markers` and gate reports; raw operational messages may be aliased until mapping is complete.

**Cross-reference:** Selection of a single `selected_scene_function` when multiple intentions compete — `docs/CANONICAL_TURN_CONTRACT_GOC.md` §3.3.

---

## 6. God of Carnage asset inventory

*(From FREEZE §15.2 — Inspection Pass; ordering §15.1.)*

| Asset / content surface | Type | Present today? | Slice relevance | Role |
|---|---|---|---|---|
| Content-module YAML tree under `content/modules/god_of_carnage/` | Structured module source | yes | High | **Canonical source authority** for the MVP slice |
| Builtins `god_of_carnage_solo` template | Authored + runtime-usable | yes | High | **Secondary** — convenience, tests, demos only |
| Writers-room markdown under `writers-room/.../god_of_carnage/` | Seed / design notes | yes | Medium | **Secondary** — reference and authoring only |
| Derived dramatic slice corpus (generated, versioned) | Derived | not explicit | Low until defined | Optional future artifact; if introduced, must declare lineage **from YAML** and versioning |

### 6.1 Canonical source authority (binding)

| Rule | Statement |
|---|---|
| **Canonical** | The **YAML module tree** at `content/modules/god_of_carnage/` (including referenced files such as `module.yaml`, `scenes.yaml`, and the `direction/` subtree) is the **sole canonical dramatic source authority** for slice content consumed by runtime and task derivation. |
| **Secondary — builtins** | The `god_of_carnage_solo` builtins template may **not** define truth that contradicts YAML. It may **not** be merged silently with YAML. If both are loaded, **YAML wins**; builtins may only mirror YAML or remain explicitly non-authoritative test fixtures. |
| **Secondary — writers-room** | Writers-room markdown **must not** influence runtime directly. It is **reference and design input only**. Changes become runtime-relevant only when reflected in YAML (or in a future derived corpus explicitly built from YAML). |
| **Derived corpus** | Any future derived corpus is **non-canonical** unless promoted by freeze amendment; until then it is a build artifact whose source of truth remains YAML. |
| **Direct runtime influence** | Only **canonical YAML** (and runtime code under freeze) may **directly** drive productive slice behavior. Secondary sources **do not** directly set module truth. |
| **Cutover / maintenance** | Content changes for the slice are **authoritative when merged into the YAML tree**. Builtins and markdown must be **reconciled or explicitly marked non-authoritative** in the same change window. **Silent merge of YAML truth with builtins truth is forbidden.** |

**Binding rule:** For God of Carnage MVP work, **if runtime or tasks need slice truth, they read it from the canonical YAML module tree**; builtins and writers-room are **secondary**, may **not** override YAML, and **must not** be silently fused with YAML into a single competing truth surface.

### 6.2 Authoring cost note (FREEZE §15.3)

Parallel shapes (YAML, builtins, writers-room) still incur coordination cost. The **canonical YAML decision** removes semantic ambiguity about **which file wins**; drift between secondary surfaces and YAML is a **defect** until reconciled.

---

## 7. Non-productive dry-run (operationalization)

Anchored to FREEZE §16 and the Reality Anchor.

| Aspect | Binding |
|---|---|
| **Infrastructure used** | Existing graph in `ai_stack/langgraph_runtime.py`; primary `_invoke_model`; fallback/mock `_fallback_model` with `adapters.get("mock")`; output includes `graph_diagnostics` from `_package_output`. |
| **What it proves** | Deterministic or semi-deterministic: node order, fallback path, `execution_health`, repro hints and cost hints are readable; slice boundaries testable without productive claims. |
| **What it does not prove** | Full dramatic quality, real validation/commit semantics (not yet in graph), productive MCP path. |
| **Productive boundary** | Dry-run **marks** test/mock mode in metadata and produces **no** claimed canonical committed truth for live players without an explicit commit step (see `docs/CANONICAL_TURN_CONTRACT_GOC.md` — seams). |
| **Inspection** | Evaluate `graph_diagnostics` (graph name/version, `nodes_executed`, `node_outcomes`, `fallback_path_taken`, `execution_health`, `errors`, `repro_metadata`, `operational_cost_hints`) plus optional tabletop overlay per `docs/GATE_SCORING_POLICY_GOC.md`. |

---

## 8. Cross-references

- Canonical turn schema, field ownership, seams, scene direction, transitions: **`docs/CANONICAL_TURN_CONTRACT_GOC.md`**
- Gate families, scoring, cadence, diagnostic modes, failure mapping, escalation, tabletop evidence: **`docs/GATE_SCORING_POLICY_GOC.md`**

---

## 9. Tabletop / traceability (pointer)

Full tabletop requirements and evidence structure: **`docs/GATE_SCORING_POLICY_GOC.md`**, Tabletop Trace-Through. This slice document supplies vocabulary, assets, and the current/target bridge against which scenarios are checked per FREEZE §21.
