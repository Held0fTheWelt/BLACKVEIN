---
id: ADR-0058
title: Director-Driven Pulse and Block-Stream-Bus
status: ACCEPTED
date: 2026-05-19
---

## Context

The World of Shadows runtime produces scene output as a flat bundle
(`visible_scene_output.blocks`). Phase 2 introduces a parallel event-stream
channel (`block_stream_events`) and a Director Pulse that computes per-tick NPC
motivation scores. The goal is to promote the event stream to primary rendering
path while preserving the bundle as fallback and avoiding any change to
commit/readiness semantics.

## Decision

### Stage A — Shadow Mode (complete)

A shadow Director tick runs once per committed turn. It produces four
Pulse-MVP contracts:

| Contract | Schema |
|---|---|
| `director_tick_decision.v1` | Tick ID, trigger, chosen actor, action, silence flag |
| `block_stream_event.v1` | One event per block, with `block_payload` copy |
| `npc_motivation_score.v1` | Weighted score per NPC, argmax initiative selection |
| `player_cut_in_event.v1` | Cut-in semantics (diagnostic-only, `shadow_only=True`) |

All output is `shadow_only=True`. No session state is mutated. No LLM call.

### Stage B — Dual Mode (complete)

`PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED=true` activates the parallel channel.
`block_stream_events` is appended to `visible_scene_output`. The bundle
(`visible_scene_output.blocks`) is unchanged and remains canonical.

Parity diagnostics (`diagnostics.director_pulse.parity`) compare bundle blocks
to stream events and classify: `aligned`, `count_mismatch`, `type_mismatch`,
`event_missing`, `bundle_missing`, `not_applicable`.

### Stage B→C — Readiness (complete)

`diagnostics.phase2_event_stream_readiness` is added to every dual-mode turn.
Fields: `event_stream_present`, `bundle_fallback_available`, `parity_status`,
`can_be_primary_candidate`, `blockers`, `proof_level`, `cut_in_readiness`,
`motivation_score_sources`, `ws_session_loop_supported`.

The frontend `BlocksOrchestrator.loadTurnFromEventStream()` was deployed behind
`window.WOS_PHASE2_BLOCK_STREAM_ENABLED` (Stage B gate). It falls back to
`loadTurn()` when events are absent or invalid.

### Stage D — WebSocket Session Loop + Live Cut-In (complete)

`PHASE2_WS_SESSION_LOOP_ENABLED=true` activates Stage D server-side.
`window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED` activates the frontend client.

**Endpoint:** `WS /api/story/sessions/{session_id}/stream`
(`world-engine/app/api/story_ws.py`, mounted alongside the existing REST
router; the runtime/lobby `/ws` endpoint is unrelated and untouched).

**Auth:** `?key=<PLAY_SERVICE_INTERNAL_API_KEY>` query param, or
`X-Play-Service-Key` header — same key the REST `/api/story/...` endpoints
use. Test mode (`FLASK_ENV=test`/`ENV=test`) bypasses the key check.

**Wire protocol (JSON over WS):**

Client → server:

| `kind` | Fields |
|---|---|
| `start_turn` | `player_input` (string) |
| `cut_in` | `player_input` (string) — mid-stream player initiative |
| `ping` | — |

Server → client:

| `kind` | Fields |
|---|---|
| `stream_started` | `session_id`, `turn_id` |
| `block_started` | `event_id`, `block_type`, `block_stream_event` (full `block_stream_event.v1`) |
| `block_completed` | `event_id` |
| `block_cut` | `cut_kind` (one of `em_dash` / `skip_to_end` / `no_active_block`), `block_type`, `player_cut_in_event` (`player_cut_in_event.v1`), `drop_remaining_blocks`, `flush_active_block` |
| `stream_idle` | `reason` (`completed` / `no_events`) |
| `stream_error` | `reason`, `detail` |
| `pong` | (ping reply) |

**Streaming model:**

1. Client connects and receives an initial `stream_started`.
2. Client sends `start_turn`. Server runs the same REST-path turn via
   `StoryRuntimeManager.execute_turn(...)` — commit/readiness/validation
   unchanged.
3. Server emits the resulting `block_stream_events` one-at-a-time as
   `block_started` → (pacing window) → `block_completed`. Empty turns
   produce a `stream_idle` with `reason="no_events"`.
