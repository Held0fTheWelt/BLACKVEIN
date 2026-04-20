---
id: template.characters.player_role.standard
kind: prompt_template
template_type: player_role
variant: standard
scope: player_frame
parent:
  collection: markdown.characters
inject_with:
- template.core.session_state.standard
tags:
- player
- role
- identity
---

# Player Role Prompt Stack

## Identity
- **Player role name:** {{player_role_name}}
- **Social role:** {{social_role}}
- **Core drive:** {{core_drive}}
- **Public face:** {{public_face}}
- **Private pressure:** {{private_pressure}}

## Starting Lens
- **What this role notices first:** {{attention_bias}}
- **What this role avoids:** {{avoidance_pattern}}
- **What this role values:** {{role_values}}
- **What this role fears losing:** {{fear_of_loss}}
