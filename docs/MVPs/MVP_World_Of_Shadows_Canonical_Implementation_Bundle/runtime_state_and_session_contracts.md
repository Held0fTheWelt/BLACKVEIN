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

### Tonal Consistency / Pi35

Tonal consistency is represented by the generic `tonal_consistency` runtime
aspect. It is the bounded tone-drift evidence surface for a turn: selected tone
profile, target and required tone-dimension ids, allowed registers, forbidden
genre labels, forbidden marker classes, structured classification evidence, and
diagnostic/recover/reject behavior.

The authoritative technical contract is
[`docs/technical/runtime/tonal_consistency_contract.md`](../../technical/runtime/tonal_consistency_contract.md).

Current status: local/partial. The contract, policy normalization,
RuntimeAspectLedger projection, and MCP matrix extraction exist. The
authoritative live LangGraph path does not yet derive/validate the aspect for
commit, and the GoC policy uses `default_drift_behavior=diagnostic`. Do not use
this surface to claim live tonal drift enforcement, staging proof, or
readiness promotion.

During a turn when the aspect is used:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.tonal_consistency`
  into `runtime_governance_policy.tonal_consistency`;
- `derive_tonal_consistency` selects a profile from scene function and adjacent
  structured state;
- the compact model context exposes profile id, dimension ids, allowed
  registers, marker classes, scene function, and pressure band without prose
  examples;
- validation consumes structured `tonal_consistency_classification` plus
  policy-declared marker classes;
- `turn_aspect_ledger.tonal_consistency` records policy presence, target
  selection, classification evidence, contract pass/fail, and failure codes;
- MCP exposes `tonal_consistency_*` fields for local diagnostics.

**ADR-0039 boundary:** Tests derive expectations from normalized policy,
schema constants, structured classification rows, marker-class counts, ledger
projection, and MCP fields. Generated narration, copied dialogue, and
LLM-as-a-Judge tone categories are not pass/fail oracles.

### Callback Web / Pi17

The callback web is implemented as a bounded `callback_web_record.v1` index over committed session continuity. It connects later committed turns back to earlier committed turns through structured evidence: continuity classes, narrative threads, repeated scene anchors, and selected branch replay events.

The callback web is diagnostic evidence and prompt support, not canonical truth. It does not mutate story state, replace narrative threads, create memory outside the session, or adopt simulated branch state. The authoritative technical contract is [`docs/technical/runtime/callback_web_contract.md`](../../technical/runtime/callback_web_contract.md).

During a turn:

- World-Engine rebuilds the callback web from committed-truth rows in `StorySession.history`, `StorySession.narrative_threads`, and the durable branch timeline;
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

### Temporal Control / Pi28

Temporal control is implemented as the generic `temporal_control` runtime
aspect. It is the bounded time-operation contract for a turn: selected
operation, committed source turn refs, committed consequence refs, elapsed-turn
bounds, structured realization evidence, and history-safety checks. It consumes
`scene_plan_record`, `scene_energy_target`, `pacing_rhythm_target`,
`semantic_move_record`, callback-web feedback, consequence-cascade feedback,
prior temporal-control state, and normalized module policy. It does not replace
branching, memory, canonical commit, or visible narration, and it must not
become a prose chronology judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.temporal_control` into `runtime_governance_policy.temporal_control`;
- LangGraph derives `temporal_control_state` and `temporal_control_target` after pacing rhythm;
- the dramatic generation packet receives only the selected operation, bounds, and committed refs;
- structured output may emit `temporal_control_events` with `operation`, `source_turn_ids`, `source_consequence_ids`, and `elapsed_turns`;
- validation checks selected operation, allowed operations, committed source refs, elapsed-turn bounds, history-rewrite flags, branch-state adoption flags, and required-event presence;
- recoverable failures feed self-correction with bounded `temporal_control_*` failure codes;
- `turn_aspect_ledger.temporal_control` records policy presence, selected operation, selected/realized refs, event count, contract pass, and failure codes;
- World-Engine persists `temporal_control_state`, `temporal_control_target`, and `temporal_control_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_temporal_control_state`;
- Langfuse and MCP expose policy, target, operation, selected refs, event count, source-bounds, history-rewrite absence, pass/fail, and failure-code evidence.

The committed temporal-control state is bounded planner feedback, not a second
canon store. It may shape the next turn and operator diagnostics, but it does
not mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, structured committed refs,
planner-truth rehydration, ledger/MCP fields, and structured
`temporal_control_events`. Generated narration, copied dialogue, branch preview
text, frontend card shape, judge labels, and hand-written flashback examples are
never the pass/fail oracle.

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

### Expectation Variation / Pi29

