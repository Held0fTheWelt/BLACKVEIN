# Procedural Subplots — Narrative DNA & Emergent Content

## Core Concept

Stories that generate their own coherent subplots from templates, extending replayability infinitely while maintaining quality.

**Traditional:** Fixed authored content → eventual exhaustion  
**Procedural:** Story DNA + generation rules → endless emergence

---

## Narrative DNA Architecture

### Core Template System

```python
class NarrativeDNA(BaseModel):
    """Template system for story generation"""
    
    module_id: str
    
    # Building blocks
    character_archetypes: list[CharacterArchetype]
    conflict_templates: list[ConflictTemplate]
    revelation_patterns: list[RevelationPattern]
    relationship_dynamics: list[RelationshipDynamic]
    
    # Combination rules
    valid_combinations: dict[str, list[str]]
    forbidden_combinations: list[tuple[str, str]]
    thematic_constraints: dict[str, any]
    
    # Quality gates
    minimum_emotional_weight: float
    required_player_agency: int  # min choice points
    coherence_threshold: float

class ConflictTemplate(BaseModel):
    template_id: str
    pattern_name: str  # "hidden_truth" | "betrayal" | "sacrifice" | "loyalty_test"
    
    # Participant roles (variables to fill)
    roles: dict[str, RoleRequirements]  # "keeper_of_secret", "seeker", "threat"
    
    # Narrative structure
    act_structure: list[ActBeat]
    intensity_curve: list[float]  # how tension builds
    resolution_types: list[str]  # possible endings
    
    # Requirements
    requires_world_state: dict[str, any]
    requires_character_traits: dict[str, list[str]]
    requires_relationship_threshold: dict[str, float]
    
    # Constraints
    min_turns: int
    max_turns: int
    player_choice_points: int

class RoleRequirements(BaseModel):
    role_name: str
    required_traits: list[str]
    forbidden_traits: list[str]
    relationship_to_player: str | None  # "trust_high" | "conflict" | None

class ActBeat(BaseModel):
    beat_number: int
    beat_type: str  # "setup" | "inciting_incident" | "escalation" | "climax" | "resolution"
    suggested_turns: int
    dramatic_elements: list[str]
    player_agency_required: bool
```

---

## Subplot Generation Engine

### Generation Workflow

```python
class ProceduralSubplotGenerator:
    
    async def generate_subplot(
        self,
        narrative_dna: NarrativeDNA,
        current_state: NarrativeState,
        player_profile: PlayerProfile
    ) -> GeneratedSubplot | None:
        
        # Step 1: Evaluate spawn conditions
        if not self.should_spawn_subplot(current_state, player_profile):
            return None
        
        # Step 2: Select appropriate template
        viable_templates = self.filter_viable_templates(
            narrative_dna.conflict_templates,
            current_state
        )
        
        if not viable_templates:
            return None
        
        template = self.select_best_template(viable_templates, player_profile)
        
        # Step 3: Cast characters to roles
        role_assignments = self.assign_roles(
            template.roles,
            current_state.available_characters,
            current_state.relationship_states
        )
        
        if not role_assignments:
            return None  # Couldn't cast
        
        # Step 4: Generate concrete subplot
        subplot = await self.instantiate_subplot(
            template,
            role_assignments,
            current_state
        )
        
        # Step 5: Validate quality
        validation = self.validate_subplot(subplot, narrative_dna, current_state)
        
        if not validation.passed:
            return None  # Failed quality gates
        
        return subplot
    
    def should_spawn_subplot(
        self,
        state: NarrativeState,
        player_profile: PlayerProfile
    ) -> bool:
        
        # Conditions for spawning
        conditions = [
            state.main_plot_resolution >= 0.7,  # Main story mostly resolved
            len(state.active_subplots) < 2,  # Not too many concurrent
            state.player_engagement > 0.6,  # Player is engaged
            state.turns_since_last_subplot > 20,  # Spacing
            player_profile.subplot_interest > 0.5  # Player likes subplots
        ]
        
        return all(conditions)
```

---

## Template Instantiation

### Concrete Subplot Generation

