---
name: visible_origin_consistency_judge
group: authority_and_origin
score_type: categorical
categories:
  - consistent
  - mostly_consistent
  - inconsistent_or_incomplete
  - contradictory
  - not_applicable
  - insufficient_evidence
severity:
  positive: [consistent]
  weak: [mostly_consistent, inconsistent_or_incomplete]
  failure: [contradictory]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - visible block origin assignment
  - actor lane gates
  - narrator / NPC / player provenance propagation
  - fallback / diagnostic text suppression in player-facing blocks
---

# visible_origin_consistency_judge

## Purpose

Bewertet, ob sichtbare Blocks zu ihren Backend-Origin-Metadaten passen.
Prüft, ob origin_aspect, origin_beat_id, origin_capability und
authority_owner mit dem sichtbaren Inhalt übereinstimmen.

## Prompt

You are evaluating whether visible story blocks are consistent with
backend-provided origin metadata in a World of Shadows generation.

This is a qualitative review signal only. Do not replace deterministic
visible-block validation, actor-lane gates, runtime origin checks,
fallback gates, or ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether each visible block appears to come from the correct
narrative origin, such as narrator, selected player actor, NPC,
system-facing diagnostics, or other declared origin metadata.

Pay attention to:
- whether narrator text is marked and written as narrator text
- whether NPC dialogue/action belongs to the correct NPC origin
- whether the selected player character is not improperly spoken for or
  controlled by another origin
- whether visible block origin metadata matches the actual visible text
- whether a block’s content contradicts its declared origin
- whether diagnostics, fallback text, or technical commentary leaks into
  player-facing visible blocks
- whether missing, ambiguous, duplicated, or contradictory origins make
  the output hard to audit
- whether origin problems create actor-lane or authority-boundary issues

Rubric:

consistent:
Visible blocks match their backend-provided origin metadata. Narrator,
NPC, and player-facing content are clearly separated and coherent.

mostly_consistent:
Visible origins are mostly coherent. There may be minor ambiguity or weak
formatting, but no serious origin contradiction.

inconsistent_or_incomplete:
Some visible block origins are missing, incomplete, ambiguous, or weakly
mismatched with the text, making the output harder to audit.

contradictory:
Visible origin metadata clearly contradicts the text, assigns content to
the wrong actor/origin, leaks technical text, or creates a serious
authority/actor-lane problem.

not_applicable:
No visible block origin metadata is present or required for this
generation.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
visible origin consistency reliably.

## Score reasoning prompt

Explain briefly why this category best matches visible origin
consistency. Mention whether visible block origins match the actual text,
whether any origin is missing or contradictory, and whether the issue
affects narrator/NPC/player authority.

## Category selection prompt

Choose exactly one category: consistent, mostly_consistent,
inconsistent_or_incomplete, contradictory, not_applicable, or
insufficient_evidence. Select contradictory when visible text is clearly
assigned to the wrong origin or when technical/fallback content leaks
into player-facing blocks.
