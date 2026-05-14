# Admin/Operator Diagnostics and Governance Surfaces

## Admin Tool Governance Surface

The administration tool (`administration-tool/`) provides operators with visibility into running sessions and control over exceptional cases.

### Primary Admin Views

#### View 1: Session Dashboard
**What it shows:** List of active sessions with status indicators

```
Session ID | Module | Player | Turn # | Status | Last Turn Time | Pressure State
-----------|--------|--------|--------|--------|----------------|--------------
sess-001  | GoC    | Alice  | 12     | active | 2m ago        | high_blame
sess-002  | GoC    | Bob    | 5      | paused | 30m ago       | medium_pressure
sess-003  | GoC    | Carol  | 18     | degraded | 1m ago      | high_exposure
```

**Actions available:**
- Click session to open full diagnostics
- Pause session (if player requests timeout)
- End session (if player wants to stop)
- Flag for review (if something looks wrong)

#### View 2: Session Turn Trace
**What it shows:** Complete turn history for a specific session

For each turn:
- Turn number, timestamp, player action
- Seams executed (proposal → validation → commit → render)
- Validation outcome (approved/rejected/waived)
- Committed effects
- Player-visible output
- Diagnostics (latency, fallbacks used, consistency checks)

**Actions available:**
- Expand any turn to see full details
- Review model prompt/output (for proposal seam)
- Review validation decision (which rules applied)
- See consistency check results
- Search turns (find when pressure changed, character acted, etc.)

#### View 3: Character State Inspector
**What it shows:** Deep state for any character in a session

```
Character: Annette Reille
Current State:
  - Pressure: 8/10 (blame + dignity injury)
  - Injuries: "humiliated by affair revelation"
  - Active alliances: [mediator]
  - Broken alliances: [vanya]
  - Emotional state: defensive, angry
  - Available actions: [confront, demand_apology, leave_room]

Turn History:
  Turn 1: Wary greeting
  Turn 2: Reveals infidelity allegation
  Turn 3: Pushed back on Vanya's blame-shift
  Turn 4: Demanded acknowledgment of hurt
  ...
```

**Actions available:**
- View full dialogue history for this character
- See how pressure vectors shaped their responses
- Audit voice consistency through `voice_consistency_validation` / `turn_aspect_ledger.voice_consistency`; reading dialogue remains a qualitative follow-up, not the primary gate
- Check alliance/relationship changes over time

#### View 4: Pressure Vector Timeline
**What it shows:** How dramatic pressure changed across turns

```
Turn | Blame | Dignity | Exposure | Alliance | Dominant Pressure
-----|-------|---------|----------|----------|------------------
1    | 5     | 7       | 4        | stable   | dignity_injury
2    | 6     | 7       | 5        | stable   | dignity_injury
3    | 8     | 8       | 6        | broken   | blame + dignity
4    | 8     | 9       | 7        | broken   | all high
5    | 7     | 8       | 6        | stable   | blame + dignity
...
```

**Insights:** Can see if pressure is building toward climax or resolving; can spot unexpected pressure changes.

#### View 5: Consistency Check Report
**What it shows:** Automated checks run before each turn render

```
Turn 12 Consistency Checks:
✓ Fact consistency (8/8 facts non-contradictory)
✓ Character state consistency (all characters coherent)
✓ Scene state consistency (present characters are valid)
✗ Authority consistency (ISSUE FOUND)
  - Committed result references alliance that was broken in turn 2
  - But dialogue doesn't reflect broken alliance
  - Recommendation: Re-render turn with corrected visibility

Turn flagged: DEGRADED
Operator alert: Review turn 12 before player sees output
```

---

## Inspection Domain Model

Operators think about sessions in these conceptual domains:

### Domain 1: Scene & Setting
- Current scene identity
- Physical space (room, objects, exits)
- Character positions (seated, standing, left)
- Environmental changes (temperature, mood)

**Query:** "What's the room like? Who's where?"

### Domain 2: Characters & Relationships
- Who's present and why
- Relationships (alliances, broken alliances, dependencies)
- Character pressure states and wounds
- Character personality and voice

**Query:** "How do Vanya and Annette relate? Who's allied?"

### Domain 3: Established Facts & Consequences
- What's been revealed (infidelity, hurt, etc.)
- What's been committed (state changes, consequences)
- What consequences are carry-forward (shaping current state)

**Query:** "What happened? What did I miss?"

### Domain 4: Player Input & Acceptance
- What move did player attempt
- Was it accepted or rejected
- Why (which rule or validation gate)
- What could work instead

**Query:** "Why did that move fail? What can player do?"

### Domain 5: Turn Execution Quality
- Did all seams execute correctly
- Were there any fallbacks or degradation
- Latency and performance
- Consistency and coherence

**Query:** "Is this turn healthy or are there issues?"

All admin views align with these domains.

---

## Incident Pathways

