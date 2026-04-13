# CANONICAL_TURN_CONTRACT_GOC.md

Canonical **starter turn contract** for the MVP vertical slice **God of Carnage**. Normative process: `docs/MVPs/MVP_VSL_And_GoC_Contracts/FREEZE_OPERATIONALIZATION_MVP_VSL.md`; product phases: `docs/MVPs/MVP_VSL_And_GoC_Contracts/ROADMAP_MVP_VSL.md` §8. **Slice boundaries, Reality Anchor, current-vs-target bridge, asset inventory, and slice-level vocabulary** are normative in `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` — this document references them, does not redefine them.

---

## 1. Purpose

A shared, implementation-adjacent turn model so contributors do not invent incompatible variants. It maps roadmap phases (interpretation → scene → responder → scene function → pacing → proposal → validation → commit → visibility → continuity → diagnostics) to **concrete field groups**.

---

## 2. Proposal / validation / commit / visible-output seams

FREEZE §10.1 applies verbatim: nothing player-visible may precede committed truth except where the visibility doctrine explicitly allows non-factual staging, implied affect, or bounded ambiguity.

### 2.1 Seam table (implementation anchor — GoC slice)

| Seam | Owner | Graph locus | Input | Output | May alter truth? | May alter visibility? |
|---|---|---|---|---|---|---|
| Proposal | Model invocation path | `invoke_model` / `fallback_model` → `proposal_normalize` | interpreted input, context, `model_prompt`, routing | `generation`, normalized `proposed_state_effects` | no | yes, proposal only |
| Validation | Rule engine (no player text) | `validate_seam` | `proposed_state_effects`, `generation`, director context | `validation_outcome` (`approved` / `rejected` / `waived`) | no, shapes only | no direct player output |
| Commit | Engine seam | `commit_seam` | `validation_outcome`, `proposed_state_effects` | `committed_result`, bounded `continuity_impacts` (GoC) | yes | indirectly |
| Visible render | Presentation seam | `render_visible` | `committed_result`, `validation_outcome`, `generation`, `transition_pattern` | `visible_output_bundle`, `visibility_class_markers` | no | yes |

**Diagnostics:** `package_output` sets `graph_diagnostics`, `diagnostics_refs`, and `experiment_preview` per `GATE_SCORING_POLICY_GOC.md`. **Operator compact view:** `build_operator_canonical_turn_record(state)` in `ai_stack/goc_turn_seams.py` (post-`package_output` state).

### 2.2 Semantics per seam (binding)

The following matches the implemented GoC slice; non-GoC modules use `waived` validation and preview-class visibility:

- **Proposal** produces **candidate** dramatic material only (`proposed_state_effects`, generation text). It **never** authorizes world truth.
- **Validation** consumes `proposed_state_effects` and scene/policy context; emits `validation_outcome`; **no** direct player-facing copy from this seam.
- **Commit** authorizes canonical consequences; writes `committed_result`; **sole** source for “what holds in the world” for dramatically relevant facts.
- **Visible render** materializes `visible_output_bundle` **only** in line with `committed_result` and visibility markers (vocabulary: `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §5).

### 2.3 Semantic closure (binding)

- **Proposal vs validation:** If `validation_outcome` is absent, any productive claim that the engine “validated” the turn is **false**; see `docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md` §6 for severity and `experiment_preview` rules.
- **Validation vs commit:** If `committed_result` is absent, no new **committed** dramatic facts may be asserted to the player; visible copy must stay in proposal/staging modes per visibility classes and failure policy.
- **Commit vs visible:** Player-visible factual statements must **trace** to `committed_result` (or to visibility classes that explicitly allow non-factual staging without factual commitment).
- **Single writer per seam:** Each seam has one owning stage in the graph contract; skipping a seam without an explicit marker is a **governance and gate** issue, not an informal shortcut.

---

## 3. Scene director representation

### 3.1 Chosen pattern (binding)

**Graph-node decomposition:** Scene-direction decisions are implemented as **named LangGraph nodes** (or short **named** sub-sequences) inserted between existing phases — e.g. after `interpret_input` / `retrieve_context` and **before** `route_model` / `invoke_model` — that write structured fields into turn state: `scene_assessment`, `selected_responder_set`, `selected_scene_function`, `pacing_mode`, `silence_brevity_decision`, visibility/fallback shaping as applicable.

### 3.2 Fit to current stack

The runtime is already a `StateGraph` with `nodes_executed` / `node_outcomes`. Director steps remain **inspectable**, align with `_package_output`, and avoid a hidden “god object” outside the graph. Model invocation for **dramatic wording** remains in the **Proposal** seam.

### 3.3 Responsibility and god-object avoidance

- **Responsibility lives in the graph:** The normative locus of scene direction is the **set of director nodes** plus shared **stateless** helpers or **injected policy** callable from those nodes — not a monolithic class that overrides all layers.
- **One primary concern per node:** Each director node has one clear responsibility; shared utilities are stateless or injected policies only.
- **Optional Python helpers:** Pure Python orchestration **inside** a node is allowed; the **normative** observability and task cuts follow **graph node names** and execution traces.

### 3.4 Deterministic before proposal generation (binding)

The following are **selected and recorded before** the proposal-generation model call (deterministic policy and/or classifier nodes; not free-form model overwrite):

- `selected_responder_set`
- `selected_scene_function` (subject to §3.5 when multiple intentions compete)
- `pacing_mode` (vocabulary: `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §5)
- `silence_brevity_decision` (including `mode` from the same §5 mini-vocabulary)
- Visibility shaping and fallback-shaping inputs that constrain proposal/render

