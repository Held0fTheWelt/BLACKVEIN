---
id: implementation.god_of_carnage.start_stack.director
kind: runtime_stack
stack_type: scenario_start
variant: director
parent:
  scenario: implementation.god_of_carnage
references:
  required:
    - template.characters.gm.standard
    - template.characters.subconscious.standard
    - template.scenes.scene.director
    - template.core.truth_layer.standard
    - template.core.session_state.standard
    - implementation.god_of_carnage.scenario.core
    - implementation.god_of_carnage.relationship_map
    - implementation.god_of_carnage.location.longstreet_apartment
    - implementation.god_of_carnage.scene.s01_arrival_and_statement
  recommended:
    - implementation.god_of_carnage.player_role.penelope_longstreet
    - implementation.god_of_carnage.player_role.michael_longstreet
    - implementation.god_of_carnage.subconscious.penelope_longstreet
    - implementation.god_of_carnage.subconscious.michael_longstreet
    - implementation.god_of_carnage.npc.annette_reille
    - implementation.god_of_carnage.npc.alain_reille
    - implementation.god_of_carnage.scene.s02_first_departure_failure
    - implementation.god_of_carnage.scene.s03_phone_intrusions
    - implementation.god_of_carnage.scene.s04_private_hypocrisy_reveal
    - implementation.god_of_carnage.scene.s05_physical_breakpoint
    - implementation.god_of_carnage.scene.s06_rum_and_realignment
    - implementation.god_of_carnage.scene.s07_total_breakdown
    - implementation.god_of_carnage.scene.s08_unresolved_ring
tags:
  - director
  - scene_leading
  - scenario_stack
---

# Start Stack — Director

Load this when you want to run the scenario as a guided chamber play with controlled escalation.

## Director Rules
- Keep the action centered on the apartment.
- Use utility spaces only to change pressure, not to escape the core conflict.
- Escalate through language first, then disgust, then loss of inhibition.
- Preserve shifting alliances.
- Let the player's subconscious layer intensify shame, pride, disgust, dread, or self-justification without taking agency away.
- Do not let the ending become clean reconciliation.