4. During the pacing window between started and completed, a `cut_in`
   message routes through `apply_cut_in()`:
   - active `actor_line` → `cut_kind="em_dash"`, drop remaining queue,
     no flush.
   - active `narrator` / `actor_action` / `souffleuse` /
     `environment_interaction` → `cut_kind="skip_to_end"`, drop
     remaining queue, flush active block.
   - no active block → `cut_kind="no_active_block"`, queue carries the
     player input forward into the next `start_turn`.
5. On `block_cut`, server emits the event and ends the current stream;
   the input is queued for the next turn (never lost).

**Pacing:** `PHASE2_WS_BLOCK_PACING_SECONDS` (default `0`) controls the
gap between `block_started` and `block_completed`. Set non-zero in
operator/test environments to make cut-in physically possible against a
real client clock.

**Server diagnostics surface:**

`GET /api/story/runtime/ws-session-loop-support` reports:

| Field | Type | Description |
|---|---|---|
| `ws_session_loop_supported` | bool | env flag enabled |
| `live_interruption_supported` | bool | mirrors `ws_session_loop_supported` |
| `endpoint` | str | `/api/story/sessions/{session_id}/stream` |
| `cut_kind_semantics` | dict | block_type → cut_kind mapping |
| `fallback_path` | str | `rest_or_event_stream` |

**Client diagnostics** (orchestrator `getState()`):

| Field | Type | Description |
|---|---|---|
| `ws_session_loop_supported` | bool | client confirmed via `stream_started` |
| `live_interruption_supported` | bool | true while a block is active |
| `ws_connected` | bool | socket is open |
| `active_block_id` | str \| null | currently rendering block's event_id |
| `last_player_cut_in_event` | dict \| null | most recent `player_cut_in_event.v1` |
| `cut_in_count` | int | total cuts applied this connection |
| `stream_fallback_reason` | str \| null | one of `flag_disabled`, `missing_url`, `websocket_unavailable`, `connect_threw`, `socket_error`, or a server `stream_error.reason` |
| `proof_level` | str | `unknown` / `live_loop_active` |
| `ws_queued_input_count` | int | inputs awaiting REST/replay |

**Fallback chain (client):** flag off → REST; flag on, socket fails →
`stream_fallback_reason` recorded and `restFallback` callback fired, REST
path remains canonical. A `block_cut` event with `cut_kind` outside the
closed enum is treated as a no-op render.

### Stage C — Primary Event Stream (complete)

`PHASE2_BLOCK_STREAM_PRIMARY_ENABLED=true` (server) and
`window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED` (frontend) activate Stage C.

**Primary selection logic (frontend):**

1. Check `window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED`
2. Read `diagnostics.phase2_event_stream_readiness.can_be_primary_candidate`
   from the server-provided envelope
3. If both true **and** events are valid: use event stream, record
   `event_stream_primary_used=true`
4. Otherwise: load bundle, record `event_stream_fallback_reason`

**Server-side selection metadata** (`diagnostics.phase2_primary_selection`):

| Field | Type | Description |
|---|---|---|
| `event_stream_primary_attempted` | bool | Stage C was active |
| `event_stream_primary_used` | bool | Event stream selected |
| `event_stream_fallback_used` | bool | Bundle fallback taken |
| `event_stream_fallback_reason` | str \| null | `readiness_not_candidate`, `event_stream_missing`, `readiness_invalid`, or null |
| `parity_status` | str | Forwarded from readiness |
| `bundle_fallback_available` | bool | Forwarded from readiness |
| `primary_flag_enabled` | bool | Server env var state |

**Fallback diagnostics** (also recorded in `orchestrator._lastPrimarySelection`
and exposed via `getState().last_primary_selection`):

Same fields, computed client-side from readiness metadata.

## Consequences

**Preserved (hard boundaries):**

- `visible_scene_output.blocks` — never removed, never mutated
- `validation_outcome` — unchanged
- Commit/Readiness semantics — unchanged
- LDSS/Ruhepunkt beat progression — unchanged
- Canonical path progression — unchanged
- No Pi/Π runtime keys
- No hardcoded actor IDs, room IDs, or speaker order
- Cut-in `live_interruption_supported=False` until WS/session-loop is ready
  (Stage D opt-in flips this to `True` only while a real block is active)
- Stage D never replaces the REST turn path; bundle remains canonical
- Stage D never implements wall-clock-only NPC ticking; the Director
  re-evaluation path always anchors a tick to a player or motivation
  trigger via the existing turn graph

