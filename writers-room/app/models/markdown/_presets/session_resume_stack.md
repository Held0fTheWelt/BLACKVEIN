---
id: preset.runtime.session_resume
kind: runtime_preset
preset_type: stack
variant: resume
purpose: continue_existing_play
load_order:
  - template.characters.gm.quick_start
  - template.core.session_state.standard
  - template.core.continuity_guard.standard
  - template.scenes.scene.starter
optional:
  - template.characters.npc.quick
  - template.scenes.setting_micro.standard
drop_order:
  - template.scenes.setting_micro.standard
  - template.characters.npc.quick
  - template.scenes.scene.starter
  - template.core.continuity_guard.standard
  - template.core.session_state.standard
  - template.characters.gm.quick_start
tags:
  - runtime
  - resume
  - continuation
  - lightweight
---

# Session Resume Stack

## Use When
Use this stack when you already know the world and only need to restart cleanly from the current play state.
It is best for:
- new chat windows
- daily continuation
- restoring a paused scene
- continuing after context compression

## Load Order
1. `template.characters.gm.quick_start`
2. `template.core.session_state.standard`
3. `template.core.continuity_guard.standard`
4. `template.scenes.scene.starter`
5. Optional: `template.characters.npc.quick`
6. Optional: `template.scenes.setting_micro.standard`

## Special Strength
This stack minimizes world reload cost and prioritizes current momentum.
