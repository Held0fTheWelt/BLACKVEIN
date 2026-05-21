"""Per-connection WebSocket session-loop state."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


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
    last_player_cut_in_handoff: dict[str, Any] | None = None
    last_cut_outcome: dict[str, Any] | None = None
    last_cut_kind: str | None = None
    queued_player_inputs: list[dict[str, Any]] = field(default_factory=list)
    completed_event_ids: list[str] = field(default_factory=list)
    started_event_ids: list[str] = field(default_factory=list)
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
        if self.active_block_id and self.active_block_id not in self.started_event_ids:
            self.started_event_ids.append(self.active_block_id)

    def mark_block_completed(self) -> None:
        if self.active_block_id and self.active_block_id not in self.completed_event_ids:
            self.completed_event_ids.append(self.active_block_id)
        self.active_block_id = None
        self.active_block_type = None

    def mark_stream_idle(self) -> None:
        self.active_block_id = None
        self.active_block_type = None
        self.stream_finished = True
