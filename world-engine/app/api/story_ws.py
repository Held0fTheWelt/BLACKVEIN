"""Phase 2 — Story-session WebSocket endpoint.

Streams ``block_stream_event.v1`` one-at-a-time to a connected client and
accepts ``cut_in`` messages mid-stream. The transport is feature-gated by
``PHASE2_WS_SESSION_LOOP_ENABLED``; bundle / event-stream / SSE fallbacks
remain on the REST router and are untouched by this module.

Hard boundaries (ADR-0058):
* REST turn path is unchanged.
* Bundle fallback is unchanged.
* Commit/Readiness semantics are unchanged.
* ``validation_outcome`` is unchanged.
* No Pi/Π keys, no hardcoded actor/room IDs.
* ``live_interruption_supported`` is only reported True when this endpoint
  is enabled and a connection has reached an active streaming block.

Protocol:

Client → server (JSON):
    {"kind": "start_turn", "player_input": "..."}
    {"kind": "cut_in",     "player_input": "..."}
    {"kind": "ping"}

Server → client (JSON):
    {"kind": "stream_started", ...}
    {"kind": "block_started", "block_stream_event": {...}}
    {"kind": "block_completed", "event_id": ...}
    {"kind": "block_cut", "cut_kind": ..., "player_cut_in_event": {...}}
    {"kind": "stream_idle", "reason": ...}
    {"kind": "stream_error", "reason": ..., "detail": ...}
"""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, status
from starlette.concurrency import run_in_threadpool

from ai_stack.phase2_autonomous_tick import (
    AutonomousTickInputs,
    AutonomousTickOutcome,
    evaluate_autonomous_tick,
    is_autonomous_tick_enabled,
)
from ai_stack.phase2_ws_session_loop import (
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
    CLIENT_MSG_START_TURN,
    WSSessionLoopState,
    apply_cut_in,
    is_ws_session_loop_enabled,
    msg_autonomous_tick_evaluated,
    msg_block_completed,
    msg_block_cut,
    msg_block_started,
    msg_stream_error,
    msg_stream_idle,
    msg_stream_started,
)
from app.story_runtime import StoryRuntimeManager
from app.story_runtime.live_governance import LiveStoryGovernanceError

logger = logging.getLogger(__name__)


story_ws_router = APIRouter(tags=["story-ws"])


# ── Auth helpers ──────────────────────────────────────────────────────────────


def _ws_test_mode() -> bool:
    return (
        os.getenv("FLASK_ENV") in {"test", "testing"}
        or os.getenv("ENV") in {"test", "testing"}
    )


def _resolve_internal_api_key() -> str:
    """Re-read the internal API key at call time so tests can clear it."""
    return (os.getenv("PLAY_SERVICE_INTERNAL_API_KEY") or "").strip()


def _verify_internal_key(provided: str | None) -> bool:
    expected = _resolve_internal_api_key()
    if expected:
        return bool(provided) and provided.strip() == expected
    # No key configured — only allowed in explicit test mode (matches HTTP rule).
    return _ws_test_mode()


# ── Pacing (configurable) ─────────────────────────────────────────────────────


def _block_pacing_seconds() -> float:
    """Seconds to wait between emitting block events.

    Defaults to 0 in tests / fail-closed. Operators can set
    ``PHASE2_WS_BLOCK_PACING_SECONDS`` to introduce a deliberate gap so
    cut-in mid-stream becomes physically possible against a real client.
    """
    raw = os.getenv("PHASE2_WS_BLOCK_PACING_SECONDS", "0").strip()
    try:
        value = float(raw)
    except (TypeError, ValueError):
        value = 0.0
    return max(0.0, value)


# ── Stream-event extraction ──────────────────────────────────────────────────


def _extract_block_stream_events(turn: dict[str, Any] | None) -> list[dict[str, Any]]:
    """Return the ``block_stream_events`` from a turn payload, or [].

    The list ordering is whatever the bundle produced — one event per block,
    in delivery order. We never re-sort.
    """
    if not isinstance(turn, dict):
        return []
    envelope = turn.get("envelope") if isinstance(turn.get("envelope"), dict) else turn
    vso = envelope.get("visible_scene_output") if isinstance(envelope, dict) else None
    if not isinstance(vso, dict):
        return []
    events = vso.get("block_stream_events")
    if not isinstance(events, list):
        return []
    return [e for e in events if isinstance(e, dict) and isinstance(e.get("block_payload"), dict)]


