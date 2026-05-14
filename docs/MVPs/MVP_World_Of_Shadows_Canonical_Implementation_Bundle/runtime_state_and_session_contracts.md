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

**Runtime enforcement:** The live GoC path derives `CharacterVoiceProfileRecord` values from canonical `direction/character_voice.yaml` and exposes them to generation as profile guidance. During validation, `voice_consistency_validation.v1` checks structured `spoken_lines` against the active profiles and records a `voice_consistency` runtime aspect before commit. Policy-declared forbidden language markers can reject an otherwise approved turn through the `runtime_voice_consistency_v1` lane. The semantic classifier also compares spoken lines against canonical profile dimensions; in `schema_plus_semantic` it records warnings, while `strict_rule_engine` can reject high-confidence cross-actor voice confusion through `runtime_voice_consistency_v2`. Recovery keeps speaker ownership stable and rewrites only the offending wording.

**ADR-0039 boundary:** `dialogue_examples` in `character_voice.yaml` are authoring examples, not validation or test oracles. Runtime profiles omit them, and tests assert structured validator/aspect outcomes derived from the policy block and canonical profile dimensions rather than copied narrative prose.

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

---

## Non-Compliance Degradation

If state consistency fails:

- **Fact contradiction detected** → Turn is marked `degraded`; operator is alerted; fallback message is shown
- **Carry-forward missing** → Operator audit shows which consequences disappeared; recommended fix is provided
- **Character voice inconsistency** → Operator can see in turn trace and request regeneration
- **Scene identity lost** → Operator can see scene_core changed; can rollback or manually correct

All degradation is audited and recoverable.
