---
name: recoverable_outcome_quality_judge
group: recovery_and_playability
score_type: categorical
categories:
  - playable_recovery
  - acceptable_recovery
  - weak_recovery
  - failed_recovery
  - not_applicable
  - insufficient_evidence
severity:
  positive: [playable_recovery]
  weak: [acceptable_recovery, weak_recovery]
  failure: [failed_recovery]
  neutral: [not_applicable]
  insufficient_evidence: [insufficient_evidence]
suggested_repair_areas:
  - blocked-action handling
  - outcome routing (recoverable / partial / constrained)
  - recovery affordances in content modules
  - prompt enforcement of in-fiction explanation over technical refusal
---

# recoverable_outcome_quality_judge

## Purpose

Bewertet die Qualität von recoverable, blockierten, unklaren oder
teilweise möglichen Turn-Ergebnissen. Achtet darauf, dass solche Fälle
in-world, verständlich, HTTP-200-spielbar und ohne falschen Commit
bleiben.

## Prompt

You are evaluating the quality of a recoverable, blocked, ambiguous,
unknown-target, partial-success, or constrained outcome in a World of
Shadows player turn.

This is a qualitative review signal only. Do not replace deterministic
action-resolution, legality checks, actor-lane gates, runtime outcome
checks, fallback gates, or ADR-0033 commit semantics.

Generation input:
{{input}}

Generation output:
{{output}}

Observation metadata:
{{metadata}}

Your task:
Judge whether the system turns a blocked, ambiguous, failed, partial, or
constrained player action into a playable dramatic outcome instead of a
dead end.

Pay attention to:
- whether the output explains the obstacle through the fiction rather
  than through technical/system language
- whether the player’s attempted action remains recognizable
- whether the selected player character retains agency
- whether the result creates a concrete next step, alternative, clue,
  pressure, or consequence
- whether the outcome is dramatically useful rather than a flat denial
- whether unknown targets, impossible actions, blocked movement, failed
  attempts, or ambiguity are handled gracefully
- whether the output invents unsupported success or ignores the
  block/failure entirely
- whether metadata indicates a recoverable outcome, blocked action,
  partial success, clarification, redirection, or constrained result

Rubric:

playable_recovery:
The blocked, failed, ambiguous, or constrained action becomes a clear
playable outcome with fictional explanation, consequence, and a usable
next situation.

acceptable_recovery:
The recovery is understandable and usable, though it may be plain,
compressed, or only lightly dramatized.

weak_recovery:
The recovery is weak. The output acknowledges the problem but gives
little dramatic consequence, weak continuation, or unclear next steps.

failed_recovery:
The outcome is not recovered playably. It becomes a flat rejection,
technical explanation, unrelated output, unsupported success, or dead
end.

not_applicable:
No recoverable, blocked, ambiguous, failed, partial, or constrained
outcome is present.

insufficient_evidence:
The provided input, output, or metadata is too incomplete to judge
recoverable outcome quality reliably.

## Score reasoning prompt

Explain briefly why this category best matches recoverable outcome
quality. Mention the attempted action, the obstacle or constraint, how
the output recovered or failed to recover it, and whether the player has
a playable next step.

## Category selection prompt

Choose exactly one category: playable_recovery, acceptable_recovery,
weak_recovery, failed_recovery, not_applicable, or insufficient_evidence.
Select failed_recovery when the result is a flat denial, technical/fallback
text, unrelated output, unsupported success, or a dead end.
