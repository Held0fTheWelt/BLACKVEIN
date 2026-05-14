---
name: blocked_action_playability_judge
group: recovery_and_playability
score_type: categorical
categories:
  - playable_block
  - acceptable_clarification
  - unclear_block
  - technical_failure
severity:
  positive: [playable_block]
  weak: [acceptable_clarification, unclear_block]
  failure: [technical_failure]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - blocked-action handling in runtime
  - recovery affordances in content modules
  - fallback / technical-error suppression
  - clarification prompt templates
---

# blocked_action_playability_judge

## Purpose

Bewertet, ob blockierte, unklare oder nur teilweise mögliche Aktionen
spielbar beantwortet werden. Prüft, ob der Spieler eine verständliche,
in-world Erklärung oder Rückfrage erhält statt eines technischen Fehlers.

## Prompt

You are evaluating whether a blocked, ambiguous, or unresolved player
action is handled in a playable way.

This is a qualitative review signal only. Do not replace deterministic
affordance or safety gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the system gives the player a clear, in-world, playable
response when an action cannot be completed, needs clarification, or is
only partially possible.

Pay attention to:
- whether the response avoids raw technical errors
- whether the player understands why the action cannot proceed
- whether the message remains diegetic and playable
- whether the response asks a useful clarification when the target is
  ambiguous
- whether blocked movement/action is explained through scene context
- whether the output preserves the selected player role
- whether the player can reasonably decide what to do next

Rubric:

playable_block:
The blocked or limited action is explained clearly and diegetically. The
player understands the constraint and can continue playing.

acceptable_clarification:
The response asks a useful clarification or gives a mostly playable
limitation, though it may be a bit plain or mechanical.

unclear_block:
The action is blocked or unclear, but the explanation is vague, awkward,
not very playable, or does not help the player continue.

technical_failure:
The output exposes technical failure, generic error text, stack-trace-like
content, or gives no playable response.

## Score reasoning prompt

Explain briefly why this category best matches the blocked/clarification
handling. Mention whether the player receives a playable explanation or
useful next-step clarification.

## Category selection prompt

Choose exactly one category: playable_block, acceptable_clarification,
unclear_block, or technical_failure. Select technical_failure when the
output exposes backend/runtime failure or gives no playable blocked-action
response.
