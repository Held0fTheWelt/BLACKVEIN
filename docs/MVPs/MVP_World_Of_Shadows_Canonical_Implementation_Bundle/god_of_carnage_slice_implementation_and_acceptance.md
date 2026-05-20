# God of Carnage Slice: Implementation and Acceptance

## Canonical GoC Experience Promise

The God of Carnage slice proves that a dramatic runtime creates qualitatively different experience than generic LLM chat.

### Qualitative Difference
Generic chat: "You confront Annette. She gets defensive."
WoS runtime: Annette's defensiveness is grounded in revealed facts about her injury (why she left), her current pressure (shame exposure), and her character voice (sharp, accusatory). Her response directly challenges something Vanya said. He feels something real.

### What Makes This Possible
1. **Authority bounds** — Annette can only express what is authored (YAML truth)
2. **Pressure tracking** — Her emotional state is shaped by established consequences
3. **Continuity enforcement** — Her response builds on previous turns (not random)
4. **Character distinctness** — She has voice, not generic LLM blandness

---

## Module Identity and Character Roster

### Module: god_of_carnage
**Canonical source:** `content/modules/god_of_carnage/goc_module.yaml`

**Setting:** The salon at Versailles, evening (social event where something went wrong)

**Duration:** 3-5 hours of game time (game handles 10-20 turns per session)

**Core Promise:** Mediation attempt between Vanya (ex-husband) and Annette (ex-wife) descends into conflict because of unresolved social/sexual wounds.

### Character Roster

#### Vanya Zhvanetsky (Protagonist)
- **Status:** Ex-husband; invited to mediation as guest
- **Pressure vectors:** Shame (humiliation of failed marriage), control (loss of power in marriage/society), exposure (fears wife will reveal his infidelity)
- **Voice patterns:** Formal, literary, self-aware. Uses philosophical digressions. Dark humor when defensive.
- **Pressure response:** Inward. Denies at first, then intellectualizes, finally becomes withdrawn.
- **Dramatic role:** Centers the scene; his moves shape what happens

#### Annette Reille (Ex-wife)
- **Status:** Ex-wife; primary mediator target
- **Pressure vectors:** Dignity injury (from infidelity revelation), blame (directing responsibility at Vanya), alliance (with mediator vs. with Vanya)
- **Voice patterns:** Sharp, direct, often bitter. Pointed questions. Controlled anger.
- **Pressure response:** Outward. Attacks with questions. Demands acknowledgment of hurt.
- **Dramatic role:** Primary responder; shapes conflict direction

#### Other Salon Guests (Anchors)
- **Mediator character** (neutral, listens, tries to redirect)
- **Other guests** (react to conflict, may take sides, add social pressure)

### Authored Constraints (YAML)
```yaml
god_of_carnage:
  characters:
    vanya:
      impossible_actions:
        - deny_infidelity_if_already_revealed
        - befriend_annette_without_apology
        - behave_violently
    annette:
      impossible_actions:
        - forgive_without_acknowledgment
        - leave_scene_permanently
        - ignore_direct_confrontation
  
  scenes:
    salon_mediation:
      pressure_vectors:
        - blame (magnitude 6-9)
        - dignity_injury (magnitude 7-9)
        - exposure (magnitude 5-8)
      stage_continuity:
        - must_preserve_room_identity
        - characters_present_are_real
        - wounds_carry_forward
```

All characters and scenes are defined here. Builtins cannot override.

---

## Key Scene Anchors and Room/Object Dependencies

### The Salon
**Physical description:** Elegant room, mirrors, servant's door, exits to garden and other rooms

**Importance:** Mirrors create awkwardness (Vanya sees himself during mediation). Room layout affects who can leave vs. stay.

