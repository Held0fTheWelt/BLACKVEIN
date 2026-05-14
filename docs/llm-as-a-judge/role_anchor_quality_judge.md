---
name: role_anchor_quality_judge
group: opening_quality
score_type: categorical
categories:
  - clear
  - partial
  - missing
  - wrong_role
severity:
  positive: [clear]
  weak: [partial]
  failure: [missing, wrong_role]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - role selection / human actor binding
  - opening prompt role-anchor instructions
  - content module role-anchor affordances
  - selected_player_role propagation to prompt
---

# role_anchor_quality_judge

## Purpose

Bewertet, ob der ausgewählte Spielercharakter klar und korrekt im Output
verankert ist. Erkennt fehlende, falsche oder nur schwache
Rollenorientierung.

## Prompt

You are evaluating whether the generated opening clearly anchors the
selected player role in an interactive dramatic scene in World of
Shadows.

Evaluate only the player-facing text. Do not judge backend implementation
quality. Do not reward technical metadata by itself.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the generated output makes the selected player role clear
to the player.

Pay attention to:
- whether the player can understand which character they are inhabiting
- whether the selected role is introduced before or during the opening
- whether the role anchor is explicit or strongly implied through context
- whether the output confuses the player role with an NPC
- whether the output makes another character seem like the player
- whether the selected human actor is treated as AI-controlled
- whether the role anchor is missing because the text starts directly in
  dialogue/action

Rubric:

clear:
The selected player role is clearly anchored. The player can confidently
understand who they are playing. The role may be named directly or made
unmistakable through context, perspective, and scene setup.

partial:
The selected player role is hinted at, but not fully established. The
player may infer their role, but the introduction is weak, indirect, or
easy to miss.

missing:
The generated output does not provide a usable player-role anchor. The
opening may contain scene atmosphere or dialogue, but the player cannot
confidently tell who they are playing.

wrong_role:
The generated output anchors the wrong character, treats an NPC as the
player role, makes the selected human actor speak/act autonomously as AI
output, or otherwise confuses the player’s identity.

## Score reasoning prompt

Explain briefly why this category best matches the role anchoring. Mention
whether the selected player role is clear, partial, missing, or confused
with another character.

## Category selection prompt

Choose exactly one category: clear, partial, missing, or wrong_role.
Select wrong_role if the output anchors or controls the wrong character.
Select missing if no usable player-role anchor is present.
