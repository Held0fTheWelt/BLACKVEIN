# Multiplayer Narrative — Collaborative Storytelling

## Core Concept

2-4 players experience the same story, each controlling a different character. Drama emerges from human interaction, not just AI responses.

**Single Player:** You vs AI  
**Multiplayer:** You + Friends vs Narrative Challenges

---

## Architecture

### Session Management

```python
class MultiPlayerSession(BaseModel):
    session_id: str
    story_module: str
    
    # Players
    players: dict[str, PlayerAssignment]  # player_id → assignment
    active_players: list[str]
    
    # Shared state
    canonical_narrative_state: CanonicalWorldState
    turn_order: list[str]
    current_turn_player: str
    
    # Communication
    allow_ooc_chat: bool  # out-of-character discussion
    private_channels_enabled: bool
    
    # Sync
    all_players_ready: bool
    pending_actions: dict[str, str]

class PlayerAssignment(BaseModel):
    player_id: str
    character_id: str
    role_type: str  # "protagonist" | "supporting" | "antagonist"
    
    # Private knowledge
    character_secrets: list[str]
    private_objectives: list[str]
```

---

## Turn Resolution

### Simultaneous Actions

```python
class MultiPlayerTurnResolver:
    async def resolve_turn(
        self,
        session: MultiPlayerSession,
        player_actions: dict[str, str]
    ) -> MultiPlayerTurnResult:
        
        # All players submit actions simultaneously
        # System resolves in dramatic order
        
        resolution_order = self.determine_dramatic_order(
            player_actions,
            session.canonical_narrative_state
        )
        
        results = []
        for player_id in resolution_order:
            action = player_actions[player_id]
            character_id = session.players[player_id].character_id
            
            # Generate outcome
            result = await self.generate_character_action(
                character_id=character_id,
                player_action=action,
                current_state=session.canonical_narrative_state,
                other_actions=player_actions
            )
            
            # Update shared state
            session.canonical_narrative_state = self.apply_result(
                session.canonical_narrative_state,
                result
            )
            
            results.append(result)
        
        # Detect emergent interactions
        synergies = self.detect_player_synergies(results)
        conflicts = self.detect_player_conflicts(results)
        
        return MultiPlayerTurnResult(
            results_by_player=results,
            emergent_synergies=synergies,
            emergent_conflicts=conflicts,
            new_state=session.canonical_narrative_state
        )
```

---

## Example Session

**Setup:**
- Player A (Sarah): Playing "The Investigator" (you)
- Player B (Tom): Playing Veronique
- Player C (Mike): Playing Michel

**Turn 23:**

```
Player A input: "I confront Veronique about the phone"
Player B input: "I try to change the subject"
Player C input: "I silently observe"

System resolves:
1. Player A confronts
2. Player B deflects (visible to all)
3. Player C observes (notices B is panicking)

Output to all:
> Investigator: You place the phone on the table. "Veronique, we need to talk about Laurent."
> Veronique (Player B): You laugh nervously. "Laurent? Who's Laurent? Maybe we should..."
> Michel (Player C): You notice Veronique's hands are shaking.

Shared State:
- tension: 0.6 → 0.85
- veronique_exposure: 0.3 → 0.7
- michel_suspicion: 0.4 → 0.6
```

---

## Private Actions

### Secret Moves

```python
class PrivateActionSystem:
    async def execute_private_action(
        self,
        player_id: str,
        secret_action: str,
        session: MultiPlayerSession
    ) -> PrivateActionResult:
        
        # Only this player sees the result
        result = await self.generate_secret_action_outcome(
            secret_action,
            session
        )
        
        # Other players see hint or nothing
        public_hint = self.generate_public_hint(result)
        
        return PrivateActionResult(
            private_outcome=result,  # Only for this player
            public_observation=public_hint,  # For others
            reveal_condition=result.reveal_trigger
        )
```

**Example:**
```
Player B (Veronique) private action: "I secretly text Laurent under the table"

To Player B:
> You type quickly: "He knows. Don't call."

To others:
> Veronique seems distracted, glances at phone.

IF Player A investigates:
> Perception check → Success: "You see she's typing a message"
```

---

## Player Conflict Resolution

### When Players Disagree

Player goals naturally conflict → creates dramatic tension

```
Player A wants: Immediate confrontation
Player B wants: Avoid at all costs

System creates IN-CHARACTER conflict:
> Tension between you is palpable.
> "I insist you answer," you say.
> "I won't," Veronique replies.

Player C (Michel) must choose:
[ ] Support Player A (pressure)
[ ] Protect Player B (defend)
[ ] Stay neutral
```

**This is emergent drama from player choices.**

---

## Session Flow

### Pre-Session

1. Players select or are assigned characters
2. Private objectives distributed
3. Character sheets shared
4. Session parameters set (length, pacing)

### During Session

1. Turn-based or semi-real-time
2. Private channel for secrets
3. Public channel for shared narrative
4. System narrates outcomes

### Post-Session

1. Session summary generated
2. Relationship changes saved
3. Next session hooks created
4. Player feedback collected

---

## Success Metrics

- **Session Completion:** >65% with 3+ players
- **Friend Recommendation:** >75%
- **Emergent Drama Quality:** >4.0/5
- **Return for Next Session:** >70%

---

## Implementation

**Phase 1 (3 weeks):** Core multiplayer engine
**Phase 2 (3 weeks):** Private actions & conflict resolution
**Phase 3 (2 weeks):** Session management & persistence
**Phase 4 (2 weeks):** UX & onboarding

**Total: 10 weeks**

---

## Risks

- **Coordination complexity:** Hard to schedule 3-4 people
- **Player conflict:** Real friendships tested
- **Dropout handling:** What if someone leaves mid-session?
- **Griefing:** Malicious players disrupting others

**Mitigation:** Strong session management, moderation tools, graceful degradation for dropouts
