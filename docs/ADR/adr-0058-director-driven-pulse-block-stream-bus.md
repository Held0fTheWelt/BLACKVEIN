---
id: ADR-0058
title: Director-Driven Pulse and Block-Stream-Bus
status: ACCEPTED
date: 2026-05-20
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
2. ~~Multi-tick autonomous evaluation during a pause window~~ —
   **Stage H (complete).** See `Stage H` below.
3. ~~Future-only replanning after a player cut-in~~ —
   **Stage I (complete).** See `Stage I` below.
4. ~~Player cut-in immediate Director handoff~~ —
   **Stage K (complete).** See `Stage K` below.
5. ~~Post-cut-in Director re-read and follow-up composition~~ —
   **Stages L+M (complete; provider wiring deferred).** See
   `Stage L` and `Stage M` below.
6. **Stage J — controlled mid-turn graph mutation.** Still deferred.
   Stage I's `future_events_only` scope is the boundary; Stage J
   would re-run validation/commit against a delta. Out of Phase-2
   scope; tracked in
   `docs/MVPs/phase_2_director_pulse_status.md` §5.1.
7. **Production semantic-provider wiring for Stage M.** The
   dispatcher and gates ship in Phase 2; no production provider is
   registered on the WS endpoint. Out of Phase-2 scope; tracked in
   `docs/MVPs/phase_2_director_pulse_status.md` §5.2.
8. Real-time `block_stream_event.cut_in_state` rewrite after cut —
   Stage D emits a `block_cut` envelope but does not rewrite the
   original event's `cut_in_state` field; consumers should read the
   `block_cut` message, not retro-mutate prior events. Every later
   stage (E–M) preserves this discipline.

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
| `PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED` | off | Enable Stage H multi-tick pause-loop iteration (separately gated from Stage E) |
| `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED` | off | Enable Stage M semantic-generation dispatcher (provider must also be injected) |

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
- Stage G anti-hardcoding: commit policy is opt-in per call;
  `allowed_candidate_kinds`, `commit_target`, and `skipped_reason` are
  closed enums; `auto_commit_enabled` defaults to `False`;
  `max_commits_per_tick` is bounded `[0, 8]`; the safety gate from
  Stage F is re-run before any commit projection
- Stage H anti-hardcoding: loop bounds (`max_ticks_per_pause`,
  `min_tick_interval_ms`) come from content policy
  (`pacing_rhythm`); loop triggers and stop reasons are closed
  enums; no wall-clock polling; the loop never weakens any Stage-E
  per-iteration gate
- Stage I anti-hardcoding: replanning scope is fixed at
  `future_events_only`; replanned diagnostic event is built from
  closed-enum contract constants (`director_replanning`,
  `replanned_after_cut_in`, `player_input_priority_replan`); no actor,
  room, or verb literal in any replanning artifact
- Stage K anti-hardcoding: `handoff_status` and `non_handoff_reason`
  are closed enums; the handoff carries IDs only, never invented
  player text; `next_turn_trigger` value is the closed-enum constant
  `player_cut_in_handoff`
- Stage L anti-hardcoding: `selected_next_action_source` is a closed
  enum (`player_input_priority` / `npc_response` / `silence` /
  `idle`); candidate/rejected lists are structured records, never
  free text; the follow-up event reuses the existing
  `block_stream_event.v1` shape
- Stage M anti-hardcoding: composition modes
  (`template_render` / `semantic_generation` /
  `template_fallback_after_semantic_failure` / `not_applicable`),
  safety gates (`length`, `actor_lane`, `voice_forbidden_markers`,
  `no_new_people`, `no_new_rooms`, `no_forbidden_plot_facts`,
  `information_disclosure`), source contexts, and gate results
  (`pass` / `reject` / `not_applicable`) are all closed enums;
  template placeholders are restricted to a closed allowlist; the
  semantic provider returns text only — the safety gates are owned
  by this module; no hardcoded actor IDs, NPC lines, or assistant
  phrasing anywhere in the dispatcher
- Stage M canonical-surface registration: `phase2_ws_session_loop.py`
  is the registered Stage-M canonical surface in
  `SCENE_ENERGY_CANONICAL_SURFACES` and
  `INFORMATION_DISCLOSURE_CANONICAL_SURFACES`
  (`tests/gates/test_table_b_anti_hardcoding_gate.py`)
