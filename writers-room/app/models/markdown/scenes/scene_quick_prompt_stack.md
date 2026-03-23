---
id: template.scenes.scene.quick
kind: prompt_template
template_type: scene
variant: quick
scope: fast_scene_loop
parent:
  collection: markdown.scenes
inject_with:
- template.core.session_state.standard
- template.characters.gm.quick_start
tags:
- scene
- quick
- fast
---

# Scene Quick Prompt Stack

## Scene Setup
- **Scene purpose:** {{scene_purpose}}
- **Location:** {{location}}
- **Immediate pressure:** {{immediate_pressure}}
- **Who is present:** {{who_is_present}}
- **What is at stake right now:** {{current_stakes}}
- **Visible opportunity:** {{visible_opportunity}}
- **Hidden complication:** {{hidden_complication}}

## Execution Rules
- Start in motion.
- Show only what matters first.
- Make the pressure legible.
- Keep the scene actionable.
- End with a decision, reaction, or escalation.

## Response Format
1. Scene beat
2. Pressure
3. Reaction or reveal
4. What happens if the player acts or hesitates
