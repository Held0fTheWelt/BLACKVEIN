# Cross-Session Memory — Persistent Character Development

## Core Concept

Characters remember you across sessions. Relationships evolve over real time, not just in-game time.

**Traditional approach:**
```
Session 1: Veronique at state A
Session 2: Veronique at state A (reset)
Session 3: Veronique at state A (reset)
```

**Cross-session memory:**
```
Session 1: Defensive Veronique (A) → Opens up (B)
Session 2: Already vulnerable (B) → Trust built (C)
Session 3: Transformed (C) → New depth unlocked (D)
```

---

## Data Models

### Cross-Session Character Memory

```python
class CrossSessionCharacterMemory(BaseModel):
    actor_id: str
    player_id: str
    
    # Relationship evolution
    relationship_history: list[RelationshipSnapshot]
    cumulative_trust: float  # 0.0 - 1.0, builds over sessions
    cumulative_intimacy: float  # how deep is the connection
    
    # Shared history
    shared_memories: list[SharedMemory]
    breakthrough_moments: list[BreakthroughMoment]
    
    # Character growth arc
    character_arc_stage: str  # defensive → vulnerable → transformed → actualized
    transformation_triggers: list[str]  # what caused growth
    
    # Player-specific adaptations
    learned_player_patterns: dict[str, float]
    effective_approaches: dict[str, float]  # what works with this player
    failed_approaches: list[str]  # what didn't work
    
    # Meta
    first_session_date: str
    last_session_date: str
    total_sessions: int
    total_turns: int

class SharedMemory(BaseModel):
    memory_id: str
    session_id: str
    turn_number: int
    
    event_description: str
    event_type: str  # confession | conflict | breakthrough | betrayal | reconciliation
    emotional_weight: float  # 0.0 - 1.0, how significant
    
    characters_present: list[str]
    player_action_that_triggered: str
    character_reaction: str
    
    canonical: bool  # is this an established fact or perception?
    memorable: bool  # will character reference this later?

class BreakthroughMoment(BaseModel):
    moment_id: str
    session_id: str
    turn_number: int
    
    description: str
    emotional_shift: str  # "defensive → vulnerable"
    trust_delta: float
    
    what_player_did: str
    why_it_worked: str
    
    unlocks_content: list[str]  # new dialogue branches, actions available

class RelationshipSnapshot(BaseModel):
    session_id: str
    session_date: str
    
    trust_level: float
    intimacy_level: float
    conflict_level: float
    
    dominant_emotion: str  # how character feels about player
    relationship_label: str  # stranger → acquaintance → confidant → intimate
```

---

## Memory Formation

### When to Create Shared Memories

```python
class MemoryFormationEngine:
    def evaluate_turn_for_memory(
        self, 
        turn_output: RuntimeTurnStructuredOutputV2,
        scene_packet: NarrativeDirectorScenePacket
    ) -> MemoryCandidate | None:
        
        # Criteria for memory-worthy events
        memory_score = 0.0
        
        # High emotional intensity
        if turn_output.detected_triggers:
            trigger_weight = self.get_trigger_significance(turn_output.detected_triggers)
            memory_score += trigger_weight * 0.3
        
        # Relationship state change
        if turn_output.proposed_state_effects:
            for effect in turn_output.proposed_state_effects:
                if effect.effect_type == "relationship_change":
                    memory_score += abs(effect.magnitude) / 100 * 0.4
        
        # Narrative significance
        if self.is_plot_critical(turn_output, scene_packet):
            memory_score += 0.3
        
        # Threshold
        if memory_score >= 0.6:
            return MemoryCandidate(
                event_description=self.summarize_event(turn_output),
                emotional_weight=memory_score,
                memorable=memory_score >= 0.8
            )
        
        return None
```

---

## Memory Retrieval

### Session Start: Loading Character State

```python
class SessionInitializer:
    async def initialize_session_with_memory(
        self,
        player_id: str,
        module_id: str
    ) -> SessionStartState:
        
        # Load all character memories for this player
        character_memories = await self.load_character_memories(player_id, module_id)
        
        # Adjust starting state based on history
        adjusted_characters = {}
        for actor_id, memory in character_memories.items():
            
            # Load base actor mind
            base_actor = await self.load_base_actor(actor_id, module_id)
            
            # Adjust based on cumulative relationship
            adjusted_actor = self.adapt_character_for_player(
                base_actor,
                memory
            )
            
            adjusted_characters[actor_id] = adjusted_actor
        
        return SessionStartState(
            characters=adjusted_characters,
            relationship_states=character_memories,
            greeting_mode="returning_player"  # vs "first_time"
        )
    
    def adapt_character_for_player(
        self,
        base_actor: ActorMind,
        memory: CrossSessionCharacterMemory
    ) -> ActorMind:
        
        adjusted = base_actor.copy()
        
        # Trust adjustments
        if memory.cumulative_trust > 0.8:
            adjusted.default_stance = "trusting"
            adjusted.reveal_threshold = 0.2  # more willing to share
            adjusted.defensive_responses = False
        
        elif memory.cumulative_trust < 0.3:
            adjusted.default_stance = "guarded"
            adjusted.reveal_threshold = 0.9  # very reluctant
            adjusted.defensive_responses = True
        
        # Character arc stage
        if memory.character_arc_stage == "transformed":
            adjusted.emotional_baseline = "reflective"
            adjusted.available_dialogues.extend(memory.unlocked_content)
        
        # Learned patterns
        if memory.learned_player_patterns.get("gentle_approach", 0) > 0.7:
            adjusted.preferred_player_approach = "gentle"
            adjusted.reaction_to_aggression = "hurt_surprised"
        
        return adjusted
```

