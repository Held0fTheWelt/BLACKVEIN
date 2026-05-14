---
name: beat_realization_judge
group: dramatic_runtime_realization
score_type: categorical
categories:
  - strong_realization
  - serviceable_realization
  - weak_realization
  - not_realized
  - not_applicable
  - insufficient_evidence
severity:
  positive: [strong_realization]
  weak: [serviceable_realization, weak_realization]
  failure: [not_realized]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - beat selection algorithm
  - prompt injection of selected beat as actionable instruction
  - runtime beat metadata propagation
  - content module beat affordances and intents
---

# beat_realization_judge

## Purpose

Bewertet, ob der ausgewählte dramatische Beat im sichtbaren Output
tatsächlich realisiert wurde. Unterscheidet zwischen starker, serviceabler,
schwacher oder fehlender Beat-Realisierung.

## Prompt

You are evaluating whether the selected dramatic beat was realized in a
live interactive World of Shadows turn.

This is a qualitative review signal only. Do not replace deterministic
beat selection, runtime validation, pacing gates, actor-lane gates, or
ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the selected or implied beat is visible in the generated
output and whether it advances the scene in a concrete, playable, and
dramatically coherent way.

Pay attention to:
- whether the selected beat or beat intent is visible in the output
- whether the output advances the scene according to that beat instead of
  stalling
- whether the beat is realized through action, pressure, consequence,
  gesture, dialogue, silence, reveal, escalation, redirection, or changed
  relationship state
- whether the output contradicts the selected beat
- whether the beat is too generic, too weak, or disconnected from player
  input
- whether NPCs, narrator, and player actor boundaries remain intact while
  realizing the beat
- whether the beat supports the current scene rhythm instead of repeating
  prior state

Rubric:

strong_realization:
The selected beat is clearly and effectively realized. The output
advances the scene with concrete dramatic pressure, consequence, or
change.

serviceable_realization:
The beat is present and usable. The output advances or maintains the
scene, but the realization may be somewhat plain, compressed, or
predictable.

weak_realization:
The beat is only weakly visible. The output is generic, repetitive,
underdeveloped, or only loosely connected to the selected beat.

not_realized:
The selected beat is missing, contradicted, replaced by unrelated
content, or does not produce a playable dramatic result.

not_applicable:
No meaningful beat evidence is required or present for this generation.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge beat
realization reliably.

## Score reasoning prompt

Explain briefly why this category best matches beat realization. Mention
the selected or implied beat, whether it is visible in the output, and
whether it advances the scene.

## Category selection prompt

Choose exactly one category: strong_realization, serviceable_realization,
weak_realization, not_realized, not_applicable, or insufficient_evidence.
Select not_realized when the selected beat is absent, contradicted, or
replaced by unrelated/generic output.
