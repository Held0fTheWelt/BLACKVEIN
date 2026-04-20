---
id: template.gameplay.quest.standard
kind: prompt_template
template_type: quest_or_mission
variant: standard
scope: objective_chain
parent:
  collection: markdown.gameplay
inject_with:
- template.core.session_state.standard
- template.gameplay.consequence_heat.standard
tags:
- quest
- mission
- objective
---

# Quest or Mission Prompt Stack

## Identity
- **Mission name:** {{mission_name}}
- **Mission type:** {{mission_type}}
- **Source:** {{mission_source}}
- **Public objective:** {{public_objective}}
- **Actual objective:** {{actual_objective}}

## Stakes
- **Why it matters:** {{why_it_matters}}
- **Who benefits:** {{who_benefits}}
- **Who suffers:** {{who_suffers}}
- **Time pressure:** {{time_pressure}}
- **Failure cost:** {{failure_cost}}
- **Success complication:** {{success_complication}}

## Structure
- **Entry point:** {{entry_point}}
- **Expected path:** {{expected_path}}
- **Likely obstacle:** {{likely_obstacle}}
- **Likely twist:** {{likely_twist}}
- **Likely fallout:** {{likely_fallout}}

## Information Control
- **What the client says:** {{client_version}}
- **What is hidden:** {{hidden_truth}}
- **What is false or incomplete:** {{false_or_incomplete}}
- **What clues can expose the truth:** {{truth_clues}}

## Rewards
- **Primary reward:** {{primary_reward}}
- **Secondary reward:** {{secondary_reward}}
- **Reputation effect:** {{reputation_effect}}
- **Future leverage created:** {{future_leverage}}

## Rule
A mission should create action, uncertainty, and consequences.
It should not feel like a checklist detached from the world.
