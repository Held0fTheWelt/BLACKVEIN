# No-dead-end Recovery Contract

Status: Canonical technical contract for bounded Pi30 no-dead-end recovery.

## Purpose

`no_dead_end_recovery.v1` is the structured runtime evidence that a
player-visible turn remains playable even when the original player action is
blocked, ambiguous, partially possible, recoverable, or handled through a safe
fallback.

The contract is deterministic evidence. It does not judge dramatic prose and it
does not make qualitative live/staging claims by itself.

## Scope

The implemented runtime scope covers normal player-visible turns and
recoverable player-visible failure turns:

- committed success
- partial success
- blocked playable outcome
- redirected playable outcome
- clarification-needed outcome
- safe fallback playable outcome
- unrecoverable system error classification

Programming and contract failures are not converted into story. They roll back
the attempted turn and propagate as errors.

## Runtime Shape

`no_dead_end_recovery.v1` records:

- `recovery_class`
- `obstacle_kind`
- `obstacle_reason`
- player-attempt fingerprint
- playability booleans
- commit policy
- bounded `next_step_options`
- structural validation result

The runtime aspect is `turn_aspect_ledger.no_dead_end_recovery`.

## Authority

Recovery records do not override validation, actor-lane authority, state-delta
boundaries, or the commit seam.

Commit policy is explicit:

- recoverable/false-commit rows use `commits_story_truth=false` and
  `committed_truth_scope=none`;
- blocked committed outcomes may use
  `committed_truth_scope=blocked_attempt_only`;
- normal committed outcomes may use `committed_truth_scope=full_turn`;
- `false_truth_feedback_allowed=false` for every recovery record.

Callback web, consequence cascade, and memory must continue to derive from
committed-truth rows only.

## ADR-0039 Boundary

Tests assert schema version, recovery class, commit policy, next-step count,
technical-leak flag, exception boundary, and ledger projection.

Generated recovery wording, judge categories, and Pi labels are not pass/fail
oracles. LLM judges such as `recoverable_outcome_quality_judge` remain
qualitative diagnostics unless a later ADR promotes them into a governed gate.

## Implementation Anchors

- `story_runtime_core/recovery/no_dead_end.py`
- `world-engine/app/story_runtime/manager.py`
- `ai_stack/runtime_aspect_ledger.py`
- `story_runtime_core/tests/test_no_dead_end_recovery.py`
- `world-engine/tests/test_story_runtime_narrative_commit.py`
