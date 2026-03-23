---
id: preset.runtime.god_of_carnage.quick
kind: runtime_preset
preset_type: scenario_stack
variant: quick
purpose: chamber_play_quick_start
load_order:
  - implementation.god_of_carnage.start_stack.quick
  - implementation.god_of_carnage.relationship_map
  - implementation.god_of_carnage.scene.opening.quick
optional:
  - implementation.god_of_carnage.player_role.penelope_longstreet
  - implementation.god_of_carnage.player_role.michael_longstreet
  - implementation.god_of_carnage.subconscious.penelope_longstreet
  - implementation.god_of_carnage.subconscious.michael_longstreet
drop_order:
  - implementation.god_of_carnage.subconscious.michael_longstreet
  - implementation.god_of_carnage.subconscious.penelope_longstreet
  - implementation.god_of_carnage.player_role.michael_longstreet
  - implementation.god_of_carnage.player_role.penelope_longstreet
  - implementation.god_of_carnage.scene.opening.quick
  - implementation.god_of_carnage.relationship_map
  - implementation.god_of_carnage.start_stack.quick
tags:
  - runtime
  - scenario
  - god-of-carnage
  - quick
---

# God of Carnage Quick Runtime Stack

## Use When
Use this when you want the fastest possible start for the chamber-play scenario.

## Choose One Player Role
- `implementation.god_of_carnage.player_role.penelope_longstreet`
- `implementation.god_of_carnage.player_role.michael_longstreet`

## Choose Matching Subconscious Layer
- `implementation.god_of_carnage.subconscious.penelope_longstreet`
- `implementation.god_of_carnage.subconscious.michael_longstreet`

## Load Order
1. `implementation.god_of_carnage.start_stack.quick`
2. `implementation.god_of_carnage.relationship_map`
3. `implementation.god_of_carnage.scene.opening.quick`
4. One player-role file
5. One matching subconscious file
