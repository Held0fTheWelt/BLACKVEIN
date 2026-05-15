# Runtime State and Session Contracts

## Session State Schema (Binding)

Every session maintains explicit state with three visibility tiers:

### Tier 1: Canonical Session State (Authoritative)
```json
{
  "session": {
    "session_id": "uuid",
    "player_id": "uuid",
    "module_id": "god_of_carnage",
    "created_at": "ISO-8601",
    "status": "active|paused|ended",
    "content_snapshot": {
      "module_version": "hash",
      "published_at": "ISO-8601",
      "rules_version": "hash"
    }
  },
    "world_state": {
      "current_scene_id": "string",
      "environment_state": {
        "schema_version": "environment_state.v1",
        "current_room_id": "string|null",
        "previous_room_id": "string|null",
        "actor_locations": {"actor_id": "room_id"},
        "prop_states": {"object_id": {"status": "present|changed", "room_id": "string|null"}},
        "visible_room_ids": ["room_id"],
        "salient_object_ids": ["object_id"],
        "last_environment_events": []
      },
      "scene_state": {
        "scene_core": "string",
        "present_characters": ["actor_id"],
      "room_state": "string",
      "pressure_vectors": [
        {
          "type": "blame|dignity|alliance|exposure",
          "target_actor": "string",
          "magnitude": "low|medium|high",
          "sources": ["actor_id"]
        }
      ],
      "established_facts": [
        {
          "fact": "string",
          "established_by": "turn_id",
          "consequence_class": "revealed_fact|dignity_injury|alliance_shift|etc"
        }
      ]
    },
    "character_state": {
      "actor_id": {
        "current_pressure": "number",
        "injuries_and_wounds": ["string"],
        "active_alliances": ["actor_id"],
        "visible_emotional_state": "string",
        "internal_goals": ["string"],
        "turn_history": [
          {
            "turn_id": "string",
            "action_taken": "string",
            "consequence": "string"
          }
        ]
      }
    }
  },
  "turn_log": [
    {
      "turn_id": "uuid",
      "turn_number": "number",
      "player_action": "string",
      "committed_result": {...},
      "visible_output": {...},
      "timestamp": "ISO-8601"
    }
  ],
  "governance_state": {
    "last_operator_intervention": "turn_id|null",
    "validation_overrides": [
      {
        "turn_id": "uuid",
        "override_reason": "string",
        "override_type": "force_accept|force_reject|state_correction",
        "recorded_by": "operator_id"
      }
    ],
    "integrity_markers": ["string"]
  }
}
```

### Tier 2: Player-Visible Projection
The player sees a subset of canonical state:

```json
{
  "visible_state": {
    "scene_description": "string",
    "present_characters": [
      {
        "name": "string",
        "visible_emotional_state": "string",
        "visible_relationships": ["string"]
      }
    ],
    "recent_events": ["string (last 3 turns)"],
    "available_actions": ["string"],
    "consequence_feedback": {
      "this_turn": "string",
      "carry_forward": ["string (from previous turns)"]
    }
  }
}
```

**Authority:** Player-visible state is computed from canonical state; it is always a **projection**, never an authoritative source.

**Carry-forward:** Consequences from turns 1-3 must be visible in turn 4+ narrative; this proves continuity is working.

### Tier 3: Operator Diagnostics Payload
Operators see full truth for incident investigation:

```json
{
  "diagnostics": {
    "full_canonical_state": {...},
    "turn_trace": [
      {
        "turn_id": "uuid",
        "interpreted_move": {...},
        "scene_assessment": {...},
        "proposal_seam": {
          "model_prompt": "string (sanitized if needed)",
          "proposal_output": {...},
          "proposal_latency_ms": "number"
        },
        "validation_seam": {
          "rules_checked": ["string"],
          "outcome": "approved|rejected|waived",
          "validation_explanation": "string"
        },
        "commit_seam": {
          "committed_effects": [...],
          "state_delta": {...},
          "commit_timestamp": "ISO-8601"
        },
        "render_seam": {
          "visibility_class_markers": ["string"],
          "fallback_markers": ["string"],
          "render_latency_ms": "number"
        },
        "diagnostics_refs": ["string"]
      }
    ],
    "governance_log": [
      {
        "event": "state_correction|override|intervention",
        "recorded_by": "operator_id|system",
        "reason": "string",
        "timestamp": "ISO-8601",
        "evidence": "string"
      }
    ],
    "consistency_check_results": {
      "passed": ["check_name"],
      "failed": ["check_name"],
      "warnings": ["string"]
    }
  }
}
```

