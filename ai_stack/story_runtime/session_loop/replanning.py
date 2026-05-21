"""Future-only replanning request and decision helpers."""

from __future__ import annotations

import uuid
from typing import Any

from .constants import *
from .state import WSSessionLoopState


def _event_ids(events: list[dict[str, Any]] | None) -> list[str]:
    ids: list[str] = []
    for event in events or []:
        if not isinstance(event, dict):
            continue
        event_id = str(event.get("event_id") or "").strip()
        if event_id:
            ids.append(event_id)
    return ids


def build_replanning_request(
    *,
    state: WSSessionLoopState,
    tick_id: str,
    cut_outcome: dict[str, Any],
    pending_events: list[dict[str, Any]] | None = None,
    canceled_autonomous_ticks: int = 0,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build a diagnostic request for post-cut future-event replanning.

    The request documents the delivery boundary only. It does not mutate graph
    state, turn validation, readiness, canonical path, mandatory beats, or
    already completed delivery events.
    """
    active_id = str(cut_outcome.get("interrupted_block_id") or "").strip()
    streamed_but_not_committed = (
        [active_id]
        if active_id and active_id not in state.completed_event_ids
        else []
    )
    canceled_ticks = max(0, int(canceled_autonomous_ticks or 0))
    return {
        "schema_version": SCHEMA_REPLANNING_REQUEST,
        "request_id": request_id or str(uuid.uuid4()),
        "tick_id": tick_id,
        "replanning_reason": REPLANNING_REASON_PLAYER_CUT_IN,
        "cut_kind": cut_outcome.get("cut_kind"),
        "player_cut_in_event_id": (
            (cut_outcome.get("player_cut_in_event") or {}).get("cut_in_id")
            if isinstance(cut_outcome.get("player_cut_in_event"), dict)
            else None
        ),
        "interrupted_block_id": cut_outcome.get("interrupted_block_id"),
        "interrupted_block_type": cut_outcome.get("interrupted_block_type"),
        "committed_event_ids": list(state.completed_event_ids),
        "streamed_but_not_committed_event_ids": streamed_but_not_committed,
        "not_yet_started_event_ids": _event_ids(pending_events),
        "canceled_ticks": canceled_ticks,
        "replanning_scope": REPLANNING_SCOPE_FUTURE_EVENTS_ONLY,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


def build_replanned_event_after_cut_in(
    *,
    request: dict[str, Any],
    player_input_payload: dict[str, Any] | None,
    tick_id: str | None = None,
    event_id: str | None = None,
) -> dict[str, Any]:
    """Build one replacement event for future-only controlled replanning.

    The event is diagnostic and player-priority oriented. It carries no new
    plot fact and consumes no beat; the queued player input remains the next
    authoritative action source.
    """
    resolved_tick_id = tick_id or str(uuid.uuid4())
    director_decision = build_director_tick_decision(
        trigger_kind=TRIGGER_PLAYER_INPUT,
        triggering_actor_id=None,
        chosen_action_kind=ACTION_SILENCE,
        chosen_actor_id=None,
        composition_inputs=[],
        since_last_tick_ms=None,
        silence_reason=REPLANNED_SILENCE_REASON_PLAYER_INPUT_PRIORITY,
        tick_id=resolved_tick_id,
    )
    replaces_event_ids = list(request.get("not_yet_started_event_ids") or [])
    payload = {
        "id": str(uuid.uuid4()),
        "block_type": BLOCK_TYPE_NARRATOR,
        "text": "",
        "originator": "director_replanning",
        "event_generation": EVENT_GENERATION_REPLANNED_AFTER_CUT_IN,
        "replanning_reason": request.get("replanning_reason"),
        "replanning_request_id": request.get("request_id"),
        "next_action_source": NEXT_ACTION_SOURCE_PLAYER_INPUT,
        "replaces_event_ids": replaces_event_ids,
        "diagnostic_only": True,
        "director_tick_decision": director_decision,
        "player_input_present": bool(player_input_payload),
    }
    event = build_block_stream_event(
        tick_id=resolved_tick_id,
        block_type=BLOCK_TYPE_NARRATOR,
        block_payload=payload,
        cut_in_state=CUT_IN_UNINTERRUPTED,
        lane=LANE_VISIBLE_SCENE_OUTPUT,
        source="director_replanning",
        event_id=event_id,
    )
    event["event_generation"] = EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
    event["replanning_reason"] = request.get("replanning_reason")
    event["next_action_source"] = NEXT_ACTION_SOURCE_PLAYER_INPUT
    event["replaces_event_ids"] = replaces_event_ids
    event["director_tick_decision"] = director_decision
    return event


def build_replanning_decision(
    *,
    request: dict[str, Any],
    player_input_queued: bool = True,
    player_input_payload: dict[str, Any] | None = None,
    replanned_events: list[dict[str, Any]] | None = None,
    decision_id: str | None = None,
) -> dict[str, Any]:
    """Decide the safe Stage-I action for a replanning request.

    Stage I readiness never rewrites existing output and never performs graph
    mutation. The only live decision is to cancel future, not-yet-started
    events/ticks and let the queued player input drive the next turn.
    """
    next_action_source = (
        NEXT_ACTION_SOURCE_PLAYER_INPUT if player_input_queued else NEXT_ACTION_SOURCE_IDLE
    )
    resolved_replanned_events = (
        list(replanned_events)
        if replanned_events is not None
        else (
            [
                build_replanned_event_after_cut_in(
                    request=request,
                    player_input_payload=player_input_payload,
                )
            ]
            if player_input_queued
            else []
        )
    )
    replanned_event_ids = _event_ids(resolved_replanned_events)
    replanned_director_tick_decision = None
    if resolved_replanned_events:
        first_event = resolved_replanned_events[0]
        if isinstance(first_event.get("director_tick_decision"), dict):
            replanned_director_tick_decision = first_event["director_tick_decision"]
        else:
            payload = first_event.get("block_payload")
            if isinstance(payload, dict) and isinstance(payload.get("director_tick_decision"), dict):
                replanned_director_tick_decision = payload["director_tick_decision"]
    return {
        "schema_version": SCHEMA_REPLANNING_DECISION,
        "decision_id": decision_id or str(uuid.uuid4()),
        "request_id": request.get("request_id"),
        "replanning_reason": request.get("replanning_reason"),
        "decision": REPLANNING_DECISION_PRIORITIZE_PLAYER_INPUT,
        "next_action_source": next_action_source,
        "canceled_event_ids": list(request.get("not_yet_started_event_ids") or []),
        "canceled_ticks": int(request.get("canceled_ticks") or 0),
        "replanning_scope": REPLANNING_SCOPE_FUTURE_EVENTS_ONLY,
        "event_generation": EVENT_GENERATION_REPLANNED_AFTER_CUT_IN
        if resolved_replanned_events
        else None,
        "replanned_event_ids": replanned_event_ids,
        "replanned_block_stream_events": resolved_replanned_events,
        "replanned_director_tick_decision": replanned_director_tick_decision,
        "mutates_committed_events": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }
