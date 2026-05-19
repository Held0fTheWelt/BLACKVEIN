"""Phase 2 — WebSocket Session Loop helpers.

Pure helpers for the live block-stream session loop (ADR-0058 §"Real-time"):

* ``is_ws_session_loop_enabled()`` — server-side feature flag
* ``WSSessionLoopState`` — per-connection runtime state (active block, cut counts)
* ``apply_cut_in()`` — translate an inbound cut-in into a ``player_cut_in_event.v1``
  plus the resulting cut semantics (which blocks to drop / flush)
* Message builders for the WS protocol (``stream_started``, ``block_started``,
  ``block_completed``, ``block_cut``, ``stream_idle``, ``stream_error``)

This module is intentionally I/O-free. No FastAPI, no asyncio, no socket
handling. The WS endpoint in ``world-engine/app/api/story_ws.py`` orchestrates
the transport; this module owns the semantics.

Hard guarantees (ADR-0058):
* No commit/readiness mutation.
* No ``validation_outcome`` change.
* No Pi/Π keys.
* No hardcoded actor/room IDs.
* Cut semantics are block-type driven via
  ``resolve_cut_kind_for_block_type()``.
"""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass, field
from typing import Any

from ai_stack.director_pulse_contracts import (
    CUT_IN_CUT_EM_DASH,
    CUT_IN_CUT_SKIP_TO_END,
    CUT_KIND_EM_DASH,
    CUT_KIND_NO_ACTIVE_BLOCK,
    CUT_KIND_SKIP_TO_END,
    CUT_KINDS,
    build_player_cut_in_event,
    resolve_cut_kind_for_block_type,
)

# ── Feature flag ──────────────────────────────────────────────────────────────

PHASE2_WS_SESSION_LOOP_ENABLED = "PHASE2_WS_SESSION_LOOP_ENABLED"

_TRUE_VALUES = frozenset(("1", "true", "yes", "on"))


def is_ws_session_loop_enabled() -> bool:
    """Return True when the Phase-2 WS session loop is enabled server-side.

    Fail-closed: any unset / unparseable value is treated as disabled.
    """
    raw = os.environ.get(PHASE2_WS_SESSION_LOOP_ENABLED, "false")
    return str(raw or "").strip().lower() in _TRUE_VALUES


# ── WS message kinds (closed enum) ────────────────────────────────────────────

MSG_STREAM_STARTED = "stream_started"
MSG_BLOCK_STARTED = "block_started"
MSG_BLOCK_COMPLETED = "block_completed"
MSG_BLOCK_CUT = "block_cut"
MSG_STREAM_IDLE = "stream_idle"
MSG_STREAM_ERROR = "stream_error"
MSG_AUTONOMOUS_TICK_EVALUATED = "autonomous_tick_evaluated"

SERVER_MSG_KINDS = frozenset({
    MSG_STREAM_STARTED,
    MSG_BLOCK_STARTED,
    MSG_BLOCK_COMPLETED,
    MSG_BLOCK_CUT,
    MSG_STREAM_IDLE,
    MSG_STREAM_ERROR,
    MSG_AUTONOMOUS_TICK_EVALUATED,
})

CLIENT_MSG_START_TURN = "start_turn"
CLIENT_MSG_CUT_IN = "cut_in"
CLIENT_MSG_PING = "ping"

CLIENT_MSG_KINDS = frozenset({
    CLIENT_MSG_START_TURN,
    CLIENT_MSG_CUT_IN,
    CLIENT_MSG_PING,
})


# ── Per-connection state ──────────────────────────────────────────────────────


@dataclass
class WSSessionLoopState:
    """Mutable state for one WS connection's streaming pass.

    A new state is created per ``start_turn`` and discarded when the stream
    ends (or is cut). Persistence across turns lives in the StoryRuntime
    session, not here.
    """

    session_id: str
    active_block_id: str | None = None
    active_block_type: str | None = None
    last_event_id: str | None = None
    cut_in_count: int = 0
    last_player_cut_in_event: dict[str, Any] | None = None
    last_cut_kind: str | None = None
    queued_player_inputs: list[dict[str, Any]] = field(default_factory=list)
    stream_finished: bool = False

    def mark_block_started(self, event: dict[str, Any]) -> None:
        self.active_block_id = str(event.get("event_id") or "") or None
        block_payload = event.get("block_payload") or {}
        # Prefer payload block_type (LDSS-truth) over the event-level normalised type
        # so the cut semantics match what the player actually sees being rendered.
        bt = (
            block_payload.get("block_type")
            if isinstance(block_payload, dict) and block_payload.get("block_type")
            else event.get("block_type")
        )
        self.active_block_type = str(bt) if bt else None
        self.last_event_id = self.active_block_id

    def mark_block_completed(self) -> None:
        self.active_block_id = None
        self.active_block_type = None

    def mark_stream_idle(self) -> None:
        self.active_block_id = None
        self.active_block_type = None
        self.stream_finished = True


