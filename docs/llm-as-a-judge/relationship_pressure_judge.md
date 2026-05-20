---
name: relationship_pressure_judge
group: dramatic_runtime_realization
score_type: categorical
categories:
  - strong_pressure
  - serviceable_pressure
  - weak_pressure
  - missing_or_wrong
  - not_applicable
  - insufficient_evidence
severity:
  positive: [strong_pressure]
  weak: [serviceable_pressure, weak_pressure]
  failure: [missing_or_wrong]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - relationship state tracking
  - NPC reaction model (god_of_carnage_scene_director, god_of_carnage_character_mind)
  - beat pressure / scene function injection
  - content module relationship & social-tension affordances
---

# relationship_pressure_judge

## Purpose

Bewertet, ob Beziehungsspannung sichtbar und kohärent fortgeführt wird.
Achtet auf Paar-Dynamiken, Elternkonflikt, soziale Reibung, Allianzen,
Abwehr und charakterbezogene Reaktionen.

## Prompt

You are evaluating whether the generation preserves and advances
relationship pressure in a World of Shadows dramatic scene.

This is a qualitative review signal only. Do not replace deterministic
beat selection, relationship-state tracking, runtime gates, actor-lane
checks, or ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the output makes the relevant character relationships,
tensions, obligations, resentments, alliances, evasions, or power shifts
visible and dramatically useful.

Pay attention to:
- whether relationship pressure is visible through dialogue, silence,
  gesture, avoidance, accusation, interruption, concession, escalation,
  or subtext
- whether the pressure follows from the current scene state and prior
  relationship context
- whether the output advances, sharpens, redirects, or preserves the
  relationship tension
- whether NPC reactions are socially and dramatically appropriate
- whether the selected player character’s agency is respected within the
  relationship pressure
- whether the output becomes generic action narration without social
  consequence
- whether relationship metadata, thread pressure, beat intent, or scene
  function is reflected in the visible text
- whether the pressure is overplayed, underplayed, contradicted, or
  assigned to the wrong actor

Rubric:

strong_pressure:
Relationship pressure is clear, specific, and dramatically effective. The
output visibly advances or sharpens the social tension while respecting
actor boundaries.

serviceable_pressure:
Relationship pressure is present and coherent. It supports the scene,
though it may be somewhat plain, subtle, or not strongly developed.

weak_pressure:
Relationship pressure is weak, generic, or only indirectly present. The
output remains understandable but misses a clear social/dramatic
opportunity.

missing_or_wrong:
Relationship pressure is absent, contradicted, assigned to the wrong
actor, disconnected from the scene, or replaced by generic
narration/action.

not_applicable:
The generation does not require relationship pressure for the evaluated
aspect.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
relationship pressure reliably.

## Score reasoning prompt

Explain briefly why this category best matches relationship pressure.
Mention the relevant relationship or social tension, how it appears or
fails to appear in the visible output, and whether it advances the scene.

## Category selection prompt

Choose exactly one category: strong_pressure, serviceable_pressure,
weak_pressure, missing_or_wrong, not_applicable, or
insufficient_evidence. Select missing_or_wrong when relationship pressure
is absent, contradicted, assigned to the wrong actor, or replaced by
generic narration/action.
