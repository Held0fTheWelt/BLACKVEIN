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

from ai_stack.contracts.director_pulse_contracts import ACTION_SILENCE, ACTION_SPEAK
from ai_stack.story_runtime.autonomous_tick import (
    AutonomousTickInputs,
    AutonomousTickOutcome,
    LOOP_STOP_COOLDOWN_ACTIVE,
    LOOP_STOP_MAX_TICKS,
    LOOP_STOP_NO_MOTIVATION_THRESHOLD,
    LOOP_STOP_PLAYER_CUT_IN,
    LOOP_STOP_TICK_SUPPRESSED,
    LOOP_STOP_UNSAFE_CANDIDATE,
    LOOP_TRIGGER_GATHERING_PAUSED,
    LOOP_TRIGGER_SILENCE,
    LOOP_TRIGGER_USER_PAUSE,
    evaluate_autonomous_tick,
    is_autonomous_pause_loop_enabled,
    is_autonomous_tick_enabled,
    resolve_max_ticks_per_pause,
    resolve_min_tick_interval_ms,
)
from ai_stack.story_runtime.ws_session_loop import (
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
    CLIENT_MSG_START_TURN,
    HANDOFF_STATUS_PROMOTED,
    NEXT_ACTION_SOURCE_NPC_RESPONSE,
    NEXT_ACTION_SOURCE_SILENCE,
    NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF,
    WSSessionLoopState,
    apply_cut_in,
    build_post_cut_in_follow_up_event,
    build_post_cut_in_replanning_decision,
    is_ws_session_loop_enabled,
    msg_autonomous_tick_evaluated,
    msg_block_completed,
    msg_block_cut,
    msg_block_started,
    msg_post_cut_in_follow_up_event,
    msg_post_cut_in_replanning_decision,
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
        off_stage_updates_policy=director_pulse.get("off_stage_updates_policy")
        if isinstance(director_pulse.get("off_stage_updates_policy"), dict)
        else None,
        relationship_state_record=cap_outputs.get("relationship_state_output")
        if isinstance(cap_outputs.get("relationship_state_output"), dict)
        else None,
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
        "off_stage_commit_result": dict(outcome.off_stage_commit_result),
    }


def _summary_with_loop_metadata(
    outcome: AutonomousTickOutcome,
    *,
    tick_index: int,
    max_ticks_per_pause: int,
    loop_enabled: bool,
    loop_trigger_kind: str,
) -> dict[str, Any]:
    summary = _autonomous_tick_summary(outcome)
    summary["autonomous_pause_loop"] = {
        "enabled": bool(loop_enabled),
        "tick_index": tick_index,
        "tick_number": tick_index + 1,
        "max_ticks_per_pause": max_ticks_per_pause,
        "loop_trigger_kind": loop_trigger_kind,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": "local_only",
    }
    return summary


def _autonomous_candidate_blocked(outcome: AutonomousTickOutcome) -> bool:
    candidate = (
        outcome.off_stage_update_candidate
        if isinstance(outcome.off_stage_update_candidate, dict)
        else {}
    )
    return candidate.get("off_stage_safety_gate_result") == "blocked"


async def _wait_for_pause_interval_or_input(
    websocket: WebSocket,
    *,
    seconds: float,
) -> dict[str, Any] | None:
    """Wait during an explicit pause interval; return player input if one arrives."""
    if seconds <= 0:
        return None
    while True:
        try:
            message = await asyncio.wait_for(websocket.receive_json(), timeout=seconds)
        except asyncio.TimeoutError:
            return None
        except WebSocketDisconnect:
            raise
        except Exception:
            return None
        if not isinstance(message, dict):
            return None
        kind = str(message.get("kind") or "")
        if kind == CLIENT_MSG_PING:
            await websocket.send_json({"kind": "pong"})
            continue
        if kind == CLIENT_MSG_CUT_IN:
            return message
        if kind == CLIENT_MSG_START_TURN and str(message.get("player_input") or "").strip():
            return {
                "kind": CLIENT_MSG_CUT_IN,
                "player_input": str(message.get("player_input") or "").strip(),
                "source_kind": CLIENT_MSG_START_TURN,
            }
        return None