# ── Cut-in application ───────────────────────────────────────────────────────


def apply_cut_in(
    state: WSSessionLoopState,
    *,
    tick_id: str,
    player_input_payload: dict[str, Any],
) -> dict[str, Any]:
    """Apply a player cut-in to the current stream state.

    Returns a dict describing the outcome:

        ``cut_kind``            — one of CUT_KIND_* (em_dash / skip_to_end / no_active_block)
        ``player_cut_in_event`` — a ``player_cut_in_event.v1`` record
        ``interrupted_block_id``    — the active block's event_id (or None)
        ``interrupted_block_type``  — the active block's block_type (or None)
        ``drop_remaining_blocks``   — True when the cut should clear the queue
        ``flush_active_block``      — True when remaining text of active block
                                       should be flushed before stopping
        ``queue_input_for_next_turn``— True when the player input should be
                                       carried into the next Director turn

    Semantics (ADR-0058 §6):

    * ``actor_line`` → ``em_dash``: append "—" to active line, drop the rest
      of the stream, queue input for next turn.
    * ``narrator`` / ``actor_action`` / ``souffleuse`` / ``environment_interaction``
      → ``skip_to_end``: complete active block immediately, drop the rest of
      the stream, queue input for next turn.
    * No active block → ``no_active_block``: queue input for next turn; do
      not touch the (empty) stream.

    Mutates ``state.cut_in_count`` and records ``last_player_cut_in_event``.
    """
    cut_kind = resolve_cut_kind_for_block_type(state.active_block_type)

    cut_event = build_player_cut_in_event(
        tick_id=tick_id,
        interrupted_block_id=state.active_block_id,
        interrupted_block_type=state.active_block_type,
        cut_kind=cut_kind,
        player_input_payload=dict(player_input_payload or {}),
    )

    state.cut_in_count += 1
    state.last_player_cut_in_event = cut_event
    state.last_cut_kind = cut_kind
    if player_input_payload:
        state.queued_player_inputs.append(dict(player_input_payload))

    if cut_kind == CUT_KIND_EM_DASH:
        outcome = {
            "cut_kind": cut_kind,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": state.active_block_id,
            "interrupted_block_type": state.active_block_type,
            "drop_remaining_blocks": True,
            "flush_active_block": False,
            "queue_input_for_next_turn": True,
        }
    elif cut_kind == CUT_KIND_SKIP_TO_END:
        outcome = {
            "cut_kind": cut_kind,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": state.active_block_id,
            "interrupted_block_type": state.active_block_type,
            "drop_remaining_blocks": True,
            "flush_active_block": True,
            "queue_input_for_next_turn": True,
        }
    else:
        # no_active_block: input queues for next turn, no stream impact
        outcome = {
            "cut_kind": CUT_KIND_NO_ACTIVE_BLOCK,
            "player_cut_in_event": cut_event,
            "interrupted_block_id": None,
            "interrupted_block_type": None,
            "drop_remaining_blocks": False,
            "flush_active_block": False,
            "queue_input_for_next_turn": True,
        }

    return outcome


# ── Server → client message builders ─────────────────────────────────────────


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


# ── Cut-in-state mapping for block_stream_event annotation ───────────────────


def cut_in_state_for_kind(cut_kind: str) -> str:
    """Map a player cut_kind to the block_stream_event cut_in_state enum."""
    if cut_kind == CUT_KIND_EM_DASH:
        return CUT_IN_CUT_EM_DASH
    if cut_kind == CUT_KIND_SKIP_TO_END:
        return CUT_IN_CUT_SKIP_TO_END
    # no_active_block — block is not actually interrupted
    return "uninterrupted"


__all__ = [
    "PHASE2_WS_SESSION_LOOP_ENABLED",
    "is_ws_session_loop_enabled",
    "MSG_STREAM_STARTED",
    "MSG_BLOCK_STARTED",
    "MSG_BLOCK_COMPLETED",
    "MSG_BLOCK_CUT",
    "MSG_STREAM_IDLE",
    "MSG_STREAM_ERROR",
    "MSG_AUTONOMOUS_TICK_EVALUATED",
    "SERVER_MSG_KINDS",
    "CLIENT_MSG_START_TURN",
    "CLIENT_MSG_CUT_IN",
    "CLIENT_MSG_PING",
    "CLIENT_MSG_KINDS",
    "WSSessionLoopState",
    "apply_cut_in",
    "msg_stream_started",
    "msg_block_started",
    "msg_block_completed",
    "msg_block_cut",
    "msg_stream_idle",
    "msg_stream_error",
    "msg_autonomous_tick_evaluated",
    "cut_in_state_for_kind",
]
