---
name: opening_experience_judge
group: opening_quality
score_type: categorical
categories:
  - excellent
  - acceptable
  - weak
  - invalid
severity:
  positive: [excellent]
  weak: [acceptable, weak]
  failure: [invalid]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - opening prompt construction
  - narrator authority on opening
  - role anchor and scene staging content
  - fallback / debug text leakage at opening
---

# opening_experience_judge

## Purpose

Bewertet, ob die Eröffnung als spielbarer Einstieg funktioniert. Achtet auf
Narrator-geführte Einführung, klare Rollenverankerung, Ort, Prämisse,
sozialen Druck und fehlende Debug-/Fallback-Artefakte.

## Prompt

You are evaluating the player-facing opening experience of an interactive
dramatic scene in World of Shadows.

Evaluate only the generated opening text and its player-facing quality. Do
not evaluate backend implementation quality. Do not reward technical
metadata by itself. A technically healthy trace can still have a weak or
invalid opening.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the generated output works as a proper opening introduction
for the selected player role.

Pay attention to:
- whether the opening begins with narrator-led introduction before actor
  dialogue/action
- whether the selected player role is clearly anchored
- whether the scene premise, place, social pressure, and stakes are
  understandable
- whether the prose feels theatrical, concrete, and playable rather than
  generic filler
- whether the narrator stages the scene through details, pressure, gesture,
  and subtext
- whether diagnostics/debug/fallback-like text appears in the player-facing
  opening
- whether actor dialogue/action starts too early
- whether the output feels like the beginning of a scene rather than a
  response in the middle of the scene

Rubric:

excellent:
The opening begins with a literary narrator-led introduction, clearly
anchors the selected player role, establishes place, social pressure,
dramatic premise, and stakes before actor dialogue/action begins. It feels
playable, theatrical, concrete, and intentionally staged.

acceptable:
The opening is understandable and role-aware. It provides orientation,
scene setup, and a usable player entry point, but may be stylistically
plain, compressed, or slightly mechanical.

weak:
The opening has some atmosphere or partial setup, but the player role,
premise, place, pressure, or stakes are unclear. It may feel abrupt,
generic, too short, or insufficiently staged.

invalid:
The opening starts directly with actor dialogue/action, lacks a clear role
anchor, lacks scene setup, uses fallback-like generic text, shows
diagnostics/debug text, or does not function as an introduction.

## Score reasoning prompt

Explain briefly why this category best matches the player-facing opening.
Mention the main strength or failure: role anchor, premise, staging,
theatrical quality, fallback-like text, diagnostics, or actor dialogue
before introduction.

## Category selection prompt

Choose exactly one category: excellent, acceptable, weak, or invalid.
Select invalid if the opening does not function as a player-facing
introduction.