### 3.5 Single `selected_scene_function` under multiple intentions (binding)

When `interpreted_move` and `scene_assessment` support **more than one** plausible scene function (including when `pacing_mode` is `multi_pressure`), the runtime **must** emit exactly one `selected_scene_function` using this **priority rule**:

1. Consider the set of candidate scene functions that are **consistent** with `interpreted_move` and `scene_assessment` and the canonical scene-function vocabulary.
2. Rank candidates by the **strongest continuity obligation** they would create **if committed**, using this **continuity-class severity order** (highest first): `revealed_fact` > `dignity_injury` > `alliance_shift` > `blame_pressure` > `situational_pressure` > `repair_attempt` > `refused_cooperation` > `silent_carry`.
3. Choose the candidate tied at the **highest** implied obligation. If still tied, break ties by **lexicographically smallest** canonical scene-function label.

### 3.6 Model output boundaries (binding)

The proposal model may **elaborate dramatic expression** (dialogue, beats, proposed effects wording) but **must not silently replace** the following fields once set by director nodes:

- `selected_scene_function`
- `selected_responder_set`
- `pacing_mode`
- `silence_brevity_decision`

Changing any of these after director selection requires a **new explicit decision step** (another named graph node or validator-owned transition) that **re-documents** the change in `diagnostics_refs` or structured markers. **Silent overwrite from raw model output is forbidden.**

---

## 4. Starter canonical turn schema

Structure per FREEZE §11 (required field groups). The JSON skeleton is binding in shape; example values are illustrative but **must** use canonical vocabulary where vocabulary applies (`pacing_mode`, `silence_brevity_decision.mode`, `selected_scene_function`).