async def _emit_replanned_events(
    websocket: WebSocket,
    replanning_decision: dict[str, Any] | None,
) -> None:
    """Deliver controlled future-only replanned events, if the decision made any."""
    if not isinstance(replanning_decision, dict):
        return
    replanned_events = replanning_decision.get("replanned_block_stream_events")
    if not isinstance(replanned_events, list):
        return
    for event in replanned_events:
        if not isinstance(event, dict):
            continue
        await websocket.send_json(msg_block_started(event=event))
        await websocket.send_json(msg_block_completed(event_id=event.get("event_id")))


def _player_input_text(payload: dict[str, Any] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in ("player_input", "text", "utterance"):
        text = str(payload.get(key) or "").strip()
        if text:
            return text
    return ""


def _priority_start_from_cut_outcome(cut_outcome: dict[str, Any] | None) -> dict[str, Any] | None:
    """Promote a Stage-K handoff into an internal next-turn trigger."""
    if not isinstance(cut_outcome, dict):
        return None
    handoff = cut_outcome.get("player_cut_in_handoff")
    cut_event = cut_outcome.get("player_cut_in_event")
    if not isinstance(handoff, dict) or not isinstance(cut_event, dict):
        return None
    if handoff.get("handoff_status") != HANDOFF_STATUS_PROMOTED:
        return None
    payload = (
        cut_event.get("player_input_payload")
        if isinstance(cut_event.get("player_input_payload"), dict)
        else {}
    )
    player_input = _player_input_text(payload)
    if not player_input:
        return None
    promoted_input_id = str(handoff.get("promoted_player_input_id") or "").strip()
    if not promoted_input_id:
        return None
    return {
        "kind": CLIENT_MSG_START_TURN,
        "player_input": player_input,
        "player_input_id": promoted_input_id,
        "source_kind": NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF,
        "handoff_id": handoff.get("handoff_id"),
        "_cut_outcome": cut_outcome,
    }


def _queue_handoff_for_next_turn(
    cut_outcome: dict[str, Any] | None,
    queued_carryover: list[dict[str, Any]],
    processed_handoff_input_ids: set[str],
) -> dict[str, Any] | None:
    handoff_start = _priority_start_from_cut_outcome(cut_outcome)
    if handoff_start is None:
        return None
    input_id = str(handoff_start.get("player_input_id") or "").strip()
    if not input_id or input_id in processed_handoff_input_ids:
        return None
    already_queued = any(
        str(item.get("player_input_id") or "").strip() == input_id
        for item in queued_carryover
        if isinstance(item, dict)
    )
    if not already_queued:
        queued_carryover.append(dict(handoff_start))
    return handoff_start


def _candidate_actions_from_outcome(
    outcome: AutonomousTickOutcome | None,
) -> list[dict[str, Any]]:
    if outcome is None:
        return [{
            "candidate_id": "silence",
            "actor_id": None,
            "action_kind": ACTION_SILENCE,
            "score": 0.0,
            "source": "fallback_no_director_context",
        }]
    candidates: list[dict[str, Any]] = []
    for row in outcome.npc_motivation_scores:
        if not isinstance(row, dict):
            continue
        actor_id = str(row.get("npc_id") or row.get("actor_id") or "").strip()
        if not actor_id:
            continue
        try:
            score = float(row.get("score") or outcome.motivation_scores.get(actor_id) or 0.0)
        except (TypeError, ValueError):
            score = 0.0
        candidates.append({
            "candidate_id": f"npc_response:{actor_id}",
            "actor_id": actor_id,
            "action_kind": ACTION_SPEAK,
            "score": score,
            "source": "motivation_score",
        })
    candidates.append({
        "candidate_id": "silence",
        "actor_id": None,
        "action_kind": ACTION_SILENCE,
        "score": 0.0,
        "source": "director_silence",
    })
    return candidates


def _rejected_post_cut_in_candidates(
    candidate_actions: list[dict[str, Any]],
    *,
    selected_actor_id: str | None,
    selected_action_kind: str,
) -> list[dict[str, Any]]:
    rejected: list[dict[str, Any]] = []
    for candidate in candidate_actions:
        actor_id = candidate.get("actor_id")
        action_kind = str(candidate.get("action_kind") or "")
        selected = (
            (selected_action_kind == ACTION_SILENCE and action_kind == ACTION_SILENCE)
            or (
                selected_actor_id is not None
                and str(actor_id or "") == selected_actor_id
                and action_kind == selected_action_kind
            )
        )
        if selected:
            continue
        rejected.append({
            **candidate,
            "rejection_reason": "lower_priority_after_cut_in",
        })
    return rejected


def _extract_actor_voice_profiles_from_envelope(
    envelope: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    """Surface authored voice profiles for the post-cut-in composition layer.

    The profiles are diagnostic — they ride along the turn envelope so the
    follow-up composition can reference baseline_tone / current_phase_voice_hint
    / speech_patterns from authored content. We never synthesize a profile here.
    """
    if not isinstance(envelope, dict):
        return []
    diagnostics = (
        envelope.get("diagnostics")
        if isinstance(envelope.get("diagnostics"), dict)
        else {}
    )
    for source in (
        envelope.get("character_voice_profiles"),
        envelope.get("actor_voice_profiles"),
        diagnostics.get("character_voice_profiles"),
        diagnostics.get("actor_voice_profiles"),
    ):
        if isinstance(source, list) and source:
            return [row for row in source if isinstance(row, dict)]
        if isinstance(source, dict) and source:
            return [
                {**row, "runtime_actor_id": row.get("runtime_actor_id") or actor_id}
                for actor_id, row in source.items()
                if isinstance(row, dict)
            ]
    return []


def _post_cut_in_director_context(
    turn: dict[str, Any] | None,
    *,
    events: list[dict[str, Any]],
    tick_inputs: AutonomousTickInputs | None,
    outcome: AutonomousTickOutcome | None,
) -> dict[str, Any]:
    envelope = _extract_envelope(turn) or {}
    diagnostics = envelope.get("diagnostics") if isinstance(envelope.get("diagnostics"), dict) else {}
    director_pulse = (
        diagnostics.get("director_pulse")
        if isinstance(diagnostics.get("director_pulse"), dict)
        else {}
    )
    validator_plan = (
        diagnostics.get("validator_plan")
        if isinstance(diagnostics.get("validator_plan"), dict)
        else {}
    )
    actor_voice_profiles = _extract_actor_voice_profiles_from_envelope(envelope)
    capability_outputs = (
        director_pulse.get("capability_outputs")
        if isinstance(director_pulse.get("capability_outputs"), dict)
        else {}
    )
    context = {
        "turn_id": _extract_turn_id(turn),
        "block_event_count": len(events),
        "block_types": [
            str(event.get("block_type") or "")
            for event in events
            if isinstance(event, dict)
        ],
        "capability_selection_present": bool(director_pulse.get("capability_outputs")),
        "validator_plan_present": bool(validator_plan),
        "gathering_paused": bool(tick_inputs.gathering_paused) if tick_inputs else False,
        "npc_actor_ids": list(tick_inputs.npc_ids) if tick_inputs else [],
        "visible_npc_actor_ids": list(tick_inputs.visible_npc_ids) if tick_inputs else [],
        "known_actor_ids": list(tick_inputs.known_actor_ids) if tick_inputs else [],
        "known_room_ids": list(tick_inputs.known_room_ids) if tick_inputs else [],
        "actor_voice_profiles": actor_voice_profiles,
        "scene_energy_output": (
            capability_outputs.get("scene_energy_output")
            if isinstance(capability_outputs.get("scene_energy_output"), dict)
            else None
        ),
        "social_pressure_output": (
            capability_outputs.get("social_pressure_output")
            if isinstance(capability_outputs.get("social_pressure_output"), dict)
            else None
        ),
        "relationship_state_output": (
            capability_outputs.get("relationship_state_output")
            if isinstance(capability_outputs.get("relationship_state_output"), dict)
            else None
        ),
        "narrative_momentum_output": (
            capability_outputs.get("narrative_momentum_output")
            if isinstance(capability_outputs.get("narrative_momentum_output"), dict)
            else None
        ),
    }
    if outcome is not None:
        context.update({
            "director_tick_context": dict(outcome.director_tick_decision),
            "capability_outputs_used": list(outcome.capability_outputs_used),
            "capability_outputs_missing": list(outcome.capability_outputs_missing),
            "motivation_scores": dict(outcome.motivation_scores),
            "motivation_score_component_sources": dict(
                outcome.motivation_score_component_sources
            ),
            "autonomous_tick_suppressed_reason": outcome.autonomous_tick_suppressed_reason,
        })
    else:
        context.update({
            "director_tick_context": {},
            "capability_outputs_used": [],
            "capability_outputs_missing": ["director_context_unavailable"],
            "motivation_scores": {},
            "motivation_score_component_sources": {},
            "autonomous_tick_suppressed_reason": "director_context_unavailable",
        })
    return context


def _build_post_cut_in_decision_for_turn(
    *,
    turn: dict[str, Any] | None,
    events: list[dict[str, Any]],
    cut_outcome: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not isinstance(cut_outcome, dict):
        return None
    handoff = cut_outcome.get("player_cut_in_handoff")
    if not isinstance(handoff, dict) or handoff.get("handoff_status") != HANDOFF_STATUS_PROMOTED:
        return None

    tick_inputs = _extract_autonomous_tick_inputs(turn, trigger_kind="player_input")
    autonomous_outcome: AutonomousTickOutcome | None = None
    if tick_inputs is not None:
        tick_inputs.since_last_tick_ms = None
        tick_inputs.pending_player_input = False
        tick_inputs.already_streaming_block = False
        tick_inputs.off_stage_updates_policy = None
        tick_inputs.tick_id = str(uuid.uuid4())
        autonomous_outcome = evaluate_autonomous_tick(tick_inputs, enabled=True)

    candidate_actions = _candidate_actions_from_outcome(autonomous_outcome)
    if autonomous_outcome is not None and autonomous_outcome.chosen_actor_id:
        selected_actor = autonomous_outcome.chosen_actor_id
        selected_action = autonomous_outcome.chosen_action_kind
        selected_source = NEXT_ACTION_SOURCE_NPC_RESPONSE
        silence_reason = None
    else:
        selected_actor = None
        selected_action = ACTION_SILENCE
        selected_source = NEXT_ACTION_SOURCE_SILENCE
        silence_reason = (
            autonomous_outcome.silence_reason
            if autonomous_outcome is not None
            else "director_context_unavailable"
        )
    return build_post_cut_in_replanning_decision(
        source_handoff=handoff,
        cut_outcome=cut_outcome,
        new_director_context=_post_cut_in_director_context(
            turn,
            events=events,
            tick_inputs=tick_inputs,
            outcome=autonomous_outcome,
        ),
        selected_next_action_source=selected_source,
        selected_next_actor_id=selected_actor,
        selected_next_action_kind=selected_action,
        candidate_actions=candidate_actions,
        rejected_candidates=_rejected_post_cut_in_candidates(
            candidate_actions,
            selected_actor_id=selected_actor,
            selected_action_kind=selected_action,
        ),
        silence_reason=silence_reason,
    )


# ── Streaming loop ────────────────────────────────────────────────────────────


async def _stream_events_to_client(
    websocket: WebSocket,
    state: WSSessionLoopState,
    events: list[dict[str, Any]],
    *,
    cut_in_queue: asyncio.Queue,
    pacing_seconds: float,
    autonomous_originator: bool = False,
    canceled_autonomous_ticks_on_cut: int = 0,
) -> None:
    """Emit each block as block_started → (pacing) → block_completed.

    Between events, drain the cut_in_queue. If a cut-in arrives, apply it
    via apply_cut_in() and emit block_cut, then stop the stream.

    ``autonomous_originator`` only affects bookkeeping (the WSSessionLoopState
    is augmented by the caller for the autonomous-tick branch); the transport
    semantics are identical between user-driven and autonomous block events.
    """
    for event_index, event in enumerate(events):
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
                pending_events=events[event_index + 1 :],
                canceled_autonomous_ticks=canceled_autonomous_ticks_on_cut,
            )
            await websocket.send_json(msg_block_cut(cut_outcome=outcome))
            await _emit_replanned_events(
                websocket,
                outcome.get("replanning_decision")
                if isinstance(outcome.get("replanning_decision"), dict)
                else None,
            )
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


async def _run_autonomous_followup_after_turn(
    *,
    websocket: WebSocket,
    session_id: str,
    turn: dict[str, Any],
    queued_carryover: list[dict[str, Any]],
    processed_handoff_input_ids: set[str],
    pacing_seconds: float,
    autonomous_last_tick_ms: float | None,
    autonomous_summaries: list[dict[str, Any]],
) -> tuple[float | None, dict[str, Any] | None]:
    """Run the optional autonomous Director follow-up after a clean user turn."""
    if not is_autonomous_tick_enabled():
        await websocket.send_json(msg_stream_idle(reason="completed"))
        return autonomous_last_tick_ms, None

    tick_inputs = _extract_autonomous_tick_inputs(
        turn, trigger_kind="motivation_threshold_crossed",
    )
    if tick_inputs is None:
        await websocket.send_json(msg_stream_idle(reason="completed"))
        return autonomous_last_tick_ms, None

    loop_enabled = is_autonomous_pause_loop_enabled()
    max_ticks_per_pause = (
        resolve_max_ticks_per_pause(tick_inputs.pacing_rhythm_policy)
        if loop_enabled
        else 1
    )
    min_tick_interval_ms = resolve_min_tick_interval_ms(
        tick_inputs.pacing_rhythm_policy,
        tick_inputs.min_tick_interval_ms_override,
    )
    loop_trigger_kind = (
        LOOP_TRIGGER_GATHERING_PAUSED
        if tick_inputs.gathering_paused
        else LOOP_TRIGGER_USER_PAUSE
    )
    stop_reason = LOOP_STOP_MAX_TICKS
    autonomous_block_emitted = False
    autonomous_stop_cut_in = False
    pending_priority_start: dict[str, Any] | None = None

    for tick_index in range(max_ticks_per_pause):
        if tick_index == 0:
            tick_inputs.since_last_tick_ms = autonomous_last_tick_ms
        else:
            wait_message = await _wait_for_pause_interval_or_input(
                websocket,
                seconds=min_tick_interval_ms / 1000.0,
            )
            if wait_message is not None:
                stop_reason = LOOP_STOP_PLAYER_CUT_IN
                autonomous_stop_cut_in = True
                if wait_message.get("source_kind") == CLIENT_MSG_START_TURN:
                    pending_priority_start = {
                        "kind": CLIENT_MSG_START_TURN,
                        "player_input": str(wait_message.get("player_input") or ""),
                    }
                else:
                    idle_cut_state = WSSessionLoopState(session_id=session_id)
                    cut_outcome = apply_cut_in(
                        idle_cut_state,
                        tick_id=str(uuid.uuid4()),
                        player_input_payload=wait_message,
                        pending_events=[],
                        canceled_autonomous_ticks=max(
                            0, max_ticks_per_pause - tick_index
                        ),
                    )
                    await websocket.send_json(msg_block_cut(cut_outcome=cut_outcome))
                    await _emit_replanned_events(
                        websocket,
                        cut_outcome.get("replanning_decision")
                        if isinstance(cut_outcome.get("replanning_decision"), dict)
                        else None,
                    )
                    pending_priority_start = _queue_handoff_for_next_turn(
                        cut_outcome,
                        queued_carryover,
                        processed_handoff_input_ids,
                    )
                break
            tick_inputs.since_last_tick_ms = min_tick_interval_ms

        tick_inputs.pending_player_input = bool(queued_carryover)
        tick_inputs.already_streaming_block = False
        autonomous_outcome = evaluate_autonomous_tick(tick_inputs)
        summary = _summary_with_loop_metadata(
            autonomous_outcome,
            tick_index=tick_index,
            max_ticks_per_pause=max_ticks_per_pause,
            loop_enabled=loop_enabled,
            loop_trigger_kind=loop_trigger_kind,
        )

        if autonomous_outcome.autonomous_tick_suppressed_reason == LOOP_STOP_COOLDOWN_ACTIVE:
            stop_reason = LOOP_STOP_COOLDOWN_ACTIVE
            summary["autonomous_pause_loop"]["stop_reason"] = stop_reason
        elif autonomous_outcome.autonomous_tick_suppressed_reason:
            stop_reason = LOOP_STOP_TICK_SUPPRESSED
            summary["autonomous_pause_loop"]["stop_reason"] = stop_reason
        elif _autonomous_candidate_blocked(autonomous_outcome):
            stop_reason = LOOP_STOP_UNSAFE_CANDIDATE
            summary["autonomous_pause_loop"]["stop_reason"] = stop_reason
        elif autonomous_outcome.block_stream_event is None:
            stop_reason = LOOP_STOP_NO_MOTIVATION_THRESHOLD
            summary["autonomous_pause_loop"]["stop_reason"] = stop_reason
        elif tick_index + 1 >= max_ticks_per_pause:
            summary["autonomous_pause_loop"]["stop_reason"] = LOOP_STOP_MAX_TICKS

        autonomous_summaries.append(summary)
        autonomous_last_tick_ms = 0.0
        await websocket.send_json(msg_autonomous_tick_evaluated(summary=summary))

        if stop_reason in {
            LOOP_STOP_COOLDOWN_ACTIVE,
            LOOP_STOP_TICK_SUPPRESSED,
            LOOP_STOP_UNSAFE_CANDIDATE,
            LOOP_STOP_NO_MOTIVATION_THRESHOLD,
        }:
            break

        if autonomous_outcome.block_stream_event is None:
            break

        autonomous_block_emitted = True
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
                canceled_autonomous_ticks_on_cut=max(
                    0, max_ticks_per_pause - tick_index - 1
                ),
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
            stop_reason = LOOP_STOP_PLAYER_CUT_IN
            autonomous_stop_cut_in = True
            pending_priority_start = _queue_handoff_for_next_turn(
                autonomous_state.last_cut_outcome,
                queued_carryover,
                processed_handoff_input_ids,
            )
            if autonomous_summaries:
                autonomous_summaries[-1] = {
                    **autonomous_summaries[-1],
                    "cut_in_interrupted_autonomous_tick": True,
                }
            break

        if not loop_enabled:
            break

    if autonomous_stop_cut_in:
        return autonomous_last_tick_ms, pending_priority_start

    if loop_enabled:
        await websocket.send_json(msg_stream_idle(reason="autonomous_pause_loop_completed"))
    elif autonomous_block_emitted:
        await websocket.send_json(msg_stream_idle(reason="autonomous_tick_completed"))
    else:
        await websocket.send_json(msg_stream_idle(reason="completed"))
    return autonomous_last_tick_ms, None


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
    pending_priority_start: dict[str, Any] | None = None
    processed_handoff_input_ids: set[str] = set()

    try:
        await websocket.send_json(msg_stream_started(session_id=session_id, turn_id=None))

        while True:
            if pending_priority_start is not None:
                message = pending_priority_start
                pending_priority_start = None
            else:
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
                pending_priority_start = _queue_handoff_for_next_turn(
                    outcome,
                    queued_carryover,
                    processed_handoff_input_ids,
                )
                continue

            if kind != CLIENT_MSG_START_TURN:
                await websocket.send_json(msg_stream_error(reason="unknown_kind", detail=kind))
                continue

            source_kind = str(message.get("source_kind") or "")
            message_input_id = str(message.get("player_input_id") or "").strip()
            handoff_cut_outcome = (
                message.get("_cut_outcome")
                if isinstance(message.get("_cut_outcome"), dict)
                else None
            )
            player_input = str(message.get("player_input") or "").strip()
            if not player_input and queued_carryover:
                # Replay carryover from a prior cut-in if the immediate
                # handoff could not be processed before another start request.
                carryover = queued_carryover[-1]
                player_input = str(carryover.get("player_input") or "").strip()
                source_kind = str(carryover.get("source_kind") or source_kind)
                message_input_id = str(
                    carryover.get("player_input_id") or message_input_id
                ).strip()
                handoff_cut_outcome = (
                    carryover.get("_cut_outcome")
                    if isinstance(carryover.get("_cut_outcome"), dict)
                    else handoff_cut_outcome
                )

            if not player_input:
                await websocket.send_json(msg_stream_error(reason="missing_player_input"))
                continue

            is_handoff_turn = source_kind == NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF
            if is_handoff_turn and message_input_id in processed_handoff_input_ids:
                await websocket.send_json(msg_stream_idle(reason="duplicate_handoff_input_ignored"))
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

            if is_handoff_turn and message_input_id:
                processed_handoff_input_ids.add(message_input_id)
                queued_carryover[:] = [
                    item for item in queued_carryover
                    if str(item.get("player_input_id") or "").strip() != message_input_id
                ]
            else:
                queued_carryover.clear()
            turn_id = _extract_turn_id(turn)
            events = _extract_block_stream_events(turn)
            await websocket.send_json(msg_stream_started(session_id=session_id, turn_id=turn_id))
            if is_handoff_turn:
                post_cut_in_decision = _build_post_cut_in_decision_for_turn(
                    turn=turn,
                    events=events,
                    cut_outcome=handoff_cut_outcome,
                )
                if post_cut_in_decision is not None:
                    await websocket.send_json(
                        msg_post_cut_in_replanning_decision(
                            decision=post_cut_in_decision,
                        )
                    )
                    follow_up = build_post_cut_in_follow_up_event(
                        decision=post_cut_in_decision,
                    )
                    await websocket.send_json(
                        msg_post_cut_in_follow_up_event(follow_up=follow_up)
                    )
                    follow_up_event = follow_up.get("block_stream_event")
                    if isinstance(follow_up_event, dict):
                        events = [*events, follow_up_event]
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
                # Player interrupted the user-input turn — promote the queued
                # input into the next Director evaluation and pause autonomy.
                pending_priority_start = _queue_handoff_for_next_turn(
                    state.last_cut_outcome,
                    queued_carryover,
                    processed_handoff_input_ids,
                )
                continue

            if is_handoff_turn:
                await websocket.send_json(msg_stream_idle(reason="player_cut_in_handoff_completed"))
                continue

            # ── Stage E/H: Autonomous Director Tick / Pause Loop ───────────
            # After a clean user-turn delivery, the Director MAY emit
            # autonomous NPC blocks. Stage E remains a single tick by default;
            # Stage H enables a bounded explicit-pause loop behind its own flag.
            autonomous_last_tick_ms, pending_priority_start = await _run_autonomous_followup_after_turn(
                websocket=websocket,
                session_id=session_id,
                turn=turn,
                queued_carryover=queued_carryover,
                processed_handoff_input_ids=processed_handoff_input_ids,
                pacing_seconds=pacing_seconds,
                autonomous_last_tick_ms=autonomous_last_tick_ms,
                autonomous_summaries=autonomous_summaries,
            )

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
    autonomous_loop_enabled = is_autonomous_pause_loop_enabled()
    return {
        "ws_session_loop_supported": enabled,
        "live_interruption_supported": enabled,
        "autonomous_tick_enabled": autonomous_enabled,
        "autonomous_pause_loop_enabled": autonomous_loop_enabled,
        "autonomous_pause_loop_trigger_kinds": [
            LOOP_TRIGGER_USER_PAUSE,
            LOOP_TRIGGER_SILENCE,
            LOOP_TRIGGER_GATHERING_PAUSED,
        ],
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