When something goes wrong, operators follow this pathway:

### Pathway 1: Player Reports Issue
**Trigger:** Player contacts support ("Something feels wrong" / "My move didn't work")

**Operator actions:**
1. Look up player's current session
2. Open session dashboard
3. Find the problematic turn
4. Review turn trace (did seams execute correctly?)
5. Inspect consistency checks (are there flagged issues?)
6. Inspect character state (does it match what player is seeing?)

**Investigation questions:**
- Was the move rejected at validation? (expected behavior)
- Did validation pass but something went wrong at commit? (bug)
- Did something become inconsistent? (data integrity issue)

**Recovery:**
- If validation rejection: explain to player, suggest alternative move
- If commit/render issue: pause session, notify player, investigate deeper

### Pathway 2: Operator Notices Degradation Flag
**Trigger:** Admin dashboard shows session marked "DEGRADED"

**Operator actions:**
1. Click on degraded session
2. Review consistency check report (what failed?)
3. Look at the turn that failed
4. Inspect full diagnostics (proposal, validation, commit, render outputs)
5. Determine root cause

**Investigation questions:**
- Which seam failed (proposal, validation, commit, render)?
- What was the specific error?
- Can it be recovered or must session be ended?

**Recovery:**
- If minor (render glitch): Try re-rendering turn with same state
- If major (state corruption): Rollback to previous valid turn
- If severe (data loss): Pause, notify player, begin investigation

### Pathway 3: Operator Auditing for Quality
**Trigger:** Routine check (daily/weekly) to ensure quality

**Operator actions:**
1. Review random sample of completed sessions
2. Check that all 5 quality signals are present
3. Verify character voices are distinct
4. Verify consequences carry-forward in dialogue
5. Check consistency reports (any pattern of failures?)

**Audit checklist:**
- [ ] Scene clarity present in narration
- [ ] Player actions have visible effects
- [ ] Turn effects are traceable to committed results
- [ ] Character voices are recognizable
- [ ] Consequences from turn N appear in turn N+1
- [ ] No silent failures (all issues are explicit)
- [ ] Fallbacks are used only when necessary

**Result:** Quality report; flag any patterns requiring fix.

---

## Corrective Governance Controls

### Control 1: Turn Regeneration
**When to use:** Turn output is incoherent or inconsistent

**What it does:** Takes committed state from end of turn, re-runs render seam only

**Outcome:** New player-visible text (narration/dialogue), same committed state

**Audit trail:** Previous version is preserved; change is recorded in governance log

```json
{
  "intervention": "turn_regenerate",
  "turn_id": "uuid",
  "reason": "render_incoherence_detected",
  "previous_output": {...},
  "new_output": {...},
  "operator_id": "admin_1",
  "timestamp": "ISO-8601"
}
```

### Control 2: Validation Override
**When to use:** Validation gate is too strict; valid move was rejected

**What it does:** Bypasses validation, allows proposed effects to commit

**Preconditions:**
- Operator must review the proposal
- Operator must confirm it's valid in scene context
- Operator must document reason

**Outcome:** Proposed effects are committed despite validation rejection

**Audit trail:** Fully recorded; future consistency checks highlight this override

```json
{
  "intervention": "validation_override",
  "turn_id": "uuid",
  "reason": "validation_gate_overly_strict",
  "original_validation": "rejected",
  "override_by": "operator_id",
  "justification": "string",
  "timestamp": "ISO-8601",
  "committed_effects_now": [...]
}
```

### Control 3: State Correction
**When to use:** World state has become corrupted or inconsistent

**What it does:** Modifies character state, pressure vectors, or established facts

**Preconditions:**
- Issue must be documented and verified
- Operator must explain why state is wrong
- Operator must specify exact correction

**Outcome:** State is corrected; all future turns use corrected state

**Audit trail:** Before/after states are recorded; explanation is required

```json
{
  "intervention": "state_correction",
  "corrected_domain": "character_state",
  "character_id": "annette",
  "field": "pressure",
  "previous_value": 5,
  "new_value": 8,
  "reason": "pressure_did_not_update_in_turn_5",
  "operator_id": "admin_1",
  "timestamp": "ISO-8601"
}
```

### Control 4: Session Pause
**When to use:** Investigation is needed; player should wait

**What it does:** Pauses turn execution; preserves all state

**Outcome:** Player sees "Session paused" message; can resume later from same point

**Audit trail:** Pause reason recorded; resume automatically triggers when operator ends pause

```json
{
  "intervention": "session_pause",
  "reason": "operator_investigation",
  "details": "string",
  "operator_id": "admin_1",
  "timestamp": "ISO-8601",
  "expected_resume": "ISO-8601 (estimated)"
}
```

### Control 5: Session Rollback
**When to use:** Turn is unrecoverable; must go back to previous state

**What it does:** Discards last turn; session returns to end-of-turn state from turn N-1

