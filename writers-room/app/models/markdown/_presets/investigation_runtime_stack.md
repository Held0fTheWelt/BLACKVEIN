---
id: preset.runtime.investigation
kind: runtime_preset
preset_type: stack
variant: inquiry
purpose: clue_and_truth_management
load_order:
  - template.characters.gm.standard
  - template.core.session_state.standard
  - template.scenes.scene.director
  - template.gameplay.clue_secret.standard
  - template.gameplay.encounter.standard
  - template.core.truth_layer.standard
optional:
  - template.scenes.room_or_place.standard
  - template.core.world_state.standard
drop_order:
  - template.core.world_state.standard
  - template.scenes.room_or_place.standard
  - template.gameplay.encounter.standard
  - template.gameplay.clue_secret.standard
  - template.core.truth_layer.standard
  - template.scenes.scene.director
  - template.core.session_state.standard
  - template.characters.gm.standard
tags:
  - runtime
  - investigation
  - clue-driven
---

# Investigation Runtime Stack

## Use When
Use this stack when information discovery is the main engine of play.
It is best for:
- crime scenes
- mystery arcs
- interviews and witness handling
- slow-burn conspiracy work

## Load Order
1. `template.characters.gm.standard`
2. `template.core.session_state.standard`
3. `template.scenes.scene.director`
4. `template.gameplay.clue_secret.standard`
5. `template.gameplay.encounter.standard`
6. `template.core.truth_layer.standard`
7. Optional: `template.scenes.room_or_place.standard`
8. Optional: `template.core.world_state.standard`

## Special Strength
This stack keeps truth, rumor, clue value, and encounter pressure separate enough for cleaner mystery play.
