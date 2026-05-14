---
name: dramatic_pacing_judge
group: dramatic_runtime_realization
score_type: categorical
categories:
  - strong_pacing
  - acceptable_pacing
  - weak_pacing
  - broken_pacing
severity:
  positive: [strong_pacing]
  weak: [acceptable_pacing, weak_pacing]
  failure: [broken_pacing]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - pacing / silence decision
  - scene director responder cadence
  - narrator authority on consequence
  - prompt restraint instructions
---

# dramatic_pacing_judge

## Purpose

Bewertet den dramatischen Rhythmus eines Turns. Prüft, ob der Turn Druck,
Reaktion oder Konsequenz erzeugt, ohne zu hetzen, zu stocken oder zu viel
zu erklären.

## Prompt

You are evaluating dramatic pacing in a World of Shadows turn.

This is a qualitative pacing signal only. Do not replace deterministic
runtime gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the turn has a playable dramatic rhythm.

Pay attention to:
- whether the turn produces too many cards or too much explanation
- whether the response is too thin or mechanical
- whether every player action unnecessarily triggers NPC dialogue
- whether narrator and NPC beats are balanced
- whether the scene advances without rushing or stalling
- whether tension remains present but not over-explained
- whether the turn feels like live drama rather than a summary

Rubric:

strong_pacing:
The turn has clear rhythm, useful restraint, and dramatic pressure. It
advances play without over-explaining.

acceptable_pacing:
The turn is playable and reasonably paced, though not especially elegant.

weak_pacing:
The turn is too thin, too explanatory, too repetitive, or slightly out of
rhythm.

broken_pacing:
The turn feels mechanically broken, bloated, stalled, repetitive, or
dramatically incoherent.

## Score reasoning prompt

Explain briefly why this category best matches dramatic pacing. Mention
whether the turn is too thin, too verbose, too repetitive, or well paced.

## Category selection prompt

Choose exactly one category: strong_pacing, acceptable_pacing, weak_pacing,
or broken_pacing. Select broken_pacing when the turn is visibly incoherent,
stalled, or repetitive.
