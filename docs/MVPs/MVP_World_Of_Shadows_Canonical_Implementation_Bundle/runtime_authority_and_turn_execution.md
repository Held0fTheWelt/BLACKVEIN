# Runtime Authority and Turn Execution

## Authority Ownership Boundaries

The MVP implements a three-stage authority model:

### 1. Authored Authority
- **Owner:** YAML module tree at `content/modules/god_of_carnage/`
- **Responsibility:** Canonical source for GoC slice content, character roster, scene structure, and dramatic constraints
- **Governance:** Writers room artifacts and builtins are secondary; YAML wins in case of conflict
- **Entry point:** `content/backend_loader.py` loads YAML modules as the primary source

### 2. Published Authority
- **Owner:** Backend publish/activation API at `backend/api/publish.py`
- **Responsibility:** Marks content ready for runtime consumption; activation boundary is explicit
- **Governance:** No content may be used at runtime without explicit publish record
- **Implementation:** Session creation queries published-only content; non-published content is invisible to runtime

### 3. Runtime Authority
- **Owner:** `world-engine/app/story_runtime_shell.py` and turn execution graph
- **Responsibility:** Owns committed dramatic facts; no parallel truth surfaces
- **Governance:** Only committed results (from `commit_seam`) become canonical truth; proposals are candidates only
- **Projection:** Player-visible output is computed from committed truth, not from proposals

### Authority Drift Prevention
- **Single writer per seam:** Each seam (proposal, validation, commit, render) has one owning stage; no ad-hoc shortcuts
- **Governance closure:** Missing stage visibility or silent seam-skipping is a governance defect, not a feature
- **Auditability:** Every turn records which seams executed and which were skipped; diagnostics surface this explicitly

---

## Turn Execution Lifecycle

The complete turn flow from player input to rendered output:

### Stage 1: Input Interpretation
- **Location:** `world-engine/app/interpret_input.py`
- **Input:** Player text, current scene ID, session state
- **Output:** `interpreted_move` (move class, player intent, scene reference)
- **Governance:** Input is interpreted deterministically; no model calls yet

### Stage 2: Context Retrieval
- **Location:** `world-engine/app/retrieve_context.py`
- **Input:** `interpreted_move`, session/scene state
- **Output:** Retrieved scene context, character profiles, applicable rules
- **Governance:** Retrieval is bounded by content authority (published content only)

### Stage 3: Scene Assessment
- **Location:** `world-engine/app/scene_assessment.py`
- **Input:** Interpreted move, retrieved context, current scene state
- **Output:** `scene_assessment` (scene core, pressure state, applicable rules)
- **Governance:** Deterministic policy + rule engine; no proposal generation yet

### Stage 4: Responder Selection
- **Location:** `world-engine/app/select_responders.py`
- **Input:** `scene_assessment`, interpreted move, character relationships
- **Output:** `selected_responder_set` (which characters respond, why)
- **Governance:** Deterministic policy based on dramatic continuity and scene rules

### Stage 5: Scene Function Selection
- **Location:** `world-engine/app/select_scene_function.py`
- **Input:** Interpreted move, scene assessment, responder set
- **Output:** `selected_scene_function` (escalate_conflict, offer_repair, reveal_fact, etc.)
- **Governance:** Priority rule applies when multiple scene functions are valid (see CANONICAL_TURN_CONTRACT_GOC.md §3.5)

### Stage 6: Pacing and Visibility Shaping
- **Location:** `world-engine/app/shape_pacing_and_visibility.py`
- **Input:** Scene function, turn history, character pressure state
- **Output:** `pacing_mode`, `silence_brevity_decision`, visibility constraints
- **Governance:** Deterministic policy; shapes what proposal generation may express
- **Π14 negative space:** `silence_brevity_decision` carries `silence_negative_space.v1` when silence, withheld response, or non-lexical input is the dramatic move. This is soft shaping only: it may require a visible beat and block forced player speech, but it does not commit new truth.

---

## The Four Explicit Seams