**Feature flags:**

| Flag | Default | Purpose |
|---|---|---|
| `PHASE2_BLOCK_STREAM_DUAL_MODE_ENABLED` | off | Produce `block_stream_events` in parallel |
| `PHASE2_BLOCK_STREAM_PRIMARY_ENABLED` | off | Enable Stage C primary selection (server) |
| `PHASE2_WS_SESSION_LOOP_ENABLED` | off | Enable Stage D WebSocket session loop endpoint |
| `PHASE2_WS_BLOCK_PACING_SECONDS` | `0` | Gap between `block_started`/`block_completed` for cut-in window |
| `window.WOS_PHASE2_BLOCK_STREAM_ENABLED` | off | Stage B frontend event stream consumption |
| `window.WOS_PHASE2_BLOCK_STREAM_PRIMARY_ENABLED` | off | Stage C frontend primary selection |
| `window.WOS_PHASE2_WS_SESSION_LOOP_ENABLED` | off | Stage D frontend WS session loop client |

All flags fail closed. Invalid values treat as false.

**Remaining work for full real-time co-existence (post Stage D):**

1. ~~Autonomous NPC ticking~~ — **Stage E (complete).** See `Stage E` below.
2. Live re-evaluation that mutates an in-flight turn — the current model
   queues cut-in input for the next `start_turn`. Mid-turn Director
   re-planning remains gated and is *not* part of Stage E.
3. Real-time `block_stream_event.cut_in_state` rewrite after cut — Stage D
   emits a `block_cut` envelope but does not rewrite the original event's
   `cut_in_state` field; consumers should read the `block_cut` message,
   not retro-mutate prior events. Stage E preserves this discipline.

### Stage E — Autonomous Director Ticks and NPC Coexistence (complete)

`PHASE2_AUTONOMOUS_TICK_ENABLED=true` activates Stage E server-side. Off by
default; invalid values fail closed.

**What Stage E adds:** After a clean user-input turn completes streaming
over the WS session loop (Stage D), the Director MAY emit *one*
autonomous NPC block when motivation scoring promotes an initiative
actor. Stage E does **not** replace Stage D; it composes on top.

**New module:** `ai_stack/phase2_autonomous_tick.py`

- `AutonomousTickInputs` — pure inputs (trigger kind, NPCs, capability
  outputs, pacing policy, gathering_paused, cooldown timestamp).
- `AutonomousTickOutcome` — outcome (chosen actor, block event or None,
  silence reason, cooldown state, suppression reason). `shadow_only=False`
  (live path).
- `should_emit_autonomous_tick()` — pre-check for flag, trigger validity,
  cooldown, pending input, in-flight block, and NPC presence.
- `evaluate_autonomous_tick()` — delegates initiative selection to
  `evaluate_director_tick()` (the Stage A shadow contract), then
  promotes the selection into one `block_stream_event.v1` with
  `block_type=actor_line`, `originator=autonomous_tick`.

**Triggers (closed enum, event-driven only):**

- `player_input`
- `motivation_threshold_crossed`
- `state_change`
- `cooldown_check`

Wall-clock-only ticking is explicitly forbidden by Stage E. The
coordinator is invoked at a discrete, observable moment (today: post
user-turn delivery in the WS session loop).

**Per-tick semantics:**

- Evaluate per-NPC motivation scores using existing
  `npc_motivation_score_engine` — no LLM call, principled-deterministic.
- Pick the highest-score NPC above threshold (no rotation, no roster).
- If picked: build one `block_stream_event.v1` (`actor_line`,
  `originator=autonomous_tick`).
- If nobody crosses: silence with closed-enum reason
  (`no_npc_above_motivation_threshold` /
  `gathering_paused_off_stage_only` / `director_chose_silence`).
- Cooldown comes from `pacing_rhythm.min_tick_interval_ms` policy
  (default `1500ms` if absent). First tick is always free.
- `gathering_paused` propagates through but never consumes mandatory
  beats and never advances the canonical path.

**Suppression reasons (closed enum):**

- `flag_disabled`
- `no_npcs_present`
- `cooldown_active`
- `pending_player_input`
- `invalid_trigger`
- `already_emitting`

**New WS server-to-client message:**