**Authority:** Diagnostics are read-only for operators; they may not modify world state directly (only via explicit override commands recorded in governance log).

---

## Turn Output Contract

Every turn produces this output structure:

```json
{
  "turn_id": "uuid",
  "turn_number": "number",
  "status": "committed|failed|degraded",
  "player_visible": {
    "narration": "string (GM description of what happened)",
    "dialogue": [
      {
        "actor": "string",
        "line": "string"
      }
    ],
    "state_update": {
      "scene_changes": ["string"],
      "character_changes": ["string"]
    },
    "consequence_preview": "string (what this means for next turn)"
  },
  "committed_effects": [
    {
      "effect_type": "pressure_increase|alliance_shift|fact_established|etc",
      "target": "actor_id|scene_id",
      "magnitude": "low|medium|high",
      "permanent": true|false,
      "evidence_turn_id": "uuid"
    }
  ],
  "diagnostics": {
    "latency_ms": "number",
    "model_calls": "number",
    "fallback_used": true|false,
    "seams_executed": ["proposal|validation|commit|render"],
    "seams_skipped": []
  }
}
```

**Commitment:** All data in `committed_effects` is authoritative; player-visible wording must trace to these effects.

**Diagnostics:** Latency, fallback usage, and seam execution are audited for performance and reliability tracking.

---

## Continuity Across Turns

### Consequence Carry-Forward (Mandatory)

A consequence established in turn N must be:

1. **Turn N+1:** Referenced in scene context (reminder to player and characters)
2. **Turn N+2-3:** Actively shaped by pressure vectors or character behavior
3. **Turn N+4+:** May fade into background (but not disappear) if new consequences dominate

**Validation:** Operator diagnostics show which established facts are active in current turn state.

### Character Voice Consistency

Characters must maintain consistent:

- Speech patterns (formal/informal, vocabulary)
- Emotional trajectories (pressure builds, recovers, etc.)
- Relationship dynamics (how they speak to each other)

**Runtime enforcement:** The live GoC path derives `CharacterVoiceProfileRecord` values from canonical `direction/character_voice.yaml` and exposes them to generation as profile guidance. During validation, `voice_consistency_validation.v1` checks structured `spoken_lines` against the active profiles and records a `voice_consistency` runtime aspect before commit. Policy-declared forbidden language markers can reject an otherwise approved turn through the `runtime_voice_consistency_v1` lane. The semantic classifier compares spoken lines against every active canonical profile dimension, records profile rankings and dimension winners, and surfaces ambiguity, mixed-signature, weak-alignment, and cross-actor findings. In `schema_plus_semantic` these are diagnostic warnings; in `strict_rule_engine`, high-confidence cross-actor or mixed voice drift can reject through `runtime_voice_consistency_v2`. Recovery keeps speaker ownership stable and rewrites only the offending wording.

**ADR-0039 boundary:** `dialogue_examples` in `character_voice.yaml` are authoring examples, not validation or test oracles. Runtime profiles omit them, and tests assert structured validator/aspect outcomes derived from the policy block and canonical profile dimensions rather than copied narrative prose.

### Callback Web / Pi17

The callback web is implemented as a bounded `callback_web_record.v1` index over committed session continuity. It connects later committed turns back to earlier committed turns through structured evidence: continuity classes, narrative threads, repeated scene anchors, and selected branch replay events.

The callback web is diagnostic evidence and prompt support, not canonical truth. It does not mutate story state, replace narrative threads, create memory outside the session, or adopt simulated branch state. The authoritative technical contract is [`docs/technical/runtime/callback_web_contract.md`](../../technical/runtime/callback_web_contract.md).

During a turn:

- World-Engine rebuilds the callback web from `StorySession.history`, `StorySession.narrative_threads`, and the durable branch timeline;
- the latest history row receives `callback_web_summary`, `callback_web_feedback`, and `callback_web_validation`;
- the next LangGraph turn receives bounded `prior_callback_web_state`;
- `turn_aspect_ledger.callback_web` records policy, selected edge, edge counts, validation status, and failure codes;
- internal operator endpoints expose the record, edge list, and rebuild operation.