### Seam 1: Proposal Seam (Candidate Only)
- **Location:** `world-engine/app/invoke_model.py` → `ai_stack/story_runtime/turn/god_of_carnage_turn_seams.py`
- **What happens:** Model generates candidate dramatic output (dialogue, effects wording, narrative beats)
- **Output:** `proposed_state_effects` (list of candidate effects), `generation` (text)
- **Authority:** Proposal is a **candidate only**; it does not authorize world truth
- **Constraints:** Model must respect `selected_responder_set`, `selected_scene_function`, `pacing_mode` set by director stages
- **Failure modes:** Proposal may be malformed, incoherent, or off-character; validation seam catches these
- **Code path:** `ai_stack/model_invoke.py` calls LLM with bounded prompt; `proposal_normalize.py` cleans up output

**Key rule:** No player-visible factual claim may be made from proposal alone. Proposal is staging only.

### Seam 2: Validation Seam (Policy + Rules)
- **Location:** `world-engine/app/validate_seam.py` and `backend/rules/goc_rule_engine.py`
- **What happens:** Proposed effects are checked against scene rules, character constraints, and governance policies
- **Input:** `proposed_state_effects`, validation context (scene state, rules, policies)
- **Output:** `validation_outcome` (approved / rejected / waived)
- **Authority:** Validation does **not** alter world truth; it only shapes proposal acceptance
- **Governance:** Validation is deterministic; no LLM calls; rule engine is authoritative
- **Failure modes:** If proposal violates rules, `validation_outcome` is `rejected`; commit seam will refuse the effects
- **Code path:** `goc_rule_engine.py` runs policy checks; returns `approved` or `rejected`

**Key rule:** Validation rejects invalid proposals but does not commit anything. Validation is a gate, not an authority transfer.

### Seam 3: Commit Seam (Sole Truth Authority)
- **Location:** `world-engine/app/commit_seam.py`
- **What happens:** Validated effects are committed to canonical world state; this is the **only** place where truth is written
- **Input:** `validation_outcome`, `proposed_state_effects` (if approved)
- **Output:** `committed_result` (committed effects, commit applied flag)
- **Authority:** **Sole source** for "what holds in the world" for dramatic facts; no parallel truth surfaces
- **Governance:** Commit is conditional (only happens if validation is `approved`); rejections leave state unchanged
- **Failure modes:** If proposal is rejected, commit does nothing; runtime state persists unchanged
- **Code path:** `world_state_store.py` applies `committed_result` to session state; this write is audited

**Key rule:** Only committed effects become canonical world truth. All player-visible factual claims must trace to committed results.

### Seam 4: Visible Render Seam (Projection Only)
- **Location:** `world-engine/app/render_visible.py` and `frontend/api/package_for_player.py`
- **What happens:** Committed truth is projected to player-visible output
- **Input:** `committed_result`, `generation` (model text), visibility markers
- **Output:** `visible_output_bundle` (narration, dialogue, scene state projection)
- **Authority:** Render **does not alter truth**; it only shapes what the player sees
- **Governance:** Visibility rules determine what parts of truth are projected vs. hidden
- **Visibility classes:**
  - `factual` (committed truth, must be visible)
  - `implied` (committed truth, conveyed indirectly)
  - `ambiguous` (non-factual staging allowed; explicitly permitted by visibility rules)
  - `hidden` (truth exists but is player-invisible)
- **Failure modes:** If committed state is incomplete or internally inconsistent, render may fail gracefully
- **Code path:** `frontend/app/routes.py` receives visible bundle; renders to player

**Key rule:** Player-visible factual statements must trace to `committed_result`. Non-factual staging is only allowed where visibility rules explicitly permit it.

---

## Seam Dependency Chain

```
interpreted_move
    ↓
scene_assessment
    ↓
selected_responder_set + selected_scene_function + pacing_mode
    ↓
[PROPOSAL SEAM: model generates candidate effects]
    ↓
[VALIDATION SEAM: rules check proposed effects]
    ↓
[COMMIT SEAM: approved effects become truth]
    ↓
[RENDER SEAM: truth is projected to player output]
```

