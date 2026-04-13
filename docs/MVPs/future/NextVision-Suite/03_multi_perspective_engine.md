# Multi-Perspective Engine — Dynamic POV Switching

## Core Concept

Experience the same story from multiple character perspectives. Switch POV mid-scene to gain emotional depth and dramatic irony.

**Single POV:** Limited understanding, mystery through ignorance  
**Multi POV:** Deep understanding, mystery through dramatic irony

---

## Architecture

### Perspective System

```python
class PerspectiveSwitch(BaseModel):
    session_id: str
    current_pov: str  # character_id or "player"
    available_perspectives: list[PerspectiveOption]
    shared_events: list[SharedEvent]
    
    # Canon formation
    objective_facts: CanonicalEventRecord
    subjective_layers: dict[str, SubjectivePerspective]

class PerspectiveOption(BaseModel):
    character_id: str
    unlock_condition: str  # "relationship_threshold" | "dramatic_moment" | "always"
    narrative_mode: str  # "inner_monologue" | "limited_knowledge" | "omniscient"
    
    knowledge_state: KnowledgeState
    hidden_information: list[str]  # what they know but others don't
    inner_conflict: str  # private struggle
    
    # UI
    display_name: str
    unlock_message: str  # "Veronique's perspective is now available"

class SharedEvent(BaseModel):
    event_id: str
    canonical_turn: int
    occurred_at: str
    
    # Different POVs of same event
    perspectives: dict[str, PerspectiveRecording]

class PerspectiveRecording(BaseModel):
    character_id: str
    
    # What they observed
    external_observations: list[str]
    
    # What they thought/felt (invisible to others)
    inner_monologue: str
    emotional_state: str
    interpretation: str  # how they understood the event
    
    # What they hid
    suppressed_reactions: list[str]
    hidden_knowledge: list[str]
```

---

## POV Switching Mechanics

### Scene Packet for Different POVs

```python
class MultiPerspectiveEngine:
    
    def build_scene_packet_for_pov(
        self,
        character_id: str,
        shared_event: SharedEvent,
        current_state: NarrativeState
    ) -> NarrativeDirectorScenePacket:
        
        # Base packet
        packet = self.build_base_packet(shared_event, current_state)
        
        if character_id == "player":
            # Standard player POV
            return self.build_player_packet(packet, current_state)
        
        # Character POV modifications
        character = current_state.characters[character_id]
        
        # 1. Knowledge constraints
        packet.available_information = character.knowledge_state.known_facts
        packet.hidden_from_view = character.knowledge_state.unknown_facts
        
        # 2. Inner state
        packet.inner_conflict = character.inner_conflict
        packet.suppressed_emotions = character.emotional_state.suppressed
        packet.private_knowledge = character.secrets
        
        # 3. Available actions differ by character
        packet.available_actions = self.get_character_actions(
            character_id,
            shared_event,
            current_state
        )
        
        # 4. Narrative mode
        if character.perspective_mode == "inner_monologue":
            packet.system_directive = f"""
You are narrating {character.name}'s internal experience.

The player will experience:
- {character.name}'s thoughts (they can hear what you're thinking)
- {character.name}'s emotions (they feel what you feel)
- {character.name}'s private knowledge (they know what you know but others don't)

Narrate in FIRST PERSON INTERNAL.
Show the gap between what you display externally and what you feel internally.
"""
        
        return packet
```

---

## Example: Phone Confrontation from Three POVs

### Player POV

```
You confront Veronique about the phone.
She becomes pale and says: "That... goes you nothing concerns."
Her voice trembles.

[Switch Perspective Available: Veronique | Michel]
```

### Veronique POV (Inner Monologue)

```
[INNER MONOLOGUE MODE]

My heart pounds. He knows. HE KNOWS.
Laurent's name is there, on the display, and he saw it.

I want to scream, I want to run, I want...

"Das... geht dich nichts an."

My voice shakes. Idiot. He KNOWS I'm lying.
But what should I say? The truth? That I...

Michel sits three meters away. He can't hear this.
Not like this. Please not like this.

[Your Choice]
→ Continue lying (maintain control, risk exposure)
→ Break down and confess (relief but consequences)
→ Attack: shift focus to his secrets (deflect)
```

