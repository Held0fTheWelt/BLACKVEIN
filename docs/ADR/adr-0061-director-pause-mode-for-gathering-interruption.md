# ADR-0061: Director-Pause Mode for Gathering Interruption

## Status

Accepted (Phase-1 PR-C wiring + PR-D operator aggregation and hold-path audit, 2026-05-20)

## Date

2026-05-19

## Related ADRs

- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — semantic-name vocabulary discipline; no Pi / Π runtime keys; no hardcoded oracle bypass.
- [ADR-0041](adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) — semantic capability selection.
- [ADR-0053](adr-0053-bounded-semantic-scene-planner.md) — Director is advisory, not the authoritative truth-author.
- [ADR-0057](adr-0057-canon-safe-player-freedom-and-affordance-inference.md) — canon-safe player freedom; ADR-0057's Phase-1 amendment names the four Phase-1 contracts and reserves the Director-Pause contract for this ADR.
- [ADR-0062](adr-0062-director-realization-thin-path.md) — Resolver → Director → Narrator thin path; Director-Pause rides on the same composition surface.

## Context

The roadmap [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md) §3.4 corrects a conceptual error in earlier plan versions: when the player interrupts a gathering — by leaving the apartment, walking to another room, drifting to the window mid-conversation — the runtime today either (a) holds the player ("you can't leave now") or (b) lets the canonical step advance even though `named_characters[current_step]` is no longer co-present in the scene.

Both behaviors are wrong. The correct behavior is the inversion: the **gathering** waits while the **player** remains free. The Director switches into a `gathering_paused` mode. The player may freely pursue mundane actions; NPCs may freely pursue their own mundane actions; mandatory-beat consumption pauses; canonical-step advance pauses; the narrator may emit at most one transition reaction block on entry.

This requires a contract for the Director-Pause state and a deterministic composition function that decides whether the pause is on, derived from the resolver's semantic output and the current actor topology. It must **not** be a verb whitelist, a room enum, or a `step.mode` switch.

PR-0 of the roadmap (the contracts + PIV baseline PR) names this contract by reserving `director_gathering_state.v1` in ADR-0057's Phase-1 amendment. This ADR-0061 Draft fixes the contract shape and the composition rule. The PR that delivers the implementation is PR-C of Phase 1; ADR-0061 transitions from Draft to Accepted with PR-C.

## Decision

### 1. Contract — `director_gathering_state.v1`

A per-tick atomic snapshot emitted by the Director. Required fields:

- `paused` — boolean.
- When `paused == true`:
  - `step_id` — canonical step at the entry to the pause.
  - `missing_actor_ids` — list of actor ids that should be co-present per `named_characters[current_step]` but are not.
  - `since_turn` — turn number at which the pause entered.
  - `presence_required_for_step` — snapshot of `named_characters` for that step, captured at entry time. Subsequent edits to canonical content do not retroactively alter this snapshot for an ongoing pause.

Transitions `paused: false → true` and `paused: true → false` each emit exactly one state-change event in the per-turn evidence stream so a transition can be observed without polling.

### 2. Composition function — `compute_gathering_state`

Pure function in the Director (the canonical surface will live in `ai_stack/director/scene_director_goc.py`; the function is introduced by PR-C, not PR-0).

Signature (informal):

```
compute_gathering_state(
    actor_locations: dict[actor_id, location_id],
    current_step_named_characters: list[actor_id],
    current_step_scene_id: location_id,
    participation_relevance: enum,
    visibility_audibility: enum,
) -> { paused: bool, missing: list[actor_id] }
```

Composition rule (semantic, not lexical):

- `paused == true` iff at least one actor in `current_step_named_characters` is **either** not at `current_step_scene_id` **or** has lost participation-relevance (e.g. the player turns demonstratively away in the same room) **or** has lost visibility / audibility relative to the gathering.
- `missing` is the subset of `current_step_named_characters` failing any of those conditions.
- The function is **pure** — it reads its inputs and returns a value. No mutation of session state, no side effects.

The contract field `presence_breaks_gathering` in `free_player_action_resolution.v1` (see ADR-0057 amendment) is the resolver-side input that lets `compute_gathering_state` decide; the resolver delivers it, the Director composes the final state.

### 3. Required presence from `named_characters`

`current_step_named_characters` is sourced from the canonical content. For God-of-Carnage step 005 the field declares the four named actors at the meeting; future module content declares its own equivalent. The Director **never** edits or paraphrases `named_characters`; it reads it as a content snapshot.

### 4. `actor_locations`, `participation_relevance`, `visibility / audibility` inputs

