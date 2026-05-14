---
name: narrator_authority_judge
group: authority_and_origin
score_type: categorical
categories:
  - fulfilled
  - mostly_fulfilled
  - partial_or_ambiguous
  - violated
  - not_applicable
  - insufficient_evidence
severity:
  positive: [fulfilled]
  weak: [mostly_fulfilled, partial_or_ambiguous]
  failure: [violated]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - narrator authority contract
  - visible block origin assignment
  - NPC authority contract (narrator displacement)
  - prompt enforcement of narrator framing duties
---

# narrator_authority_judge

## Purpose

Bewertet, ob der Narrator seine zuständige Rolle erfüllt. Besonders
relevant für Bewegung, Wahrnehmung, Umgebung, physische Konsequenzen und
Szenenrahmung.

## Prompt

You are evaluating narrator authority in a live interactive World of
Shadows turn.

This is a qualitative review signal only. Do not replace deterministic
actor-lane gates, narrator routing rules, runtime authority checks, or
ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the narrator performs the narrative functions that belong
to the narrator, without being displaced by NPCs, player actors,
technical text, or unsupported runtime behavior.

Pay attention to:
- whether scene framing, spatial orientation, transitions, consequences,
  and perceptual narration are handled by the narrator when needed
- whether the narrator clarifies what is visible, felt, implied, or
  changed in the scene
- whether NPCs improperly take over narrator duties
- whether the selected player character is allowed to act without the
  narrator overwriting their intent
- whether the narrator becomes too weak, absent, generic, or purely
  mechanical
- whether the narrator exposes implementation details, diagnostics,
  fallback language, or system commentary
- whether the narrator’s visible authority matches metadata such as
  visible block origin, actor lane, beat, capability, or outcome state

Rubric:

fulfilled:
Narrator authority is clearly fulfilled. The narrator handles framing,
consequence, perception, transition, or scene pressure where appropriate,
while respecting actor and NPC boundaries.

mostly_fulfilled:
Narrator authority is mostly fulfilled. The narrator supports the scene
adequately, with only minor weakness, compression, or slight boundary
blur.

partial_or_ambiguous:
Narrator authority is only partially fulfilled or ambiguous. The output
may be playable, but narrator duties are underdeveloped, unclear, or
partly displaced.

violated:
Narrator authority is violated. NPCs, player actors, technical text, or
unsupported output take over narrator responsibilities, or the narrator
overrides actor ownership in a serious way.

not_applicable:
The generation does not require meaningful narrator authority for the
evaluated aspect.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
narrator authority reliably.

## Score reasoning prompt

Explain briefly why this category best matches narrator authority. Mention
what narrator function was required, whether the narrator fulfilled it,
and whether any NPC, player actor, technical text, or fallback-like
output displaced narrator authority.

## Category selection prompt

Choose exactly one category: fulfilled, mostly_fulfilled,
partial_or_ambiguous, violated, not_applicable, or insufficient_evidence.
Select violated when narrator duties are clearly taken over by the wrong
origin or when the narrator improperly overrides actor ownership.