### Michel POV (Limited Knowledge)

```
[LIMITED KNOWLEDGE MODE]

Veronique just went pale. What happened?

I see her staring at the phone... then at HIM.
She's trembling.

What did he find? What does he know now?

I should intervene. But... if I intervene,
I look weak. Veronique hates when I "rescue" her.

But she needs help. I can see it.

[Your Choice]
→ Interrupt: "Is everything okay?"
→ Stay silent: observe
→ Intervene aggressively: defend Veronique
```

---

## Canon Formation from Multiple POVs

### Objective vs Subjective Truth

```python
class CanonResolver:
    
    def resolve_multi_pov_canon(
        self,
        event: SharedEvent,
        perspectives: dict[str, PerspectiveRecording]
    ) -> CanonicalEventRecord:
        
        # Extract facts observable by all
        objective_facts = self.extract_shared_observations(perspectives)
        
        # Preserve subjective interpretations
        subjective_truths = {}
        for char_id, recording in perspectives.items():
            subjective_truths[char_id] = {
                "emotional_state": recording.emotional_state,
                "interpretation": recording.interpretation,
                "inner_monologue": recording.inner_monologue,
                "hidden_knowledge": recording.hidden_knowledge
            }
        
        return CanonicalEventRecord(
            event_id=event.event_id,
            
            # Facts (agreed upon by all observers)
            objective_truth={
                "player_mentioned_phone": True,
                "veronique_became_pale": True,
                "veronique_said": "Das geht dich nichts an",
                "voice_was_shaking": True,
                "michel_was_present": True
            },
            
            # Interpretations (POV-specific)
            subjective_truths=subjective_truths,
            
            # Which POV(s) player experienced
            player_experienced_povs=["player", "veronique"],
            
            # Dramatic irony unlocked
            dramatic_irony={
                "player_knows_veronique_is_terrified": True,
                "player_knows_michel_is_confused": True
            }
        )
```

---

## Unlock Conditions

### When POVs Become Available

```python
class PerspectiveUnlockManager:
    
    def check_unlock_conditions(
        self,
        character_id: str,
        current_state: NarrativeState,
        player_profile: PlayerProfile
    ) -> bool:
        
        character = current_state.characters[character_id]
        
        # Condition 1: Relationship threshold
        if character.unlock_condition == "relationship_threshold":
            relationship = current_state.relationships.get(character_id, 0)
            return relationship >= character.unlock_threshold
        
        # Condition 2: Dramatic moment
        if character.unlock_condition == "dramatic_moment":
            # Specific story beat reached
            return current_state.story_beats_reached.get(character.unlock_beat, False)
        
        # Condition 3: Player choice
        if character.unlock_condition == "player_choice":
            # Player explicitly asked to see this POV
            return player_profile.requested_povs.get(character_id, False)
        
        # Condition 4: Always available (main characters)
        if character.unlock_condition == "always":
            return True
        
        return False
```

---

## Dramatic Irony System

### Knowing More Than Your Character

```python
class DramaticIronyTracker:
    """Track what player knows vs what their character knows"""
    
    def __init__(self):
        self.player_meta_knowledge = set()  # Things player knows from other POVs
        self.character_knowledge = {}  # What each character knows
    
    def switch_to_pov(self, character_id: str):
        """When switching, mark what's meta-knowledge"""
        
        current_knowledge = self.character_knowledge.get(character_id, set())
        
        # Everything player knows that this character doesn't
        meta_knowledge = self.player_meta_knowledge - current_knowledge
        
        if meta_knowledge:
            return DramaticIronyAlert(
                character_id=character_id,
                player_knows_but_character_doesnt=list(meta_knowledge),
                suggested_ui_hint="You know things this character doesn't"
            )
    
    def on_pov_revelation(self, character_id: str, revelation: str):
        """Add to player's meta-knowledge"""
        self.player_meta_knowledge.add(revelation)
        self.character_knowledge.setdefault(character_id, set()).add(revelation)
```

