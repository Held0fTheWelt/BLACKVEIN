---
id: template.core.world_state.standard
kind: prompt_template
template_type: world_state
variant: standard
scope: campaign_state
parent:
  collection: markdown.core
inject_with:
- template.characters.gm.standard
- template.core.session_state.standard
- template.factions.faction.standard
tags:
- world
- state
- campaign
---

# World State Prompt Stack

## Snapshot Identity
- **Timestamp / phase:** {{timestamp_or_phase}}
- **Current campaign stage:** {{campaign_stage}}
- **Current regional focus:** {{regional_focus}}
- **Current player position:** {{player_position}}

## Active Threads
- **Main thread:** {{main_thread}}
- **Secondary threads:** {{secondary_threads}}
- **Unresolved mysteries:** {{unresolved_mysteries}}
- **Unresolved debts / promises:** {{unresolved_debts_or_promises}}
- **Escalating threats:** {{escalating_threats}}

## Power and Motion
- **Faction shifts in progress:** {{faction_shifts}}
- **Current public mood:** {{public_mood}}
- **Current security / instability level:** {{security_or_instability_level}}
- **Current resource pressure:** {{resource_pressure}}
- **Current rumor climate:** {{rumor_climate}}

## Player Impact
- **What the player changed recently:** {{recent_player_impact}}
- **Who now notices the player:** {{who_now_notices_the_player}}
- **What doors opened:** {{opened_doors}}
- **What doors closed:** {{closed_doors}}
- **What consequences are still incoming:** {{incoming_consequences}}

## Canon Guard
- Preserve established truths.
- Preserve unresolved hooks unless explicitly resolved.
- Preserve meaningful consequences.
- Use this state as the living truth layer for current play.