Expectation variation is implemented as the generic `expectation_variation`
runtime aspect. It is the bounded surprise-budget contract for a turn: selected
variation ids, variation types, required setup refs, per-turn budget, cooldown
state, and structured realization evidence. It consumes selected setup evidence
from adjacent runtime aspects such as information disclosure, dramatic irony,
social pressure, relationship state, sensory context, callback web, consequence
cascade, and prior committed expectation-variation state. It does not replace
committed truth, hidden-fact safety, relationship state, or visible narration,
and it must not become a prose surprise judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.expectation_variation` into `runtime_governance_policy.expectation_variation`;
- LangGraph derives `expectation_variation_state` and `expectation_variation_target` before relationship-state derivation;
- the dramatic generation packet receives only selected variation ids, selected variation types, budget, and setup refs;
- structured output may emit `expectation_variation_events` with `variation_id`, `variation_type`, and `source_refs`;
- validation checks selected ids, allowed types, setup-ref support, budget, cooldown, and required-event presence;
- recoverable failures feed self-correction with bounded `expectation_variation_*` failure codes;
- `turn_aspect_ledger.expectation_variation` records policy presence, selected/realized ids and types, budget, contract pass, and failure codes;
- World-Engine persists `expectation_variation_state`, `expectation_variation_target`, and `expectation_variation_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_expectation_variation_state`;
- Langfuse and MCP expose policy, target, selected ids/types, realized ids/types, budget, setup support, pass/fail, and failure-code evidence.

The committed expectation-variation state is bounded planner feedback, not a
second canon store. It may shape the next turn and operator diagnostics, but it
does not mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, structured setup refs,
planner-truth rehydration, ledger/MCP fields, and structured
`expectation_variation_events`. Generated narration, copied dialogue, frontend
card shape, judge labels, and hand-written surprise beats are never the
pass/fail oracle.

### Narrative Momentum / Pi31

Narrative momentum is implemented as the generic `narrative_momentum` runtime
aspect. It is the bounded momentum state-machine contract for a turn: current
state/score, target state/score, trend, velocity, allowed next states,
forward-motion requirement, release permission, structured progress events,
source refs, and stall budget. It consumes `scene_plan_record`,
`scene_energy_target`, `pacing_rhythm_target`, `social_pressure_target`,
`expectation_variation_target`, semantic move evidence, prior committed
momentum state, and normalized module policy. It does not replace scene energy,
pacing rhythm, social pressure, relationship state, committed truth, or visible
narration, and it must not become a prose intensity judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.narrative_momentum` into `runtime_governance_policy.narrative_momentum`;
- LangGraph derives `narrative_momentum_state` and `narrative_momentum_target` after expectation variation and before relationship-state derivation;
- the dramatic generation packet receives only bounded state-machine fields, progress requirements, allowed next states, release permission, and selected source refs;
- structured output may emit `narrative_momentum_events`;
- validation checks target presence, allowed transition, required progress-event count, max velocity delta, stall budget, and source-ref validity;
- recoverable failures feed self-correction with bounded `narrative_momentum_*` failure codes;
- `turn_aspect_ledger.narrative_momentum` records policy presence, current/target state and score, transition allowance, event presence, stall-budget status, contract pass, and failure codes;
- World-Engine persists `narrative_momentum_state`, `narrative_momentum_target`, and `narrative_momentum_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_narrative_momentum_state`;
- Langfuse and MCP expose policy, selected target, current/target score, trend, velocity, transition/progress/stall evidence, pass/fail, and failure-code fields.

The committed momentum state is bounded planner feedback, not a second canon
store. It may shape the next turn and operator diagnostics, but it does not
mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, structured source refs,
state-machine transitions, planner-truth rehydration, ledger/MCP fields, and
structured `narrative_momentum_events`. Generated narration, copied dialogue,
frontend card shape, judge labels, and hand-written dramatic-momentum beats are
never the pass/fail oracle.

### Relationship State / Pi27