- Completion Pass: every Stage A–M artifact records the same six
  invariants (`historical_events_mutated`,
  `graph_state_mutated_mid_turn`, `validation_outcome_changed`,
  `commit_or_readiness_changed`, `canonical_path_advanced`,
  `mandatory_beat_consumed`), all `False`; REST/bundle fallback is
  preserved; WebSocket is not mandatory; full mid-turn graph
  mutation (Stage J) and production semantic-provider wiring are
  explicit Future Work, tracked in
  `docs/MVPs/phase_2_director_pulse_status.md`

### Stage G — Off-Stage Safe Commit Path (complete, scaffold)

Stage G adds an *opt-in*, *per-call* commit path on top of the Stage F
preview scaffold. Stage F still produces every candidate; Stage G adds the
mechanics that route an accepted candidate to the existing safe
relationship-state / hierarchical-memory commit surfaces.

**New entry points:** `ai_stack/phase2_off_stage_updates.py`

- `OffStageCommitInputs` — per-call policy + targets. Plain data only;
  the caller (autonomous-tick coordinator or test) supplies the
  candidate result, normalized policy, known actor/room sets, the
  current relationship-state record, the hierarchical-memory snapshot
  and its module policy.
- `commit_off_stage_update_candidates(...)` — validates the policy
  vector, re-runs the structural safety gate on the candidate, and
  produces an `off_stage_commit_result.v1` envelope that names the
  exact commit target(s) and the *projected* updated artifact (an
  updated `relationship_state_record` and/or a merged hierarchical
  memory snapshot). The function **never** writes back to a store —
  persistence stays inside the existing runtime/session layer.
- `build_default_off_stage_commit_result(...)` — closed-enum
  "no-commit" sentinel for the case where Stage G inputs are omitted.

**Closed-enum policy / commit-target vocabulary:**

| Field | Closed enum |
|---|---|
| `off_stage_updates_policy.v1.allowed_candidate_kinds` | `relationship_tension_update` / `off_stage_memory_note` |
| `off_stage_commit_result.v1.commit_target` | `relationship_state` / `hierarchical_memory` |
| `off_stage_commit_result.v1.skipped_reason` (closed enum) | `policy_disabled` / `candidate_kind_not_allowed` / `safety_gate_blocked` / `max_commits_per_tick_exhausted` / `no_off_stage_candidate` |

**Hard boundaries (Stage G preserves Stage A–F promises and adds):**

- Default fail-closed: when `off_stage_updates_policy` is omitted from
  `OffStageCommitInputs` the path stays preview-only and returns
  `skipped_reason="policy_disabled"`.
- `auto_commit_enabled` is false by default; enabling it requires an
  explicit caller-supplied policy.
- Commits are bounded per tick (`max_commits_per_tick`, default 1,
  clamped to `[0, 8]`).
- The safety gate from Stage F runs *again* before any projected
  commit; `require_safety_gate_pass=True` is the default.
- The function projects a **next-state artifact**; it does not invoke
  a writer. Validation/Commit/Readiness/`validation_outcome` remain
  unchanged.
- `canonical_path_advanced` / `mandatory_beat_consumed` invariants
  remain false on every commit-result row.

### Stage H — Multi-Tick Autonomous Pause Loop (complete)

`PHASE2_AUTONOMOUS_PAUSE_LOOP_ENABLED=true` activates Stage H server-side.
Off by default; invalid values fail closed; separately gated from the
single-tick Stage-E flag (enabling autonomous ticks does *not*
automatically enable pause-loop iteration).

**What Stage H adds:** explicit, bounded multi-tick evaluation during a
single pause opportunity. The Director can decide to keep emitting
autonomous NPC blocks while a pause window is open, as long as every
loop step still passes the Stage-E pre-check, the cooldown clock has
advanced enough between iterations, and no player cut-in has been
queued.

**New entry points:** `ai_stack/phase2_autonomous_tick.py`

- `AutonomousPauseLoopInputs` — pure inputs (`tick_inputs`,
  `loop_trigger_kind`, optional `max_ticks_per_pause` override,
  per-step elapsed times, an optional cut-in index).
- `AutonomousPauseLoopOutcome` — outcome (flag state, trigger kind,
  per-step `AutonomousTickOutcome` list, `stop_reason` closed enum,
  resolved `max_ticks_per_pause`, resolved `min_tick_interval_ms`).
- `evaluate_autonomous_pause_loop(...)` — runs the bounded loop and
  records exactly one closed-enum stop reason.

**Loop trigger kinds (closed enum):** `user_pause`, `silence`,
`gathering_paused`.

**Stop reasons (closed enum):** `loop_disabled`, `invalid_loop_trigger`,
`max_ticks_per_pause`, `cooldown_active`, `elapsed_input_missing`,
`player_cut_in`, `unsafe_candidate`, `no_motivation_threshold_crossed`,
`tick_suppressed`.

