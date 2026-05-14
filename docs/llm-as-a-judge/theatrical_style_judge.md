---
name: theatrical_style_judge
group: language_style_cleanliness
score_type: categorical
categories:
  - theatrical
  - serviceable
  - flat
  - bad
severity:
  positive: [theatrical]
  weak: [serviceable, flat]
  failure: [bad]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - prompt style / theatrical voice instructions
  - narrator authority on staging detail
  - content module scene atmosphere
  - filler / cliché suppression
---

# theatrical_style_judge

## Purpose

Bewertet die theatrale Qualität des Outputs. Achtet auf konkrete
Inszenierung, Spannung, Gesten, Subtext und vermeidet flache oder rein
funktionale Prosa.

## Prompt

You are evaluating the theatrical and literary quality of the
narrator/opening prose in World of Shadows.

Evaluate only the player-facing generated text. Do not judge backend
implementation quality. Do not reward technical metadata by itself.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the generated opening feels like a staged, playable,
dramatic scene rather than generic filler or mechanical exposition.

Pay attention to:
- concrete staging details: gesture, posture, room, objects, rhythm,
  silence, proximity
- subtext and social pressure instead of direct explanation of emotions
- whether the narrator creates atmosphere through scene action rather
  than telling the player what to feel
- whether the prose feels literary, theatrical, and playable
- whether the opening has pacing and tension
- whether the prose is generic, cliché, abstract, or filler-like
- whether the text feels like a real opening rather than a summary or
  debug placeholder

Rubric:

theatrical:
The prose stages the scene vividly through concrete details, subtext,
gesture, rhythm, and social pressure. It feels literary, playable, and
intentionally dramatic without overexplaining emotions.

serviceable:
The prose is clear and usable. It establishes some scene feeling or
pressure, but the style may be plain, slightly mechanical, or not
especially theatrical.

flat:
The prose is understandable but weak. It relies on abstract statements,
generic atmosphere, direct emotional explanation, or underdeveloped
staging. It does not strongly feel like theatre or interactive drama.

bad:
The prose is generic filler, debug-like, incoherent, overly mechanical,
cliché-heavy, or fails to stage a dramatic scene. It may tell the player
what to feel instead of dramatizing the situation.

## Score reasoning prompt

Explain briefly why this category best matches the theatrical style.
Mention concrete staging, subtext, rhythm, generic filler, emotional
overexplanation, or lack of dramatic pressure.

## Category selection prompt

Choose exactly one category: theatrical, serviceable, flat, or bad. Select
bad if the prose is generic filler, debug-like, incoherent, or not a
playable dramatic scene.
