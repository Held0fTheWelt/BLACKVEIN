---
id: preset.runtime.campaign_bootstrap
kind: runtime_preset
preset_type: stack
variant: campaign_boot
purpose: world_and_conflict_initialization
load_order:
  - template.characters.gm.standard
  - template.scenes.setting_macro.standard
  - template.scenes.district.standard
  - template.factions.faction.standard
  - template.core.world_state.standard
  - template.core.session_state.standard
  - template.core.continuity_guard.standard
optional:
  - template.gameplay.quest.standard
  - template.core.event.standard
drop_order:
  - template.core.event.standard
  - template.gameplay.quest.standard
  - template.core.continuity_guard.standard
  - template.core.world_state.standard
  - template.factions.faction.standard
  - template.scenes.district.standard
  - template.scenes.setting_macro.standard
  - template.core.session_state.standard
  - template.characters.gm.standard
tags:
  - runtime
  - campaign
  - bootstrap
  - setup
---

# Campaign Bootstrap Stack

## Use When
Use this stack at the beginning of a campaign, region, district, or major arc reset.
It is best for:
- defining the active map of power
- grounding the player in a larger environment
- initializing faction pressure
- opening a new chapter cleanly

## Load Order
1. `template.characters.gm.standard`
2. `template.scenes.setting_macro.standard`
3. `template.scenes.district.standard`
4. `template.factions.faction.standard`
5. `template.core.world_state.standard`
6. `template.core.session_state.standard`
7. `template.core.continuity_guard.standard`
8. Optional: `template.gameplay.quest.standard`
9. Optional: `template.core.event.standard`

## Special Strength
This stack creates strong world grounding before play narrows to a scene.
