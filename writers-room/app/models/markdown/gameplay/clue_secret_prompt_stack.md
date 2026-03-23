---
id: template.gameplay.clue_secret.standard
kind: prompt_template
template_type: clue_secret
variant: standard
scope: information_payload
parent:
  collection: markdown.gameplay
inject_with:
- template.core.truth_layer.standard
- template.scenes.scene.director
tags:
- clue
- secret
- investigation
---

# Clue and Secret Prompt Stack

## Identity
- **Clue / secret name:** {{name}}
- **Type:** {{type}}
- **Associated mystery:** {{associated_mystery}}
- **Source:** {{source}}
- **Reliability:** {{reliability}}

## Truth Layers
- **Objective truth:** {{objective_truth}}
- **Public version:** {{public_version}}
- **Rumor version:** {{rumor_version}}
- **False interpretation:** {{false_interpretation}}

## Discovery Logic
- **How it can be found:** {{discovery_method}}
- **What makes it noticeable:** {{noticeable_feature}}
- **What skill / action reveals more:** {{deeper_reveal_trigger}}
- **What may hide it:** {{obfuscation}}

## Dramatic Function
- **Why this matters:** {{why_it_matters}}
- **What it changes if understood:** {{what_it_changes}}
- **What danger comes with learning it:** {{danger_of_knowing}}
- **What wrong conclusion is tempting:** {{tempting_wrong_conclusion}}

## Usage Rule
A clue should point, complicate, or reframe.
A secret should change power, trust, or stakes once exposed.
