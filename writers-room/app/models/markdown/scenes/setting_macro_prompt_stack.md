---
id: template.scenes.setting_macro.standard
kind: prompt_template
template_type: setting_macro
variant: standard
scope: world_frame
parent:
  collection: markdown.scenes
inject_with:
- template.factions.faction.standard
- template.core.world_state.standard
tags:
- setting
- macro
- world
---

# Macro Setting Prompt Stack

## Role
This prompt defines the setting of the roleplaying experience.

It establishes:
- the world
- its tone and atmosphere
- its rules and limitations
- its factions and tensions
- its places, conflicts, and themes
- the narrative boundaries within which the GameMaster and NPCs operate

The setting must feel coherent, immersive, and alive.

## Core Identity
- **Setting name:** {{setting_name}}
- **Genre:** {{genre}}
- **Subgenre:** {{subgenre}}
- **Tone:** {{tone}}
- **Mood:** {{mood}}
- **Core fantasy:** {{core_fantasy}}
- **Player fantasy:** {{player_fantasy}}

## World Overview
- **World summary:** {{world_summary}}
- **Current era:** {{current_era}}
- **Civilization level:** {{civilization_level}}
- **Technological level:** {{technology_level}}
- **Magic / special systems:** {{magic_or_special_systems}}
- **Everyday life:** {{everyday_life}}
- **What makes this world distinct:** {{world_uniqueness}}

## Themes
The setting should consistently support these themes:
- **Primary themes:** {{primary_themes}}
- **Secondary themes:** {{secondary_themes}}
- **Emotional pillars:** {{emotional_pillars}}
- **Philosophical or moral tensions:** {{moral_tensions}}

## Setting Logic
The setting must follow clear internal logic:
- Power has sources and costs.
- Institutions have motives.
- Culture shapes behavior.
- Conflict has causes.
- Scarcity, danger, or power imbalances affect daily life.
- Rumors, beliefs, propaganda, and truth are not the same thing.
- The world does not exist only around the player; it has its own motion.

## Major World Rules
- **What is possible:** {{what_is_possible}}
- **What is difficult:** {{what_is_difficult}}
- **What is forbidden or rare:** {{what_is_forbidden_or_rare}}
- **What the population believes:** {{public_beliefs}}
- **What is actually true:** {{hidden_truths}}
- **What is misunderstood:** {{misunderstood_truths}}

## Geography and Places
- **Core region:** {{core_region}}
- **Important locations:** {{important_locations}}
- **Frontier / danger zones:** {{danger_zones}}
- **Safe zones:** {{safe_zones}}
- **Travel conditions:** {{travel_conditions}}
- **Environmental character:** {{environmental_character}}

## Power Structure
- **Dominant powers:** {{dominant_powers}}
- **Secondary powers:** {{secondary_powers}}
- **Informal powers:** {{informal_powers}}
- **Law and enforcement:** {{law_and_enforcement}}
- **Economy and resources:** {{economy_and_resources}}
- **What people fight over:** {{resource_conflicts}}

## Factions
Each faction should have:
- a goal
- a method
- a public face
- a hidden agenda
- allies and enemies
- a relationship to the player’s possible actions

### Key factions
- **Faction list:** {{faction_list}}

## Society and Culture
- **Social order:** {{social_order}}
- **Class structure:** {{class_structure}}
- **Cultural norms:** {{cultural_norms}}
- **Taboos:** {{taboos}}
- **Religions / ideologies:** {{religions_or_ideologies}}
- **Language style / naming feel:** {{language_style}}
- **Common fears:** {{common_fears}}
- **Common desires:** {{common_desires}}

## Conflict Field
The setting should naturally generate conflict in these areas:
- **Political conflict:** {{political_conflict}}
- **Social conflict:** {{social_conflict}}
- **Economic conflict:** {{economic_conflict}}
- **Military or physical conflict:** {{military_conflict}}
- **Mystery or hidden conflict:** {{hidden_conflict}}
- **Personal-scale conflict:** {{personal_conflict}}

## Story Fuel
This setting should naturally produce:
- secrets
- tensions
- unstable alliances
- competing truths
- hard choices
- local problems with larger implications
- opportunities for discovery, risk, and consequence

## Narrative Boundaries
Do not allow the setting to become:
- generic
- consequence-free
- omnisciently explained
- purely decorative
- inconsistent in tone
- overloaded with lore that does not matter in play

Instead:
- keep details relevant
- reveal the world through play
- let setting details affect decisions
- make places, systems, and factions matter materially

## GM Guidance
When using this setting:
- present the world through scenes, systems, NPC attitudes, and consequences
- reveal lore gradually through relevance
- keep regional perspective important
- let factions push events forward
- let the player discover the world rather than receive a lecture
- preserve mystery where mystery belongs
- ensure the setting shapes every conflict and opportunity

## Output Guidance
The setting should feel:
- grounded in its own logic
- rich in atmosphere
- playable
- conflict-generating
- memorable in identity
- capable of supporting both major arcs and small local stories
