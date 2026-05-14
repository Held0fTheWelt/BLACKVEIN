---
name: narrator_npc_boundary_judge
group: actor_lane_narrative_boundary
score_type: categorical
categories:
  - clean_boundary
  - minor_blur
  - npc_narrates_action
  - severe_boundary_violation
severity:
  positive: [clean_boundary]
  weak: [minor_blur, npc_narrates_action]
  failure: [severe_boundary_violation]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - actor lane gates
  - narrator authority contract
  - NPC authority contract
  - visible block origin assignment
---

# narrator_npc_boundary_judge

## Purpose

Bewertet die Grenze zwischen Narrator- und NPC-Aufgaben. Prüft, ob der
Narrator Raum, Wahrnehmung und Konsequenzen führt und NPCs nicht unzulässig
narrativ übernehmen.

## Prompt

You are evaluating whether narrator and NPC responsibilities remain
properly separated.

This is a qualitative review signal only. Do not replace deterministic
runtime gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the narrator and NPCs each perform their correct narrative
function.

The narrator should handle:
- space, movement, perception, environmental consequence, transition,
  physical staging

NPCs should handle:
- dialogue, social reaction, gestures, interpersonal pressure, refusal,
  courtesy, irritation

Pay attention to:
- whether an NPC explains the player’s movement or perception instead of
  the narrator
- whether the narrator summarizes NPC dialogue that should be spoken
- whether NPCs merely paraphrase the player’s action
- whether narrator and NPC blocks are cleanly separated
- whether the output feels like a playable scene rather than NPCs
  narrating the world

Rubric:

clean_boundary:
Narrator and NPC roles are clean. Movement/perception belongs to narrator;
NPCs react socially or speak.

minor_blur:
There is slight overlap, but the scene remains understandable and
playable.

npc_narrates_action:
An NPC wrongly explains, narrates, or paraphrases the player’s
physical/perceptual action instead of reacting naturally.

severe_boundary_violation:
Narrator/NPC roles collapse badly. NPCs take over narration, player
action, or environmental description in a way that breaks the scene.

## Score reasoning prompt

Explain briefly why this category best matches narrator/NPC boundary
quality. Mention whether spatial/perceptual consequences are handled by
the narrator or incorrectly by NPCs.

## Category selection prompt

Choose exactly one category: clean_boundary, minor_blur,
npc_narrates_action, or severe_boundary_violation. Select
severe_boundary_violation when NPCs take over narrator or player-action
responsibilities.