---

## UI/UX Flow

### POV Switch Interface

```
[During intense scene]

┌─────────────────────────────────────┐
│ Veronique's eyes widen in shock.    │
│ Michel stands frozen.               │
│                                     │
│ [Current POV: You (Player)]        │
│                                     │
│ Switch Perspective:                 │
│  [👁️ See through Veronique's eyes]  │
│  [👁️ See through Michel's eyes]     │
│                                     │
│ [Continue as Player]                │
└─────────────────────────────────────┘
```

**After switching:**

```
┌─────────────────────────────────────┐
│ [VERONIQUE'S PERSPECTIVE]           │
│ Inner Monologue Mode                │
│                                     │
│ God, he knows. Laurent's name...    │
│ How do I explain this?              │
│                                     │
│ What do you do?                     │
│  → Continue lying                   │
│  → Confess everything               │
│  → Deflect to Michel's secrets      │
│                                     │
│ [Switch back to Player POV]         │
└─────────────────────────────────────┘
```

---

## Narrative Continuity

### Maintaining Story Flow

```python
class MultiPOVContinuityManager:
    
    def ensure_continuity(
        self,
        from_pov: str,
        to_pov: str,
        shared_event: SharedEvent
    ) -> ContinuityBridge:
        
        # Capture last state from previous POV
        previous_state_snapshot = self.snapshot_current_state()
        
        # Find temporal connection point
        if from_pov == "player" and to_pov != "player":
            # Switching from player to character
            bridge_text = f"""
You see the same moment through {to_pov}'s eyes.
What you observed as external, you now experience as internal.
"""
        
        elif from_pov != "player" and to_pov == "player":
            # Switching back to player
            bridge_text = f"""
You return to your own perspective.
You now know what {from_pov} was thinking in that moment.
"""
        
        else:
            # Character to character
            bridge_text = f"""
You shift from {from_pov}'s mind to {to_pov}'s mind.
Same moment, different inner world.
"""
        
        return ContinuityBridge(
            bridge_text=bridge_text,
            preserved_state=previous_state_snapshot,
            temporal_anchor=shared_event.canonical_turn
        )
```

---

## Integration with Governance Foundation

### Package Support for Multi-POV

```python
class MultiPOVPackageExtension(BaseModel):
    """Extension to NarrativePackage for POV support"""
    
    pov_enabled_characters: list[str]
    
    # Per-character perspective configs
    character_perspective_configs: dict[str, PerspectiveConfig]
    
    # Unlock rules
    pov_unlock_rules: dict[str, UnlockRule]
    
    # Shared event definitions
    multi_pov_scenes: list[MultiPOVScene]

class PerspectiveConfig(BaseModel):
    character_id: str
    narrative_mode: str
    knowledge_constraints: list[str]
    inner_conflict_template: str
    
class MultiPOVScene(BaseModel):
    scene_id: str
    requires_multi_pov: bool
    canonical_povs: list[str]  # Which POVs are canon for this scene
```

---

## Success Metrics

- **POV Switch Usage:** >40% of eligible moments
- **Narrative Depth Rating:** >4.3/5
- **Player Confusion:** <10% report being lost
- **Dramatic Irony Appreciation:** >75% report "deeper understanding"
- **Replay for Different POVs:** >50%

---

## Implementation Phases

### Phase 1: Core Engine (4 weeks)
- POV switching mechanics
- Scene packet adaptation
- Knowledge state tracking

### Phase 2: Canon Formation (2 weeks)
- Objective/subjective separation
- Dramatic irony tracker
- Continuity bridges

### Phase 3: UI/UX (2 weeks)
- POV switch interface
- Unlock notifications
- Inner monologue presentation

### Phase 4: Polish (2 weeks)
- Edge cases
- Quality validation
- Player testing

**Total: 10 weeks**

---

## Open Questions

1. How many POV switches per session before fatigue?
2. Should all POVs be equally detailed or player-primary?
3. Can player actions in character POV affect that character permanently?
4. How to prevent "optimal strategy" meta-gaming?
5. Accessibility: How to make this clear for non-gamers?