| `kind` | Fields |
|---|---|
| `autonomous_tick_evaluated` | `summary` (full diagnostic — see below) |

The `summary` payload always carries: `tick_id`, `tick_trigger_kind`,
`chosen_actor_id`, `chosen_action_kind`, `motivation_scores` (mapping
of `actor_id → float`), `silence_reason`,
`autonomous_tick_suppressed_reason`, `cooldown_state`,
`gathering_paused`, `canonical_path_advanced` (always `false`),
`mandatory_beat_consumed` (always `false`), `block_emitted`.

**WS session-loop integration:** after the user-turn stream idles
without a cut-in, the Director evaluates one autonomous tick. If the
outcome emits a block, the server streams it through the existing
`block_started`/`block_completed` pacing window with full
`block_cut` support — a player cut into an autonomous `actor_line`
yields `cut_kind=em_dash`, drops the queue, and carries the player
input into the next `start_turn`. If silence is chosen, the server
sends `autonomous_tick_evaluated` followed by `stream_idle(reason=completed)`.

**Diagnostic surface additions** (HTTP `/api/story/runtime/ws-session-loop-support`):

| Field | Type | Description |
|---|---|---|
| `autonomous_tick_enabled` | bool | env flag enabled |
| `autonomous_tick_trigger_kinds` | list[str] | closed-enum trigger list |

**Client diagnostics** (orchestrator `getState()`):

| Field | Type | Description |
|---|---|---|
| `autonomous_tick_evaluated_count` | int | Number of evaluations received |
| `autonomous_tick_block_received_count` | int | Number of autonomous blocks rendered |
| `autonomous_tick_silence_count` | int | Number of silence evaluations |
| `autonomous_tick_cut_in_interrupted_count` | int | Cut-ins that hit an autonomous block |
| `last_autonomous_tick_summary` | dict \| null | Most recent server-sent summary |
| `active_block_is_autonomous` | bool | Currently rendering block was Director-driven |

**Hard boundaries (Stage E preserves Stage A–D promises and adds):**

- Wall-clock-only NPC ticking is forbidden. Stage E ticks are event-driven.
- Mid-turn replanning is forbidden. Once a turn commits, its
  `validation_outcome`, `block_stream_events`, and bundle blocks are
  immutable; Stage E adds new blocks *after* the committed turn delivers.
- No new Pi/Π runtime keys.
- No hardcoded actor IDs, rooms, verbs, or fixed speaker rotation.
- Canonical path advance and mandatory beat consumption stay at `False`
  for every autonomous tick, even when an NPC speaks.
- Cut-in semantics (block-type → cut_kind) are identical between
  user-turn blocks and autonomous blocks.
- REST/bundle fallback is unchanged; Stage E only adds messages after
  the canonical bundle delivery.

**Feature flags additions:**

| Flag | Default | Purpose |
|---|---|---|
| `PHASE2_AUTONOMOUS_TICK_ENABLED` | off | Enable Stage E autonomous Director ticks |

### Stage F — Capability-Fed Autonomous Ticks and Off-Stage Memory (complete)

Stage F preserves every Stage E surface and gate. It adds three things:

1. **Capability feeding.** The dual-mode envelope augmenter
   (`augment_envelope_with_block_stream`) now accepts and persists
   `actor_pressure_profiles`, `npc_motivation_score_policy`,
   `pacing_rhythm_policy`, plus the structured capability outputs that
   fed the tick (`scene_energy_output`, `social_pressure_output`,
   `relationship_state_output`, `narrative_momentum_output`). These flow
   from `graph_state` (via
   `extract_capability_outputs_from_graph_state`) and from
   `graph_state["module_runtime_policy"]` /
   `module.yaml.runtime_intelligence` (via the Stage F helper
   `extract_module_policies_for_director`). They surface on
   `diagnostics.director_pulse.{capability_outputs,
   actor_pressure_profiles, npc_motivation_score_policy,
   pacing_rhythm_policy}` for the WS endpoint to read.

2. **Source classification (three-tier).** A new component-source
   vocabulary distinguishes:

   - `real_runtime_signal` — a structured capability output was supplied
   - `module_policy_default` — only the module policy (e.g. score weights
     or actor pressure profiles) was available
   - `missing_signal` — neither runtime output nor policy default was
     present; the engine fell back to a neutral mid-range constant

   The autonomous-tick coordinator surfaces these on
   `AutonomousTickOutcome.motivation_score_component_sources` and the WS
   summary, plus `capability_outputs_used` / `capability_outputs_missing`
   lists that enumerate every Stage F surface that was (or was not)
   supplied this tick.