def _extract_turn_id(turn: dict[str, Any] | None) -> str | None:
    if not isinstance(turn, dict):
        return None
    for key in ("canonical_turn_id", "turn_id", "turn_number"):
        val = turn.get(key)
        if val is not None:
            return str(val)
    return None


def _extract_envelope(turn: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(turn, dict):
        return None
    envelope = turn.get("envelope")
    if isinstance(envelope, dict):
        return envelope
    # Some manager stubs / older paths return the envelope at the top level.
    if isinstance(turn.get("visible_scene_output"), dict):
        return turn
    return None


def _extract_autonomous_tick_inputs(
    turn: dict[str, Any] | None,
    *,
    trigger_kind: str,
) -> AutonomousTickInputs | None:
    """Build ``AutonomousTickInputs`` from a freshly committed turn envelope.

    Returns None if the envelope does not expose the required Phase-2
    diagnostics. The function is best-effort and never raises; missing
    keys collapse into None values that the coordinator handles natively.
    """
    envelope = _extract_envelope(turn)
    if envelope is None:
        return None
    npc_ids_raw = envelope.get("npc_actor_ids")
    npc_ids: list[str] = (
        [str(x) for x in npc_ids_raw if isinstance(x, str) and x]
        if isinstance(npc_ids_raw, list)
        else []
    )
    diagnostics = envelope.get("diagnostics") if isinstance(envelope.get("diagnostics"), dict) else {}
    director_pulse = diagnostics.get("director_pulse") if isinstance(diagnostics.get("director_pulse"), dict) else {}
    cap_outputs = (
        director_pulse.get("capability_outputs")
        if isinstance(director_pulse.get("capability_outputs"), dict)
        else {}
    )
    gathering_state = (
        diagnostics.get("director_gathering_state")
        if isinstance(diagnostics.get("director_gathering_state"), dict)
        else {}
    )
    # Stage F — surface the visible-NPC / known-actor / known-room sets so
    # the autonomous tick coordinator's off-stage safety gate can run.
    # Important: a *present but empty* list means "no NPCs visible" and must
    # not fall through to the npc_ids default — that distinction is what
    # lets the off-stage gate pass.
    def _list_or_default(raw_a: Any, raw_b: Any, default: list[str]) -> list[str]:
        for raw in (raw_a, raw_b):
            if isinstance(raw, list):
                return [str(x) for x in raw if isinstance(x, str) and x]
        return list(default)

    visible_npc_ids = _list_or_default(
        envelope.get("visible_npc_actor_ids"),
        envelope.get("visible_npc_ids"),
        npc_ids,
    )
    known_actor_ids = _list_or_default(
        envelope.get("known_actor_ids"),
        envelope.get("module_actor_ids"),
        npc_ids,
    )
    known_room_ids = _list_or_default(
        envelope.get("known_room_ids"),
        envelope.get("module_room_ids"),
        [],
    )

    return AutonomousTickInputs(
        trigger_kind=trigger_kind,
        npc_ids=npc_ids,
        scene_energy_output=cap_outputs.get("scene_energy_output")
        if isinstance(cap_outputs.get("scene_energy_output"), dict)
        else None,
        social_pressure_output=cap_outputs.get("social_pressure_output")
        if isinstance(cap_outputs.get("social_pressure_output"), dict)
        else None,
        relationship_state_output=cap_outputs.get("relationship_state_output")
        if isinstance(cap_outputs.get("relationship_state_output"), dict)
        else None,
        narrative_momentum_output=cap_outputs.get("narrative_momentum_output")
        if isinstance(cap_outputs.get("narrative_momentum_output"), dict)
        else None,
        actor_pressure_profiles=director_pulse.get("actor_pressure_profiles")
        if isinstance(director_pulse.get("actor_pressure_profiles"), dict)
        else None,
        npc_motivation_score_policy=director_pulse.get("npc_motivation_score_policy")
        if isinstance(director_pulse.get("npc_motivation_score_policy"), dict)
        else None,
        pacing_rhythm_policy=director_pulse.get("pacing_rhythm_policy")
        if isinstance(director_pulse.get("pacing_rhythm_policy"), dict)
        else None,
        gathering_paused=bool(gathering_state.get("paused")) if isinstance(gathering_state, dict) else False,
        visible_npc_ids=visible_npc_ids,
        known_actor_ids=known_actor_ids,
        known_room_ids=known_room_ids,
    )


def _autonomous_tick_summary(outcome: AutonomousTickOutcome) -> dict[str, Any]:
    """Compact summary of one autonomous-tick outcome for diagnostics.

    Stage F additions: ``capability_outputs_used``,
    ``capability_outputs_missing``, ``motivation_score_component_sources``,
    ``off_stage_update_candidate`` (full Stage F scaffold dict).
    """
    return {
        "tick_id": outcome.tick_id,
        "tick_trigger_kind": outcome.tick_trigger_kind,
        "chosen_actor_id": outcome.chosen_actor_id,
        "chosen_action_kind": outcome.chosen_action_kind,
        "silence_reason": outcome.silence_reason,
        "autonomous_tick_suppressed_reason": outcome.autonomous_tick_suppressed_reason,
        "cooldown_state": dict(outcome.cooldown_state),
        "motivation_scores": dict(outcome.motivation_scores),
        "gathering_paused": outcome.gathering_paused,
        "canonical_path_advanced": outcome.canonical_path_advanced,
        "mandatory_beat_consumed": outcome.mandatory_beat_consumed,
        "block_emitted": outcome.block_stream_event is not None,
        "capability_outputs_used": list(outcome.capability_outputs_used),
        "capability_outputs_missing": list(outcome.capability_outputs_missing),
        "motivation_score_component_sources": dict(outcome.motivation_score_component_sources),
        "off_stage_update_candidate": dict(outcome.off_stage_update_candidate),
    }


# ── Streaming loop ────────────────────────────────────────────────────────────


async def _stream_events_to_client(
    websocket: WebSocket,
    state: WSSessionLoopState,
    events: list[dict[str, Any]],
    *,
    cut_in_queue: asyncio.Queue,
    pacing_seconds: float,
    autonomous_originator: bool = False,
) -> None:
    """Emit each block as block_started → (pacing) → block_completed.

    Between events, drain the cut_in_queue. If a cut-in arrives, apply it
    via apply_cut_in() and emit block_cut, then stop the stream.

    ``autonomous_originator`` only affects bookkeeping (the WSSessionLoopState
    is augmented by the caller for the autonomous-tick branch); the transport
    semantics are identical between user-driven and autonomous block events.
    """
    for event in events:
        if state.stream_finished:
            return
        state.mark_block_started(event)
        await websocket.send_json(msg_block_started(event=event))

        # Pacing window — during this gap cut-in can fire.
        if pacing_seconds > 0:
            try:
                cut_msg = await asyncio.wait_for(cut_in_queue.get(), timeout=pacing_seconds)
            except asyncio.TimeoutError:
                cut_msg = None
        else:
            try:
                cut_msg = cut_in_queue.get_nowait()
            except asyncio.QueueEmpty:
                cut_msg = None

        if cut_msg is not None:
            outcome = apply_cut_in(
                state,
                tick_id=str(event.get("tick_id") or uuid.uuid4()),
                player_input_payload=cut_msg,
            )
            await websocket.send_json(msg_block_cut(cut_outcome=outcome))
            state.mark_stream_idle()
            return

        await websocket.send_json(msg_block_completed(event_id=state.active_block_id))
        state.mark_block_completed()

    state.mark_stream_idle()


async def _drain_cut_in_messages(
    websocket: WebSocket,
    cut_in_queue: asyncio.Queue,
    state: WSSessionLoopState,
) -> None:
    """Background reader: route cut_in messages into the queue."""
    while not state.stream_finished:
        try:
            message = await websocket.receive_json()
        except WebSocketDisconnect:
            state.stream_finished = True
            return
        except Exception:
            state.stream_finished = True
            return
        if not isinstance(message, dict):
            continue
        kind = str(message.get("kind") or "")
        if kind == CLIENT_MSG_CUT_IN:
            await cut_in_queue.put(message)
            # Cut-in is a one-shot stream event; subsequent inputs flow on next turn.
            return
        if kind == CLIENT_MSG_PING:
            try:
                await websocket.send_json({"kind": "pong"})
            except Exception:
                state.stream_finished = True
                return


# ── Endpoint ──────────────────────────────────────────────────────────────────


@story_ws_router.websocket("/api/story/sessions/{session_id}/stream")
async def story_session_stream(websocket: WebSocket, session_id: str) -> None:  # noqa: C901
    """Live block-stream WebSocket for a story session.

    Connection lifecycle:
        1. Client connects with ``?key=<internal_api_key>``
        2. Server accepts and sends nothing until ``start_turn`` arrives
        3. On ``start_turn``: server runs the turn (REST path identical
           code) then streams events one-at-a-time. Bundle is still
           available on the REST channel.
        4. On ``cut_in`` mid-stream: server applies cut semantics, emits
           ``block_cut``, ends the stream. Player input is queued and
           replayed on the next ``start_turn``.
    """
    if not is_ws_session_loop_enabled():
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="ws_session_loop_disabled")
        return

    provided_key = websocket.query_params.get("key") or websocket.headers.get("x-play-service-key")
    if not _verify_internal_key(provided_key):
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="auth_required")
        return

    manager: StoryRuntimeManager | None = getattr(websocket.app.state, "story_manager", None)
    if manager is None:
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="story_manager_unavailable")
        return

    await websocket.accept()
    state = WSSessionLoopState(session_id=session_id)
    pacing_seconds = _block_pacing_seconds()
    queued_carryover: list[dict[str, Any]] = []
    # Stage E — autonomous tick bookkeeping (per-connection).
    autonomous_last_tick_ms: float | None = None
    autonomous_summaries: list[dict[str, Any]] = []
    autonomous_cut_in_interrupted: bool = False

    try:
        await websocket.send_json(msg_stream_started(session_id=session_id, turn_id=None))

        while True:
            try:
                message = await websocket.receive_json()
            except WebSocketDisconnect:
                return
            if not isinstance(message, dict):
                await websocket.send_json(msg_stream_error(reason="malformed_message"))
                continue

            kind = str(message.get("kind") or "")

            if kind == CLIENT_MSG_PING:
                await websocket.send_json({"kind": "pong"})
                continue

            if kind == CLIENT_MSG_CUT_IN:
                # No active stream — surface as no_active_block cut.
                outcome = apply_cut_in(
                    state,
                    tick_id=str(uuid.uuid4()),
                    player_input_payload=message,
                )
                await websocket.send_json(msg_block_cut(cut_outcome=outcome))
                # Player input is preserved — carry forward to the next start_turn.
                queued_carryover.append(message)
                continue

            if kind != CLIENT_MSG_START_TURN:
                await websocket.send_json(msg_stream_error(reason="unknown_kind", detail=kind))
                continue

            player_input = str(message.get("player_input") or "").strip()
            if not player_input and queued_carryover:
                # Replay carryover from a prior cut-in.
                player_input = str(queued_carryover[-1].get("player_input") or "").strip()

            if not player_input:
                await websocket.send_json(msg_stream_error(reason="missing_player_input"))
                continue

            try:
                turn = await run_in_threadpool(
                    manager.execute_turn,
                    session_id=session_id,
                    player_input=player_input,
                    trace_id=None,
                )
            except KeyError:
                await websocket.send_json(msg_stream_error(reason="session_not_found"))
                await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="session_not_found")
                return
            except LiveStoryGovernanceError as exc:
                await websocket.send_json(msg_stream_error(reason="governance_error", detail=str(exc)))
                continue
            except Exception as exc:  # noqa: BLE001
                logger.exception("WS turn execution failed: %s", exc)
                await websocket.send_json(msg_stream_error(reason="turn_execution_failed", detail=str(exc)))
                continue

            queued_carryover.clear()
            turn_id = _extract_turn_id(turn)
            await websocket.send_json(msg_stream_started(session_id=session_id, turn_id=turn_id))

            events = _extract_block_stream_events(turn)
            state = WSSessionLoopState(session_id=session_id)

            if not events:
                await websocket.send_json(msg_stream_idle(reason="no_events"))
                continue

            cut_in_queue: asyncio.Queue = asyncio.Queue(maxsize=1)
            reader_task = asyncio.create_task(_drain_cut_in_messages(websocket, cut_in_queue, state))
            try:
                await _stream_events_to_client(
                    websocket,
                    state,
                    events,
                    cut_in_queue=cut_in_queue,
                    pacing_seconds=pacing_seconds,
                )
            finally:
                state.stream_finished = True
                if not reader_task.done():
                    reader_task.cancel()
                    try:
                        await reader_task
                    except (asyncio.CancelledError, Exception):
                        pass

            user_turn_cut = state.last_cut_kind is not None

            if user_turn_cut:
                # Player interrupted the user-input turn — do not start an
                # autonomous tick on top of a cut. The cut already queued
                # the input for the next user turn.
                continue

            # ── Stage E: Autonomous Director Tick ─────────────────────────
            # After a clean user-turn delivery, the Director MAY emit one
            # autonomous NPC block when motivation crosses threshold. The
            # coordinator decides; the transport just delivers.
            autonomous_outcome: AutonomousTickOutcome | None = None
            if is_autonomous_tick_enabled():
                tick_inputs = _extract_autonomous_tick_inputs(
                    turn, trigger_kind="motivation_threshold_crossed",
                )
                if tick_inputs is not None:
                    tick_inputs.since_last_tick_ms = autonomous_last_tick_ms
                    tick_inputs.pending_player_input = bool(queued_carryover)
                    tick_inputs.already_streaming_block = False
                    autonomous_outcome = evaluate_autonomous_tick(tick_inputs)
                    summary = _autonomous_tick_summary(autonomous_outcome)
                    autonomous_summaries.append(summary)
                    autonomous_last_tick_ms = 0.0  # reset clock — next tick is "now"
                    await websocket.send_json(
                        msg_autonomous_tick_evaluated(summary=summary)
                    )

            if autonomous_outcome is None or autonomous_outcome.block_stream_event is None:
                # No autonomous emission (flag off, no NPCs above threshold,
                # cooldown, etc.). The user-turn stream already idled cleanly;
                # one stream_idle marks the conversation as quiescent.
                await websocket.send_json(msg_stream_idle(reason="completed"))
                continue

            # Emit the autonomous block (with cut-in support identical to the
            # user-turn stream).
            autonomous_state = WSSessionLoopState(session_id=session_id)
            cut_in_queue = asyncio.Queue(maxsize=1)
            reader_task = asyncio.create_task(
                _drain_cut_in_messages(websocket, cut_in_queue, autonomous_state)
            )
            try:
                await _stream_events_to_client(
                    websocket,
                    autonomous_state,
                    [autonomous_outcome.block_stream_event],
                    cut_in_queue=cut_in_queue,
                    pacing_seconds=pacing_seconds,
                    autonomous_originator=True,
                )
            finally:
                autonomous_state.stream_finished = True
                if not reader_task.done():
                    reader_task.cancel()
                    try:
                        await reader_task
                    except (asyncio.CancelledError, Exception):
                        pass

            if autonomous_state.last_cut_kind is not None:
                # Player interrupted the autonomous block. Carry input to
                # the next start_turn — identical semantics to the user-turn cut.
                autonomous_cut_in_interrupted = True
                if autonomous_state.queued_player_inputs:
                    queued_carryover.extend(autonomous_state.queued_player_inputs)
                # Mark interruption in the most recent summary so audit + tests
                # can correlate the cut with its originating tick.
                if autonomous_summaries:
                    autonomous_summaries[-1] = {
                        **autonomous_summaries[-1],
                        "cut_in_interrupted_autonomous_tick": True,
                    }
            else:
                await websocket.send_json(msg_stream_idle(reason="autonomous_tick_completed"))

    except WebSocketDisconnect:
        return
    except Exception as exc:  # noqa: BLE001
        logger.exception("Story WS loop fatal error: %s", exc)
        try:
            await websocket.send_json(msg_stream_error(reason="fatal", detail=str(exc)))
        except Exception:
            pass
        try:
            await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="fatal")
        except Exception:
            pass