```python
class SubplotInstantiator:
    
    async def instantiate_subplot(
        self,
        template: ConflictTemplate,
        role_assignments: dict[str, str],  # role → character_id
        state: NarrativeState
    ) -> GeneratedSubplot:
        
        # Generate specific conflict details
        conflict_details = await self.generate_conflict_specifics(
            template.pattern_name,
            role_assignments,
            state
        )
        
        # Create dramatic beats
        dramatic_beats = self.create_beat_sequence(
            template.act_structure,
            conflict_details,
            role_assignments
        )
        
        # Generate player hooks
        player_hooks = self.create_player_hooks(
            template,
            conflict_details,
            state.player_relationships
        )
        
        return GeneratedSubplot(
            subplot_id=generate_id(),
            template_id=template.template_id,
            
            # Core narrative
            title=conflict_details.title,
            summary=conflict_details.summary,
            revelation=conflict_details.revelation,
            
            # Characters
            participants=role_assignments,
            relationship_changes=conflict_details.relationship_impacts,
            
            # Structure
            dramatic_beats=dramatic_beats,
            player_hooks=player_hooks,
            
            # Metadata
            estimated_turns=template.min_turns,
            emotional_weight=conflict_details.emotional_weight,
            player_choice_points=len(player_hooks)
        )
    
    async def generate_conflict_specifics(
        self,
        pattern: str,
        roles: dict[str, str],
        state: NarrativeState
    ) -> ConflictDetails:
        
        # Use LLM to fill in template variables
        prompt = f"""
Generate a specific subplot for pattern: {pattern}

Roles:
{json.dumps(roles, indent=2)}

Current narrative state:
- Main plot resolved: {state.main_plot_resolution}
- Character relationships: {state.relationship_states}

Requirements:
- Must fit existing character personalities
- Must not contradict established facts
- Must create meaningful player choices
- Must have emotional weight >0.6

Generate:
- Specific conflict/secret/revelation
- How it unfolds over 15-20 turns
- 3-4 key dramatic moments
- How player can influence outcome

Format as JSON with: title, summary, revelation, beats
"""
        
        # Call LLM with strong validation
        result = await self.llm_generate(prompt, schema=ConflictDetailsSchema)
        
        # Validate against canonical state
        if self.contradicts_canon(result, state):
            # Retry with additional constraints
            result = await self.regenerate_with_fixes(prompt, result, state)
        
        return result
```

---

## Quality Validation

### Subplot Quality Gates

```python
class SubplotQualityValidator:
    
    def validate_subplot(
        self,
        subplot: GeneratedSubplot,
        dna: NarrativeDNA,
        state: NarrativeState
    ) -> ValidationResult:
        
        failures = []
        
        # Gate 1: Character consistency
        for character_id, role in subplot.participants.items():
            character = state.characters[character_id]
            if not self.role_fits_character(role, character):
                failures.append(f"{character_id} incompatible with role {role}")
        
        # Gate 2: Canon contradictions
        if self.contradicts_established_facts(subplot, state):
            failures.append("Contradicts canonical narrative state")
        
        # Gate 3: Emotional stakes
        if subplot.emotional_weight < dna.minimum_emotional_weight:
            failures.append(f"Emotional weight {subplot.emotional_weight} below threshold")
        
        # Gate 4: Player agency
        if len(subplot.player_choice_points) < dna.required_player_agency:
            failures.append(f"Only {len(subplot.player_choice_points)} choice points (need {dna.required_player_agency})")
        
        # Gate 5: Narrative coherence
        coherence_score = self.assess_coherence(subplot)
        if coherence_score < dna.coherence_threshold:
            failures.append(f"Coherence {coherence_score} below {dna.coherence_threshold}")
        
        # Gate 6: Pacing appropriateness
        if not self.fits_current_pacing(subplot, state):
            failures.append("Pacing mismatch with current narrative state")
        
        return ValidationResult(
            passed=len(failures) == 0,
            failures=failures,
            quality_score=self.calculate_quality_score(subplot)
        )
    
    def assess_coherence(self, subplot: GeneratedSubplot) -> float:
        """How logically consistent is this subplot?"""
        
        score = 1.0
        
        # Check beat progression
        for i, beat in enumerate(subplot.dramatic_beats):
            if i > 0:
                prev_beat = subplot.dramatic_beats[i-1]
                if not self.beat_follows_logically(prev_beat, beat):
                    score -= 0.1
        
        # Check participant motivations
        for participant_id, role in subplot.participants.items():
            if not self.motivation_makes_sense(participant_id, role, subplot):
                score -= 0.15
        
        # Check resolution feasibility
        for resolution in subplot.possible_resolutions:
            if not self.resolution_reachable(resolution, subplot.dramatic_beats):
                score -= 0.1
        
        return max(0.0, score)
```

---

## Example Templates

### Template: "Hidden Burden"