3. **Off-stage update scaffold.** A new pure module
   `ai_stack/phase2_off_stage_updates.py` builds *candidate*
   relationship and hierarchical-memory updates from autonomous ticks
   that target an NPC outside the visible scene. The scaffold:

   - returns `relationship_update_candidate` and `memory_update_candidate`
     dicts with closed-enum `candidate_kind`
     (`relationship_tension_update`, `off_stage_memory_note`) and a
     structured payload; no free-text body, no plot-bearing facts
   - rejects new people (NPC not in `known_actor_ids`), new rooms
     (room not in `known_room_ids` when referenced), free-text body
     fields (`text`/`body`/`narration`/`*_text`), plot facts
     (`plot_fact`/`revelation`/`secret`/`hidden_fact`/`twist`/`reveal`),
     `canonical_path_advance` attempts, and
     `mandatory_beat_consume` attempts — each rejection is a
     closed-enum blocker reason
   - reports `off_stage_safety_gate_result` as one of
     `pass` / `blocked` / `not_applicable`
   - never commits — commit must flow through the existing safe
     relationship-state or hierarchical-memory mechanisms; Stage F only
     surfaces the *proposal*

**New diagnostic fields on the WS `autonomous_tick_evaluated.summary`:**

| Field | Type | Description |
|---|---|---|
| `capability_outputs_used` | list[str] | Stage F surfaces actually supplied |
| `capability_outputs_missing` | list[str] | Stage F surfaces absent |
| `motivation_score_component_sources` | dict[str,str] | per-component three-tier label |
| `off_stage_update_candidate` | dict | full scaffold result (gate + blockers + candidates) |

`AutonomousTickOutcome.to_dict()` includes the same fields under the same
names.

**Hard boundaries (Stage F preserves Stage A–E promises and adds):**

- Off-stage candidates never advance the canonical path
  (`canonical_path_advanced=False` is an invariant on every candidate).
- Off-stage candidates never consume a mandatory beat
  (`mandatory_beat_consumed=False` is an invariant on every candidate).
- Off-stage candidates never introduce a new person, room, or plot
  fact (closed-enum blockers).
- Candidate payloads are structured-only — free text bodies are a
  closed-enum blocker.
- No new Pi/Π runtime keys.
- No hardcoded actor IDs, rooms, or speaker rotations.
- REST/bundle fallback unchanged.
- `validation_outcome`, Commit, Readiness unchanged.
- The coordinator never fakes real capability evidence: when no
  structured runtime output is supplied, the component source is
  `module_policy_default` or `missing_signal`, never
  `real_runtime_signal`.

## Governance

- ADR-0039 — No Pi/Π runtime keys
- ADR-0059 — Semantic NPC Motivation Score
- ADR-0060 — Souffleuse Inner Voice Composition
- Table B anti-hardcoding gate — `phase2_stream_readiness.py`,
  `block_stream_dual_mode.py`, `npc_motivation_score_engine.py`,
  `director_pulse_contracts.py`, `director_pulse_shadow.py`,
  `phase2_ws_session_loop.py`, `phase2_autonomous_tick.py` registered as
  canonical surfaces for `scene_energy`, `narrative_momentum`, and
  `pacing_rhythm` aspects
- Stage D anti-hardcoding: cut-in semantics are block-type-driven via
  `resolve_cut_kind_for_block_type()`; no actor IDs, room IDs, or verbs
  influence the cut decision
- Stage E anti-hardcoding: initiative selection is the highest motivation
  score above threshold (no fixed roster, no rotation); cooldown derives
  from content `pacing_rhythm.min_tick_interval_ms`; triggers are a
  closed enum and never include wall-clock polling
- Stage F anti-hardcoding: capability sources are labelled with a
  closed-enum three-tier vocabulary
  (`real_runtime_signal` / `module_policy_default` / `missing_signal`);
  off-stage candidate blockers are a closed enum
  (`new_person` / `new_room` / `new_plot_fact` / `free_text_body` /
  `canonical_path_advance_attempted` /
  `mandatory_beat_consume_attempted` / `no_off_stage_actor` /
  `no_npc_chosen`); candidate payload shape is structured-only and
  schema-versioned
