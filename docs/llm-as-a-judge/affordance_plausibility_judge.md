---
name: affordance_plausibility_judge
group: player_action_resolution
score_type: categorical
categories:
  - plausible
  - acceptable_inference
  - questionable
  - implausible
severity:
  positive: [plausible]
  weak: [acceptable_inference, questionable]
  failure: [implausible]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - affordance resolution
  - object admission policy
  - content module room/object inventory
  - scene context propagation
---

# affordance_plausibility_judge

## Purpose

Bewertet, ob die angenommene Handlungsmöglichkeit zur Szene und zu den
etablierten Objekten/Orten passt. Hilft zu erkennen, ob die Runtime
plausible Affordances nutzt oder unpassende Dinge erfindet.

## Prompt

You are evaluating whether the resolved action target and affordance are
plausible for the current scene.

This is a qualitative review signal only. Do not replace deterministic
affordance resolution or safety rules.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the action resolution makes sense in the implied scene and
module context.

Pay attention to:
- whether resolved locations, objects, or actors fit the current scene
- whether inferred spaces such as bathroom, hallway, kitchen, window,
  table, or door are plausible in the setting
- whether the action target is unsupported, too convenient, or invented in
  a disruptive way
- whether movement to offscreen/inferred areas is handled plausibly
- whether blocked or ambiguous targets are treated reasonably
- whether the resolution contradicts known scene facts
- whether the result preserves dramatic continuity

Rubric:

plausible:
The resolved target and action affordance fit the scene naturally and do
not strain continuity.

acceptable_inference:
The resolution is not explicitly established but is a reasonable inference
from the scene context.

questionable:
The target or affordance may be possible, but it feels under-supported,
too convenient, or weakly justified.

implausible:
The resolution contradicts the scene, invents an unsupported
location/object, ignores obvious constraints, or breaks continuity.

## Score reasoning prompt

Explain briefly why this category best matches affordance plausibility.
Mention the action target, whether it fits the scene, and whether the
inference is justified or disruptive.

## Category selection prompt

Choose exactly one category: plausible, acceptable_inference, questionable,
or implausible. Select implausible when the resolved target or affordance
clearly contradicts or breaks the scene context.