---

## Memory-Aware Dialogue

### Referencing Shared History

```python
class MemoryReferencingSystem:
    def inject_memory_references(
        self,
        scene_packet: NarrativeDirectorScenePacket,
        character_memory: CrossSessionCharacterMemory
    ) -> NarrativeDirectorScenePacket:
        
        # Select 1-3 most relevant memories for current context
        relevant_memories = self.select_relevant_memories(
            character_memory.shared_memories,
            current_scene=scene_packet.scene_id,
            recency_weight=0.3,
            emotional_weight=0.7
        )
        
        # Inject into scene guidance
        scene_packet.scene_guidance["memory_callbacks"] = [
            {
                "memory_id": mem.memory_id,
                "reference_text": mem.event_description,
                "emotional_context": mem.emotional_weight,
                "usage_hint": f"Character may reference: {mem.event_description}"
            }
            for mem in relevant_memories
        ]
        
        # Add to system directive
        if relevant_memories:
            scene_packet.system_directive += f"""

SHARED HISTORY WITH PLAYER:
The character remembers these events from previous sessions:
{self.format_memories_for_prompt(relevant_memories)}

The character should naturally reference these if contextually appropriate.
Do not force references, but be aware of the shared history.
"""
        
        return scene_packet
```

---

## Character Arc Progression

### Stage Transitions

```python
class CharacterArcManager:
    
    arc_stages = [
        "stranger",        # Session 1-2: No trust, defensive
        "acquaintance",    # Session 3-4: Basic trust, testing player
        "opening_up",      # Session 5-7: Sharing some truths
        "vulnerable",      # Session 8-10: Deep sharing, emotional
        "transformed",     # Session 11+: Changed by relationship
        "actualized"       # Session 15+: Full character evolution
    ]
    
    def check_arc_progression(
        self,
        memory: CrossSessionCharacterMemory,
        recent_session: SessionRecord
    ) -> CharacterArcTransition | None:
        
        current_stage = memory.character_arc_stage
        current_index = self.arc_stages.index(current_stage)
        
        # Can we progress to next stage?
        if current_index >= len(self.arc_stages) - 1:
            return None  # Already at max
        
        next_stage = self.arc_stages[current_index + 1]
        
        # Check progression criteria
        criteria_met = self.check_progression_criteria(
            memory,
            recent_session,
            next_stage
        )
        
        if criteria_met:
            return CharacterArcTransition(
                from_stage=current_stage,
                to_stage=next_stage,
                trigger=recent_session.breakthrough_moments[-1] if recent_session.breakthrough_moments else None,
                unlocked_content=self.get_unlocked_content(next_stage)
            )
        
        return None
    
    def check_progression_criteria(
        self,
        memory: CrossSessionCharacterMemory,
        recent_session: SessionRecord,
        target_stage: str
    ) -> bool:
        
        criteria = {
            "acquaintance": lambda: (
                memory.cumulative_trust >= 0.3 and
                memory.total_sessions >= 2
            ),
            "opening_up": lambda: (
                memory.cumulative_trust >= 0.5 and
                len(memory.breakthrough_moments) >= 1
            ),
            "vulnerable": lambda: (
                memory.cumulative_trust >= 0.7 and
                len(memory.breakthrough_moments) >= 2 and
                memory.total_sessions >= 6
            ),
            "transformed": lambda: (
                memory.cumulative_trust >= 0.85 and
                len(memory.breakthrough_moments) >= 3 and
                memory.total_sessions >= 10
            ),
            "actualized": lambda: (
                memory.cumulative_trust >= 0.95 and
                memory.total_sessions >= 15 and
                self.has_major_conflict_resolution(memory)
            )
        }
        
        return criteria.get(target_stage, lambda: False)()
```

---

## Greeting System

### Session Start Dialogues

