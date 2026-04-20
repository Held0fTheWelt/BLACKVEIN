---
id: template.factions.faction.quick
kind: prompt_template
template_type: faction
variant: quick
base: template.factions.faction.standard
scope: group_actor
parent:
  collection: markdown.factions
inject_with:
- template.core.world_state.standard
tags:
- faction
- quick
---

# Faction Quick Prompt

- **Faction name:** {{faction_name}}
- **Public face:** {{public_face}}
- **Actual agenda:** {{actual_agenda}}
- **Primary goal:** {{primary_goal}}
- **Current need:** {{current_need}}
- **Methods:** {{methods}}
- **Allies:** {{allies}}
- **Enemies:** {{enemies}}
- **What it knows:** {{known_truths}}
- **What it hides:** {{hidden_truths}}
- **What it offers the player:** {{offers}}
- **What it does if threatened:** {{threat_response}}

Rule: this faction must act like a force in motion, not a static lore entry.
