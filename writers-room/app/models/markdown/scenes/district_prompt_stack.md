---
id: template.scenes.district.standard
kind: prompt_template
template_type: district
variant: standard
scope: regional_play_space
parent:
  collection: markdown.scenes
inject_with:
- template.scenes.setting_macro.standard
- template.factions.faction.standard
tags:
- district
- region
- space
---

# District Prompt Stack

## Role
Define a district, zone, borough, neighborhood, sprawl segment, or controlled sector that sits between macro setting and local play.

## Identity
- **District name:** {{district_name}}
- **District type:** {{district_type}}
- **City / region:** {{city_or_region}}
- **Controlling power:** {{controlling_power}}
- **Public reputation:** {{public_reputation}}
- **Actual reality:** {{actual_reality}}

## Core Feel
- **Mood:** {{mood}}
- **Visual identity:** {{visual_identity}}
- **Sensory signature:** {{sensory_signature}}
- **What defines daily life here:** {{daily_life}}
- **What stands out immediately:** {{immediate_impression}}

## Structure
- **Social composition:** {{social_composition}}
- **Economic role:** {{economic_role}}
- **Security level:** {{security_level}}
- **Access rules:** {{access_rules}}
- **Movement conditions:** {{movement_conditions}}
- **Key landmarks:** {{key_landmarks}}

## Tensions
- **Open tension:** {{open_tension}}
- **Hidden tension:** {{hidden_tension}}
- **Resource pressure:** {{resource_pressure}}
- **Active threat:** {{active_threat}}
- **Opportunity space:** {{opportunity_space}}

## Powers and Actors
- **Dominant faction:** {{dominant_faction}}
- **Secondary factions:** {{secondary_factions}}
- **Institutional presence:** {{institutional_presence}}
- **Street-level actors:** {{street_level_actors}}
- **Who profits here:** {{who_profits_here}}
- **Who gets crushed here:** {{who_gets_crushed_here}}

## Play Hooks
- **Typical jobs here:** {{typical_jobs}}
- **Typical crimes here:** {{typical_crimes}}
- **Typical rumors here:** {{typical_rumors}}
- **Typical conflicts here:** {{typical_conflicts}}
- **Player leverage points:** {{player_leverage_points}}

## Rule
This district should generate stories by itself.
It must create pressure, identity, and recurring consequences.
