"""Player cut-in handoff and post-cut-in replanning artifacts."""

from __future__ import annotations

import uuid
from typing import Any

from .constants import *
from .player_input import _compact_one_line, _player_input_text, _promoted_player_input_id


def build_player_cut_in_handoff(
    *,
    cut_outcome: dict[str, Any],
    replanning_decision: dict[str, Any] | None = None,
    player_input_payload: dict[str, Any] | None = None,
    handoff_id: str | None = None,
    autonomous_loop_paused: bool = True,
) -> dict[str, Any]:
    """Build the Stage-K immediate handoff diagnostic.

    The handoff is the bridge from a cut/replanning artifact into the next
    Director evaluation. It carries only IDs and invariants; the actual player
    text stays in the existing queued cut-in payload.
    """
    cut_event = (
        cut_outcome.get("player_cut_in_event")
        if isinstance(cut_outcome.get("player_cut_in_event"), dict)
        else {}
    )
    payload = (
        dict(player_input_payload)
        if isinstance(player_input_payload, dict)
        else (
            dict(cut_event.get("player_input_payload"))
            if isinstance(cut_event.get("player_input_payload"), dict)
            else {}
        )
    )
    decision = replanning_decision if isinstance(replanning_decision, dict) else {}
    has_player_input = bool(_player_input_text(payload))
    status = HANDOFF_STATUS_PROMOTED if has_player_input else HANDOFF_STATUS_NOT_APPLICABLE
    return {
        "schema_version": SCHEMA_PLAYER_CUT_IN_HANDOFF,
        "handoff_id": handoff_id or str(uuid.uuid4()),
        "cut_in_id": cut_event.get("cut_in_id"),
        "promoted_player_input_id": (
            _promoted_player_input_id(payload) if has_player_input else None
        ),
        "source_replanning_decision_id": decision.get("decision_id"),
        "next_turn_trigger": NEXT_TURN_TRIGGER_PLAYER_CUT_IN_HANDOFF
        if has_player_input
        else None,
        "autonomous_loop_paused": bool(autonomous_loop_paused and has_player_input),
        "canceled_event_ids": list(decision.get("canceled_event_ids") or []),
        "canceled_ticks": int(decision.get("canceled_ticks") or 0),
        "handoff_status": status,
        "non_handoff_reason": None
        if status == HANDOFF_STATUS_PROMOTED
        else NON_HANDOFF_REASON_NO_PLAYER_INPUT,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }


def build_post_cut_in_replanning_decision(
    *,
    source_handoff: dict[str, Any],
    cut_outcome: dict[str, Any] | None = None,
    new_director_context: dict[str, Any] | None = None,
    selected_next_action_source: str | None = None,
    selected_next_actor_id: str | None = None,
    selected_next_action_kind: str | None = None,
    candidate_actions: list[dict[str, Any]] | None = None,
    rejected_candidates: list[dict[str, Any]] | None = None,
    silence_reason: str | None = None,
    replanning_id: str | None = None,
) -> dict[str, Any]:
    """Build the Stage-L post-handoff Director reevaluation artifact.

    This is an audit record for a fresh Director read after promoted input.
    It can cancel prior future plans and choose a next action source, but it
    never rewrites committed output or mutates validation/readiness state.
    """
    handoff = source_handoff if isinstance(source_handoff, dict) else {}
    outcome = cut_outcome if isinstance(cut_outcome, dict) else {}
    cut_event = (
        outcome.get("player_cut_in_event")
        if isinstance(outcome.get("player_cut_in_event"), dict)
        else {}
    )
    player_input_payload = (
        cut_event.get("player_input_payload")
        if isinstance(cut_event.get("player_input_payload"), dict)
        else {}
    )
    promoted_text = _player_input_text(player_input_payload)
    request = (
        outcome.get("replanning_request")
        if isinstance(outcome.get("replanning_request"), dict)
        else {}
    )
    canceled_event_ids = list(handoff.get("canceled_event_ids") or [])
    canceled_ticks = int(handoff.get("canceled_ticks") or 0)
    candidates = [
        dict(candidate)
        for candidate in (candidate_actions or [])
        if isinstance(candidate, dict)
    ]
    rejected = [
        dict(candidate)
        for candidate in (rejected_candidates or [])
        if isinstance(candidate, dict)
    ]
    return {
        "schema_version": SCHEMA_POST_CUT_IN_REPLANNING_DECISION,
        "replanning_id": replanning_id or str(uuid.uuid4()),
        "source_handoff_id": handoff.get("handoff_id"),
        "promoted_player_input_id": handoff.get("promoted_player_input_id"),
        "interrupted_block_id": outcome.get("interrupted_block_id"),
        "interrupted_block_type": outcome.get("interrupted_block_type"),
        "cut_kind": outcome.get("cut_kind") or cut_event.get("cut_kind"),
        "prior_plan_canceled": bool(canceled_event_ids or canceled_ticks),
        "canceled_event_ids": canceled_event_ids,
        "canceled_ticks": canceled_ticks,
        "new_director_context": dict(new_director_context or {}),
        "selected_next_action_source": selected_next_action_source or NEXT_ACTION_SOURCE_SILENCE,
        "selected_next_actor_id": selected_next_actor_id,
        "selected_next_action_kind": selected_next_action_kind or ACTION_SILENCE,
        "candidate_actions": candidates,
        "rejected_candidates": rejected,
        "silence_reason": silence_reason,
        "interrupted_context": {
            "interrupted_block_id": outcome.get("interrupted_block_id"),
            "interrupted_block_type": outcome.get("interrupted_block_type"),
            "cut_kind": outcome.get("cut_kind") or cut_event.get("cut_kind"),
            "committed_event_ids": list(request.get("committed_event_ids") or []),
            "streamed_but_not_committed_event_ids": list(
                request.get("streamed_but_not_committed_event_ids") or []
            ),
            "not_yet_started_event_ids": list(
                request.get("not_yet_started_event_ids") or []
            ),
        },
        "promoted_input": {
            "promoted_player_input_id": handoff.get("promoted_player_input_id"),
            "source_handoff_id": handoff.get("handoff_id"),
            "text_present": bool(handoff.get("promoted_player_input_id")),
            "text_excerpt": _compact_one_line(
                promoted_text,
                limit=MAX_PROMOTED_INPUT_EXCERPT_CHARS,
            ),
            "text_length": len(promoted_text),
        },
        "canceled_prior_plan": {
            "prior_plan_canceled": bool(canceled_event_ids or canceled_ticks),
            "canceled_event_ids": canceled_event_ids,
            "canceled_ticks": canceled_ticks,
        },
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }
