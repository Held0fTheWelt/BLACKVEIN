# Integration Architecture — How Features Work Together

## System Layers

```
┌─────────────────────────────────────────────────┐
│  Meta-Narrative Layer (opt-in)                  │
│  ↓ characters can resist/comment                │
├─────────────────────────────────────────────────┤
│  Multi-Perspective Engine                       │
│  ↓ switch POVs to gain understanding            │
├─────────────────────────────────────────────────┤
│  Multiplayer Session (optional)                 │
│  ↓ multiple players control different chars     │
├─────────────────────────────────────────────────┤
│  Procedural Subplot Generator                   │
│  ↓ emergent content from templates              │
├─────────────────────────────────────────────────┤
│  Cross-Session Memory                           │
│  ↓ characters remember across sessions          │
├─────────────────────────────────────────────────┤
│  NARRATIVE GOVERNANCE FOUNDATION (base)         │
│  - Compiled packages                            │
│  - Scene packets                                │
│  - Policy resolution                            │
│  - Output validation                            │
└─────────────────────────────────────────────────┘
```

---

## Feature Combinations

### Cross-Session + Procedural

**Synergy:**
- Procedural subplots can reference cross-session memories
- Character relationships inform subplot generation
- Breakthrough moments unlock new subplot templates

**Example:**
```
Session 5: Player achieved high trust with Michel
→ Unlocks "trusted_confidant" role in procedural subplots
→ Next session: "Michel's Brother" subplot can spawn
→ References Session 3 breakthrough moment naturally
```

---

### Multi-POV + Multiplayer

**Synergy:**
- Player B controls Veronique, can switch to her POV
- Player A sees through their character, then switches to see B's inner state
- Creates meta-game of "what is B thinking?"

**Example:**
```
Player A (Investigator): Confronts Veronique
Player B (Veronique): Deflects

Player A switches to Veronique POV:
→ Sees Player B's inner monologue
→ Dramatic irony: knows B is panicking
→ Switches back, now acts with that knowledge
```

---

### Cross-Session + Meta-Narrative

**Synergy:**
- Character awareness builds over multiple sessions
- Meta-comments reference past playthroughs
- "We've had this conversation before" becomes literal

**Example:**
```
Session 7 with Veronique:
"You know, when we first met, I would have lied to you about this.
But now... after everything we've been through...
I can't pretend anymore. You know me too well."

[Meta-awareness + Cross-session memory combined]
```

---

### All Features Together

**Ultimate Experience:**

```
Session 8, Multiplayer (3 players):

Player A (You): Confronts Veronique
Player B (Veronique): Has cross-session trust with A
→ Procedural subplot about Laurent active
→ Switch to Veronique POV: See her inner conflict
→ Meta-moment: "This is where I'm supposed to confess, isn't it?"
→ Player B chooses to resist narrative
→ System adapts: Story branches unexpectedly
→ Player C (Michel) reacts to the unexpected turn

All layers engaged simultaneously.
```

---

## Data Flow Integration

### Shared Canonical State

```python
class IntegratedNarrativeState(BaseModel):
    # Foundation
    compiled_package: NarrativePackage
    canonical_world_state: CanonicalWorldState
    
    # Cross-Session
    character_memories: dict[str, CrossSessionCharacterMemory]
    relationship_states: dict[str, RelationshipState]
    
    # Procedural
    active_subplots: list[GeneratedSubplot]
    subplot_history: list[SubplotRecord]
    
    # Multi-POV
    available_perspectives: list[PerspectiveOption]
    shared_events: list[SharedEvent]
    
    # Multiplayer (if active)
    multiplayer_session: MultiPlayerSession | None
    
    # Meta (if enabled)
    meta_layer_state: MetaNarrativeLayer | None
```

---

## Conflict Resolution Across Features

### Priority Order

1. **Foundation constraints** (immutable)
2. **Cross-session continuity** (preserve relationships)
3. **Procedural coherence** (validate subplots)
4. **Multi-POV consistency** (same objective facts)
5. **Multiplayer sync** (resolve simultaneous actions)
6. **Meta-layer** (can override but flagged)

