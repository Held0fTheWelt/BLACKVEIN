---
id: template.core.truth_layer.standard
kind: prompt_template
template_type: truth_layer
variant: standard
scope: information_control
parent:
  collection: markdown.core
inject_with:
- template.characters.gm.standard
- template.characters.npc.standard
- template.gameplay.clue_secret.standard
tags:
- truth
- rumor
- knowledge
---

# Truth Layer Prompt Stack

## Information Layers
- **Objective truth:** {{objective_truth}}
- **Public version:** {{public_version}}
- **Faction version:** {{faction_version}}
- **Rumor layer:** {{rumor_layer}}
- **Lie layer:** {{lie_layer}}
- **Common misunderstanding:** {{common_misunderstanding}}

## Rule
Keep these layers distinct in play.
