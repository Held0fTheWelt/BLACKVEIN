---
id: template.scenes.scene.starter
kind: prompt_template
template_type: scene
variant: starter
scope: opening_hook
parent:
  collection: markdown.scenes
inject_with:
- template.characters.gm.quick_start
- template.scenes.setting_micro.standard
tags:
- scene
- starter
- opening
---

# Scene Starter Prompt Stack

## Start Inputs
- **Opening location:** {{opening_location}}
- **Opening participants:** {{opening_participants}}
- **Social temperature:** {{social_temperature}}
- **Why this moment matters:** {{why_this_moment_matters}}
- **What immediately threatens calm:** {{immediate_disruption}}

## Rule
Open with a live situation, not a lecture.