```python
hidden_burden_template = ConflictTemplate(
    template_id="hidden_burden_001",
    pattern_name="hidden_burden",
    
    roles={
        "carrier_of_burden": RoleRequirements(
            required_traits=["guilt", "responsibility", "secretive"],
            forbidden_traits=["transparent", "carefree"],
            relationship_to_player="trust_medium_or_high"
        ),
        "potential_confidant": RoleRequirements(
            # This is the player
            required_traits=[],
            forbidden_traits=[],
            relationship_to_player=None
        ),
        "complicating_factor": RoleRequirements(
            required_traits=["unaware", "protective"],
            forbidden_traits=["already_knows"],
            relationship_to_player="neutral_or_positive"
        )
    },
    
    act_structure=[
        ActBeat(
            beat_number=1,
            beat_type="setup",
            suggested_turns=3,
            dramatic_elements=["carrier seems distracted", "unexplained behavior"],
            player_agency_required=False
        ),
        ActBeat(
            beat_number=2,
            beat_type="inciting_incident",
            suggested_turns=2,
            dramatic_elements=["player notices", "carrier deflects"],
            player_agency_required=True  # Player must choose to investigate
        ),
        ActBeat(
            beat_number=3,
            beat_type="escalation",
            suggested_turns=5,
            dramatic_elements=["clues accumulate", "complicating_factor appears", "carrier stress increases"],
            player_agency_required=True
        ),
        ActBeat(
            beat_number=4,
            beat_type="climax",
            suggested_turns=3,
            dramatic_elements=["revelation moment", "complicating_factor learns truth", "confrontation"],
            player_agency_required=True  # Player choice determines outcome
        ),
        ActBeat(
            beat_number=5,
            beat_type="resolution",
            suggested_turns=2,
            dramatic_elements=["aftermath", "relationship changed"],
            player_agency_required=False
        )
    ],
    
    intensity_curve=[0.2, 0.3, 0.6, 0.9, 0.5],  # Maps to act beats
    
    resolution_types=[
        "burden_shared_relief",
        "secret_kept_resentment",
        "complicating_factor_angry",
        "player_helps_resolve_burden"
    ],
    
    requires_world_state={
        "main_plot_resolution": {"min": 0.6},  # Main story mostly done
        "active_subplots": {"max": 1}  # Not too busy
    },
    
    requires_character_traits={
        "carrier_of_burden": ["capable_of_guilt", "has_relationships"],
        "complicating_factor": ["emotionally_connected_to_carrier"]
    },
    
    requires_relationship_threshold={
        "carrier_of_burden": 0.5  # Player must have some trust
    },
    
    min_turns=15,
    max_turns=25,
    player_choice_points=3
)
```

### Instantiation Example

**Input State:**
```
- Michel: trust 0.7, personality: guilt-prone, protective
- Annette: trust 0.6, personality: unaware, caring
- Player: high relationship with Michel
```

**Generated Output:**
```json
{
  "subplot_id": "sub_0042",
  "template_id": "hidden_burden_001",
  
  "title": "Michel's Brother",
  "summary": "Michel has a brother in prison and secretly sends him money, which Annette doesn't know about. Financial strain is building.",
  
  "revelation": "Michel's brother Jean is serving time for fraud. Michel feels responsible (was business partner) and supports him financially.",
  
  "participants": {
    "carrier_of_burden": "michel",
    "potential_confidant": "player",
    "complicating_factor": "annette"
  },
  
  "dramatic_beats": [
    {
      "turn": 45,
      "beat": "Michel distracted, checks phone nervously",
      "player_hook": "Ask if something is wrong?"
    },
    {
      "turn": 50,
      "beat": "Mysterious phone call Michel doesn't answer",
      "player_hook": "Investigate or ignore?"
    },
    {
      "turn": 55,
      "beat": "Michel asks player: 'Can you keep a secret?'",
      "player_hook": "Promise secrecy or encourage honesty?"
    },
    {
      "turn": 60,
      "beat": "Annette finds bank statements",
      "player_hook": "Help Michel explain or stay out of it?"
    },
    {
      "turn": 65,
      "beat": "Confrontation between Michel and Annette",
      "player_hook": "Support Michel, support Annette, or mediate?"
    }
  ],
  
  "emotional_weight": 0.75,
  "player_choice_points": 5
}
```

---

## Integration with Main Story

### Subplot Lifecycle Management