No seam may be skipped without an explicit marker in `diagnostics_refs`. Skipping a seam is a governance defect.

---

## Turn State Schema (Binding)

Every turn maintains this structure:

```json
{
  "turn_metadata": {
    "turn_id": "string (unique)",
    "session_id": "string (session owner)",
    "trace_id": "string (for auditing)",
    "module_id": "god_of_carnage"
  },
  "interpreted_move": {
    "player_intent": "string",
    "move_class": "string (confrontation|repair|question|etc)"
  },
  "scene_assessment": {
    "scene_core": "string (scene identity)",
    "pressure_state": "string (high_blame|escalating|etc)"
  },
  "selected_responder_set": [
    {
      "actor_id": "string",
      "reason": "string (why this character responds)"
    }
  ],
  "selected_scene_function": "string (establish_pressure|escalate_conflict|probe_motive|repair_or_stabilize|withhold_or_evade|reveal_surface|redirect_blame|scene_pivot)",
  "pacing_mode": "standard|compressed|thin_edge|containment|multi_pressure",
  "silence_brevity_decision": {
    "contract": "silence_negative_space.v1",
    "mode": "normal|brief|withheld|expanded",
    "reason": "string",
    "source": "default|semantic_move|interpreted_input|raw_text|slice_boundary|non_goc_slice|sparse_fragment|narrative_thread|player_request",
    "silence_kind": "none|empty_input|non_lexical_input|explicit_silence|withheld_answer|awkward_pause|defensive_pause|discomfort_pause|refusal_pressure|provocation_pause|charged_after_tension|player_requested_brevity|boundary_containment|thread_pressure|thread_interpretation_pressure",
    "dramatic_function": "not_applicable|default_verbal_density|withhold_response|carry_tension|compress_response|maintain_pressure|escalate_pressure|contain_boundary",
    "pressure_basis": "string|null",
    "duration_hint": "none|beat|short|held",
    "requires_visible_beat": true,
    "blocks_forced_speech": false,
    "semantic_move_type": "silence_withdrawal|null",
    "interpreter_signal": "string|null"
  },
  "proposed_state_effects": [],
  "validation_outcome": {
    "status": "approved|rejected|waived",
    "reason": "string",
    "validator_lane": "goc_rule_engine_v1"
  },
  "committed_result": {
    "committed_effects": [],
    "commit_applied": true|false,
    "commit_lane": "goc_commit_seam_v1"
  },
  "visible_output_bundle": {
    "gm_narration": [],
    "spoken_lines": []
  },
  "diagnostics_refs": []
}
```

---

## Acceptance Criteria

A turn execution is valid when:

1. **All director stages executed** (`scene_assessment`, `responder_set`, `scene_function` are populated)
2. **Proposal is traceable** (if model is called, `proposed_state_effects` and `generation` are recorded)
3. **Validation outcome is recorded** (every turn has `validation_outcome`, even if `waived`)
4. **Commit decision is explicit** (`committed_result.commit_applied` is true or false)
5. **Render output is auditable** (if turn reaches player, `visible_output_bundle` is recorded)
6. **No player-visible factual claim bypasses committed truth** (all factual statements trace to `committed_result` or are explicitly marked non-factual)
7. **Negative space stays structured** (`silence_brevity_decision.contract` is `silence_negative_space.v1` and active silence sets reason/flags rather than relying on generated prose)
8. **Diagnostics are complete** (if seam behavior was exceptional, `diagnostics_refs` records why)

---

## Non-Compliance Degradation

If a turn fails at any seam:

- **Proposal fails:** Fallback proposal is generated or turn is cancelled; validation outcome is `rejected`
- **Validation fails:** Commit does not happen; scene state persists; fallback message is rendered explaining why move failed
- **Commit fails:** Player is notified that move could not be applied; scene state persists; operator is alerted
- **Render fails:** Fallback generic message is shown; operator is alerted; full turn trace is available for debugging

All degradation is governed (not silent). Operators can inspect what happened via diagnostics.
