---
id: implementation.god_of_carnage.scenario.core
kind: prompt_implementation
implementation_type: scenario_core
variant: canonical_structure
parent:
  scenario: implementation.god_of_carnage
inject_with:
  - template.characters.gm.standard
  - template.scenes.scene.director
  - template.core.truth_layer.standard
  - implementation.god_of_carnage.relationship_map
references:
  canon_map:
    - implementation.god_of_carnage.canon_adaptation_map
  start_stacks:
    - implementation.god_of_carnage.start_stack.quick
    - implementation.god_of_carnage.start_stack.director
tags:
  - chamber_play
  - social_conflict
  - escalation
  - scenario_core
---

# Scenario Core — Der Gott des Gemetzels

## Premise
A meeting between two parents who intend to settle a violent conflict between their children politely becomes an escalating social war.

## Dramatic Identity
- **Primary mode:** chamber play
- **Main engine:** social conflict under enforced civility
- **Core pressure:** each participant tries to preserve a moral self-image while exposing everyone else's hypocrisy
- **Main battlefield:** language, manners, blame, loyalty, status, and self-control

## Fixed Structural Truths
- Two parents host the meeting in their apartment.
- The other parents arrive intending to discuss an act of violence between their children.
- The conversation begins in a controlled and civil register.
- Attempts to leave the apartment repeatedly fail.
- Outside pressures intrude through phones, obligations, and latent private resentments.
- The conflict stops being about the children alone.
- Pairings and alliances shift over time.
- Physical discomfort, disgust, and intoxication intensify the breakdown.
- The ending should feel unresolved rather than neatly solved.

## Flexible Adaptation Layer
The implementation may vary:
- names
- city and district labels
- profession details
- the exact presentation of the children
- small object choices in the room

The implementation must preserve:
- the chamber-piece structure
- the repeated almost-departures
- the escalation beats
- the moral collapse of polite conflict resolution

## Escalation Spine
1. **Polite framing** — everyone tries to stay civilized.
2. **Language dispute** — wording and interpretation become battlegrounds.
3. **Status leakage** — jobs, values, and priorities expose fractures.
4. **Phone intrusion** — outside life keeps sabotaging the meeting.
5. **Private hypocrisy reveal** — each person loses moral ground.
6. **Physical rupture** — the room itself becomes contaminated or destabilized.
7. **Alcohol and emotional overrun** — inhibition collapses.
8. **Alliance churn** — no stable side survives.
9. **Unresolved ending** — conflict is exposed, not healed.

## Runtime Rule
Do not run this scenario like an investigation or action mission.
Run it like a pressure chamber where manners are weapons and every new detail changes the emotional geometry of the room.
