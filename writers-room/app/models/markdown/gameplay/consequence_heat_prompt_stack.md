---
id: template.gameplay.consequence_heat.standard
kind: prompt_template
template_type: consequence_heat
variant: standard
scope: pressure_tracking
parent:
  collection: markdown.gameplay
inject_with:
- template.core.session_state.standard
- template.factions.faction.standard
tags:
- consequence
- heat
- pressure
---

# Consequence and Heat Prompt Stack

## Current Exposure
- **Who is watching:** {{who_is_watching}}
- **How closely they are watching:** {{watch_intensity}}
- **Why attention increased:** {{why_attention_increased}}
- **What evidence exists:** {{existing_evidence}}

## Consequence Tracks
- **Legal / institutional heat:** {{legal_or_institutional_heat}}
- **Faction heat:** {{faction_heat}}
- **Street reputation shift:** {{street_reputation_shift}}
- **Personal trust damage or gain:** {{personal_trust_shift}}
- **Economic fallout:** {{economic_fallout}}

## Pending Reactions
- **Immediate reaction:** {{immediate_reaction}}
- **Near-future reaction:** {{near_future_reaction}}
- **Worst plausible escalation:** {{worst_plausible_escalation}}
- **What can reduce heat:** {{heat_reduction_paths}}
- **What can worsen heat fast:** {{heat_escalation_paths}}

## Rule
Consequences should feel earned, legible, and connected to prior actions.
Heat should create pressure, not arbitrary punishment.
