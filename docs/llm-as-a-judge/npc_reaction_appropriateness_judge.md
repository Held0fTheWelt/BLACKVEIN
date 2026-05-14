---
name: npc_reaction_appropriateness_judge
group: authority_and_origin
score_type: categorical
categories:
  - appropriate_reaction
  - minor_overreaction
  - unnecessary_commentary
  - npc_takes_over
severity:
  positive: [appropriate_reaction]
  weak: [minor_overreaction, unnecessary_commentary]
  failure: [npc_takes_over]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - NPC authority contract
  - scene director responder selection
  - actor lane gates
  - silence / passivity affordances
---

# npc_reaction_appropriateness_judge

## Purpose

Bewertet, ob NPCs passend auf Spielerhandlung, Sprache oder Situation
reagieren. Achtet darauf, dass NPCs sozial/dramatisch reagieren, aber nicht
Narrator-Aufgaben oder Spielerhandlungen übernehmen.

## Prompt

You are evaluating whether NPC reactions to the player’s action are
appropriate and playable.

This is a qualitative review signal only. Do not replace deterministic
actor-lane or action-resolution gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether NPCs react naturally to the player’s latest action, speech,
perception, or movement without taking over the narrator’s role or the
player’s agency.

Pay attention to:
- whether NPC reaction is socially or dramatically appropriate
- whether NPCs unnecessarily comment on every small player movement
- whether an NPC explains spatial/perceptual consequences that should
  belong to the narrator
- whether NPCs paraphrase the player’s action instead of reacting
- whether NPC dialogue advances social tension or playability
- whether NPCs take over or block the player action without reason
- whether silence or a narrator-only consequence would have been more
  appropriate

Rubric:

appropriate_reaction:
The NPC reaction is natural, socially grounded, and helps the scene without
taking over narration or player agency.

minor_overreaction:
The NPC response is mostly acceptable but slightly too explanatory, too
immediate, or too reactive for the action.

unnecessary_commentary:
The NPC comments on, explains, or paraphrases the player action when a
narrator consequence or silence would be better.

npc_takes_over:
The NPC takes over the player action, narrates the world instead of the
narrator, blocks the action without basis, or makes the turn feel
controlled by the NPC.

## Score reasoning prompt

Explain briefly why this category best matches the NPC reaction. Mention
whether the NPC response is socially appropriate, unnecessary commentary,
or a takeover of narrator/player responsibility.

## Category selection prompt

Choose exactly one category: appropriate_reaction, minor_overreaction,
unnecessary_commentary, or npc_takes_over. Select npc_takes_over when the
NPC controls, explains, or overrides the player action in a way that
breaks playability.