**Hard boundaries (Stage H preserves Stage A–G promises and adds):**

- Loop is bounded by content policy: `max_ticks_per_pause` comes from
  `pacing_rhythm.max_ticks_per_pause` (default 1, clamped to `[1, 8]`).
- Cooldown is enforced between iterations using the same
  `min_tick_interval_ms` resolution used by Stage E.
- Per-step elapsed timings are *required* input; a missing entry stops
  the loop with `elapsed_input_missing`.
- A queued or in-flight player cut-in stops the loop at that index
  (`player_cut_in`).
- An unsafe off-stage candidate (Stage F `safety_gate_blocked`) stops
  the loop with `unsafe_candidate`.
- `canonical_path_advanced` / `mandatory_beat_consumed` invariants
  remain false across every loop step, including the loop-level
  outcome.
- Stage H never replaces Stage E — every step of the loop is a real
  Stage-E evaluation and obeys every Stage-E gate.

### Stage I — Mid-Turn Replanning Readiness (complete)

Stage I introduces the *readiness* contract for canceling future, not-yet-
started events after a player cut-in — without rewriting history and
without mutating mid-turn graph state. Stage I is the "future events only"
boundary that mid-turn graph mutation (a future-work item) will need to
respect.

**New entry points:** `ai_stack/phase2_ws_session_loop.py`

- `build_replanning_request(...)` — `replanning_request.v1`. Captures
  the delivery boundary at the cut moment (committed event IDs,
  streamed-but-not-committed event IDs, not-yet-started event IDs,
  canceled tick count). Records `historical_events_mutated=False`,
  `graph_state_mutated_mid_turn=False`,
  `validation_outcome_changed=False`,
  `commit_or_readiness_changed=False`,
  `canonical_path_advanced=False`,
  `mandatory_beat_consumed=False`.
- `build_replanned_event_after_cut_in(...)` — one diagnostic
  `block_stream_event.v1` (`originator="director_replanning"`,
  `event_generation="replanned_after_cut_in"`,
  `next_action_source="player_input_priority"`) replacing the
  not-yet-started event IDs.
- `build_replanning_decision(...)` — `replanning_decision.v1`.
  Decides `prioritize_player_input` and lists the canceled event IDs
  plus the bounded replanned-event set. Replanning scope is fixed at
  `future_events_only`.

**Closed-enum next-action source set:** `player_input_priority`,
`idle`, `npc_response`, `silence`.

**Hard boundaries (Stage I preserves Stage A–H promises and adds):**

- Replanning scope is `future_events_only` — already-emitted or
  committed events are never mutated.
- Replanned diagnostic events carry `diagnostic_only=true` and a
  silence director tick decision with
  `silence_reason="player_input_priority_replan"`.
- No commit-or-readiness mutation. No `validation_outcome` mutation.
- Stage I emits messages *after* the canonical delivery boundary; the
  REST/bundle fallback path remains unchanged.

### Stage J — Controlled Mid-Turn Replanning

Stage J is **deliberately deferred** to a future ADR. Stage I documents
the readiness boundary; Stage J is the "mid-turn graph mutation" decision
that would re-run validation/commit against a delta. Phase 2 does not
ship Stage J. The status doc (`docs/MVPs/phase_2_director_pulse_status.md`)
lists this under explicit Future Work.

### Stage K — Player Cut-In Immediate Director Handoff (complete)

Stage K adds the immediate Director handoff that promotes a queued
player cut-in into the next turn's authoritative trigger, while pausing
any in-progress autonomous-pause loop.

**New entry points:** `ai_stack/phase2_ws_session_loop.py`

- `build_player_cut_in_handoff(...)` — `player_cut_in_handoff.v1`.
  Carries `handoff_id`, the originating `cut_in_id`, the
  `promoted_player_input_id` (or `null` when there is no promotable
  player input), the source replanning-decision ID, the canceled
  event-ID and tick counts inherited from Stage I, and a closed-enum
  `handoff_status` (`promoted` or `not_applicable`) with a closed-enum
  `non_handoff_reason` (`no_promotable_player_input`).
- `next_turn_trigger="player_cut_in_handoff"` on promoted handoffs;
  null on `not_applicable` handoffs.
- `autonomous_loop_paused` boolean — Stage H loops pause while a
  promoted handoff is in flight.

**Hard boundaries (Stage K preserves Stage A–I promises and adds):**

- The handoff carries IDs and invariants only; the player's literal
  text stays in the existing queued cut-in payload.
- Handoff status is a closed enum; missing/empty payloads result in
  `not_applicable`, never an invented handoff.