**Example:**
```
Procedural subplot suggests: "Michel betrays player"
Cross-session memory shows: Michel trust = 0.95
→ CONFLICT

Resolution:
→ Reject subplot (violates cross-session state)
→ OR: Adapt subplot (Michel's "betrayal" is actually protective)
```

---

## Performance Considerations

### Latency Budget

```
Base Turn (Foundation only): 800-1200ms

+ Cross-Session Memory: +100ms (memory retrieval)
+ Procedural Subplot: +200ms (if spawning, otherwise 0)
+ Multi-POV: +300ms (additional scene packet builds)
+ Multiplayer: +400ms (action resolution coordination)
+ Meta-Layer: +150ms (negotiation checks)

Worst case (all features): ~2.5 seconds
Target: <2.0 seconds 95th percentile
```

### Optimization Strategies

- Cache cross-session memories in session
- Pre-generate procedural subplots
- Parallel POV packet building
- Multiplayer: background state sync
- Meta-layer: lazy evaluation

---

## Database Schema Integration

### Core Tables

```sql
-- Foundation
packages, scenes, actors, policies

-- Cross-Session
player_character_memories
relationship_snapshots
shared_memories
breakthrough_moments

-- Procedural
subplot_templates
generated_subplots
subplot_executions

-- Multi-POV
perspective_recordings
shared_events
canonical_event_records

-- Multiplayer
multiplayer_sessions
player_assignments
session_turns

-- Meta
meta_awareness_states
narrative_negotiations
```

---

## API Surface

### Unified Session API

```python
POST /api/sessions/create
{
    "player_id": "...",
    "module_id": "...",
    "features": {
        "cross_session_memory": true,
        "procedural_subplots": true,
        "multi_pov": false,
        "multiplayer": false,
        "meta_layer": false
    }
}

POST /api/sessions/{session_id}/turn
{
    "player_action": "...",
    "pov": "player",  # or character_id
    "multiplayer_actions": {...}  # if applicable
}

GET /api/sessions/{session_id}/state
→ Returns IntegratedNarrativeState
```

---

## Testing Strategy

### Feature Isolation Tests

- Each feature tested independently
- Foundation + Feature X only
- Validates feature doesn't break base

### Integration Tests

- Foundation + Cross-Session + Procedural
- Foundation + Multi-POV + Multiplayer
- All features enabled (stress test)

### Regression Suite

- Golden scenarios across feature combinations
- Performance benchmarks
- Quality metrics

---

## Rollout Strategy

**Phase 1:** Foundation MVP (done)  
**Phase 2:** Cross-Session (first add-on)  
**Phase 3:** Procedural (builds on cross-session)  
**Phase 4:** Multi-POV (independent path)  
**Phase 5:** Multiplayer (social platform)  
**Phase 6:** Meta-Layer (experimental opt-in)

**Each phase validates before next.**

---

## Monitoring & Observability

### Key Metrics Per Feature

```python
class FeatureMetrics(BaseModel):
    # Cross-Session
    average_sessions_per_player: float
    relationship_progression_rate: float
    memory_reference_frequency: float
    
    # Procedural
    subplot_generation_success_rate: float
    subplot_quality_average: float
    subplot_completion_rate: float
    
    # Multi-POV
    pov_switch_frequency: float
    dramatic_irony_engagement: float
    
    # Multiplayer
    session_completion_rate: float
    player_conflict_frequency: float
    
    # Meta
    meta_activation_rate: float
    player_retention_with_meta: float
```

---

## Graceful Degradation

### Feature Failure Handling

```python
if cross_session_memory_unavailable:
    # Fallback to fresh start, notify player
    session.mode = "standalone"

if procedural_generation_fails:
    # Continue with authored content only
    session.procedural_disabled = True

if multi_pov_errors:
    # Lock to player POV
    session.pov_switching_disabled = True

if multiplayer_desync:
    # Convert to single-player for affected player
    session.split_to_solo(player_id)
```

**System remains playable even with partial failures.**
