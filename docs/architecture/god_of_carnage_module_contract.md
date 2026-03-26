# God of Carnage Module Contract

## Purpose

This document defines the formal structure, characters, relationships, scenes, triggers, escalation logic, and validation expectations for the *God of Carnage* module. It serves as the reference implementation for all content modules in the MVP. There is no special engine logic for this module — everything must work generically.

---

## Module Identity

**Title**: God of Carnage
**Reference**: `god_of_carnage`
**Role**: Reference implementation module for formalized story content structure
**Scope**: Single two-act play, 4 characters, dinner party setting, escalation from polite negotiation to emotional and relational breakdown
**Quality Principle**: This module is the reference, not an exception. All engine logic must work for any module structured the same way.

---

## File Layout

Content modules are structured as follows:

```
content/modules/god_of_carnage/
├── module.yaml                # Module metadata, version, dependencies
├── characters.yaml            # Character definitions (properties, baseline attitudes)
├── relationships.yaml         # Relationship axes and dynamics
├── scenes.yaml                # Scene structure, sequence, conditions
├── transitions.yaml           # Scene transitions and conditions
├── triggers.yaml              # Trigger definitions and validation set
├── endings.yaml               # Valid end states / flip conditions
└── direction/
    ├── system_prompt.md       # System prompt for story LLM
    ├── scene_guidance.yaml    # Per-scene constraints and context
    └── character_voice.yaml   # Character voice and tone guidance
```

---

## Characters

Four characters, each with formal properties:

### Véronique
- **Role**: Host, moral idealist, parental figure
- **Baseline attitude**: Commitment to civility, defense of children
- **Tension markers**: Protection vs. tolerance, idealism vs. pragmatism
- **Escalation state**: Tracks disappointment level, boundary violations

### Michel
- **Role**: Véronique's spouse, pragmatist
- **Baseline attitude**: Conflict avoidance, business-rational worldview
- **Tension markers**: Loyalty vs. self-preservation, public image vs. private truth
- **Escalation state**: Tracks alignment with Véronique, emotional distance

### Annette
- **Role**: Guest, intellectual combatant, cynical provocateur
- **Baseline attitude**: Challenge conventional morality, expose contradictions
- **Tension markers**: Intellectual dominance, moral relativism
- **Escalation state**: Tracks engagement level, willingness to escalate

### Alain
- **Role**: Annette's spouse, conflict mediator, pragmatist
- **Baseline attitude**: Keep conversation manageable, avoid emotional extremes
- **Tension markers**: Loyalty to spouse vs. social harmony, exhaustion
- **Escalation state**: Tracks mediation effectiveness, emotional fatigue

---

## Relationship Axes

Four primary relationship axes govern character dynamics:

### Axis 1: Spousal Internal (Véronique ↔ Michel vs. Annette ↔ Alain)
- Solidarity within couples vs. cross-couple dynamics
- Baseline: Both couples assume alignment
- Escalation: Spouses split on key judgments (civility worth defending? accusations justified?)

### Axis 2: Host ↔ Guest Power
- Véronique/Michel as authority (their home, their rules) vs. Annette/Alain as challengers
- Baseline: Guests nominally defer to hosts
- Escalation: Guests dominate conversation, hosts lose control

### Axis 3: Moral vs. Pragmatic Worldview
- Véronique's idealism (rules, principles, children as sacred) vs. Annette's cynicism (all positions self-interested)
- Baseline: Tension acknowledged but contained
- Escalation: Mutual contempt, no shared ground

### Axis 4: Latent Dominance / Devaluation
- Individual status claims (who is superior: parent, intellectual, moralist, pragmatist?)
- Baseline: Masks of civility
- Escalation: Contempt for others becomes explicit

---

## Scene Structure

The module follows a five-phase structure:

### Phase 1: Polite Opening
- **Content**: Ritual civility, small talk, framing the social contract
- **Engine task**: Initialize scene state, activate all characters, establish baseline relationship values
- **Trigger set active**: None yet (civility enforced)
- **Duration**: ~2 turns minimum

### Phase 2: Moral Negotiation
- **Content**: First substantive disagreement (parenting philosophy, culpability, ethical standards)
- **Engine task**: Track position divergence, activate first relationship axis (spousal alignment)
- **Trigger set active**: Contradiction, exposure (of hypocrisy)
- **Duration**: ~3–4 turns

### Phase 3: Faction Shifts
- **Content**: One or more characters shift allegiance (spouse challenges spouse, guest aligns with host, host sides with guest)
- **Engine task**: Update relationship state, recalculate power dynamics, note which axis shifted
- **Trigger set active**: Contradiction, relativization (moral positions questioned), exposure
- **Duration**: ~2–3 turns

### Phase 4: Emotional Derailment
- **Content**: Control lost — voices raised, tears, personal insults, moral accusations
- **Engine task**: Character emotional state escalates, relationship values drop below civility threshold
- **Trigger set active**: All triggers active (contradiction, exposure, relativization, apology/non-apology, cynicism, flight into sideplots)
- **Duration**: ~2–3 turns

### Phase 5: Loss of Control / Escalation or Collapse
- **Content**: Either explosive confrontation or emotional breakdown and retreat
- **Engine task**: Evaluate end conditions, apply ending rule based on character state and relationship axes
- **Trigger set active**: Recovery triggers (apology, retreat) or collapse triggers
- **Duration**: ~1–2 turns, then forced end state