```json
{
  "turn_metadata": {
    "turn_id": "ex-turn-001",
    "session_id": "ex-session-aa",
    "trace_id": "ex-trace-001",
    "module_id": "god_of_carnage",
    "current_scene_id": "ex-scene-living-room"
  },
  "interpreted_move": {
    "player_intent": "challenge_anettes_account",
    "move_class": "confrontation"
  },
  "scene_assessment": {
    "scene_core": "mediation_gone_wrong",
    "pressure_state": "high_blame"
  },
  "selected_responder_set": [
    {
      "actor_id": "annette_reille",
      "reason": "primary_target_of_challenge"
    }
  ],
  "selected_scene_function": "escalate_conflict",
  "pacing_mode": "standard",
  "silence_brevity_decision": {
    "mode": "normal",
    "reason": "default_verbal_density"
  },
  "proposed_state_effects": [],
  "validation_outcome": {
    "status": "approved",
    "reason": "goc_default_validator_pass",
    "validator_lane": "goc_rule_engine_v1"
  },
  "committed_result": {
    "committed_effects": [],
    "commit_applied": false,
    "commit_lane": "goc_commit_seam_v1"
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

---

## 5. Field ownership table

Phase legend: **deterministic pre-model** · **model-proposed** · **validation-shaped** · **commit-owned** · **visible-output-only** · **diagnostics-only**

| Field / group | Owner | Phase | Optional? | Cardinality | Notes |
|---|---|---|---|---|---|
| turn_metadata | Runtime / session host | deterministic pre-model | required for a complete turn | 1 | Supports replay; `trace_id` aligns with `graph_diagnostics.repro_metadata` |
| interpreted_move | Interpretation (deterministic + optional classifying model) | deterministic pre-model → optional model-proposed labels | required | 1 | `move_class` should use slice vocabulary where possible |
| scene_assessment | Scene director + context aggregation | deterministic pre-model; contents partly from retrieval | required for target slice | 1 | See §5.1 minimal keys; built in `director_assess_scene` |
| selected_responder_set | Scene director policy | deterministic pre-model (target) | required for target slice | 0..n | Do not confuse with provider routing |
| selected_scene_function | Scene director policy | deterministic pre-model | required for target slice | 1 | Values: canonical scene functions (`VERTICAL_SLICE_CONTRACT_GOC.md` §5); §3.5 if multiple intentions |
| pacing_mode | Scene director policy | deterministic pre-model | required for target slice | 1 | Canonical pacing vocabulary (`VERTICAL_SLICE_CONTRACT_GOC.md` §5) |
| silence_brevity_decision | Scene director policy | deterministic pre-model | required for target slice | 1 | Canonical `mode` vocabulary (`VERTICAL_SLICE_CONTRACT_GOC.md` §5) |
| proposed_state_effects | Model (proposal seam) | model-proposed | required when model runs | 0..n | May be fed from `generation.metadata.structured_output` until normalized |
| validation_outcome | Rule validator (`validate_seam` / `run_validation_seam`) | validation-shaped | required (always set on graph exit) | 1 | No player text; `validator_lane` identifies engine |
| committed_result | Commit authority (`commit_seam` / `run_commit_seam`) | commit-owned | required when dramatic truth is claimed | 1 | Empty shell when validation not `approved`; `commit_lane` identifies engine |
| visible_output_bundle | Render / presentation | visible-output-only | required for player-visible turns | 1 | Must match `committed_result` + visibility |
| continuity_impacts | Commit authority + continuity service | commit-owned / carry-forward | optional until continuity active | 0..n | Entries use **continuity class** labels |
| visibility_class_markers | Scene director + validator | validation-shaped / commit-adjacent | optional default `truth_aligned` | 0..n | Labels: slice contract §5 |
| failure_markers | Validator / host | validation-shaped or diagnostics-only | optional | 0..n | Uses **failure class** labels |
| fallback_markers | Runtime graph | diagnostics-only + visible degradation | optional | 0..n | e.g. model fallback, missing adapter |
| diagnostics_refs | `package_output` / telemetry | diagnostics-only | recommended | 0..n | Graph name, version, node order, health; may carry `experiment_preview` per gate policy |

### 5.1 `scene_assessment` minimal schema (GoC, binding)

When `module_id == god_of_carnage` and canonical YAML resolved, `scene_assessment` **must** include at least:

| Key | Type | Purpose |
|---|---|---|
| `scene_core` | string | Stable scene identity anchor (e.g. `goc_scene:{scene_id}` or `goc_unresolved` if YAML missing). |
| `pressure_state` | string | Director pressure label (e.g. `high_blame`, `moderate_tension`). |
| `module_slice` | string | Module id for slice boundary checks. |

Optional keys (director enrichment, same object): `canonical_setting`, `narrative_scope`, `active_continuity_classes`, `continuity_carry_forward_note`, YAML guidance hints (`guidance_phase_key`, …), and `multi_pressure_resolution` after `director_select_dramatic_parameters`. Tests enforce the minimal triple on successful GoC paths.

---

## 6. Controlled vocabulary (turn reference)

Canonical values for **scene function**, **pacing**, **silence/brevity**, **continuity class**, **visibility class**, and **failure class** are identical to `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §5 — no divergent definitions.

Additional reference for this document:

