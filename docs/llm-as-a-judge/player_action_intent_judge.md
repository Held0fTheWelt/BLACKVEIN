---
name: player_action_intent_judge
group: player_action_resolution
score_type: categorical
categories:
  - correct_intent
  - minor_mismatch
  - wrong_intent
  - invalid_takeover
severity:
  positive: [correct_intent]
  weak: [minor_mismatch, wrong_intent]
  failure: [invalid_takeover]
  neutral: []
  insufficient_evidence: []
suggested_repair_areas:
  - input interpretation / semantic move classification
  - actor lane gates
  - player_input_kind attribution
  - NPC authority contract
---

# player_action_intent_judge

## Purpose

Bewertet, ob die Spielereingabe semantisch richtig verstanden wurde.
Unterscheidet unter anderem Sprache, Frage, Bewegung, Wahrnehmung, soziale
Handlung, Objektinteraktion und Mixed Input.

## Prompt

You are evaluating whether the player input was interpreted and rendered
with the correct intent in World of Shadows.

This is a qualitative review signal only. Do not replace deterministic
player-input attribution gates.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the visible output treats the player input as the correct
kind of action, speech, perception, or mixed move.

Pay attention to:
- whether a question is rendered as a question/speech
- whether a free action such as “Gehe in die Küche” is rendered as an
  action, not as quoted speech
- whether perception such as “Schau aus dem Fenster” leads to player
  perception/narrator result, not NPC explanation
- whether mixed input preserves both action and speech
- whether the selected player role owns the player input
- whether an NPC takes over, repeats, or explains the player’s action
  incorrectly

Rubric:

correct_intent:
The player input is rendered as the correct intent type. Speech, action,
perception, or mixed input is handled naturally.

minor_mismatch:
The output mostly follows the intended player input, but phrasing is
slightly awkward or over-explicit.

wrong_intent:
The output uses the wrong intent type, such as rendering a physical action
as quoted speech or treating a perception as an NPC answer.

invalid_takeover:
The player input is assigned to an NPC, or an NPC takes over/explains the
player’s action in a way that breaks agency.

## Score reasoning prompt

Explain briefly why this category best matches player intent handling.
Mention the apparent player_input_kind and whether the output preserves
the player’s intended action/speech/perception.

## Category selection prompt

Choose exactly one category: correct_intent, minor_mismatch, wrong_intent,
or invalid_takeover. Select invalid_takeover when the player input is
assigned to an NPC or the NPC takes over the player action.
