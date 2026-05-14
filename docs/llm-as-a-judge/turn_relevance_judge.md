---
name: turn_relevance_judge
group: turn_relevance
score_type: categorical
categories:
  - directly_relevant
  - broadly_relevant
  - weakly_related
  - irrelevant_or_wrong
severity:
  positive: [directly_relevant]
  weak: [broadly_relevant, weakly_related]
  failure: [irrelevant_or_wrong]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - input interpretation
  - scene director focus
  - prompt grounding on player input
  - context pack assembly
---

# turn_relevance_judge

## Purpose

Bewertet, ob der Output auf den aktuellen Spielerinput und die aktuelle
Szene relevant reagiert. Erkennt ausweichende, generische oder thematisch
falsche Antworten.

## Prompt

You are evaluating whether the generated turn response is relevant to the
player’s input.

This is a qualitative review signal only. Do not replace deterministic
runtime gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the visible response follows meaningfully from the player’s
latest input.

Pay attention to:
- whether a player question receives an actual answer or useful dramatic
  response
- whether a player action receives spatial/perceptual consequence or
  appropriate social reaction
- whether the response ignores the input
- whether the response merely paraphrases the input without advancing the
  scene
- whether the response over-explains instead of reacting
- whether the response stays in the current scene and role context

Rubric:

directly_relevant:
The response clearly and naturally addresses the player’s input and
advances the scene.

broadly_relevant:
The response is related and mostly sensible, but may be generic, indirect,
or slightly underdeveloped.

weakly_related:
The response has only a loose connection to the player input or mostly
paraphrases it.

irrelevant_or_wrong:
The response ignores, contradicts, misattributes, or wrongly explains the
player input.

## Score reasoning prompt

Explain briefly why this category best matches turn relevance. Mention
whether the response answers, reacts to, or misinterprets the player
input.

## Category selection prompt

Choose exactly one category: directly_relevant, broadly_relevant,
weakly_related, or irrelevant_or_wrong. Select irrelevant_or_wrong when
the output ignores or misattributes the player input.
