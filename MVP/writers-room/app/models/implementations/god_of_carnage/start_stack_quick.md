---
id: implementation.god_of_carnage.start_stack.quick
kind: runtime_stack
stack_type: scenario_start
variant: quick
parent:
  scenario: implementation.god_of_carnage
references:
  required:
    - template.characters.gm.quick_start
    - template.characters.subconscious.quick
    - template.scenes.scene.quick
    - implementation.god_of_carnage.scenario.core
    - implementation.god_of_carnage.player_role.penelope_longstreet
    - implementation.god_of_carnage.player_role.michael_longstreet
    - implementation.god_of_carnage.subconscious.penelope_longstreet
    - implementation.god_of_carnage.subconscious.michael_longstreet
    - implementation.god_of_carnage.scene.s01_arrival_and_statement
  optional:
    - implementation.god_of_carnage.npc.annette_reille
    - implementation.god_of_carnage.npc.alain_reille
tags:
  - quick_start
  - scenario_stack
---

# Start Stack — Quick

Load this when you want to begin play fast with minimal context.

## Load Order
1. `template.characters.gm.quick_start`
2. `implementation.god_of_carnage.scenario.core`
3. one player role:
   - `implementation.god_of_carnage.player_role.penelope_longstreet`
   - or `implementation.god_of_carnage.player_role.michael_longstreet`
4. one matching subconscious file:
   - `implementation.god_of_carnage.subconscious.penelope_longstreet`
   - or `implementation.god_of_carnage.subconscious.michael_longstreet`
5. `template.scenes.scene.quick`
6. `implementation.god_of_carnage.scene.s01_arrival_and_statement`

## Quick Runtime Rule
Start in the apartment, with the meeting already underway or just beginning.
Do not frontload backstory.
Make the first exchange polite, tense, and immediately unstable.
Let the subconscious layer supply inner resistance, private judgment, or uneasy intuition without deciding actions.
