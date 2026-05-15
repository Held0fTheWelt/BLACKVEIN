# Narrative Momentum Runtime Contract

Last updated: 2026-05-15

`narrative_momentum` is the dedicated runtime aspect for the historical Pi31
momentum capability. The production key is semantic and stable; Pi labels stay
documentation-only index vocabulary.

## Boundary

The aspect models turn-level dramatic momentum as bounded state, not as a prose
judge. It derives a score and state from adjacent structured runtime signals:
scene energy, pacing rhythm, social pressure, expectation variation, semantic
move evidence, and prior committed momentum state.

The canonical state machine is:

- `resting`
- `building`
- `driving`
- `cresting`
- `releasing`
- `stalled`

Module policy defines allowed transitions, score thresholds, source weights,
decay, max velocity, stall budget, structured-event requirements, and commit
impact. The runtime normalizes this policy under
`ModuleRuntimePolicy.runtime_governance_policy.narrative_momentum`.

## Runtime Flow

1. LangGraph derives `narrative_momentum_state` and
   `narrative_momentum_target` after `expectation_variation`.
2. The dramatic generation packet receives only bounded target fields:
   target state, score, allowed next states, forward-motion requirement, release
   flag, minimum progress-event count, and selected driver refs.
3. Generated structured output may emit `narrative_momentum_events`.
4. The validator checks allowed transitions, required progress events, velocity
   bounds, stall budget, and event source refs.
5. `RuntimeAspectLedger.narrative_momentum` records expected, selected, and
   actual evidence.
6. Planner truth persists state, target, and validation, so the next turn can
   rehydrate prior momentum without inspecting prose.
7. Langfuse/MCP surfaces expose semantic `narrative_momentum_*` fields for
   local and live-evidence review.

## Failure Codes

- `narrative_momentum_target_missing`
- `narrative_momentum_transition_forbidden`
- `narrative_momentum_event_missing`
- `narrative_momentum_velocity_exceeded`
- `narrative_momentum_stall_budget_exceeded`
- `narrative_momentum_source_ref_invalid`

Failures are recoverable dramatic failures unless a future policy explicitly
promotes them. They feed self-correction instructions and retry diagnostics
without changing the proposal-until-validation commit boundary.

## ADR-0039 Discipline

Tests assert policy-normalized schema fields, state-machine transitions,
structured events, ledger projection, MCP matrix rows, planner-truth
rehydration, and anti-hardcoding coverage. Generated dramatic prose is not a
pass/fail oracle.