**ADR-0039 boundary:** Tests derive expectations from schema constants, edge kinds, session/turn ids, branch lifecycle fields, normalized policy bounds, and stable ids. Generated narration, branch preview prose, and authored example paragraphs are not valid pass/fail oracles.

### Pacing Rhythm / Pi18

Pacing rhythm is implemented as the generic `pacing_rhythm` runtime aspect. It
is the cadence contract for a turn: selected cadence, tempo arc, response
shape, visible-block bounds, actor-turn expectations, pause obligations, and
forced-speech protection. It consumes `pacing_mode`,
`silence_brevity_decision`, `scene_energy_target`, prior rhythm feedback,
narrative-thread pressure, and callback-web feedback. It does not replace scene
energy and must not become a prose rhythm judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.pacing_rhythm` into `runtime_governance_policy.pacing_rhythm`;
- LangGraph derives `pacing_rhythm_state` and `pacing_rhythm_target` after scene energy;
- the dramatic generation packet receives the bounded target as structural guidance;
- validation checks structured output counts and writes `pacing_rhythm_validation`;
- recoverable failures feed self-correction with bounded pacing-rhythm failure codes;
- `turn_aspect_ledger.pacing_rhythm` records policy presence, selected target, actual counts, contract pass, and failure codes;
- World-Engine persists `pacing_rhythm_state`, `pacing_rhythm_target`, and `pacing_rhythm_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_pacing_rhythm_state`;
- Langfuse and MCP expose target/pass/density/pause evidence.

The committed rhythm state is bounded planner feedback, not a second canon
store. It may shape the next turn and operator diagnostics, but it does not
mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, ledger/MCP fields, and structured
visible-block or actor-turn counts. Generated narration, copied dialogue,
frontend card shape, and judge labels are never the pass/fail oracle.

### Social Pressure / Pi22

Social pressure is implemented as the generic `social_pressure` runtime aspect.
It is the continuous pressure contract for a turn: normalized score,
low/moderate/high band, trend, velocity, source evidence, and policy-threshold
validation. It consumes `scene_assessment`, `social_state_record`,
`scene_energy_target`, `pacing_rhythm_target`, prior planner truth, committed
narrative-thread pressure, and the latest committed `prior_social_pressure_state`.
It does not replace `social_risk_band` and must not become a prose intensity
judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.social_pressure` into `runtime_governance_policy.social_pressure`;
- LangGraph derives `social_pressure_state` and `social_pressure_target` after scene energy and pacing rhythm;
- the dramatic generation packet receives the bounded target as structural pressure guidance;
- validation checks schema and policy-threshold consistency and writes `social_pressure_validation`;
- `turn_aspect_ledger.social_pressure` records policy presence, selected target, actual metric, contract pass, and failure codes;
- World-Engine persists `social_pressure_state`, `social_pressure_target`, and `social_pressure_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_social_pressure_state`;
- Langfuse and MCP expose score, band, trend, pass/fail, boundedness, and failure-code evidence.

The committed pressure metric is bounded planner feedback, not a second canon
store. It may shape the next turn and operator diagnostics, but it does not
mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, ledger/MCP fields, and structured
source fields such as `thread_pressure_state`, `social_risk_band`, and
`thread_pressure_level`. Generated narration, copied dialogue, frontend card
shape, and judge labels are never the pass/fail oracle.

### Improvisational Coherence / Pi24

