---
id: template.core.session_state.standard
kind: prompt_template
template_type: session_state
variant: standard
scope: runtime_state
parent:
  collection: markdown.core
inject_with:
- template.characters.gm.standard
- template.scenes.scene.quick
tags:
- session
- state
- runtime
---

# Session State Prompt Stack

## Session Snapshot
- **Session goal:** {{session_goal}}
- **Current location:** {{current_location}}
- **Immediate objective:** {{immediate_objective}}
- **Immediate threat:** {{immediate_threat}}
- **Available leverage:** {{available_leverage}}

## Local Continuity
- **Who is present or nearby:** {{who_is_present_or_nearby}}
- **Current NPC attitudes:** {{current_npc_attitudes}}
- **Known clues in play:** {{known_clues_in_play}}
- **Items / tools that matter right now:** {{relevant_items_or_tools}}
- **Outstanding promises or deadlines:** {{outstanding_promises_or_deadlines}}

## Tone and Rhythm
- **Current tone:** {{current_tone}}
- **Current tempo:** {{current_tempo}}
- **What should be emphasized next:** {{next_emphasis}}
- **What should not be repeated:** {{what_should_not_be_repeated}}

## Rule
This layer keeps the model focused on what matters right now.
Prefer active, local, high-relevance information over broad lore.
