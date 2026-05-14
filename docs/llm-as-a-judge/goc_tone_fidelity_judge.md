---
name: goc_tone_fidelity_judge
group: language_style_cleanliness
score_type: categorical
categories:
  - strong_fidelity
  - acceptable_fidelity
  - generic_tone
  - wrong_tone
severity:
  positive: [strong_fidelity]
  weak: [acceptable_fidelity, generic_tone]
  failure: [wrong_tone]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - prompt tone instructions
  - content module style hints
  - narrator voice contract
  - genre / register guardrails
---

# goc_tone_fidelity_judge

## Purpose

Bewertet, ob der Turn den God-of-Carnage-artigen Ton trifft. Achtet auf
höfliche Oberfläche, Subtext, soziale Peinlichkeit, Eskalation und vermeidet
generische Mediation oder Genre-Drift.

## Prompt

You are evaluating whether the output fits the intended God of Carnage-style
social drama tone in World of Shadows.

This is a qualitative tone signal only. Do not replace deterministic runtime
gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the visible output fits a tense bourgeois social scene
inspired by God of Carnage, without becoming generic conflict-resolution
prose.

Pay attention to:
- civilized politeness covering aggression
- social pressure beneath manners
- subtle accusation, discomfort, status tension
- concrete room details rather than generic moral summary
- whether characters behave like socially constrained adults
- whether the text avoids fantasy/game-master tone
- whether the output avoids generic “solve the conflict” language

Rubric:

strong_fidelity:
The output strongly fits the intended social-drama tone: polite surface,
pressure underneath, specific staging, and restrained conflict.

acceptable_fidelity:
The output mostly fits the tone, though it may be somewhat plain or lightly
generic.

generic_tone:
The output is understandable but sounds like generic conflict resolution,
generic drama, or neutral improv.

wrong_tone:
The output does not fit the intended tone. It feels like fantasy,
game-master narration, therapy-speak, action-adventure, debug text, or
another genre.

## Score reasoning prompt

Explain briefly why this category best matches GoC tone fidelity. Mention
whether the output has bourgeois politeness, social pressure, and specific
staging or instead feels generic/wrong-genre.

## Category selection prompt

Choose exactly one category: strong_fidelity, acceptable_fidelity,
generic_tone, or wrong_tone. Select wrong_tone when the output clearly
belongs to the wrong genre or style.
