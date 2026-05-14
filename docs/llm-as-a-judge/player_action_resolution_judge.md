---
name: player_action_resolution_judge
group: player_action_resolution
score_type: categorical
categories:
  - resolved_well
  - partially_resolved
  - misresolved
  - not_resolved
severity:
  positive: [resolved_well]
  weak: [partially_resolved, misresolved]
  failure: [not_resolved]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - action resolution stage-1
  - actor lane gates
  - NPC authority contract
  - perception / movement narrator consequence
---

# player_action_resolution_judge

## Purpose

Bewertet, ob eine freie Spielerhandlung korrekt aufgelöst wurde. Prüft, ob
Ziel, Affordance, Konsequenz und sichtbare Antwort zur Handlung passen,
ohne Actor-Lane- oder Narrator/NPC-Grenzen zu brechen.

## Prompt

You are evaluating whether a free player action was resolved correctly in
an interactive World of Shadows turn.

This is a qualitative review signal only. Do not replace deterministic
action-resolution, actor-lane, or runtime gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the player’s input was resolved as the correct kind of
in-world action, perception, movement, speech, or mixed move.

Pay attention to:
- whether movement such as “Gehe ins Bad” becomes an actual
  movement/action, not quoted speech
- whether perception such as “Schau aus dem Fenster” leads to a
  perceptual/narrator consequence
- whether speech/questions remain speech/questions
- whether mixed input preserves both action and speech
- whether the selected human actor owns the action
- whether NPCs incorrectly explain or perform the player’s action
- whether the visible result is playable and follows the player’s intent

Rubric:

resolved_well:
The player action is clearly and correctly resolved. The selected player
character performs or attempts the intended action, and the visible
output follows naturally.

partially_resolved:
The action is mostly understood, but the result is incomplete, slightly
awkward, too generic, or missing part of the intended consequence.

misresolved:
The system interprets the input as the wrong action type, wrong target,
wrong actor, or wrong narrative function, but some relation to the input
remains.

not_resolved:
The action is not resolved at all, is ignored, becomes technical failure
text, or is replaced by unrelated NPC/narrator output.

## Score reasoning prompt

Explain briefly why this category best matches the player action
resolution. Mention the player’s apparent intent, how it was rendered,
and whether the selected player character actually performed or attempted
the intended action.

## Category selection prompt

Choose exactly one category: resolved_well, partially_resolved,
misresolved, or not_resolved. Select not_resolved when the player action
is ignored, turned into technical failure text, or not represented in the
visible output.
