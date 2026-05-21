"""Cut-in application and derived replanning records."""

from __future__ import annotations

from typing import Any

from .constants import *
from .handoff import build_player_cut_in_handoff
from .replanning import build_replanning_decision, build_replanning_request
from .state import WSSessionLoopState


def apply_cut_in(
    state: WSSessionLoopState,
    *,
    tick_id: str,
    player_input_payload: dict[str, Any],
    pending_events: list[dict[str, Any]] | None = None,
    canceled_autonomous_ticks: int = 0,
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

    replanning_request = build_replanning_request(
        state=state,
        tick_id=tick_id,
        cut_outcome=outcome,
        pending_events=pending_events,
        canceled_autonomous_ticks=canceled_autonomous_ticks,
    )
    replanning_decision = build_replanning_decision(
        request=replanning_request,
        player_input_queued=bool(player_input_payload),
        player_input_payload=player_input_payload,
    )
    handoff = build_player_cut_in_handoff(
        cut_outcome=outcome,
        replanning_decision=replanning_decision,
        player_input_payload=player_input_payload,
    )
    outcome["replanning_request"] = replanning_request
    outcome["replanning_decision"] = replanning_decision
    outcome["player_cut_in_handoff"] = handoff
    state.last_player_cut_in_handoff = handoff
    state.last_cut_outcome = outcome

    return outcome
