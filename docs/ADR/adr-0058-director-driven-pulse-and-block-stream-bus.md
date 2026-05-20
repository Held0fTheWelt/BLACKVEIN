# ADR-0058: Director-Driven Pulse and Block-Stream-Bus

## Status

Accepted

## Date

2026-05-20

## Phase 2 Completion Note (2026-05-20)

This file is the **conceptual** ADR — the 10-section Decision block other
ADRs cross-link to. The **stage-by-stage implementation record** for
Phase 2 lives in the companion file
[`adr-0058-director-driven-pulse-block-stream-bus.md`](adr-0058-director-driven-pulse-block-stream-bus.md)
(note: no "and" in the slug). That file documents **Stages A–M** plus a
**Completion Pass** that proves the end-to-end player-experience chain:

```
Player Turn → block_stream_event → autonomous tick → player cut-in →
handoff → promoted input → post-cut-in replanning → follow-up event →
silence fallback → diagnostics
```

Phase 2 ships behind feature flags. Bundle delivery, REST fallback,
Commit / Readiness semantics, and `validation_outcome` are unchanged.
WebSocket is not mandatory. Full mid-turn graph mutation (Stage J) and
production semantic-provider wiring for the Stage-M dispatcher are
explicit Future Work. Current status:
[`docs/MVPs/phase_2_director_pulse_status.md`](../MVPs/phase_2_director_pulse_status.md).

The two ADR-0058 files are a known governance duplication; their
conceptual layer (this file) and implementation layer (the long file)
agree on every hard boundary listed below.

## Related ADRs

- [ADR-0039](adr-0039-gate-tests-no-hardcoded-oracle-bypass.md) — semantic-name vocabulary discipline; no Pi/Π runtime keys.
- [ADR-0041](adr-0041-semantic-capability-selection-and-runtime-capability-budgeting.md) — semantic capability selection; Director composes from Table B.
- [ADR-0053](adr-0053-bounded-semantic-scene-planner.md) — Director is advisory; truth pipeline is proposal → validation → commit.
- [ADR-0059](adr-0059-semantic-npc-motivation-score.md) — defines how motivation scores are computed per tick.
- [ADR-0060](adr-0060-souffleuse-inner-voice-composition.md) — Souffleuse as inner voice; composition semantics parallel to NPC initiative.
- [ADR-0061](adr-0061-director-pause-mode-for-gathering-interruption.md) — Director-Pause (gathering_paused) is the pre-condition for NPC mundane autonomy.
- [ADR-0062](adr-0062-director-realization-thin-path.md) — thin path on which Director-Pulse rides.

## Context

Today the runtime delivers all blocks for a turn as a bundle after the AI model
call completes. NPCs speak only when a bundle is assembled; the player waits for
the full bundle before input is re-opened at the Ruhepunkt. This makes the scene
feel turn-based rather than alive.

`NPC_INTERACTION_AND_INTERACTIVITY_PLAN.md` §4 defines Phase 2: NPCs must be
able to act from motivation on their own pulse, the player must be able to cut
in at any time, and blocks must be deliverable one-at-a-time rather than only
as full bundles. The Director — not an external engine-scheduler — must be the
source of these ticks.

Phase 2 requires a new contract surface:

1. The Director emits one tick decision per evaluation.
2. Each tick may emit at most one block.
3. Silence is an active, recorded Director choice.
4. The player's input is an equal-weight event next to NPC initiative.
5. The existing bundle path must remain valid and available as fallback.

The Phase-2 Pulse is implemented as a **shadow path**: it runs alongside the
existing bundle path and does not replace it. The bundle path is still primary.
The shadow path produces diagnostic events (`director_tick_decision.v1`,
`block_stream_event.v1`, `npc_motivation_score.v1`, `player_cut_in_event.v1`)
that can be observed without breaking the live session.

## Decision

### 1. Director as tick source

The Director is the source of ticks. No external wall-clock scheduler emits
ticks independently; the Director decides when a tick fires. Tick triggers are
event-driven:

- `player_input` — player sends input.
- `motivation_threshold_crossed` — a motivation score computation indicates an
  NPC above threshold.
- `state_change` — a Director-relevant state change occurs (e.g. `gathering_paused`
  transition).
- `cooldown_check` — minimum cooldown from `pacing_rhythm` has elapsed.

Wall-clock ticking alone is explicitly prohibited. Silence is always a valid,
recorded Director response to any trigger.

### 2. Contract: `director_tick_decision.v1`

One record per tick, always. Silence ticks are not omitted. Required fields:

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"director_tick_decision.v1"` | constant |
| `tick_id` | UUID string | unique per tick |
| `trigger_kind` | closed enum | `player_input \| motivation_threshold_crossed \| state_change \| cooldown_check` |
| `triggering_actor_id` | string \| null | actor who triggered, or null |
| `chosen_action_kind` | closed enum | `speak \| gesture \| local_mundane_action \| follow \| react_locally \| silence` |
| `chosen_actor_id` | string \| null | actor with initiative; null when silence |
| `composition_inputs` | list[string] | semantic capability names consulted; **no Pi/Π IDs** |
| `since_last_tick_ms` | float \| null | elapsed ms since previous tick |
| `silence_reason` | string \| null | populated when `chosen_action_kind == "silence"` |

### 3. Contract: `block_stream_event.v1`

One block = one event. No bundles. Required fields:

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"block_stream_event.v1"` | constant |
| `event_id` | UUID string | unique per event |
| `tick_id` | UUID string | references the tick that produced this block |
| `block_type` | closed enum | `narrator \| actor_line \| actor_action \| environment_interaction \| souffleuse` |
| `block_payload` | dict | the block's content (matches existing block shapes) |
| `cut_in_state` | closed enum | `uninterrupted \| cut_em_dash \| cut_skip_to_end` |
| `lane` | closed enum | `visible_scene_output \| player_hint` |
| `source` | string | actor or subsystem that produced the block |