```python
class SessionGreetingGenerator:
    def generate_greeting(
        self,
        actor_id: str,
        memory: CrossSessionCharacterMemory,
        time_since_last_session: timedelta
    ) -> str:
        
        # First time meeting
        if memory.total_sessions == 0:
            return self.first_meeting_greeting(actor_id)
        
        # Returning player
        stage = memory.character_arc_stage
        time_gap = time_since_last_session.days
        
        if stage == "stranger" or stage == "acquaintance":
            return self.casual_greeting(actor_id, time_gap)
        
        elif stage == "opening_up":
            return self.friendly_greeting(actor_id, time_gap, memory)
        
        elif stage == "vulnerable" or stage == "transformed":
            return self.intimate_greeting(actor_id, time_gap, memory)
        
        elif stage == "actualized":
            return self.deep_connection_greeting(actor_id, time_gap, memory)
    
    def intimate_greeting(
        self,
        actor_id: str,
        days_gap: int,
        memory: CrossSessionCharacterMemory
    ) -> str:
        
        last_memory = memory.shared_memories[-1] if memory.shared_memories else None
        
        if days_gap < 1:
            # Same day
            return f"Du bist zurückgekommen. Ich... ich habe nachgedacht über das was wir besprochen haben."
        
        elif days_gap < 7:
            # Within a week
            return f"Ich habe gehofft du würdest wiederkommen. Nach unserem letzten Gespräch..."
        
        else:
            # Longer gap
            if last_memory and last_memory.emotional_weight > 0.7:
                return f"Es ist eine Weile her. Ich habe oft an {last_memory.event_description} gedacht."
            else:
                return f"Du bist zurück. Ich dachte schon... es ist egal. Du bist hier."
```

---

## Memory Decay & Maintenance

### Forgetting Over Time

```python
class MemoryDecayEngine:
    def apply_memory_decay(
        self,
        memory: CrossSessionCharacterMemory,
        time_since_last_session: timedelta
    ) -> CrossSessionCharacterMemory:
        
        # Memories fade over real-world time
        decay_factor = min(1.0, time_since_last_session.days / 365)  # Full decay after 1 year
        
        for shared_memory in memory.shared_memories:
            if not shared_memory.canonical:  # Core facts don't decay
                # Reduce emotional weight
                shared_memory.emotional_weight *= (1.0 - decay_factor * 0.5)
                
                # Less memorable events fade faster
                if not shared_memory.memorable:
                    shared_memory.emotional_weight *= 0.7
        
        # Trust decays slightly over very long gaps
        if time_since_last_session.days > 90:
            trust_decay = min(0.2, time_since_last_session.days / 365 * 0.3)
            memory.cumulative_trust = max(0.0, memory.cumulative_trust - trust_decay)
        
        return memory
```

---

## Integration with Governance Foundation

### Package Compilation with Memory Support

```python
class MemoryAwarePackageCompiler:
    def compile_package_with_memory_hooks(
        self,
        source_content: SourceContent,
        memory_integration: bool = True
    ) -> NarrativePackage:
        
        package = self.compile_base_package(source_content)
        
        if memory_integration:
            # Add memory reference points
            for scene_id, scene in package.scenes.items():
                scene.memory_hooks = self.identify_memory_hooks(scene)
            
            # Add character arc stages to actor minds
            for actor_id, actor_mind in package.actor_minds.items():
                actor_mind.arc_stages = self.define_arc_stages(actor_id)
        
        return package

class MemoryHook(BaseModel):
    hook_id: str
    trigger_condition: str  # "high_trust" | "breakthrough_moment" | "long_absence"
    reference_type: str  # "explicit" | "subtle" | "emotional"
    suggestion: str  # What kind of memory reference fits here
```

---

## Player Experience Flow

### Session 1 (First Meeting)
```
Player: New to module
Veronique: Standard defensive baseline
→ Player builds initial trust
→ Breakthrough at Turn 45: confession
→ Session ends
→ Memory created: confession_moment, trust: 0.6
```

### Session 2 (One Week Later)
```
Player: Returns
Veronique: "Du bist zurückgekommen. Nach unserem letzten Gespräch..."
→ Starts at trust 0.6, not 0
→ References confession naturally
→ More vulnerable from start
→ New breakthrough possible at lower threshold
→ Session ends
→ Memory updated: trust: 0.75, stage: opening_up → vulnerable
```

### Session 5 (One Month Later)
```
Player: Returns after gap
Veronique: "Es ist eine Weile her. Ich habe viel nachgedacht."
→ Starts at trust 0.7 (slight decay from 0.75)
→ Different character: reflective, not defensive
→ Deep conversations available
→ Transformed dialogue branches unlocked
```

---

## Success Metrics

- **Player Return Rate:** >70% within 30 days
- **Average Sessions per Player:** >10
- **Emotional Attachment Survey:** >4.5/5
- **Memory Reference Recognition:** >85% (players notice callbacks)
- **Character Arc Completion:** >40% reach "transformed" stage

---

## Implementation Phases

### Phase 1: Foundation (2 weeks)
- Data models
- Memory formation logic
- Basic retrieval system

### Phase 2: Character Adaptation (2 weeks)
- Arc stage definitions
- Trust-based adjustments
- Greeting system

### Phase 3: Memory References (1 week)
- Dialogue callback system
- Context-aware memory selection
- Quality validation

### Phase 4: Polish (1 week)
- Decay mechanics
- Edge case handling
- Testing with real players

**Total: 6 weeks for MVP**

---

## Open Questions

1. How many sessions until players feel "real attachment"?
2. What's the right decay rate for long absences?
3. Should memories transfer between modules? (Veronique in sequel)
4. How to handle player behavior changes? (nice → mean)
5. Privacy: How long do we store cross-session data?