Relationship state is implemented as the generic `relationship_state` runtime
aspect backed by the `relationship_state_machine` module policy. It is a
durable, bounded state machine for relationship dynamics: pair scores, axis
aggregates, transition events, target ids, pressure band, and structured
validation. It consumes canonical relationship definitions, structured social
state, social pressure, NPC initiative-pressure edges, continuity evidence, and
the latest committed `prior_relationship_state_record`. It does not replace
canonical relationship content, actor-lane safety, committed truth, or visible
narration, and it must not become a prose psychology judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.relationship_state_machine` into `runtime_governance_policy.relationship_state_machine`;
- LangGraph derives `relationship_state_record` and `relationship_dynamics_target` after expectation variation and before opt-in meta-narrative awareness / context synthesis;
- the dramatic generation packet receives bounded durable `relationship_state` plus the existing `relationship_dynamics_context`;
- structured output may emit `relationship_dynamics_events` with actor ids, relationship ids, axis ids, and transition codes;
- validation checks schema bounds, selected target ids, allowed transition codes, and actor-lane compatibility;
- recoverable failures feed self-correction with bounded `relationship_state_*` failure codes;
- `turn_aspect_ledger.relationship_state` records policy presence, target ids, pressure band, pair/axis/event counts, contract pass, and failure codes;
- World-Engine persists `relationship_state_record`, `relationship_dynamics_target`, and `relationship_state_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_relationship_state_record`;
- Langfuse and MCP expose target presence, pressure band, pair count, transition-event count, pass/fail, and failure-code evidence.

The committed relationship state is bounded planner feedback, not a second
canon store. It may shape the next turn and operator diagnostics, but it does
not mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, canonical relationship content,
structured social-state fields, NPC initiative graph edges, planner-truth
rehydration, ledger/MCP fields, and structured
`relationship_dynamics_events`. Generated narration, copied dialogue, frontend
card shape, judge labels, and hand-written GoC relationship truth are never the
pass/fail oracle.

### Symbolic Object Resonance / Pi33

Symbolic object resonance is implemented as the generic
`symbolic_object_resonance` runtime aspect. It is the bounded symbolic-object
contract for a turn: selected canonical object ids, stable symbol ids,
resonance roles, required source refs, per-turn budget, prior resonance
feedback, and structured realization evidence. It consumes canonical object
content, environment state, player action focus, adjacent runtime targets such
as sensory context, social pressure, relationship state and expectation
variation, callback/consequence feedback, and prior committed
symbolic-object state. It does not replace environment state, committed truth,
or visible narration, and it must not become a prose symbolism judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.symbolic_object_resonance` into `runtime_governance_policy.symbolic_object_resonance`;
- LangGraph derives `symbolic_object_resonance_state` and `symbolic_object_resonance_target` after relationship-state derivation;
- the dramatic generation packet receives only selected object ids, symbol ids, resonance roles, budget, and source refs;
- structured output may emit `symbolic_object_resonance_events` with `object_id`, `symbol_id`, `resonance_role`, and `source_refs`;
- validation checks selected object ids, selected symbol ids, allowed roles, source-ref consistency, event presence, and budget;
- recoverable failures feed self-correction with bounded `symbolic_object_resonance_*` failure codes;
- `turn_aspect_ledger.symbolic_object_resonance` records policy presence, selected/realized object ids, symbol ids, roles, budget, contract pass, and failure codes;
- World-Engine persists `symbolic_object_resonance_state`, `symbolic_object_resonance_target`, and `symbolic_object_resonance_validation` in planner truth and governance surfaces;
- World-Engine rehydrates the latest committed state into the next turn as `prior_symbolic_object_resonance_state`;
- Langfuse and MCP expose policy, target, selected object/symbol ids, roles, realized ids, pass/fail, and failure-code evidence.

The committed symbolic-object state is bounded planner feedback, not a second
canon store. It may shape the next turn and operator diagnostics, but it does
not mutate story truth outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, canonical object roles,
structured source refs, planner-truth rehydration, ledger/MCP fields, and
structured `symbolic_object_resonance_events`. Generated symbolic prose,
copied dialogue, frontend card shape, judge labels, and hand-written symbolic
beats are never the pass/fail oracle.

### Genre Awareness / Pi32