| Semantic area | Canonical labels | Use in turn |
|---|---|---|
| Transition pattern | `hard`, `soft`, `carry_forward`, `diagnostics_only` | Pattern inventory §7; diagnostics — **not** interchangeable with scene function |
| Gate / review family (reference) | `slice_boundary`, `turn_integrity`, `dramatic_quality`, `diagnostic_sufficiency` | In `diagnostics_refs` or external reports — detail in `GATE_SCORING_POLICY_GOC.md` |

### 6.1 Terminology rule: scene function vs transition pattern (binding)

- **`selected_scene_function`** takes values **only** from the **scene function** vocabulary in `docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md` §5.
- **`transition_pattern`** takes values **only** from `{ hard, soft, carry_forward, diagnostics_only }`.
- **It is forbidden** to use a scene-function label as a transition pattern, or a transition-pattern label as a scene function. Tables and diagnostics must use **separate columns/fields** for each.

---

## 7. State transition doctrine and pattern inventory

FREEZE §14: distinguish **hard** / **soft** / **continuity carry-forward** / **diagnostics-only**; what may be committed per turn, what remains derived, what is observed only.

### 7.1 Doctrine (compact)

- **Hard transition:** Change to canonical state binding for later turns unless explicitly retracted — **only** through the **Commit** seam.
- **Soft marking:** Dramatic weight without full commit strength may flow into assessment or continuity per policy — **no** player-world fact without commit.
- **Continuity carry-forward:** Carry prioritized pressure lines in `continuity_impacts` with explicit **continuity class**.
- **Diagnostics-only:** No effect on committed truth; reconstruction, warnings, experimental tags.

### 7.2 Pattern inventory (binding, minimal)

| Trigger / event class | Selected scene function (if any) | Transition pattern | Consequence class | Commitment type | Diagnostics marker |
|---|---|---|---|---|---|
| Player move reads as escalation in existing pressure | `escalate_conflict` | `hard` | Increased `situational_pressure` | hard if commit confirms | `transition_pattern: hard` |
| Player move aims at damage control / apology | `repair_or_stabilize` | `soft` or `hard` | Partial de-escalation or repair attempt | soft or hard per validator | `transition_pattern: soft` or `hard` |
| Character reveals previously withheld information (if allowed) | `reveal_surface` | `hard` | New `revealed_fact` line | hard on commit | `transition_pattern: hard`; continuity: `revealed_fact` |
| Scope violation or unsafe out-of-world claim | (containment policy; scene function may be `scene_pivot` or withhold) | `diagnostics_only` | No truth extension | none | `failure_class: scope_breach` |
| Model fallback or graph error | — | `diagnostics_only` | No new committed effects without explicit policy | none | `execution_health` / `failure_class: graph_error` or `model_fallback` |
| Continuity conflict between proposal and session | — | `soft` or `diagnostics_only` | Rejected or reduced effects | none | `failure_class: continuity_inconsistency` |
| Silence / brevity as dramatic choice | (director sets `silence_brevity_decision`) | `soft` | Visibility/pacing only; no new facts | soft | `transition_pattern: soft` |

---

## 8. Mapping `RuntimeTurnState` → canonical model (informative)

`RuntimeTurnState` is the execution transport. After `package_output`, canonical dramatic fields listed in §4–§5 are populated on the same state object (no duplicate runtime truth). For operators and CI artifacts, **`build_operator_canonical_turn_record(state)`** (`ai_stack/goc_turn_seams.py`) returns a single JSON-serializable dict: turn metadata (including turn-basis host fields when supplied), `interpreted_move`, director fields, proposal/validation/commit/visible summaries, continuity, markers, `experiment_preview`, `transition_pattern`, `routing` (G2-aligned observation summary from the graph), **`dramatic_turn_record`** (roadmap §6.3 six-block projection; see §8.1), and a shallow `graph_diagnostics` summary (`graph_name`, `graph_version`, `nodes_executed`, `execution_health`, `fallback_path_taken`, `repro_complete`).

### 8.1 Roadmap G3 projection and `goc_uninitialized_field_envelope_v1`

`build_roadmap_dramatic_turn_record(state)` (invoked from `build_operator_canonical_turn_record`) assembles **Turn Basis**, **Decision Boundary Records**, **Routing Record**, **Retrieval Record**, **Realization Record**, and **Outcome Record** as a **read-only projection** from the same `RuntimeTurnState` — not a second writable truth surface.

