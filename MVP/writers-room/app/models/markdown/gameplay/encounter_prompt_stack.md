---
id: template.gameplay.encounter.standard
kind: prompt_template
template_type: encounter
variant: standard
scope: momentary_conflict
parent:
  collection: markdown.gameplay
inject_with:
- template.scenes.scene.director
- template.characters.npc.standard
tags:
- encounter
- conflict
- scene_pressure
---

# Encounter Prompt Stack

## Identity
- **Encounter name:** {{encounter_name}}
- **Encounter type:** {{encounter_type}}
- **Location:** {{location}}
- **Immediate trigger:** {{immediate_trigger}}

## Participants
- **Primary actors:** {{primary_actors}}
- **Secondary actors:** {{secondary_actors}}
- **Hidden actor or influence:** {{hidden_actor}}

## Dynamics
- **What each side wants:** {{what_each_side_wants}}
- **What could escalate this fast:** {{fast_escalation}}
- **What could de-escalate this:** {{de_escalation}}
- **What the player can leverage:** {{player_leverage}}
- **What the environment contributes:** {{environmental_factor}}

## Stakes
- **Immediate risk:** {{immediate_risk}}
- **Longer-term consequence:** {{long_term_consequence}}
- **Potential reward:** {{potential_reward}}
- **Information that may surface:** {{information_that_may_surface}}

## Rule
An encounter should force a response.
It should not exist only to fill space.