Genre awareness is implemented as the generic `genre_awareness` runtime aspect.
It is the bounded module-authored genre-framing contract for a turn: selected
genre profile id, allowed registers, required conventions, forbidden marker
ids, per-turn signal budget, prior genre feedback, and structured realization
evidence. It consumes module `runtime_intelligence.genre_awareness`, scene-plan
context, adjacent runtime targets such as scene energy and social pressure, and
prior committed genre-awareness state. It does not replace tonal consistency,
voice consistency, narrative aspects, committed truth, or visible narration,
and it must not become a generated-prose genre judge.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.genre_awareness` into `runtime_governance_policy.genre_awareness`;
- LangGraph derives `genre_awareness_state` and `genre_awareness_target` after social pressure and before sensory context;
- the dramatic generation packet receives only selected profile, registers, required conventions, forbidden marker ids, and budget;
- structured output may emit `genre_awareness_events` with profile, register, convention, and forbidden-marker evidence;
- validation checks selected profile id, allowed register, required convention realization, forbidden marker absence, event presence, and budget;
- recoverable failures feed self-correction with bounded `genre_awareness_*` failure codes;
- `turn_aspect_ledger.genre_awareness` records policy presence, selected target, actual event evidence, contract pass, and failure codes;
- World-Engine persists `genre_awareness_state`, `genre_awareness_target`, and `genre_awareness_validation` in planner truth and governance surfaces;
- Langfuse and MCP expose policy, target, selected registers, conventions, event counts, pass/fail, and failure-code evidence.

The aspect is bounded planner/generation governance, not canon. It may shape
the current response and retry feedback, but it does not mutate story truth
outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, planner-truth persistence,
ledger/MCP fields, and structured `genre_awareness_events`. Generated genre
prose, copied dialogue, frontend card shape, judge labels, and hand-written
genre examples are never the pass/fail oracle.

### Sensory Context / Pi26

Sensory context is implemented as the generic `sensory_context` runtime aspect.
It is the bounded sensory-layer contract for a turn: selected authored layer
ids, layer kinds, source references, location/object focus, mood key, intensity,
required layers, and structured realization evidence. It consumes module
`runtime_intelligence.sensory_context`, narrator sensory palette content, scene
affordances, current location/object context, `scene_energy_target`,
`pacing_rhythm_target`, `social_pressure_target`, prior planner truth, and
output language. It does not replace environment state, scene energy, social
pressure, committed truth, or visible narration.

During a turn:

- `ModuleRuntimePolicy` normalizes `runtime_intelligence.sensory_context` into `runtime_governance_policy.sensory_context`;
- LangGraph derives `sensory_context_state` and `sensory_context_target` after social pressure and before improvisational coherence;
- the dramatic generation packet receives only bounded authored layers and source references;
- structured output may emit `sensory_context_events` with selected `layer_id` and `source_ref`;
- validation checks required layer realization, unselected layer use, source-ref consistency, and layer budget;
- recoverable failures feed self-correction with bounded `sensory_context_*` failure codes;
- `turn_aspect_ledger.sensory_context` records policy presence, selected target, actual event evidence, contract pass, and failure codes;
- World-Engine persists `sensory_context_state`, `sensory_context_target`, and `sensory_context_validation` in planner truth and governance surfaces;
- Langfuse and MCP expose target, intensity, location/object ids, required-layer realization, source-ref validity, pass/fail, and repair evidence.

The aspect is bounded planner/generation governance, not canon. It may shape
the current response and retry feedback, but it does not mutate story truth
outside the normal validated commit path.

**ADR-0039 boundary:** Tests derive expectations from normalized module policy,
exported contract constants, schema versions, canonical sensory-palette and
scene-affordance content, ledger/MCP fields, and structured
`sensory_context_events`. Generated narration, copied dialogue, frontend card
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

The authoritative value source for GoC is `content/modules/god_of_carnage/direction/subtext_policy.yaml`. Runtime code builds records through `ai_stack/semantic_planner/goc_subtext_policy.py` and validates labels against the contract constants in `ai_stack/semantic_planner/semantic_move_contract.py`.

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

- World-Engine rebuilds the cascade from committed-truth rows in `StorySession.history`, `StorySession.narrative_threads`, and the durable branch timeline;
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

### No-dead-end Recovery / Pi30

The implemented Pi30 scope is now the bounded `no_dead_end_recovery.v1`
contract for player-visible turns. It records whether the turn is a committed
success, partial success, blocked playable outcome, redirected playable
outcome, clarification-needed outcome, safe fallback playable outcome, or an
unrecoverable system error.

Every player-visible committed or recoverable turn records:

- `no_dead_end_recovery.recovery_class`;
- a player-attempt fingerprint;
- bounded `next_step_options`;
- `turn_aspect_ledger.no_dead_end_recovery`;
- explicit commit policy and committed-truth scope.

Recoverable validation rejections and expected graph `RuntimeError` failures
can still produce a player-visible `rejected_recoverable` turn that preserves
the attempted input, offers a retry affordance, and records
`recoverable_playability.v1` metadata. Recoverable failure rows are
audit/story-window records only:

- `committed_result.commit_applied=false`;
- `recoverable_playability.commits_story_truth=false`;
- `no_dead_end_recovery.commit_policy.committed_truth_scope=none`;
- recoverable/false-commit rows are filtered before callback-web observations
  or consequence-cascade atoms/edges are built;
- memory and committed-truth feedback must continue to derive from canonical
  committed rows, not from fallback narration.

Programming and contract failures are not failure-as-story. They roll back the
attempted turn number and propagate as errors instead of being persisted as
playable history.

**ADR-0039 boundary:** Tests assert schema/status fields, recovery class,
commit flags, exception boundaries, turn ids, next-step evidence, and
feedback-graph row counts. Generated recovery wording is not a pass/fail
oracle.

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