- `historical_events_mutated=False`,
  `graph_state_mutated_mid_turn=False`,
  `validation_outcome_changed=False`,
  `commit_or_readiness_changed=False`,
  `canonical_path_advanced=False`,
  `mandatory_beat_consumed=False`.

### Stage L — Post-Cut-In Director Replanning (complete)

Stage L runs a fresh Director read after a promoted handoff and decides
which next-action source should drive the upcoming turn (or whether
silence is the right answer). It also constructs the future-only follow-up
event that the WS transport then streams (Stage L+M jointly own the
follow-up event shape).

**New entry points:** `ai_stack/phase2_ws_session_loop.py`

- `build_post_cut_in_replanning_decision(...)` —
  `post_cut_in_replanning_decision.v1`. Carries the source handoff
  ID, the promoted-input ID, the interrupted-block context, the
  canceled prior-plan set, an optional new Director context dict,
  candidate-action / rejected-candidate audit lists, a closed-enum
  `selected_next_action_source`
  (`player_input_priority` / `npc_response` / `silence` / `idle`),
  a `selected_next_actor_id` (nullable), a closed-enum
  `selected_next_action_kind`, and a `silence_reason` (nullable).
- `build_post_cut_in_follow_up_event(...)` —
  `post_cut_in_follow_up_event.v1`. Builds the actual follow-up
  artifact: an executable `block_stream_event.v1` when an NPC
  response is composed, or an explicit silence diagnostic, or a
  "no-follow-up" record with a closed-enum rejection reason.

**Hard boundaries (Stage L preserves Stage A–K promises and adds):**

- The follow-up is appended *after* already-planned promoted-input
  output; it never rewrites the committed turn.
- The audit envelope records `prior_plan_canceled`,
  `canceled_event_ids`, `canceled_ticks`, and the interrupted
  context — full traceability for any operator review.
- The decision and the follow-up artifact each independently record
  `historical_events_mutated=False`,
  `graph_state_mutated_mid_turn=False`,
  `validation_outcome_changed=False`,
  `commit_or_readiness_changed=False`,
  `canonical_path_advanced=False`,
  `mandatory_beat_consumed=False`.

### Stage M — Semantic NPC Follow-Up Composition (complete; provider wiring deferred)

Stage M is the composition layer for the Stage-L follow-up event. It
selects between two paths — a deterministic template render and a
semantic-generation dispatcher — and runs the same closed-enum safety
gate suite on whichever output reaches the rendered-text stage.

**Feature flag:**

| Flag | Default | Purpose |
|---|---|---|
| `PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED` | off | Enable Stage M semantic dispatcher (provider must also be injected) |

**Composition modes (closed enum):**

- `template_render` — deterministic template path rendered from the
  authored voice profile (`follow_up_composition`,
  `speech_patterns`, or a top-level template key). Placeholders are
  restricted to a closed allowlist
  (`actor_id`, `baseline_tone`, `current_phase_voice_hint`,
  `interrupted_block_id`, `interrupted_block_type`,
  `motivation_score`, `player_input`, `promoted_player_input`,
  `promoted_player_input_id`, `voice_hint`).
- `semantic_generation` — the injected `FollowUpSemanticProvider` is
  called with a structured `follow_up_composition_request.v1` and
  must return either `{success: True, text: str}` or
  `{success: False, error_code: str}`. The provider is *advisory*; it
  never bypasses the safety gates.
- `template_fallback_after_semantic_failure` — when semantic
  generation was attempted and either failed at the provider boundary
  or was rejected by the safety gates, the dispatcher renders the
  deterministic template and tags the result with this mode plus a
  `semantic_attempt_metadata` block.
- `not_applicable` — no voice profile available, or no composition
  was attempted.

**Safety gates (closed enum, all run on both template and semantic
output before any block is emitted):**

| Gate | What it checks |
|---|---|
| `length` | non-empty and ≤ `MAX_COMPOSED_FOLLOW_UP_CHARS` (280) |
| `actor_lane` | actor ID is not in the AI-forbidden actor lane (human player or `ai_forbidden_actor_ids`) |
| `voice_forbidden_markers` | text contains no `voice_consistency.forbidden_language_markers` from the voice profile |
| `no_new_people` | text contains no token in `forbidden_new_person_tokens` |
| `no_new_rooms` | text contains no token in `forbidden_new_room_tokens` |
| `no_forbidden_plot_facts` | text contains no token in `forbidden_plot_fact_tokens` |
| `information_disclosure` | text contains no `forbidden_disclosure_tokens` from `information_disclosure_target.withheld_units` |

