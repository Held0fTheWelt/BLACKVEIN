---
name: player_turn_playability_judge
group: recovery_and_playability
score_type: categorical
categories:
  - playable
  - mostly_playable
  - weakly_playable
  - unplayable
  - not_applicable
  - insufficient_evidence
severity:
  positive: [playable]
  weak: [mostly_playable, weakly_playable]
  failure: [unplayable]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - action resolution stage-1
  - recovery affordances
  - content module scene support (next-step affordances)
  - actor lane gates / agency preservation
---

# player_turn_playability_judge

## Purpose

Bewertet, ob ein Player-Turn nach dem Input spielbar bleibt — egal ob die
Aktion gelingt, blockiert, umgelenkt oder unklar ist. Erkennt fehlende
Agency, technische/abweisende Antworten und unspielbare Outputs.

## Prompt

You are evaluating whether a player action turn remains playable in World
of Shadows.

This is a qualitative review signal only. Do not replace deterministic
action-resolution, actor-lane gates, runtime outcome checks, fallback
gates, or ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the turn gives the player a playable result after their
input, including cases where the action succeeds, partially succeeds, is
blocked, is redirected, is ambiguous, or cannot be completed.

Pay attention to:
- whether the player’s input is acknowledged as an in-world attempt,
  perception, movement, speech act, or mixed move
- whether the selected human actor remains the owner of the player action
- whether blocked or impossible actions are handled as playable
  consequences rather than flat rejection
- whether the output gives enough concrete scene state for the player to
  continue
- whether the result preserves agency instead of replacing the player’s
  action with NPC/narrator explanation
- whether the output is vague, generic, technical, or disconnected from
  the player input
- whether recoverable failure, clarification, partial success, or
  redirection is presented dramatically and understandably

Rubric:

playable:
The turn is clearly playable. The player’s input is represented as an
in-world attempt or consequence, the selected actor retains ownership,
and the output gives a concrete next situation.

mostly_playable:
The turn is mostly playable. The input is understood and the output
gives a usable result, though some detail, consequence, or continuation
affordance is weak.

weakly_playable:
The turn is only weakly playable. The response is vague, overly generic,
incomplete, or only partially connected to the player’s input.

unplayable:
The turn is not playable. The player action is ignored, flattened into
refusal, replaced by unrelated output, turned into technical/fallback
text, or stripped of agency.

not_applicable:
The generation does not contain a player action turn that needs
playability evaluation.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
playability reliably.

## Score reasoning prompt

Explain briefly why this category best matches player-turn playability.
Mention the player’s apparent input, how the output handled it, whether
the selected actor retained agency, and whether the player has a concrete
situation to continue from.

## Category selection prompt

Choose exactly one category: playable, mostly_playable, weakly_playable,
unplayable, not_applicable, or insufficient_evidence. Select unplayable
when the player action is ignored, replaced by unrelated content,
flattened into non-dramatic refusal, or turned into technical/fallback
text.