Improvisational coherence is implemented as the generic
`improvisational_coherence` runtime aspect. It is the bounded acceptance
contract for the current player contribution: contribution id/kind, selected
acceptance mode, allowed advance classes, required scene anchors, visible actor
context, and playable boundary-reason requirements. It consumes interpreted
input, semantic move records, scene-plan fields, selected responders,
`scene_energy_target`, `pacing_rhythm_target`, and normalized module policy. It
does not replace player agency, committed truth, social pressure, or visible
narration.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.improvisational_coherence` into `runtime_governance_policy.improvisational_coherence`;
- LangGraph derives `improvisational_coherence_target` after social pressure and before information disclosure;
- the dramatic generation packet receives only bounded structured context, not raw player text;
- structured output may emit `improvisational_coherence_events` with contribution id, acceptance mode, advance class, anchor refs, and boundary reason;
- validation checks acknowledgement, allowed mode/class, scene-anchor preservation, committed-truth safety, forced-player-revision flags, and playable boundary reasons;
- recoverable failures feed self-correction with bounded `improv_*` failure codes;
- `turn_aspect_ledger.improvisational_coherence` records policy presence, selected contribution target, actual event evidence, contract pass, and failure codes;
- Langfuse and MCP expose policy, target, acknowledgement, anchor, boundary, pass/fail, and repair evidence.

The aspect is bounded planner/generation governance, not canon. It may shape
the current response and retry feedback, but it does not mutate story truth
outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, ledger/MCP fields, and structured
`improvisational_coherence_events`. Generated narration, copied dialogue,
frontend card shape, and judge labels are never the pass/fail oracle.

### Subtext Interpretation / Pi19

Subtext is implemented as a bounded `SubtextRecord` nested under `SemanticMoveRecord.subtext`. It is a diagnostic surface for what a player move appears to be doing and which scene-pressure function it may carry; it is not a fact store, hidden-state reveal, or free-form motive inference.

The authoritative value source for GoC is `content/modules/god_of_carnage/direction/subtext_policy.yaml`. Runtime code builds records through `ai_stack/goc_subtext_policy.py` and validates labels against the contract constants in `ai_stack/semantic_move_contract.py`.

During a turn:

- semantic interpretation emits `surface_mode`, `hidden_intent_hypothesis`, `subtext_function`, `sincerity_band`, evidence codes, and policy provenance;
- the scene director can use `subtext_function` for responder/pacing pressure while preserving commit authority;
- the dramatic generation packet includes `subtext_interpretation`;
- path summaries, Langfuse spans/scores, inspector projections, and operator history expose the same fields, including `subtext_contract_pass`.

**ADR-0039 boundary:** Tests derive expected subtext labels from `subtext_policy.yaml` or exported contract sets. Generated narration, copied dialogue, and free-form motive prose are never the pass/fail oracle.

### Information Disclosure / Mystery Rationing

Mystery rationing is implemented as the generic `information_disclosure` runtime aspect. Content modules declare bounded disclosure units in `information_disclosure_policy.yaml`; runtime code does not branch on `pi_20`, Table-B labels, or module-specific prose.

During a turn, LangGraph derives an `InformationDisclosureTarget` from the current scene function, semantic move, pacing mode, prior continuity classes, and module policy. The target records selected unit ids, allowed unit ids, withheld unit ids, forbidden unit ids, disclosure mode, structured-event requirement, and per-turn visible-unit budget.

During validation, `InformationDisclosureValidation` reads structured `disclosure_events` from model output when present. It accepts only selected unit ids and can report contract failures such as missing required event, over-budget reveal, forbidden unit, forbidden stage, or forbidden mode. A recovery/reject policy may turn those failures into a recoverable validation rejection before commit.

**ADR-0039 boundary:** Tests derive positive and negative cases from normalized policy structures and assert schema fields, failure codes, ledger projection, Langfuse/MCP score fields, and anti-hardcoding gate behavior. Generated narrative wording is never the pass/fail oracle.

### Consequence Cascade / Pi21

The consequence cascade is implemented as a bounded `consequence_cascade_record.v1` graph over committed session truth. It connects consequence atoms across committed turns through continuity classes, narrative threads, resolution markers, and realized branch selections.

The consequence cascade is committed-state feedback and prompt support, not canonical truth. It does not mutate story state, replace narrative threads, create cross-session memory, or adopt simulated branch state. The authoritative technical contract is [`docs/technical/runtime/consequence_cascade_contract.md`](../../technical/runtime/consequence_cascade_contract.md).

During a turn:

- World-Engine rebuilds the cascade from `StorySession.history`, `StorySession.narrative_threads`, and the durable branch timeline;
- the latest history row receives `consequence_cascade_summary`, `consequence_cascade_feedback`, and `consequence_cascade_validation`;
- the next LangGraph turn receives bounded `prior_consequence_cascade_state`;
- `turn_aspect_ledger.consequence_cascade` records policy, selected consequence ids/classes/statuses, atom/edge counts, validation status, and failure codes;
- internal operator endpoints expose the record, edge list, and rebuild operation.

**ADR-0039 boundary:** Tests derive expectations from schema constants, edge kinds, status vocabularies, session/turn ids, branch lifecycle fields, normalized policy bounds, authority flags, and stable ids. Generated narration, branch preview prose, and authored example paragraphs are not valid pass/fail oracles.

### Environmental Story / Pi15

Environmental story is implemented as durable, bounded `EnvironmentState`, not as
free-form descriptive memory. `ai_stack/environment_state_contracts.py` builds an
`EnvironmentModel` from canonical module content and normalizes
`StorySession.environment_state` for persistence.

The authoritative fields are:

- `current_room_id` / `previous_room_id`
- `actor_locations`
- `prop_states`
- `visible_room_ids`
- `salient_object_ids`
- `last_environment_events`

Lifecycle:

1. Session creation initializes environment state from canonical layout/object
   content and actor-lane context.
2. LangGraph receives the state and uses it to derive action-resolution local
   context plus compact generation context.
3. The commit seam mutates environment state only after approved committed
   movement or admitted object interaction.
4. Render support and shell/get-state projections expose the same committed
   state through `environment_render_context.v1` and `environment_state_now`.

**Authority boundary:** Narration, RAG, and model proposals may describe or stage
environment details, but they do not create persistent environment truth. Durable
state must trace to canonical content plus committed/admitted actions.

**ADR-0039 boundary:** Tests load or derive room/object expectations from
canonical content and assert schema/state transitions, render markers, and shell
projection fields. They do not use generated narrator prose as the correctness
oracle.

### Scene Identity Preservation

Every scene must maintain:

- Core identity (what type of scene is this; does it feel coherent)
- Physical continuity (described space must be consistent)
- Pressure alignment (dominant pressure vector must be visible)

**Validation:** Scene assessment stage checks identity; operator can see if scene_core changed unexpectedly.

---

## State Consistency Checks

### Automated Checks (Run Before Render)

Before turn is shown to player:

1. **Fact consistency** — No contradiction between established facts
2. **Character state consistency** — Pressure, injuries, relationships are coherent
3. **Scene state consistency** — Present characters are alive and accounted for
4. **Authority consistency** — All commitments trace to canonical state

**Failure:** If checks fail, turn is marked `degraded`; operator is alerted; fallback message is shown to player.

### Operator Verification (On-Demand)

Operators can run extended checks:

1. **Deep continuity audit** — Trace all consequences from turn 1 through current turn
2. **Pressure trajectory audit** — Verify pressure vectors are building/resolving as expected
3. **Evidence binding audit** — All factual claims trace to committed effects or published contracts
4. **Narrative coherence review** — Read full turn sequence; assess if dramatic arc is coherent

**Result:** Audit report with findings and recommended corrections (if any).

---

## Session Lifecycle

### Birth
```
User requests session
  ↓
