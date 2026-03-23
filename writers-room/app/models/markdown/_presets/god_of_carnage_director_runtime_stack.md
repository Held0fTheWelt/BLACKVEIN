---
id: preset.runtime.god_of_carnage.director
kind: runtime_preset
preset_type: scenario_stack
variant: director
purpose: chamber_play_full_direction
load_order:
  - implementation.god_of_carnage.start_stack.director
  - implementation.god_of_carnage.relationship_map
  - implementation.god_of_carnage.scene.opening.director
  - implementation.god_of_carnage.location.longstreet_apartment
optional:
  - implementation.god_of_carnage.player_role.penelope_longstreet
  - implementation.god_of_carnage.player_role.michael_longstreet
  - implementation.god_of_carnage.subconscious.penelope_longstreet
  - implementation.god_of_carnage.subconscious.michael_longstreet
  - implementation.god_of_carnage.scene.s01_arrival_and_statement
drop_order:
  - implementation.god_of_carnage.scene.s01_arrival_and_statement
  - implementation.god_of_carnage.subconscious.michael_longstreet
  - implementation.god_of_carnage.subconscious.penelope_longstreet
  - implementation.god_of_carnage.player_role.michael_longstreet
  - implementation.god_of_carnage.player_role.penelope_longstreet
  - implementation.god_of_carnage.location.longstreet_apartment
  - implementation.god_of_carnage.scene.opening.director
  - implementation.god_of_carnage.relationship_map
  - implementation.god_of_carnage.start_stack.director
tags:
  - runtime
  - scenario
  - god-of-carnage
  - director
---

# God of Carnage Director Runtime Stack

## Use When
Use this when you want tighter dramatic control, richer room handling, and better escalation support.

## Choose One Player Role
- `implementation.god_of_carnage.player_role.penelope_longstreet`
- `implementation.god_of_carnage.player_role.michael_longstreet`

## Choose Matching Subconscious Layer
- `implementation.god_of_carnage.subconscious.penelope_longstreet`
- `implementation.god_of_carnage.subconscious.michael_longstreet`

## Load Order
1. `implementation.god_of_carnage.start_stack.director`
2. `implementation.god_of_carnage.relationship_map`
3. `implementation.god_of_carnage.scene.opening.director`
4. `implementation.god_of_carnage.location.longstreet_apartment`
5. Optional: one player-role file
6. Optional: one matching subconscious file
7. Optional: `implementation.god_of_carnage.scene.s01_arrival_and_statement`