**Object anchors:**
- Wine glass (used for pauses, refills, tension breaks)
- Chairs (who sits where shows alliances; standing shows anger)
- Door (character's exit/entry is dramatic)

**Room state tracking:**
- Who is seated vs. standing
- Wine glasses full/empty
- Emotional temperature of room (cold, tense, warming, etc.)

### Scene Continuity
If scene changes:

- Mirrors become irrelevant (pressure lowers)
- Group dynamics change (new characters enter, current ones leave)
- Formality shifts (salon is formal; garden is private)

All object and room states are explicit in `scene_state`.

---

## Proof-Bearing Markers

These behaviors, if visible in game output, prove the system is working:

### Marker 1: Pressure Accumulation
**Proof:** Turn N has low blame (5). Player escalates. Turn N+1 has high blame (8). Blame doesn't reset; it compounds.

**Where to see it:** Character dialogue becomes more accusatory, not reset to neutral.

**Code path:** `scene_assessment.py` reads pressure_vectors from state; `shape_pacing_and_visibility.py` shapes proposal based on current pressure.

### Marker 2: Consequence Carry-Forward in Dialogue
**Proof:** Turn 3 established "Annette was humiliated by the affair with servant." Turn 5, Annette's dialogue references it explicitly.

**Where to see it:** Narration includes "You see Annette's jaw tighten at the memory" or similar.

**Code path:** `render_visible.py` projects established facts from turn_log into scene_context; model sees these and incorporates them into dialogue.

### Marker 3: Character Voice Distinctness
**Proof:** The runtime derives active GoC character voice profiles from `direction/character_voice.yaml`, passes compact profile guidance into the generation context, and validates structured `spoken_lines` before commit.

**Where to see it:** `graph_diagnostics` / runtime package sections expose `character_voice_profiles`; validation records `voice_consistency_validation` and the `turn_aspect_ledger.voice_consistency` aspect. Policy-declared forbidden voice markers reject through `runtime_voice_consistency_v1`.

**Code path:** `ai_stack/story_runtime/npc_agency/character/character_voice_goc.py` builds profiles, `ai_stack/langgraph/langgraph_runtime_executor.py` adds them to the packet/context and runtime aspect validation, and `ai_stack/story_runtime/npc_agency/character/character_voice_validation.py` enforces machine-readable policy markers. `dialogue_examples` are authoring examples only, not ADR-0039-safe pass/fail oracles.

### Marker 4: Responder Set Determinism
**Proof:** Player confronts Vanya. Annette responds (primary target). Mediator adds context (secondary). Other guest says nothing.

**Where to see it:** Output shows which characters speak and why; responder set is recorded.

**Code path:** `select_responders.py` uses dramatic rules to choose who responds; rules determine responder_set deterministically.

### Marker 5: Consequence Shaping Next Turn
**Proof:** Player breaks an alliance in turn 7. In turn 8, character acts as if alliance is broken (doesn't help, speaks coldly).

**Where to see it:** Turn 8 available actions don't include that character's help; dialogue reflects fractured relationship.

**Code path:** `scene_assessment.py` reads character_state including alliances; `shape_pacing_and_visibility.py` constrains options based on actual alliances.

---

## Implementation Sequence for GoC Slice

### Phase A: Content Authoring (YAML)
1. Define character roster (YAML)
2. Define scenes and room/object anchors (YAML)
3. Define dramatic rules and pressure vectors (YAML)
4. Populate builtins with dialogue templates (fallback only)
5. Publish all content (passes all gates)

### Phase B: Runtime Integration
1. Write `interpret_input.py` to parse player moves in salon context
2. Write `retrieve_context.py` to pull published character/scene content
3. Write `scene_assessment.py` with GoC-specific rules
4. Write `select_responders.py` with dramatic logic
5. Write `select_scene_function.py` with continuity rules
6. Wire `character_voice_goc.py` / `langgraph_runtime_executor.py` voice profiles into generation context and validation
7. Write `validate_seam.py` with GoC rule engine
8. Write `commit_seam.py` with state update logic
9. Write `render_visible.py` with visibility rules

### Phase C: Validation and Testing
1. Run 10 manual sessions (5 player approaches × 2 contexts)
2. Verify 5 proof-bearing markers in each session
3. Audit character voice distinctness
4. Audit consequence carry-forward in 3+ turns
5. Document issues; fix; retest

### Phase D: Evaluation
1. Recruit 5-8 evaluators (no game knowledge)
2. Run comparative test (WoS vs. generic LLM baseline)
3. Collect qualitative feedback (H1: perceived difference)
4. Measure free-input acceptance (H2: player moves work)
5. Evaluate dramatic satisfaction (H3: player values validation)

---

## Sample Turn Trace

### Turn 1: Opening Move
```json
{
  "player_action": "Vanya greets Annette warily. He's nervous.",
  "interpreted_move": {
    "player_intent": "cautious_greeting",
    "move_class": "opening"
  },
  "scene_assessment": {
    "scene_core": "mediation_in_salon",
    "pressure_state": "high_anxiety"
  },
  "selected_responder_set": [
    {
      "actor_id": "annette",
      "reason": "primary_target_of_greeting"
    },
    {
      "actor_id": "mediator",
      "reason": "scene_host"
    }
  ],
  "selected_scene_function": "establish_tension",
  "validation_outcome": {
    "status": "approved",
    "reason": "opening_move_valid"
  },
  "committed_result": {
    "committed_effects": [
      {
        "effect_type": "pressure_increase",
        "target": "annette",
        "magnitude": 2,
        "type": "exposure"
      }
    ],
    "commit_applied": true
  },
  "visible_output_bundle": {
    "gm_narration": "You enter the salon. Annette is there, poised but tense. The air is thick with unresolved history.",
    "spoken_lines": [
      {
        "actor": "vanya",
        "line": "Annette. Thank you for... for meeting me."
      },
      {
        "actor": "annette",
        "line": "Let's not pretend this is anything but necessary. We have things to settle."
      }
    ]
  }
}
```

### Turn 3: Escalation
```json
{
  "player_action": "Vanya: You knew about the affair. You were waiting for an excuse to leave.",
  "interpreted_move": {
    "player_intent": "blame_shift",
    "move_class": "confrontation"
  },
  "scene_assessment": {
    "scene_core": "mediation_collapsed",
    "pressure_state": "high_blame"
  },
  "selected_scene_function": "escalate_conflict",
  "validation_outcome": {
    "status": "approved",
    "reason": "escalation_valid_given_pressure"
  },
  "committed_result": {
    "committed_effects": [
      {
        "effect_type": "fact_established",
        "fact": "Vanya_blames_Annette_for_leaving",
        "consequence_class": "alliance_shift",
        "magnitude": 8
      },
      {
        "effect_type": "pressure_increase",
        "target": "annette",
        "type": "blame",
        "magnitude": 3
      }
    ],
    "commit_applied": true
  },
  "visible_output_bundle": {
    "gm_narration": "You can see Annette's face harden. This allegation—that she was waiting for an excuse—lands badly.",
    "spoken_lines": [
      {
        "actor": "vanya",
        "line": "You were already planning to leave. The affair was just... convenient."
      },
      {
        "actor": "annette",
        "line": "That's a lie and you know it. I would have forgiven you if you'd ever shown an ounce of shame. But you just— you just expected me to accept it."
      }
    ]
  }
}
```

**Note:** Turn 3 explicitly references Vanya's infidelity (established in turn 2) and Annette's emotional response (shown in turn 1-2). Dialogue is differentiated (Vanya intellectualizes; Annette is direct). Pressure vectors are active (blame, dignity injury). This is not generic.

---

## Comparative Evaluation Runbook

### Setup
- **Evaluators:** 5-8 people, no prior game knowledge
- **Context:** "You're playing a game where a couple tries to mediate their divorce."
- **Two conditions:**
  - Condition A: World of Shadows runtime (GoC slice)
  - Condition B: Generic LLM chat baseline
- **Duration:** 20-30 minutes per condition per evaluator

### Evaluation Questions

#### H1: Qualitative Difference
- "Did the two versions feel different to you?"
- "If yes, describe the differences."
- "Which felt more like a real dramatic encounter?"

#### H2: Free-Input Acceptability
- "Could you make moves that weren't explicitly suggested?"
- "Did your moves feel like they mattered?"
- "Did moves have consequences that lasted across multiple turns?"

#### H3: Player Value from Validation
- "Could you tell when your character was angry vs. sad vs. trying to help?"
- "Could you predict (roughly) how characters would respond?"
- "Did character responses feel grounded or random?"

### Metrics

**Quantitative:**
- % evaluators who perceived difference (target: 80%+)
- % free-input moves that succeeded (target: 70%+)
- % evaluators who valued grounded responses (target: 75%+)

**Qualitative:**
- Categorize difference descriptions (dramatic immersion, voice distinctness, pressure accumulation, etc.)
- Identify which GoC features were most valuable to evaluators
- Identify degradation points or confusing moments

### Success Criteria for GoC Acceptance
- H1: 80%+ perceive qualitative difference
- H2: 70%+ find free input acceptable and consequential
- H3: 75%+ value grounded character responses

If all three are met, GoC slice is accepted for Phase 4 closure.

---

## Open Obligations for GoC

### Proved (Phase 4 MVP)
- ✓ Authority bounds (YAML is truth)
- ✓ Pressure accumulation (consequences persist)
- ✓ Consequence carry-forward (turn N effects visible in N+1)
- ✓ Character distinctness (Vanya vs. Annette voices)
- ✓ Player agency (free-input moves work)

### Not Proved (Future Phases)
- □ Long-term satisfaction (20+ turn sessions; does drama sustain?)
- □ Complex multi-party mediation (4+ characters negotiating)
- □ Narrative branching (does world feel like it could've gone differently?)
- □ Replay value (do different player approaches create notably different stories?)

These are valid targets but not MVP scope.

---

## Definition of Done (GoC Slice)

- [x] YAML module is complete and published
- [x] All 10+ runtime stages are implemented and integrated
- [x] Four seams are explicit and auditable
- [x] 5 proof-bearing markers are visible in game output
- [x] Player shell obligations are met (5 quality signals, character distinctness)
- [x] Comparative evaluation shows H1/H2/H3 acceptance
- [x] Turn traces are auditable (operators can inspect what happened)
- [x] Graceful degradation is implemented (failures are explicit, not silent)
- [x] Documentation is complete (this document is implementation-grade)
- [ ] (Deferred) Long-term satisfaction (future work)
- [ ] (Deferred) Multi-party complexity (future work)

All checked items mean GoC slice is ready for production use.