**Outcome:** Last turn is deleted; player is asked to take different action

**Audit trail:** Deleted turn is preserved in governance log; rollback reason documented

```json
{
  "intervention": "session_rollback",
  "rolled_back_turn": "uuid",
  "reason": "turn_unrecoverable",
  "session_returns_to_turn": "number",
  "operator_id": "admin_1",
  "timestamp": "ISO-8601",
  "preserved_deleted_turn": "archived_location"
}
```

### Approval Gates on Controls
Some controls require approval (not all):

**No approval needed:**
- Turn regeneration (same state, different text)
- Session pause (non-destructive)

**Approval recommended:**
- Validation override (changes what commits)
- State correction (changes world truth)

**Approval required:**
- Session rollback (loses a turn)

Approval workflow: Operator requests review from supervisor; supervisor reviews and approves/rejects.

---

## Diagnostics Payload Structure

Every turn produces this diagnostics structure (visible to operators only):

```json
{
  "turn_diagnostics": {
    "turn_id": "uuid",
    "seam_execution": {
      "proposal": {
        "executed": true,
        "model": "claude-opus-4.5",
        "prompt_tokens": 1200,
        "output_tokens": 340,
        "latency_ms": 1540,
        "proposal_output": {...}
      },
      "validation": {
        "executed": true,
        "rules_checked": [
          "responder_validity",
          "scene_function_coherence",
          "pressure_alignment"
        ],
        "rules_passed": 3,
        "rules_failed": 0,
        "outcome": "approved",
        "latency_ms": 45
      },
      "commit": {
        "executed": true,
        "effects_to_commit": 2,
        "effects_committed": 2,
        "state_delta": {...},
        "latency_ms": 12
      },
      "render": {
        "executed": true,
        "visibility_class_count": {
          "factual": 3,
          "implied": 2,
          "ambiguous": 0,
          "hidden": 1
        },
        "fallback_used": false,
        "latency_ms": 230
      }
    },
    "consistency_checks": {
      "fact_consistency": {
        "passed": true,
        "facts_checked": 8,
        "contradictions": 0
      },
      "character_consistency": {
        "passed": true,
        "characters_checked": 3,
        "inconsistencies": 0
      },
      "scene_consistency": {
        "passed": true,
        "present_characters_valid": true,
        "room_state_coherent": true
      },
      "authority_consistency": {
        "passed": true,
        "all_claims_traceable": true
      }
    },
    "performance_metrics": {
      "total_latency_ms": 1827,
      "model_latency_ms": 1540,
      "non_model_latency_ms": 287,
      "seam_breakdown": [
        "proposal: 1540ms (84%)",
        "render: 230ms (13%)",
        "validation: 45ms (2%)",
        "commit: 12ms (1%)"
      ]
    },
    "governance_events": [
      {
        "event": "validation_near_rejection",
        "detail": "pressure_alignment check scored 0.65 (threshold 0.7); passed narrowly",
        "recommendation": "monitor future turns; may need rule adjustment"
      }
    ]
  }
}
```

Operators can drill into any section to understand exactly what happened in a turn.

---

## Live Play Correction and Fallback Rules

### Fallback Hierarchy
If something fails at runtime:

**Level 1: Graceful Degrade**
- Try alternate approach within same seam
- Example: If model times out, use cached template dialogue
- Player sees normal output (no indication of fallback)

**Level 2: Show Fallback Explicitly**
- Fallback message is shown; player is aware
- Example: "Your move didn't land. The system is recovering. Try again?"
- Session is marked `degraded` but continues

**Level 3: Pause and Alert**
- Turn execution is paused
- Operator is notified
- Player is shown waiting message

**Level 4: Rollback**
- Turn is deleted; session goes back one turn
- Player must choose different action
- Operator investigates

### Fallback Messages (Player-Friendly)
All fallback messages are explicit and helpful:

- "Your suggestion didn't land. Annette isn't ready for that kind of confrontation. What else?"
- "The system needs a moment. Take a breath. What would you like to do?"
- "Something unexpected happened. We're recovering. Please wait..."
- "We can't continue from here. Let's back up and try differently."

No silent ignoring of failure. Player always knows what happened.

---

## Acceptance Criteria

Admin surfaces are correct when:

1. **All 5 primary views are present** (dashboard, turn trace, character state, pressure timeline, consistency checks)
2. **Incident pathways are testable** (can follow player-reports-issue → resolution path)
3. **Corrective controls are audit-trailed** (every intervention recorded with reason)
4. **Diagnostics are complete** (operators can inspect any seam execution)
5. **Fallback messages are explicit** (no silent failures)
6. **Approval gates work** (approval workflow is enforced for destructive controls)
7. **Turn regeneration is non-destructive** (re-renders use same committed state)
8. **Operators understand domains** (all views align with scene/character/facts/input/quality domains)

All criteria must be met for Phase 4 acceptance.
