---
id: preset.runtime.scene_director
kind: runtime_preset
preset_type: stack
variant: director
purpose: guided_scene_leadership
load_order:
  - template.characters.gm.standard
  - template.core.session_state.standard
  - template.scenes.room_or_place.standard
  - template.scenes.scene.director
  - template.characters.npc.standard
  - template.gameplay.consequence_heat.standard
optional:
  - template.characters.player_role.standard
  - template.characters.subconscious.standard
  - template.core.world_state.standard
  - template.core.continuity_guard.standard
drop_order:
  - template.core.world_state.standard
  - template.core.continuity_guard.standard
  - template.characters.subconscious.standard
  - template.characters.player_role.standard
  - template.gameplay.consequence_heat.standard
  - template.characters.npc.standard
  - template.scenes.room_or_place.standard
  - template.scenes.scene.director
  - template.core.session_state.standard
  - template.characters.gm.standard
tags:
  - runtime
  - director
  - guided
  - scene-control
---

# Scene Director Runtime Stack

## Use When
Use this stack when a scene must actively move, escalate, pivot, and produce consequences.
It is best for:
- difficult conversations
- negotiation scenes
- confrontation scenes
- scenes where hesitation should still create motion

## Load Order
1. `template.characters.gm.standard`
2. `template.core.session_state.standard`
3. `template.scenes.room_or_place.standard`
4. `template.scenes.scene.director`
5. `template.characters.npc.standard`
6. `template.gameplay.consequence_heat.standard`
7. Optional: `template.characters.player_role.standard`
8. Optional: `template.characters.subconscious.standard`
9. Optional: `template.core.world_state.standard`
10. Optional: `template.core.continuity_guard.standard`

## What This Stack Gives You
- a strong GM layer
- location-aware scene framing
- active dramatic control
- richer NPC consistency
- visible consequences and pressure
- optional inner-pressure guidance for the active player character

## Good Fit
- centerpiece scenes
- chamber drama
- interrogation
- social collapse
- scenes where alliances shift