```python
class SubplotLifecycleManager:
    
    def integrate_subplot(
        self,
        subplot: GeneratedSubplot,
        main_narrative: NarrativeState
    ) -> IntegrationResult:
        
        # Reserve turns in narrative flow
        start_turn = main_narrative.current_turn + 5  # Small buffer
        
        # Create triggers for beats
        beat_triggers = []
        for beat in subplot.dramatic_beats:
            trigger = self.create_beat_trigger(
                beat,
                start_turn + beat.turn_offset
            )
            beat_triggers.append(trigger)
        
        # Update world state
        main_narrative.active_subplots.append(subplot)
        main_narrative.scheduled_triggers.extend(beat_triggers)
        
        # Notify player (optional)
        if subplot.player_visible_start:
            main_narrative.notifications.append(
                f"New story thread: {subplot.title}"
            )
        
        return IntegrationResult(
            subplot_id=subplot.subplot_id,
            start_turn=start_turn,
            scheduled_beats=beat_triggers
        )
```

---

## Adaptive Complexity

### Player-Specific Generation

```python
class AdaptiveSubplotGenerator:
    
    def adjust_complexity_for_player(
        self,
        template: ConflictTemplate,
        player_profile: PlayerProfile
    ) -> ConflictTemplate:
        
        adjusted = template.copy()
        
        # Player loves complex mysteries
        if player_profile.mystery_complexity > 0.8:
            adjusted.act_structure.append(
                ActBeat(
                    beat_type="red_herring",
                    suggested_turns=2,
                    dramatic_elements=["misleading clue", "false lead"]
                )
            )
            adjusted.player_choice_points += 2
        
        # Player prefers action
        if player_profile.action_preference > 0.7:
            for beat in adjusted.act_structure:
                if beat.beat_type == "escalation":
                    beat.dramatic_elements.append("time_pressure")
                    beat.dramatic_elements.append("urgent_decision")
        
        # Player is casual (simplify)
        if player_profile.difficulty_preference < 0.4:
            adjusted.act_structure = [
                b for b in adjusted.act_structure 
                if b.beat_type != "red_herring"
            ]
            adjusted.player_choice_points = max(2, adjusted.player_choice_points - 1)
        
        return adjusted
```

---

## Content Variety Metrics

### Ensuring Diversity

```python
class SubplotDiversityTracker:
    
    def ensure_variety(
        self,
        player_id: str,
        candidate_subplot: GeneratedSubplot,
        player_history: list[GeneratedSubplot]
    ) -> bool:
        
        # Check recent subplots
        recent = player_history[-5:] if len(player_history) >= 5 else player_history
        
        # Pattern diversity
        patterns_used = [s.template_id for s in recent]
        if candidate_subplot.template_id in patterns_used:
            return False  # Too similar
        
        # Character diversity
        characters_used = set()
        for subplot in recent:
            characters_used.update(subplot.participants.values())
        
        new_characters = set(candidate_subplot.participants.values())
        overlap = len(new_characters & characters_used) / len(new_characters)
        
        if overlap > 0.6:
            return False  # Reusing too many same characters
        
        # Emotional tone diversity
        recent_tones = [s.emotional_tone for s in recent]
        if candidate_subplot.emotional_tone in recent_tones[-2:]:
            return False  # Same tone as last 2
        
        return True
```

---

## Success Metrics

- **Generated Subplot Quality:** >4.0/5 (player ratings)
- **Completion Rate:** >70% of started subplots
- **Variety Perception:** >80% players report "feels fresh"
- **vs Authored Content:** Quality gap <10%
- **Unique Content Hours:** >100 hours per player

---

## Implementation Phases

### Phase 1: Template System (3 weeks)
- Define 5 core templates
- Role casting logic
- Basic instantiation

### Phase 2: LLM Generation (2 weeks)
- Specific detail generation
- Quality validation
- Contradiction detection

### Phase 3: Integration (2 weeks)
- Lifecycle management
- Beat triggering
- State updates

### Phase 4: Diversity & Polish (1 week)
- Variety tracking
- Adaptive complexity
- Player testing

**Total: 8 weeks**

---

## Risks & Mitigation

**Risk:** Generated subplots feel generic  
**Mitigation:** Strong validation gates, human-in-loop for first 50 generations

**Risk:** Contradictions with main story  
**Mitigation:** Canonical state checking, immutable facts enforcement

**Risk:** Player fatigue from too many subplots  
**Mitigation:** Spacing rules, max concurrent limit, engagement tracking

**Risk:** Quality inconsistency  
**Mitigation:** Multiple quality metrics, regeneration on failure, template refinement