- `actor_locations` is the existing runtime-world projection (see `ai_stack/environment_state_contracts.py` and `RuntimeAspectLedger` adjacent surfaces). No new mechanism is added.
- `participation_relevance` and `visibility / audibility` are semantic signals emitted by the resolver's classification of the player action (e.g. "demonstratively turns toward the window away from the conversation" yields `participation_relevance == "broken"`; "kurzer Toilettengang" yields `visibility / audibility == "still_audible"`).
- These signals are part of the `free_player_action_resolution.v1` contract (per ADR-0057 amendment) and are populated by PR-A; ADR-0061 only consumes them.

### 5. Gathering pauses Mandatory-Beat consumption

When `paused == true`:

- The NPC-agency / mandatory-beat-consumption path (canonical surface around `ai_stack/director/scene_director_goc.py:655` `_build_responder_set()` and `ai_stack/langgraph/langgraph_runtime_executor.py:3996` `_build_npc_agency_plan_projection()`) is consulted with a `gathering_paused` gate. The gate **does not** suppress NPC mundane action; it only suppresses mandatory-beat consumption tied to the missing co-presence.
- The canonical-step pointer does **not** advance while paused. This is observable at `world-engine/app/story_runtime/manager.py:8683-8687` (`_turn_holds_canonical_path_for_free_player_action`) and at `:8746` (the gate against `session.canonical_step_id` advance).

### 6. Player remains free

The player's freedom in `gathering_paused` mode is identical to the freedom defined in [ADR-0057](adr-0057-canon-safe-player-freedom-and-affordance-inference.md): any possible (physically plausible) and morally acceptable (not criminal / not evil) action commits through the same `resolve_player_action` path. The pause does not gate the player. There is no "you must come back" coercion.

### 7. Return clears the pause

Transition `paused: true → false` fires when `current_step_named_characters ⊆ scene-presence` is restored — i.e. all required actors are again at `current_step_scene_id` with intact participation-relevance and visibility / audibility. The Director clears `gathering_paused` atomically; the next LDSS-driven turn resumes mandatory-beat consumption.

### 8. Optional narrator transition reaction

On `paused: false → true` the narrator **may** emit a single block describing the gathering's reaction ("a pause settles over the table; Veronique sets down the paper"). Required properties of the optional block:

- One block, not a stream. PR-0 (this commit) deliberately limits Phase-1 to **one summary block**; per-NPC reaction blocks are a Phase-2 (Pulse) responsibility (see ADR-0058 draft).
- Content-led from `characters/details/actor_pressure_profiles.yaml` and `characters/details/interaction_patterns.yaml`. No hardcoded text snippets in the Director.
- The block is a `narrator` block under the existing `visible_scene_output.blocks.v1` contract. No new block type is added.
- Absence is allowed and observable. The Director records `transition_reaction_emitted: false` when no block was generated.

On `paused: true → false` the narrator transition reaction is optional and follows the same constraints. Phase 1 may ship without it; Phase 2 may add structured continuity callbacks.

### 9. Non-goals

- **No Phase-2 Pulse logic.** ADR-0061 does not introduce a tick, a motivation score, a block-stream-bus, or any of the Pulse-MVP contracts. Those belong to ADR-0058 / ADR-0059 / ADR-0060.
- **No pointer repair.** ADR-0061 does not modify `_execute_opening_locked` or any of the Turn-0 narrator-path handling. Steps 001-005 of the GoC opening remain as the gameplay testpoint defined in the plan §0.
- **No `step.mode` switch.** ADR-0061 does not branch on `step.mode` enum values. The pause decision is a semantic composition over actor topology and resolver signals; reading `step.mode` to gate behavior is explicitly out of scope and prohibited.
- **No new runtime aspect ledger row in PR-0.** PR-C decides whether `gathering_paused` rides on an existing aspect (likely as an `npc_agency` companion field) or warrants its own row; PR-0 only names the contract.
- **No verb / room / actor whitelist.** All discrimination is semantic, derived from inputs the resolver and runtime-world already provide.

## Consequences

**Positive:**

- The player gains canon-safe freedom to interrupt a gathering, including by leaving the apartment, without the runtime declaring a violation or silently advancing past missing co-presence.
- Mandatory-beat consumption is gated by a single, semantic predicate (`gathering_paused`), making "did the canonical step advance this turn?" a question with a structured per-turn answer.
- The Resolver / Director split stays clean: resolver = world physics + morality + target; director = story-mechanic implication.
- Phase-2 Pulse can land later without renegotiating the gathering predicate — `compute_gathering_state` is the same in Phase 1 and Phase 2.

**Negative / trade-offs:**

