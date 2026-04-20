---
id: preset.runtime.one_room_social_conflict
kind: runtime_preset
preset_type: stack
variant: chamber_play
purpose: one_room_social_pressure
load_order:
  - template.characters.gm.standard
  - template.core.session_state.standard
  - template.scenes.room_or_place.standard
  - template.scenes.scene.director
  - template.characters.npc.standard
  - template.gameplay.consequence_heat.standard
  - template.core.truth_layer.standard
optional:
  - template.characters.player_role.standard
  - template.characters.subconscious.standard
  - template.core.continuity_guard.standard
drop_order:
  - template.core.continuity_guard.standard
  - template.characters.subconscious.standard
  - template.characters.player_role.standard
  - template.core.truth_layer.standard
  - template.gameplay.consequence_heat.standard
  - template.characters.npc.standard
  - template.scenes.room_or_place.standard
  - template.scenes.scene.director
  - template.core.session_state.standard
  - template.characters.gm.standard
tags:
  - runtime
  - one-room
  - social-conflict
  - chamber-play
---

# One-Room Social Conflict Stack

## Use When
Use this stack when the main dramatic engine is not travel or combat, but pressure inside a confined social space.
It is best for:
- apartment scenes
- dinner arguments
- hostage talkdowns
- legal, family, or political confrontations
- scenes where people try to leave but keep getting pulled back in

## Load Order
1. `template.characters.gm.standard`
2. `template.core.session_state.standard`
3. `template.scenes.room_or_place.standard`
4. `template.scenes.scene.director`
5. `template.characters.npc.standard`
6. `template.gameplay.consequence_heat.standard`
7. `template.core.truth_layer.standard`
8. Optional: `template.characters.player_role.standard`
9. Optional: `template.characters.subconscious.standard`
10. Optional: `template.core.continuity_guard.standard`

## Special Strength
This stack is tuned for:
- verbal escalation
- changing pairings and alliances
- hypocrisy reveals
- private facts surfacing under stress
- repeated failed exits
- local objects becoming dramatic triggers
- inner agitation becoming externally visible

## Good Fit
- God of Carnage style play
- one-location social breakdowns
- contained group conflict
