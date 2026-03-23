---
id: template.core.continuity_guard.standard
kind: prompt_template
template_type: continuity_guard
variant: standard
scope: consistency
parent:
  collection: markdown.core
inject_with:
- template.core.session_state.standard
- template.core.world_state.standard
tags:
- continuity
- guard
- consistency
---

# Continuity Guard Prompt Stack

## Guard Rules
- Do not contradict established facts unless the contradiction is intentional and supported.
- Do not let a local actor know campaign-level truth without cause.
- Do not erase consequences because they are inconvenient.
- Preserve promises, injuries, threats, and revealed clues.
