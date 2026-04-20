---
id: template.factions.faction.standard
kind: prompt_template
template_type: faction
variant: standard
scope: group_actor
parent:
  collection: markdown.factions
inject_with:
- template.core.world_state.standard
- template.gameplay.consequence_heat.standard
tags:
- faction
- power
- group
---

# Faction Prompt Stack

## Identity
- **Faction name:** {{faction_name}}
- **Faction type:** {{faction_type}}
- **Scale:** {{scale}}
- **Territory / area of influence:** {{territory}}
- **Public face:** {{public_face}}
- **Actual nature:** {{actual_nature}}

## Core Drive
- **Primary goal:** {{primary_goal}}
- **Secondary goals:** {{secondary_goals}}
- **Core fear:** {{core_fear}}
- **What the faction needs right now:** {{current_need}}
- **What it refuses to lose:** {{non_negotiable}}

## Methods
- **Preferred methods:** {{preferred_methods}}
- **Violence threshold:** {{violence_threshold}}
- **Political strategy:** {{political_strategy}}
- **Economic strategy:** {{economic_strategy}}
- **Recruitment style:** {{recruitment_style}}
- **How it hides its weaknesses:** {{concealment_pattern}}

## Knowledge and Belief
- **What the faction knows:** {{known_truths}}
- **What the faction suspects:** {{suspicions}}
- **What the faction believes wrongly:** {{wrong_beliefs}}
- **What the faction wants others to believe:** {{propaganda_line}}

## Structure
- **Leadership model:** {{leadership_model}}
- **Key internal roles:** {{key_internal_roles}}
- **Chain of command feel:** {{chain_of_command_feel}}
- **Internal fractures:** {{internal_fractures}}
- **Discipline and loyalty:** {{discipline_and_loyalty}}

## External Relations
- **Allies:** {{allies}}
- **Enemies:** {{enemies}}
- **Useful neutrals:** {{useful_neutrals}}
- **Public enemies:** {{public_enemies}}
- **Secret relationships:** {{secret_relationships}}

## Resources
- **Money / assets:** {{assets}}
- **Personnel:** {{personnel}}
- **Weapons / force:** {{force}}
- **Data / intelligence:** {{intelligence}}
- **Political leverage:** {{political_leverage}}
- **Unique advantage:** {{unique_advantage}}

## Story Use
- **How this faction pressures the setting:** {{setting_pressure}}
- **What kind of jobs it offers:** {{jobs_offered}}
- **What kind of trouble it causes:** {{trouble_caused}}
- **How it reacts to interference:** {{reaction_to_interference}}
- **How it treats useful outsiders:** {{treatment_of_outsiders}}

## Rule
A faction is not only lore.
It is an active machine of pressure, opportunity, and consequence.