Backend checks published content
  ↓
Content snapshot is locked into session
  ↓
world-engine initializes with starting scene
  ↓
Session is ready for player
```

### Execution (Repeated)
```
Player input
  ↓
Turn execution (seams: proposal → validation → commit → render)
  ↓
Turn is added to turn_log
  ↓
World state is updated
  ↓
Output is shown to player
```

### End States
- **Player ends session** → Session marked `ended`; turn log is preserved; diagnostics are archived
- **Operator pauses session** → Session marked `paused`; can be resumed later with same state
- **Session crashes** → Session marked `error`; operator can inspect turn_trace to debug
- **Validation failure cascade** → Session may degrade to fallback mode; operator alerted

---

## Acceptance Criteria

Session state is correct when:

1. **Canonical state is consistent** → Fact/pressure/character state have no contradictions
2. **Tier separation is enforced** → Player sees only projected state; operators see diagnostics
3. **Turn log is complete** → Every turn from player input to rendered output is recorded
4. **Carry-forward is working** → Consequences from turn N are visible in turn N+1 at minimum
5. **Consistency checks pass** → Automated checks find no contradictions
6. **Governance log is audit-trail** → Every operator intervention is recorded with reason and evidence
7. **Session snapshot is immutable** → Content changes mid-session do not affect this session
8. **Environment state is bound** → Current room, actor locations, prop states, render support, and shell projection all derive from the same committed `environment_state`

---

## Non-Compliance Degradation

If state consistency fails:

- **Fact contradiction detected** → Turn is marked `degraded`; operator is alerted; fallback message is shown
- **Carry-forward missing** → Operator audit shows which consequences disappeared; recommended fix is provided
- **Character voice inconsistency** → Operator can see in turn trace and request regeneration
- **Scene identity lost** → Operator can see scene_core changed; can rollback or manually correct

All degradation is audited and recoverable.