- PR-C must deliver `compute_gathering_state` and the beat-consumption gate. Until then, "leave the apartment" continues to misbehave (the gap is documented in PR-0's PIV artifact §3).
- `presence_breaks_gathering` requires the resolver to emit `participation_relevance` and `visibility / audibility` reliably (PR-A). Until PR-A ships, PR-C cannot fully drive the composition.

## Testing

Tests for PR-0 verify only that this ADR exists, has `Status: Draft`, and names the required surface terms. Live behavior tests belong to PR-C.

| Layer | Test | Expectation |
|---|---|---|
| ADR presence | `tests/test_npc_interactivity_piv_baseline.py::test_adr_0061_draft_exists_and_defines_director_pause` | File exists, status `Draft`, defines `director_gathering_state.v1`, `compute_gathering_state`, `named_characters`-presence predicate, beat-consumption pause, player-freedom invariant, return-clears-pause condition, narrator transition reaction, and the four non-goals above. |
| ADR-0057 amendment | `tests/test_npc_interactivity_piv_baseline.py::test_adr_0057_phase_1_amendment_names_four_contracts` | `director_gathering_state.v1` appears in ADR-0057's Phase-1 amendment with the same shape declared here. |
| Live composition function | (PR-C) `compute_gathering_state` unit tests with paraphrased movement / participation / visibility inputs; assertions on path properties, not input strings. | Pure function returns expected `{paused, missing}` for documented input combinations. |
| Live beat-consumption gate | (PR-C) live smoke against the LDSS / NPC agency path; assertions on `mandatory_beat_consumed_during_pause: false` invariant. | Mandatory beats do not consume during pause; canonical step pointer does not advance. |

Per [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md), all PR-C tests assert structured contract fields and path properties, not the player input string or example prose.

## Operational evidence

- Roadmap section: [`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md`](../../NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md) §3.4.
- PIV artifact: [`docs/implementation_logs/pr_0_npc_interactivity_contracts_piv.md`](../implementation_logs/pr_0_npc_interactivity_contracts_piv.md).
- Roadmap PIV index: [`docs/MVPs/npc_interactivity_piv_log.md`](../MVPs/npc_interactivity_piv_log.md).
- Diagnostic envelope: `runtime_diagnostic_snapshot.v1` (stub introduced in PR-0; populated by PR-A/B/C).

## Implementation Status (Phase-1 Live Wiring — 2026-05-19)

### Implemented

- `compute_gathering_state` — pure function, fully tested (39 tests green).
- `should_suppress_mandatory_beat_consumption` — beat-consumption gate.
- `gathering_pause_is_transition` — entry/exit transition detection.
- PR-C wiring in `_resolve_player_action` node:
  - `director_gathering_state.v1` computed from resolver evidence.
  - Beat-consumption gate applied in scene director.
  - `director_pause_transition_reaction` emitted on entry/exit.
- Diagnostic exposure in `graph_diagnostics.phase1_director_pause_diagnostics`:
  - `free_player_action_resolution`
  - `canonical_path_hold_effect`
  - `narrator_consequence_realization`
  - `director_gathering_state`
  - `gathering_paused_beat_suppression`
  - `director_pause_transition_reaction`

### Input Wiring (Phase-1 Live Readiness)

| Input | Source | Live Status |
|---|---|---|
| `actor_locations` | `state["environment_state"]["actor_locations"]` (fallback wired) | **Available** — populated from `normalize_environment_state` at graph init and at `goc_resolve_canonical_content`. |
| `current_step_named_characters` | 1. `canonical_path.steps[step_id].present.named_characters` 2. `actor_lane_context.npc_actor_ids + human_actor_id` | **Conditionally available** — requires `canonical_path` in state (loaded by `goc_resolve_canonical_content`) OR `actor_lane_context` (always present for player turns). |
| `current_step_scene_id` | `state["current_step_scene_id"]` ← fallback → `state["current_scene_id"]` | **Available** — `current_scene_id` is always passed by world-engine manager. |

### Diagnostic Blockers (fail-closed)

When inputs are absent, the runtime emits:
- `reason: "missing_actor_locations"` — if `actor_locations` cannot be resolved from any source.
- `reason: "missing_named_characters"` — if neither `canonical_path` step data nor `actor_lane_context` provides actor IDs.

Neither blocker fakes `paused=false` — they emit `diagnostic_blocker: true` to signal incompleteness.

### Remaining for Accepted

1. Live smoke session on real stack (requires Docker world-engine + backend).
2. Verify `canonical_path` is available in state at `_resolve_player_action` time for the full-path (non-thin-path) execution.
3. Confirm `narrative_systems.html` diagnostic page renders `phase1_director_pause_diagnostics`.

## Acceptance criteria for promotion to Accepted

ADR-0061 transitions from `Draft` to `Accepted` only when:

1. PR-C has merged with green tests for `compute_gathering_state` and the beat-consumption gate.
2. The per-turn `director_gathering_state.v1` snapshot is exposed in the operator endpoint family established by [ADR-0062](adr-0062-director-realization-thin-path.md) and rendered in the existing `narrative_systems.html` diagnostic page.
3. A live smoke session demonstrates the entry / exit transition on a documented player input class.
4. No regressions in the existing MVP3 ruhepunkt / LDSS test suite.
