---
name: npc_authority_violation_judge
group: authority_and_origin
score_type: categorical
categories:
  - no_violation
  - minor_blur
  - ambiguous_violation
  - clear_violation
  - not_applicable
  - insufficient_evidence
severity:
  positive: [no_violation]
  weak: [minor_blur, ambiguous_violation]
  failure: [clear_violation]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - NPC authority contract
  - scene director responder selection
  - actor lane gates
  - visible block origin metadata
---

# npc_authority_violation_judge

## Purpose

Bewertet, ob NPCs ihre Autoritätsgrenzen einhalten. Erkennt semantische
Übernahmen wie NPC führt Spielerhandlung aus, erzählt Spielerwahrnehmung
oder ersetzt den Narrator.

## Prompt

You are evaluating whether NPCs respected their runtime authority
boundaries in a World of Shadows turn.

This is a qualitative review signal only. Do not replace deterministic
actor-lane safety, NPC routing rules, runtime authority checks, or
ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether NPCs stay within their allowed in-world authority: speaking,
reacting, escalating, withholding, interrupting, or pressuring as
characters, without narrating the world, resolving the player’s action for
them, controlling the selected human actor, or explaining runtime
mechanics.

Pay attention to:
- whether NPCs only perform plausible NPC actions, speech, gestures, or
  reactions
- whether NPCs improperly narrate scene consequences, camera-like
  perception, room state, or system state
- whether NPCs take over or explain the selected player character’s
  action
- whether NPCs decide success/failure of a player action that should be
  resolved by runtime/narrator logic
- whether NPCs expose metadata, diagnostics, fallback reasons, or
  implementation commentary
- whether NPC behavior fits the social/dramatic situation and their
  relationship pressure
- whether visible block origin metadata agrees with what the visible text
  does

Rubric:

no_violation:
NPCs stay within their authority. They speak, react, gesture, pressure,
or escalate as characters without narrating the world, controlling the
player, or exposing runtime mechanics.

minor_blur:
There is a small boundary blur, but the output remains playable and the
NPC does not seriously take over narrator, runtime, or player authority.

ambiguous_violation:
An NPC may be exceeding authority, but the violation is unclear, limited,
or partly caused by ambiguous formatting/origin metadata.

clear_violation:
An NPC clearly takes over narrator duties, controls or explains the
player’s action, determines runtime outcome improperly, or exposes
technical/system information.

not_applicable:
No meaningful NPC authority behavior is present in this generation.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge NPC
authority reliably.

## Score reasoning prompt

Explain briefly why this category best matches NPC authority. Mention
whether NPCs stayed within character-level speech/action or whether they
took over narrator, runtime, or selected-player authority.

## Category selection prompt

Choose exactly one category: no_violation, minor_blur,
ambiguous_violation, clear_violation, not_applicable, or
insufficient_evidence. Select clear_violation when an NPC narrates the
world, controls the selected player character, resolves runtime outcome
improperly, or exposes technical/system details.
