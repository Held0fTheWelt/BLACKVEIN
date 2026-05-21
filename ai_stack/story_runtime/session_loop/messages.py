"""Server-to-client WebSocket message builders."""

from __future__ import annotations

import uuid
from typing import Any

from .constants import *


def _new_id() -> str:
    return str(uuid.uuid4())


def msg_stream_started(*, session_id: str, turn_id: str | None = None) -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_STARTED,
        "message_id": _new_id(),
        "session_id": session_id,
        "turn_id": turn_id,
    }


def msg_block_started(*, event: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_STARTED,
        "message_id": _new_id(),
        "event_id": event.get("event_id"),
        "block_type": event.get("block_type"),
        "block_stream_event": event,
    }


def msg_block_completed(*, event_id: str | None) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_COMPLETED,
        "message_id": _new_id(),
        "event_id": event_id,
    }


def msg_block_cut(*, cut_outcome: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_BLOCK_CUT,
        "message_id": _new_id(),
        "event_id": cut_outcome.get("interrupted_block_id"),
        "block_type": cut_outcome.get("interrupted_block_type"),
        "cut_kind": cut_outcome.get("cut_kind"),
        "player_cut_in_event": cut_outcome.get("player_cut_in_event"),
        "drop_remaining_blocks": bool(cut_outcome.get("drop_remaining_blocks")),
        "flush_active_block": bool(cut_outcome.get("flush_active_block")),
        "replanning_request": cut_outcome.get("replanning_request"),
        "replanning_decision": cut_outcome.get("replanning_decision"),
        "player_cut_in_handoff": cut_outcome.get("player_cut_in_handoff"),
    }


def msg_stream_idle(*, reason: str = "completed") -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_IDLE,
        "message_id": _new_id(),
        "reason": reason,
    }


def msg_stream_error(*, reason: str, detail: str | None = None) -> dict[str, Any]:
    return {
        "kind": MSG_STREAM_ERROR,
        "message_id": _new_id(),
        "reason": reason,
        "detail": detail,
    }


def msg_autonomous_tick_evaluated(*, summary: dict[str, Any]) -> dict[str, Any]:
    """One per Director autonomous-tick evaluation (Stage E).

    Always emitted when the autonomous-tick path runs, even when the outcome
    is silence or a suppression. Carries the full diagnostic ``summary``
    block so the client can record motivation scores, cooldown state, and
    the chosen action without parsing the subsequent block_started/idle
    messages.
    """
    return {
        "kind": MSG_AUTONOMOUS_TICK_EVALUATED,
        "message_id": _new_id(),
        "summary": dict(summary or {}),
    }


def msg_replanning_decision(
    *,
    request: dict[str, Any],
    decision: dict[str, Any],
) -> dict[str, Any]:
    return {
        "kind": MSG_REPLANNING_DECISION,
        "message_id": _new_id(),
        "replanning_request": dict(request or {}),
        "replanning_decision": dict(decision or {}),
    }


def msg_player_cut_in_handoff(*, handoff: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_PLAYER_CUT_IN_HANDOFF,
        "message_id": _new_id(),
        "player_cut_in_handoff": dict(handoff or {}),
    }


def msg_post_cut_in_replanning_decision(*, decision: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_POST_CUT_IN_REPLANNING_DECISION,
        "message_id": _new_id(),
        "post_cut_in_replanning_decision": dict(decision or {}),
    }


def msg_post_cut_in_follow_up_event(*, follow_up: dict[str, Any]) -> dict[str, Any]:
    return {
        "kind": MSG_POST_CUT_IN_FOLLOW_UP_EVENT,
        "message_id": _new_id(),
        "post_cut_in_follow_up_event": dict(follow_up or {}),
    }


def cut_in_state_for_kind(cut_kind: str) -> str:
    """Map a player cut_kind to the block_stream_event cut_in_state enum."""
    if cut_kind == CUT_KIND_EM_DASH:
        return CUT_IN_CUT_EM_DASH
    if cut_kind == CUT_KIND_SKIP_TO_END:
        return CUT_IN_CUT_SKIP_TO_END
    # no_active_block — block is not actually interrupted
    return "uninterrupted"