# ── Support-flag endpoint (HTTP-side companion to the WS) ────────────────────


from fastapi import APIRouter as _APIRouter  # noqa: E402  re-import to keep namespace tidy

story_ws_support_router = _APIRouter(prefix="/api/story", tags=["story-ws"])


@story_ws_support_router.get("/runtime/ws-session-loop-support")
def ws_session_loop_support() -> dict[str, Any]:
    """Operator-readable support flag for the Phase 2 WS session loop.

    Returns whether the endpoint is enabled and what cut-in semantics are
    supported (always block-type-driven). Diagnostic-only — does not change
    any runtime state.
    """
    enabled = is_ws_session_loop_enabled()
    autonomous_enabled = is_autonomous_tick_enabled()
    return {
        "ws_session_loop_supported": enabled,
        "live_interruption_supported": enabled,
        "autonomous_tick_enabled": autonomous_enabled,
        "autonomous_tick_trigger_kinds": [
            "player_input",
            "motivation_threshold_crossed",
            "state_change",
            "cooldown_check",
        ],
        "endpoint": "/api/story/sessions/{session_id}/stream",
        "cut_kind_semantics": {
            "actor_line": "em_dash",
            "narrator": "skip_to_end",
            "actor_action": "skip_to_end",
            "souffleuse": "skip_to_end",
            "environment_interaction": "skip_to_end",
            "no_active_block": "no_active_block",
        },
        "fallback_path": "rest_or_event_stream",
    }
