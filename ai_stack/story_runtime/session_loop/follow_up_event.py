"""Post-cut-in follow-up event construction."""

from __future__ import annotations

import uuid
from typing import Any

from .composition import _compose_npc_follow_up, _non_composed_result
from .constants import *


def build_post_cut_in_follow_up_event(
    *,
    decision: dict[str, Any],
    follow_up_id: str | None = None,
    composition_provider: FollowUpSemanticProvider | None = None,
) -> dict[str, Any]:
    """Build an executable future-only follow-up artifact for Stage L+M.

    A safe NPC response produces a ``block_stream_event.v1`` to append after
    already-planned promoted-input output. Silence produces an explicit
    diagnostic silence event. Unsupported or unsafe selections produce a
    no-follow-up diagnostic with no emitted block.

    Stage M (semantic composition): when ``composition_provider`` is supplied
    and ``PHASE2_FOLLOW_UP_SEMANTIC_COMPOSITION_ENABLED`` is on, the dispatcher
    invokes the provider for an NPC reply, runs every safety gate, and either
    accepts the semantic output or falls back to the deterministic template
    path. The composition_mode field on the returned ``composition_result``
    records which path produced the emitted text.
    """
    replanning = decision if isinstance(decision, dict) else {}
    resolved_follow_up_id = follow_up_id or str(uuid.uuid4())
    source = str(replanning.get("selected_next_action_source") or "").strip()
    actor_id = str(replanning.get("selected_next_actor_id") or "").strip() or None
    action_kind = str(replanning.get("selected_next_action_kind") or ACTION_SILENCE).strip()
    context = (
        replanning.get("new_director_context")
        if isinstance(replanning.get("new_director_context"), dict)
        else {}
    )
    known_actor_ids = {
        str(raw)
        for raw in context.get("known_actor_ids") or []
        if isinstance(raw, str) and raw
    }
    block_event: dict[str, Any] | None = None
    silence_reason = replanning.get("silence_reason")
    no_follow_up_reason: str | None = None
    composition_result = _non_composed_result(
        composition_kind=source or "unknown",
        reason="composition_not_attempted",
    )

    if source == NEXT_ACTION_SOURCE_NPC_RESPONSE:
        if not actor_id:
            no_follow_up_reason = "missing_selected_actor_id"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        elif known_actor_ids and actor_id not in known_actor_ids:
            no_follow_up_reason = "unsafe_unknown_actor"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        elif action_kind != ACTION_SPEAK:
            no_follow_up_reason = "unsupported_next_action_kind"
            composition_result = _non_composed_result(
                composition_kind=NEXT_ACTION_SOURCE_NPC_RESPONSE,
                reason=no_follow_up_reason,
                attempted=True,
            )
        else:
            composition_result = _compose_npc_follow_up(
                replanning=replanning,
                context=context,
                actor_id=actor_id,
                composition_provider=composition_provider,
            )
            if not composition_result.get("composed"):
                no_follow_up_reason = str(
                    composition_result.get("reason") or "follow_up_composition_rejected"
                )
            else:
                composed_text = str(composition_result.get("text") or "")
                voice_profile_actor_id = composition_result.get("voice_profile_actor_id")
                source_field = composition_result.get("voice_profile_source_field")
                input_fields_used = list(composition_result.get("input_fields_used") or [])
                motivation_score = composition_result.get("motivation_score")
                composition_mode = composition_result.get("composition_mode")
                source_contexts = list(composition_result.get("source_contexts") or [])
                safety_gate_decisions = dict(
                    composition_result.get("safety_gate_decisions") or {}
                )
                provider_metadata = composition_result.get("provider_metadata")
                payload = {
                    "id": str(uuid.uuid4()),
                    "block_type": BLOCK_TYPE_ACTOR_LINE,
                    "actor_id": actor_id,
                    "text": composed_text,
                    "originator": POST_CUT_IN_FOLLOW_UP_GENERATION,
                    "post_cut_in_replanning_id": replanning.get("replanning_id"),
                    "post_cut_in_follow_up_id": resolved_follow_up_id,
                    "selected_next_action_source": source,
                    "selected_next_action_kind": action_kind,
                    "composition_mode": composition_mode,
                    "source_contexts": source_contexts,
                    "safety_gate_decisions": safety_gate_decisions,
                    "provider_metadata": provider_metadata,
                    "voice_profile_used": True,
                    "voice_profile_actor_id": voice_profile_actor_id,
                    "voice_profile_source_field": source_field,
                    "composition_inputs_used": input_fields_used,
                    "motivation_score": motivation_score,
                    "new_people_introduced": False,
                    "new_rooms_introduced": False,
                    "plot_facts_introduced": False,
                }
                block_event = build_block_stream_event(
                    tick_id=str(uuid.uuid4()),
                    block_type=BLOCK_TYPE_ACTOR_LINE,
                    block_payload=payload,
                    cut_in_state=CUT_IN_UNINTERRUPTED,
                    lane=LANE_VISIBLE_SCENE_OUTPUT,
                    source=actor_id,
                )
                block_event["event_generation"] = POST_CUT_IN_FOLLOW_UP_GENERATION
                block_event["post_cut_in_replanning_id"] = replanning.get("replanning_id")
                block_event["post_cut_in_follow_up_id"] = resolved_follow_up_id
    elif source == NEXT_ACTION_SOURCE_SILENCE or action_kind == ACTION_SILENCE:
        silence_reason = silence_reason or "director_chose_silence"
        composition_result = _non_composed_result(
            composition_kind=NEXT_ACTION_SOURCE_SILENCE,
            reason=str(silence_reason),
            attempted=False,
        )
        composition_result["safety_gate_result"] = "pass"
    else:
        no_follow_up_reason = "unsupported_next_action_source"
        composition_result = _non_composed_result(
            composition_kind=source or "unknown",
            reason=no_follow_up_reason,
            attempted=True,
        )

    return {
        "schema_version": SCHEMA_POST_CUT_IN_FOLLOW_UP_EVENT,
        "follow_up_id": resolved_follow_up_id,
        "source_replanning_id": replanning.get("replanning_id"),
        "selected_next_action_source": source or None,
        "selected_next_actor_id": actor_id,
        "selected_next_action_kind": action_kind,
        "emitted_event_id": block_event.get("event_id") if block_event else None,
        "silence_reason": silence_reason if block_event is None else None,
        "no_follow_up_reason": no_follow_up_reason,
        "composition_result": composition_result,
        "block_stream_event": block_event,
        "historical_events_mutated": False,
        "graph_state_mutated_mid_turn": False,
        "validation_outcome_changed": False,
        "commit_or_readiness_changed": False,
        "canonical_path_advanced": False,
        "mandatory_beat_consumed": False,
        "proof_level": PROOF_LEVEL_LOCAL_ONLY,
    }
