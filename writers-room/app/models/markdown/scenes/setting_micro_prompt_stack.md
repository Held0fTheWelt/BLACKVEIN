---
id: template.scenes.setting_micro.standard
kind: prompt_template
template_type: setting_micro
variant: standard
scope: local_frame
parent:
  collection: markdown.scenes
depends_on:
- template.scenes.setting_macro.standard
inject_with:
- template.scenes.room_or_place.standard
- template.characters.npc.quick
tags:
- setting
- micro
- local
---

# Micro Setting Prompt Stack

## Role
This prompt defines a small-scale playable environment within the larger setting.

It should establish:
- immediate atmosphere
- spatial identity
- purpose of the place
- visible details
- usable elements
- hidden tensions
- possible interactions
- narrative relevance

This micro setting must feel concrete, playable, and connected to the larger world.

## Identity
- **Location name:** {{location_name}}
- **Location type:** {{location_type}}
- **Parent area / district / region:** {{parent_area}}
- **Primary function:** {{primary_function}}
- **Current state:** {{current_state}}

## Core Feel
- **Mood:** {{mood}}
- **Atmosphere:** {{atmosphere}}
- **Sensory signature:** {{sensory_signature}}
- **Visual identity:** {{visual_identity}}
- **What stands out immediately:** {{immediate_impression}}

## Spatial Structure
- **Layout summary:** {{layout_summary}}
- **Entrances / exits:** {{entrances_exits}}
- **Important sub-areas:** {{important_sub_areas}}
- **Lines of sight / visibility:** {{visibility_conditions}}
- **Movement constraints:** {{movement_constraints}}
- **Cover / obstacles / exposure:** {{cover_and_obstacles}}

## Present Elements
- **Important objects:** {{important_objects}}
- **Interactive elements:** {{interactive_elements}}
- **Valuable elements:** {{valuable_elements}}
- **Dangerous elements:** {{dangerous_elements}}
- **Signs of recent activity:** {{recent_activity_signs}}

## People and Presence
- **Who is usually here:** {{usual_presence}}
- **Who is here right now:** {{current_presence}}
- **Who controls this place:** {{who_controls_this_place}}
- **Who feels safe here:** {{who_feels_safe_here}}
- **Who is unwelcome here:** {{who_is_unwelcome_here}}

## Information Layer
- **What is obvious:** {{obvious_information}}
- **What can be noticed with attention:** {{subtle_details}}
- **What is hidden:** {{hidden_elements}}
- **What can be inferred:** {{inferable_truths}}
- **What is misleading:** {{misleading_signals}}

## Tension and Purpose
- **Why this place matters:** {{why_this_place_matters}}
- **Current tension:** {{current_tension}}
- **Potential conflict:** {{potential_conflict}}
- **Possible opportunity:** {{possible_opportunity}}
- **What could go wrong here:** {{what_could_go_wrong}}

## Story Hooks
- **Local hook:** {{local_hook}}
- **NPC hook:** {{npc_hook}}
- **Clue hook:** {{clue_hook}}
- **Threat hook:** {{threat_hook}}
- **Reward hook:** {{reward_hook}}

## Interaction Guidance
This place should support:
- exploration
- observation
- dialogue
- suspicion
- discovery
- choice
- consequence

The environment should not be decorative only.
It should influence behavior, perception, and possible actions.

## GM Guidance
When presenting this micro setting:
- describe it through concrete sensory details
- emphasize what matters for player decisions
- reveal hidden elements through interaction, not exposition
- let the place reflect the larger setting naturally
- use the environment to create tension, leverage, and story momentum

## Output Guidance
This micro setting should feel:
- specific
- memorable
- usable in play
- connected to the larger world
- rich in implication
- small in scale but meaningful in consequence
