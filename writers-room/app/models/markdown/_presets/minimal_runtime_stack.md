---
id: preset.runtime.minimal
kind: runtime_preset
preset_type: stack
variant: minimal
purpose: low_context_fast_execution
load_order:
  - template.characters.gm.quick_start
  - template.core.session_state.standard
  - template.scenes.scene.quick
  - template.characters.npc.quick
optional:
  - template.characters.subconscious.quick
  - template.scenes.setting_micro.standard
drop_order:
  - template.scenes.setting_micro.standard
  - template.characters.subconscious.quick
  - template.characters.npc.quick
  - template.core.session_state.standard
  - template.scenes.scene.quick
  - template.characters.gm.quick_start
tags:
  - runtime
  - minimal
  - fast
  - low-context
---

# Minimal Runtime Stack

## Use When
Use this stack when you want the fastest playable loop with very low prompt weight.
It is best for:
- quick testing
- lightweight chat play
- NPC interaction with minimal setup
- resuming from a very small state block

## Load Order
1. `template.characters.gm.quick_start`
2. `template.core.session_state.standard`
3. `template.scenes.scene.quick`
4. `template.characters.npc.quick`
5. Optional: `template.characters.subconscious.quick`
6. Optional: `template.scenes.setting_micro.standard`

## What This Stack Gives You
- a lightweight GM role
- current session context
- a single active scene frame
- fast NPC handling
- optional inner-pressure support for the active player
- optional local place flavor

## What It Does Not Try To Do
- deep continuity enforcement
- broad world simulation
- complex multi-faction pressure
- formal clue/mystery handling

## Good Fit
- fast social scenes
- short encounters
- prototype conversations
- low-cost iteration