**Uninitialized fields (single canonical envelope).** If a G3-projected field is genuinely not initialized when the projection runs, its JSON value **must** be exactly one object with **exactly these five keys** (no extras, no omissions):

| Key | Required value / constraint |
| --- | --- |
| `envelope_schema_id` | Literal string `goc_uninitialized_field_envelope_v1` |
| `initialization_state` | Literal string `uninitialized` |
| `initialization_issue_kind` | Literal string `pending_initialization` (means **initialization backlog**, not ambiguous semantics) |
| `setter_surface` | Exactly one of: `admin_control_plane`, `writers_room_authored`, `runtime_host_session` |
| `expected_source` | Non-empty string naming where the value must be supplied next (API parameter, session key, or route) |

**Meaning of `setter_surface`:**

- `admin_control_plane` — Administration Tool: operational setup, policy/profile, publication, or session configuration owned by admin workflows.
- `writers_room_authored` — Writers' Room: **authored / module-level** dramatic configuration only (not operational session counters).
- `runtime_host_session` — Runtime / host / session initialization: per-run execution values (e.g. `RuntimeTurnGraphExecutor.run(...)`, backend session store).

**Forbidden as substitutes for uninitialized state:** bare `null`, the string `unknown`, placeholder strings, fake defaults, or ad hoc “missing” objects with different keys.

**`turn_number` (operational).** Do not silently default `turn_number` to `1`. When the host supplies an integer via `RuntimeTurnGraphExecutor.run(..., turn_number=<int>)` (or equivalent session wiring), the projection emits that integer. When not supplied, the Turn Basis uses **`goc_uninitialized_field_envelope_v1`** with `setter_surface: runtime_host_session` (or `admin_control_plane` if session policy is admin-owned) and an `expected_source` that points to the host/session API. **Writers' Room is not** the setter for `turn_number`.

**Implementation helper:** `ai_stack/goc_field_initialization_envelope.py` (`goc_uninitialized_field_envelope`, `is_goc_uninitialized_field_envelope`) is the only supported constructor/validator for this envelope.

### 8.2 Retrieval record and governance summary (G5)

**Single provenance builder.** `ai_stack/retrieval_governance_summary.py` builds **`retrieval_governance_summary`** on the runtime `retrieval` dict (attached by the graph after context pack assembly). That summary is the **only** place that partitions hit rows into **`authored_truth_refs`** vs **`derived_artifact_refs`**, using the existing canonical `content_class` string on each row (`authored_module` vs all other `ContentClass` values in `ai_stack/rag.py`). Full hit payloads remain under `retrieval.sources`; compact ref entries in the two ref lists are projections of those rows only — not a parallel truth system.

**`dominant_visibility_class`** inside the summary is derived from `visibility_counts`: highest count wins; ties break by the declaration order of `SourceVisibilityClass` in `ai_stack/rag.py`; empty counts yield `None`.

**Dramatic turn projection.** `build_roadmap_dramatic_turn_record` copies from `retrieval.retrieval_governance_summary` into `retrieval_record` without re-classifying hits: `authored_truth_refs`, `derived_artifact_refs`, `retrieval_governance_result` (the full summary), and `retrieval_visibility_class` (= `dominant_visibility_class`). `retrieval_lane` continues to reflect the retrieval profile / route fields on `retrieval`.

**Trace and admin evidence.** `build_retrieval_trace` in `ai_stack/capabilities.py` **passthrough-embeds** the same `retrieval_governance_summary` dict under the key `retrieval_governance_summary` (no second derivation from `sources`). Backend session evidence aggregates that trace for **control-plane and diagnostic** use only — not semantic authority.

---

## 9. Cross-references

- Slice, Reality Anchor, bridge, vocabulary basis, assets, dry-run: **`docs/MVPs/MVP_VSL_And_GoC_Contracts/VERTICAL_SLICE_CONTRACT_GOC.md`**
- Gates, cadence, diagnostic modes, failure mapping, escalation, tabletop: **`docs/MVPs/MVP_VSL_And_GoC_Contracts/GATE_SCORING_POLICY_GOC.md`**