Each gate returns `pass` / `reject` / `not_applicable`. *Any* `reject`
fails the composition; the dispatcher records the first failing gate's
reason and stays on the template path or, if both paths fail, emits a
no-follow-up event with a closed-enum rejection reason.

**Source-context vocabulary (closed enum, reported per composition):**

`voice_profile`, `promoted_player_input`, `interrupted_block`,
`motivation_score`, `relationship_state`, `scene_energy`,
`social_pressure`, `recent_visible_context`,
`information_disclosure_target`.

**`follow_up_composition_request.v1`** (provider input): voice profile,
promoted player input excerpt + ID, interrupted block ID/type,
motivation score, relationship-state output, scene-energy output,
social-pressure output, recent visible block list, information-
disclosure target, `max_text_chars`, and the voice-profile
`voice_forbidden_markers`. The provider sees a *projection* of the
runtime, never the canonical graph; it has no mutators and no commit
handles.

**Hard boundaries (Stage M preserves Stage A–L promises and adds):**

- The flag *and* an injected provider are both required to take the
  semantic path. Setting the flag alone leaves the dispatcher on the
  deterministic template path.
- Provider exceptions are caught and recorded as
  `semantic_provider_exception`; the dispatcher then falls back to
  the template path.
- The safety gates are run by this module, not the provider — the
  provider's `success` flag is advisory.
- Output is capped at `MAX_COMPOSED_FOLLOW_UP_CHARS`; longer outputs
  are rejected by the `length` gate.
- `provider_metadata` is reported when a provider was invoked, never
  forged when the deterministic template path was taken.
- Composition never advances the canonical path, consumes a
  mandatory beat, or mutates committed events / `validation_outcome`.

**Future work explicitly outside Phase 2 scope:** no production semantic
provider is registered on the WS endpoint in Phase 2; the dispatcher
takes the deterministic template path whenever no provider is injected.
See `docs/MVPs/phase_2_director_pulse_status.md` §5.2.

### Completion Pass — End-to-End Player Experience Chain

The Phase-2 player-experience chain is now proven end-to-end at the
WS-transport + `ai_stack` pure-helper level:

```
Player Turn
  → block_stream_event.v1                 (Stage D — sequenced over WS)
  → autonomous_tick_evaluated             (Stage E/H — after a clean delivery)
  → block_stream_event.v1                 (autonomous NPC block,
                                           originator=autonomous_tick)
  → block_cut + player_cut_in_event.v1    (Stage D — cut-in semantics)
  → replanning_decision.v1                (Stage I — cancel future events only)
  → player_cut_in_handoff.v1              (Stage K — promote queued input)
  → post_cut_in_replanning_decision.v1    (Stage L — next-action source)
  → post_cut_in_follow_up_event.v1        (Stage L+M — composition_result
                                           with closed-enum composition_mode
                                           and safety_gate_decisions)
  → silence path: stream_idle + post_cut_in_follow_up_event.silence_reason
```

The Completion Pass clarifies that:

- The **event-stream channel is primary behind flags**. Bundle delivery
  remains the canonical fallback path and is never removed in Phase 2.
- The **REST/bundle path is preserved** as a first-class fallback for
  any session that does not opt into the WS session loop or for which
  the Stage-C primary selection records a `fallback_reason`.
- **WebSocket is not mandatory.** Stage D is an opt-in transport; a
  session that never opens a socket continues to receive the canonical
  bundle exactly as before.
- **Commit and Readiness semantics are unchanged.** Every Phase-2
  artifact records the same six invariants
  (`historical_events_mutated`, `graph_state_mutated_mid_turn`,
  `validation_outcome_changed`, `commit_or_readiness_changed`,
  `canonical_path_advanced`, `mandatory_beat_consumed`), all `False`.
- **`validation_outcome` is never mutated by Phase 2.** Stage I/K/L/M
  artifacts each carry `validation_outcome_changed=False`; the Table-B
  anti-hardcoding gate enforces that no Phase-2 module reads or writes
  a Pi/Π-named runtime key.
- **Full mid-turn graph mutation is Future Work (Stage J).** Stage I
  is `future_events_only` by construction; it does not advance into
  Stage J in Phase 2.
- **Production semantic provider wiring is Future Work** (see Stage M
  paragraph above and the status doc §5.2). The current follow-up
  composition shipping in Phase 2 is the deterministic template path
  plus the gated semantic dispatcher; no semantic provider is wired
  into the WS endpoint by default.

Local/live-smoke evidence is documented in
`docs/MVPs/phase_2_director_pulse_status.md` §4. Phase 2 makes no
staging or production-live claim that is not backed by environment
metadata on the recorded turn.