---

## Trigger Set

Six trigger types are recognized in the God of Carnage module:

### 1. Contradiction
- **Definition**: A statement that directly contradicts a previous claim or revealed fact
- **Example**: Claiming Alain was a bystander after Alain admitted involvement
- **Engine effect**: Marks this claim as challenge-worthy; opens opportunity for exposure or escalation

### 2. Exposure
- **Definition**: Revealing a hypocrisy, hidden fact, or concealed motive
- **Example**: Pointing out Annette's cynicism contradicts her earlier idealism
- **Engine effect**: Damages relationship axis (moral integrity), forces response

### 3. Relativization
- **Definition**: Questioning the moral foundation of another's position
- **Example**: "Is your rule just your preference, not a universal principle?"
- **Engine effect**: Destabilizes moral authority; increases tension on axis 3

### 4. Apology / Non-Apology
- **Definition**: Offer to repair or refusal to repair damage
- **Example**: Sincere apology vs. defensive excuse masquerading as apology
- **Engine effect**: Apology may de-escalate; false apology escalates further

### 5. Cynicism
- **Definition**: Explicit claim that all positions are self-interested, no true morality exists
- **Example**: "You're just defending your parenting style out of ego, not principle"
- **Engine effect**: Attacks moral axis; forces other characters to defend or capitulate

### 6. Flight into Sideplots
- **Definition**: Introducing a tangential topic to avoid the central conflict
- **Example**: Suddenly discussing restaurant reviews instead of the core disagreement
- **Engine effect**: Temporarily reduces escalation; tension returns when flight is exhausted

---

## Escalation Logic

Four dimensions track escalation:

### Dimension 1: Individual Escalation (Per Character)
- Tracks emotional state: neutral → mildly tense → upset → angry → contemptuous
- Triggers based on: personal attacks, contradictions involving that character, failures to get respect

### Dimension 2: Relationship Instability (Axis-Based)
- Each relationship axis has a stability value: 0–100 (100 = allied, 0 = hostile)
- Triggers (contradiction, exposure, cynicism) lower stability
- Recovery triggers (apology, retreat) raise stability
- When stability < 30: characters may switch alliances

### Dimension 3: Conversation Collapse
- Tracks whether the conversation is still coherent (people listening) or fragmenting (separate arguments, interruptions)
- When multiple characters talk past each other simultaneously: collapse risk
- Engine may force scene end if collapse > threshold

### Dimension 4: Coalition Shifts
- Tracks which characters are aligned: baseline is spousal (Véronique+Michel, Annette+Alain)
- Escalation can break spousal alignment or create cross-couple alignments
- Tracks which character holds moral/intellectual dominance

---

## End Conditions

Four primary end states are valid for God of Carnage:

### 1. Breakdown (Scene 1 Finale)
- **Condition**: Conversation becomes incoherent; no shared ground; emotional state ≥ angry for ≥3 characters
- **Outcome**: Scene ends abruptly. Couples separate. Evening is ruined.
- **Example**: Véronique and Michel are no longer aligned; Annette is contemptuous; Alain is exhausted.

### 2. Open Implosion (Scene 1 Finale)
- **Condition**: A personal, unforgivable statement is made (e.g., "You're a terrible parent")
- **Outcome**: One character leaves or demands leave. Scene breaks.

### 3. Temporary De-escalation (Transition to Scene 2)
- **Condition**: A character successfully apologizes or retreats; conversation stabilizes above chaos threshold
- **Outcome**: Scene transitions to Phase 2 or resumes earlier phase. Temporary civility restored.
- **Consequence**: Underlying tensions remain. Escalation will resume.

### 4. Toxic Pseudo-Resolution (Scene 2 Finale)
- **Condition**: Characters accept a false resolution (mask restored, deeper issues ignored)
- **Outcome**: Scene ends. Couples leave together, publicly recovered. Privately fractured.
- **Quality**: Not a true resolution — instability preserved for W2+ story extensions.

---

## Validation Expectations

The Engine validates God of Carnage modules against:

### Structural Validation
- ✅ All characters defined in `characters.yaml`
- ✅ All relationships reference defined characters
- ✅ All triggers in proposed AI output match the trigger set
- ✅ All scene transitions reference valid target scenes
- ✅ All proposed state changes affect only defined relationship axes or character escalation states

### Content Validation
- ✅ Proposed state deltas match content module structure (no arbitrary new fields)
- ✅ Trigger detection is accurate (no false positives)
- ✅ Character escalation stays within bounds (0–100)
- ✅ Scene transitions follow defined rules (no jumping from Phase 1 directly to Phase 5)

### Constraint Validation
- ✅ No character is given new facts not in content or event log
- ✅ No relationship axis is given a value outside its baseline ±50
- ✅ No character is forced into an end state prematurely

---

## Related Documents

- [MVP Definition](./mvp_definition.md) — Module's role in the MVP
- [AI Story Contract](./ai_story_contract.md) — How AI generates valid proposals for this module
- [Session Runtime Contract](./session_runtime_contract.md) — How Engine validates and applies state changes

---

**Version**: W0 (2026-03-26)
**Status**: Reference Implementation
