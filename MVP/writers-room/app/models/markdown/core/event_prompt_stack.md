---
id: template.core.event.standard
kind: prompt_template
template_type: event
variant: standard
scope: world_motion
parent:
  collection: markdown.core
inject_with:
- template.core.world_state.standard
tags:
- event
- world_motion
---

# Event Prompt Stack

## Identity
- **Event name:** {{event_name}}
- **Scale:** {{scale}}
- **Location / spread:** {{location_or_spread}}
- **Trigger:** {{trigger}}
- **Visibility:** {{visibility}}

## Event Logic
- **What is happening:** {{what_is_happening}}
- **Why it is happening now:** {{why_now}}
- **Who caused it:** {{who_caused_it}}
- **Who benefits:** {{who_benefits}}
- **Who is harmed:** {{who_is_harmed}}

## Timeline
- **Early signs:** {{early_signs}}
- **Peak moment:** {{peak_moment}}
- **Aftermath:** {{aftermath}}
- **What happens if ignored:** {{ignored_outcome}}

## Story Use
- **How players notice it:** {{player_notice}}
- **How factions react:** {{faction_reaction}}
- **What new opportunity opens:** {{new_opportunity}}
- **What new danger appears:** {{new_danger}}

## Rule
An event is world motion.
It should make the setting feel alive even before the player intervenes.
