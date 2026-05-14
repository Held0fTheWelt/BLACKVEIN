---
name: runtime_aspect_integrity_judge
group: runtime_aspect_integrity
score_type: categorical
categories:
  - complete
  - mostly_complete
  - incomplete
  - missing
  - not_applicable
  - insufficient_evidence
severity:
  positive: [complete]
  weak: [mostly_complete, incomplete]
  failure: [missing]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - runtime aspect ledger persistence
  - path summary construction
  - Langfuse generation metadata propagation
  - diagnostics / degradation chain construction
---

# runtime_aspect_integrity_judge

## Purpose

Bewertet, ob ein Turn genügend Backend-/World-Engine-Evidence enthält, um
ihn zu debuggen. Prüft, ob Ledger- oder Aspect-Daten zu Action, Beat,
Authority, Capability, Validation, Commit und Visible Projection vorhanden
sind.

## Prompt

You are evaluating whether a live World of Shadows runtime turn preserves
the required runtime-aspect evidence needed to understand and audit the
generated result.

This is a qualitative review signal only. Do not replace deterministic
runtime gates, ADR-0033 checks, actor-lane gates, fallback gates, or
commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the generation is supported by coherent runtime-aspect
evidence in the metadata and whether the visible output appears
consistent with that evidence.

Pay attention to:
- whether metadata contains meaningful runtime aspect evidence rather
  than empty, generic, or placeholder fields
- whether actor, narrator, NPC, beat, capability, origin, and outcome
  information are present when required
- whether the visible output reflects the runtime aspects that were
  supposedly selected
- whether missing evidence makes the turn impossible to audit
- whether deterministic gate outcomes and qualitative narrative output
  contradict each other
- whether the turn appears to rely on hardcoded, fallback, or
  underspecified behavior
- whether metadata is sufficient to diagnose why the output was produced

Rubric:

complete:
The runtime aspect evidence is complete and coherent. The metadata
contains the necessary actor, narrator/NPC, beat, capability, origin, and
outcome information, and the visible output is consistent with it.

mostly_complete:
Most required runtime aspect evidence is present and coherent. Some minor
fields may be missing, compressed, or not very detailed, but the turn
remains auditable.

incomplete:
Important runtime aspect evidence is missing or too vague. The visible
output may still be understandable, but the metadata is not sufficient to
fully audit how the turn was produced.

missing:
Runtime aspect evidence is absent, placeholder-like, empty, or unrelated
to the visible output. The turn cannot be meaningfully audited from the
provided metadata.

not_applicable:
The evaluated generation does not require runtime aspect evidence for the
aspect under review.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
reliably.

## Score reasoning prompt

Explain briefly why this category best matches runtime aspect integrity.
Mention which runtime aspect evidence is present, which is missing or
weak, and whether the visible output is consistent with the metadata.

## Category selection prompt

Choose exactly one category: complete, mostly_complete, incomplete,
missing, not_applicable, or insufficient_evidence. Select missing when
runtime aspect evidence is absent or placeholder-like. Select
insufficient_evidence only when the provided input, output, or metadata
is too incomplete to judge.
