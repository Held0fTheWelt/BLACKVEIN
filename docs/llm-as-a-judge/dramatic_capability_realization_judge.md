---
name: dramatic_capability_realization_judge
group: dramatic_runtime_realization
score_type: categorical
categories:
  - realized_correctly
  - mostly_realized
  - partially_realized
  - violated_or_missing
  - not_applicable
  - insufficient_evidence
severity:
  positive: [realized_correctly]
  weak: [mostly_realized, partially_realized]
  failure: [violated_or_missing]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - dramatic capability selection
  - capability validation / blocked-capability enforcement
  - prompt injection of selected capabilities as obligations
  - content module capability affordances
---

# dramatic_capability_realization_judge

## Purpose

Bewertet, ob ausgewählte dramatische Runtime-Capabilities korrekt
realisiert wurden. Prüft, ob Player-, Narrator- und NPC-Fähigkeiten passend
gewählt, umgesetzt oder blockiert wurden.

## Prompt

You are evaluating dramatic runtime capability realization in a World of
Shadows turn.

This is a qualitative review signal only. Do not replace deterministic
capability selection, runtime validation, actor-lane checks, beat
selection, fallback gates, or ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the dramatic capabilities selected or implied by the
runtime are actually realized in the visible output in a coherent,
playable, and theatrically useful way.

Pay attention to:
- whether selected capabilities appear in the visible result
- whether blocked, unavailable, or constrained capabilities are respected
- whether the visible output contradicts capability metadata
- whether capabilities create meaningful dramatic behavior instead of
  generic filler
- whether the capability realization fits the selected actor, NPCs,
  relationship pressure, beat, and scene state
- whether the output invents unsupported capabilities or ignores required
  ones
- whether partial or recoverable outcomes are represented as playable
  consequences

Rubric:

realized_correctly:
The selected or implied dramatic capabilities are clearly and correctly
realized. The visible output reflects them in a coherent, playable, and
dramatically meaningful way.

mostly_realized:
The capabilities are mostly realized. Some details may be thin, generic,
or underdeveloped, but the output remains coherent and playable.

partially_realized:
Capability realization is incomplete or inconsistent. Some selected
capabilities are missing, weakly expressed, or only indirectly
represented.

violated_or_missing:
The output ignores, contradicts, or misuses the selected capabilities,
invents unsupported capabilities, or fails to realize required dramatic
behavior.

not_applicable:
No meaningful dramatic capability evidence is required or present for
this generation.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
capability realization reliably.

## Score reasoning prompt

Explain briefly why this category best matches dramatic capability
realization. Mention which capabilities were selected, implied, blocked,
missing, contradicted, or visibly realized.

## Category selection prompt

Choose exactly one category: realized_correctly, mostly_realized,
partially_realized, violated_or_missing, not_applicable, or
insufficient_evidence. Select violated_or_missing when selected
capabilities are ignored, contradicted, or replaced by unsupported
behavior.