### 4. Contract: `npc_motivation_score.v1`

One record per NPC per tick evaluation. Below-threshold NPCs are recorded too
(for diagnostic reproducibility). Required fields: defined in ADR-0059.

### 5. Contract: `player_cut_in_event.v1`

One record when the player's input interrupts an in-flight block. Required fields:

| Field | Type | Notes |
|---|---|---|
| `schema_version` | `"player_cut_in_event.v1"` | constant |
| `cut_in_id` | UUID string | unique |
| `tick_id` | UUID string | the tick this cut-in belongs to |
| `interrupted_block_id` | string \| null | block being interrupted, or null |
| `interrupted_block_type` | string \| null | type of interrupted block |
| `cut_kind` | closed enum | `em_dash \| skip_to_end \| no_active_block` |
| `player_input_payload` | dict | raw player input evidence |

### 6. Cut-in semantics (block-type-dependent)

| Active block type | Cut kind | Effect |
|---|---|---|
| `actor_line` | `em_dash` | Append "—" to the current line; player takes next initiative |
| `narrator` | `skip_to_end` | Narrator block finishes; player takes next initiative |
| `actor_action` | `skip_to_end` | Same |
| `souffleuse` | `skip_to_end` | Same |
| `environment_interaction` | `skip_to_end` | Same |
| None (no active block) | `no_active_block` | Player speaks without interrupting anything |

Cut-in semantics are determined by **block type only**. No actor ID, room, verb,
or step-mode switch may influence cut-in kind.

### 7. Capability composition per tick

The Director composes semantic capability inputs per tick. `composition_inputs`
in `director_tick_decision.v1` must list the semantic runtime names actually
consulted. Allowed names include:

- `scene_energy`, `social_pressure`, `relationship_dynamics`, `narrative_momentum`
- `actor_pressure_profiles`, `interaction_patterns`, `pacing_rhythm`

No Pi/Π-numbered runtime keys appear in `composition_inputs` or any field of the
four contracts.

### 8. Shadow path (Phase-2 delivery mode)

The four contracts are implemented as a **shadow path** that runs in parallel to
the existing turn-bundle path. The shadow path:

- Does not mutate session state.
- Does not consume mandatory beats.
- Does not advance the canonical path.
- Does not replace the visible bundle output.
- Is always labeled `shadow_only: true`.

The existing `visible_scene_output.blocks.v1` bundle remains the primary
delivery path. Making the event stream primary is explicitly deferred to a
future decision (post-Phase-2 stabilization). No implementation change may
assume the event stream is primary in Phase 2.

### 9. `gathering_paused` compatibility

When `director_gathering_state.v1` has `paused: true` (ADR-0061):

- The shadow path still evaluates motivation scores and emits diagnostic events.
- Mandatory beats are not consumed (governed by ADR-0061, unchanged).
- NPC initiative in shadow mode does not drive beat consumption.
- The canonical path does not move.

### 10. Bundle path preserved

The existing block bundle delivery path is preserved without change. No existing
contract (`visible_scene_output.blocks.v1`, `npc_agency_simulation.v1`, etc.)
is removed, weakened, or made secondary by this ADR.

## Consequences

**Positive:**

- Director pulse is observable and reproducible from tick records.
- Silence is a first-class, recorded Director action; no silent ticks disappear.
- Player initiative (cut-in) and NPC initiative are equal-weight events with identical diagnostic visibility.
- Block-by-block delivery is possible when the event stream is made primary later, without redesigning contracts.
- Shadow path means zero risk to the existing live session.

**Negative / Trade-offs:**

- Phase 2 event stream is not yet the primary path; live cut-in is not player-visible in Phase 2.
- Shadow path produces diagnostic overhead (four contract types per tick) without immediate player-facing effect.
- Making the event stream primary requires a future ADR and frontend change; this ADR deliberately defers that.

## Implementation

### New modules

- `ai_stack/director/director_pulse_contracts.py` — the four contract builders (pure functions, no I/O).
- `ai_stack/npc_agency/npc_motivation_score_engine.py` — motivation score computation (ADR-0059).
- `ai_stack/director/director_pulse_shadow.py` — shadow-path coordinator (`evaluate_director_tick()`).

### Content change

- `content/modules/god_of_carnage/module.yaml` — `runtime_intelligence.npc_motivation_score`
  section added with weights and per-actor threshold modifiers.

### Tests

- `ai_stack/tests/test_phase2_director_pulse.py` — contract shape tests, motivation engine
  tests, shadow path tests, cut-in semantics tests, ADR-0039 guardrail tests.

### What this ADR does NOT change

- `ai_stack/director/director_gathering_state_contracts.py` — unchanged (ADR-0061 domain).
- Any existing `visible_scene_output.blocks.v1` or bundle path logic.
- Any validation, commit, or readiness semantics.
- Any MVP3 LDSS contracts or test gates.
