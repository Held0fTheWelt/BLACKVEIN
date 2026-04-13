# Dramatic Quality Extensions

This document describes high-impact extension seams that should remain possible on top of the foundation MVP.
They are not excuses to weaken runtime authority.
They are structured next layers.

## 1. Character emotional state continuity

### Problem
Without persistent emotional state, characters can swing unrealistically between turns.

### Extension seam
Introduce engine-side emotional state as runtime truth, then expose it in the scene packet.

```python
class CharacterEmotionalState(BaseModel):
    actor_id: str
    current_emotional_state: str
    emotional_intensity: float
    emotional_trajectory: str
    transition_cooldown_turns: int
    recent_emotional_beats: list[dict]
    breaking_point_proximity: float
```

### Why it matters
It keeps a furious character from becoming casually warm one turn later without narrative justification.

## 2. Proactive narrative steering

### Problem
A purely reactive system becomes static when player actions are low-engagement.

### Extension seam
Add narrative pressure and unresolved tensions to the scene packet so the runtime can let NPCs or environment create momentum.

```python
class NarrativeTension(BaseModel):
    tension_id: str
    description: str
    introduced_turn: int
    current_intensity: float
```

This supports:
- NPC initiative
- environmental pressure
- timed revelations
- pressure escalation when the player stalls

## 3. Contradiction detection against canonical world state

### Problem
Constraint checks alone do not catch logical contradictions.

### Extension seam
Maintain canonical world state and run contradiction checks before commit or during semantic validation.

```python
class CanonicalWorldState(BaseModel):
    scene_id: str
    turn_number: int
    object_states: dict[str, dict]
    character_claims: dict[str, list[dict]]
    established_facts: list[dict]
    immutable_truths: list[str]
```

This supports:
- object continuity
- claim contradiction warnings
- immutable truth protection
- stronger player trust in world memory

## 4. Preview branch simulation

### Problem
A preview package can pass static evaluation but still feel wrong across a branch of play.

### Extension seam
Allow preview branch simulation against a chosen starting state and scripted player actions.

Outputs should compare:
- emotional arc quality
- trigger behavior
- compliance
- coherence
- preview vs active differences

This is especially useful before promotion, not after rollback.

## 5. Player affect detection with enums

### Problem
A single "frustration detection" feature is too narrow and too brittle.

### Better abstraction
Use a player affect model with enum states and confidence.

```python
class PlayerAffectState(str, Enum):
    CALM = "calm"
    CURIOUS = "curious"
    ENGAGED = "engaged"
    HESITANT = "hesitant"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"
    DEFIANT = "defiant"
    EXCITED = "excited"
```

```python
class PlayerAffectSignal(BaseModel):
    affect_state: PlayerAffectState
    confidence: float
    source_type: str
    detected_turn: int
```

### Why this is better
- frustration becomes one signal, not the whole architecture
- adaptive assistance can remain bounded and inspectable
- evaluation can compare whether a preview package causes confusion or overload more often

### Usage rule
Affect detection must remain advisory and policy-bounded.
It should influence hint density, pacing, or intervention style only within allowed policy ranges.

## Implementation stance

These extensions are intentionally documented now so the foundation MVP does not paint the architecture into a corner.

The order of strategic value is:

1. emotional continuity
2. contradiction detection
3. proactive steering
4. preview branch simulation
5. player affect adaptation

The MVP should leave clean seams for all five, but the live foundation should still center on:
- package authority
- scene packet execution
- validator control
- corrective retry
- safe fallback
