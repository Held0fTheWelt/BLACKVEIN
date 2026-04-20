---
id: template.scenes.room_or_place.standard
kind: prompt_template
template_type: room_or_place
variant: standard
scope: micro_play_space
parent:
  collection: markdown.scenes
depends_on:
- template.scenes.setting_micro.standard
inject_with:
- template.scenes.scene.director
- template.characters.npc.standard
tags:
- room
- place
- micro
---

# Room or Place Prompt Stack

## Identity
- **Location name:** {{location_name}}
- **Location type:** {{location_type}}
- **Building / parent area:** {{building_or_parent_area}}
- **Purpose:** {{purpose}}
- **Current condition:** {{current_condition}}

## First Impression
- **Mood:** {{mood}}
- **Lighting:** {{lighting}}
- **Sound:** {{sound}}
- **Smell:** {{smell}}
- **Immediate visual impression:** {{immediate_visual_impression}}

## Spatial Structure
- **Size and shape:** {{size_and_shape}}
- **Entrances / exits:** {{entrances_exits}}
- **Key furniture / structures:** {{key_furniture_structures}}
- **Obstacles / cover:** {{obstacles_cover}}
- **Lines of sight:** {{lines_of_sight}}
- **Notable spatial feature:** {{notable_spatial_feature}}

## Usable Details
- **Interactive objects:** {{interactive_objects}}
- **Valuables:** {{valuables}}
- **Hidden elements:** {{hidden_elements}}
- **Dangerous elements:** {{dangerous_elements}}
- **Signs of use or struggle:** {{signs_of_use_or_struggle}}

## Information Layer
- **What is obvious:** {{obvious_information}}
- **Subtle clue:** {{subtle_clue}}
- **False impression:** {{false_impression}}
- **What this place suggests about its owner or function:** {{owner_or_function_signal}}

## Dramatic Use
- **Why the place matters:** {{why_the_place_matters}}
- **What can happen here:** {{what_can_happen_here}}
- **What can go wrong here:** {{what_can_go_wrong_here}}
- **Connection to larger events:** {{connection_to_larger_events}}

## Rule
This place is not just scenery.
It must support decisions, tension, and discovery.
