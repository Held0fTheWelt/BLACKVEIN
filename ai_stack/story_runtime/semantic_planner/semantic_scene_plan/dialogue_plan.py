"""NPC dialogue planning and dialogue-aware handover policy."""

from __future__ import annotations

from typing import Any

from .content_frame import _quote_anchor_policy, _quote_anchor_ref
from .utils import (
    _actor_id_index,
    _ai_forbidden_actor_ids,
    _as_dict,
    _as_list,
    _clean,
    _resolve_actor_id,
    _unique_clean,
)


def _select_dialogue_actor(
    *,
    preferred_actor_ref: str,
    content_frame: dict[str, Any],
    selected_responder_set: list[dict[str, Any]] | None,
    actor_lane_context: dict[str, Any] | None,
    actor_id_by_ref: dict[str, str],
) -> str:
    forbidden = _ai_forbidden_actor_ids(actor_lane_context)
    candidates: list[str] = []
    preferred = _resolve_actor_id(preferred_actor_ref, actor_id_by_ref)
    if preferred:
        candidates.append(preferred)
    for row in selected_responder_set or []:
        if isinstance(row, dict):
            candidates.append(_clean(row.get("actor_id") or row.get("responder_id")))
    for actor_id in _as_list(content_frame.get("present_actor_ids")):
        candidates.append(_clean(actor_id))
    for actor_id in candidates:
        if actor_id and actor_id not in forbidden:
            return actor_id
    return ""


def _dialogue_plan(
    *,
    content_frame: dict[str, Any],
    speech_policy: dict[str, Any],
    selected_responder_set: list[dict[str, Any]] | None,
    actor_lane_context: dict[str, Any] | None,
    beat_library: dict[str, Any] | None,
    character_documents: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not speech_policy.get("speech_recommended") or not speech_policy.get("npc_speech_allowed"):
        return []
    actor_id_by_ref = _actor_id_index(character_documents)
    profile = _as_dict(content_frame.get("dialogue_profile"))
    profile_beats = list(profile.get("beats") or [])
    if not profile_beats:
        actor_id = _select_dialogue_actor(
            preferred_actor_ref="",
            content_frame=content_frame,


            selected_responder_set=selected_responder_set,
            actor_lane_context=actor_lane_context,
            actor_id_by_ref=actor_id_by_ref,
        )
        if not actor_id:
            return []
        profile_beats = [
            {
                "beat_pattern_ref": "paraphrase_required_with_facts",
                "actor_ref": actor_id,
                "intent": speech_policy.get("speech_function") or "respond_to_scene_pressure",
                "quote_anchor_id": None,
                "paraphrase_policy": "structural_paraphrase_required",
                "minimum_visible": "one short character-specific line",
                "required_facts": tuple(content_frame.get("carry_forward_markers") or ["scene_pressure_visible"]),
            }
        ]

    known_patterns = _as_dict(_as_dict(beat_library).get("patterns"))
    plan: list[dict[str, Any]] = []
    forbidden = _ai_forbidden_actor_ids(actor_lane_context)
    for idx, spec in enumerate(profile_beats, start=1):
        if not isinstance(spec, dict):
            continue
        preferred_actor_ref = _clean(spec.get("actor_ref") or spec.get("actor_id"))
        preferred_actor_id = _resolve_actor_id(preferred_actor_ref, actor_id_by_ref)
        if preferred_actor_ref and preferred_actor_id and preferred_actor_id in forbidden:
            continue
        actor_id = _select_dialogue_actor(
            preferred_actor_ref=preferred_actor_ref,
            content_frame=content_frame,
            selected_responder_set=selected_responder_set,
            actor_lane_context=actor_lane_context,
            actor_id_by_ref=actor_id_by_ref,
        )
        if not actor_id:
            continue
        pattern_ref = _clean(spec.get("beat_pattern_ref")) or "paraphrase_required_with_facts"
        quote_ref = _quote_anchor_ref(spec.get("quote_anchor_id"), _as_list(content_frame.get("quote_anchor_refs")))
        chain = _as_dict(spec.get("forces_response_chain"))
        if chain:
            preferred_target_ref = _clean(chain.get("target_actor_ref") or chain.get("target_actor_id"))
            preferred_target_id = _resolve_actor_id(preferred_target_ref, actor_id_by_ref)
            target_actor_id = ""
            if not preferred_target_ref or not preferred_target_id or preferred_target_id not in forbidden:
                target_actor_id = _select_dialogue_actor(
                    preferred_actor_ref=preferred_target_ref,
                    content_frame=content_frame,
                    selected_responder_set=[],
                    actor_lane_context=actor_lane_context,
                    actor_id_by_ref=actor_id_by_ref,
                )
            chain = {
                "target_actor_id": target_actor_id or None,
                "target_intent": chain.get("target_intent"),
                "target_pattern_ref": chain.get("target_pattern_ref"),
                "required_state_change": chain.get("required_state_change"),
                "max_delay_seconds": chain.get("max_delay_seconds") or 6,
                "failure_handling": chain.get("failure_handling") or "regenerate_target_response",
            }
            if not target_actor_id:
                chain["degraded_reason"] = "target_actor_not_available_to_ai"
        plan.append(
            {
                "dialogue_order": idx,
                "beat_kind": "npc_speak",
                "beat_pattern_ref": pattern_ref,
                "beat_pattern_available": pattern_ref in known_patterns if known_patterns else None,
                "actor_id": actor_id,
                "actor_ref": preferred_actor_ref or actor_id,
                "intent": spec.get("intent"),
                "required": bool(spec.get("required", speech_policy.get("speech_required"))),


                "quote_anchor_ref": quote_ref,
                "quote_use": spec.get("quote_use") or (
                    "exact_anchor_allowed"
                    if quote_ref and speech_policy.get("quote_policy") == "moment_locked_short_anchor"
                    else "paraphrase_or_transform"
                ),
                "paraphrase_policy": spec.get("paraphrase_policy") or "structural_paraphrase_required",
                "required_facts": list(spec.get("required_facts") or []),
                "minimum_visible": spec.get("minimum_visible"),
                "forced_by_previous_beat": bool(spec.get("forced_by_previous_beat")),
                "forces_response_chain": chain,
                "constraints": [
                    "do_not_force_player_speech",
                    "respect_actor_lane",
                    "do_not_commit_new_truth",
                    "quote_anchor_must_remain_short",
                ],
            }
        )
    return plan


def _quote_moment_policy(
    *,
    content_frame: dict[str, Any],
    speech_policy: dict[str, Any],
    dialogue_plan: list[dict[str, Any]],
    opening_quote_anchors: dict[str, Any] | None,
) -> dict[str, Any]:
    anchor_refs = _unique_clean(_as_list(content_frame.get("quote_anchor_refs")))
    quote_policy = _quote_anchor_policy(opening_quote_anchors)
    exact_allowed = bool(anchor_refs and speech_policy.get("speech_recommended"))
    exact_used_by = [
        row.get("dialogue_order")
        for row in dialogue_plan
        if isinstance(row, dict) and row.get("quote_use") == "exact_anchor_allowed"
    ]
    return {
        "mode": "moment_locked" if exact_allowed else "default_transform",
        "default": "paraphrase_or_transform",
        "exact_quote_allowed": exact_allowed,
        "exact_quote_preferred_for_dialogue_orders": exact_used_by,
        "quote_anchor_refs": anchor_refs,
        "max_words_per_runtime_quote": quote_policy["max_words_per_runtime_quote"],
        "exact_quote_requires": [
            "canonical_path_step_has_quote_anchor",
            "beat_function_requires_source_pressure",
            "speaker_and_context_match",
            "quote_not_recently_used",
        ],
        "frequency_policy": "rare",
        "failure_mode": "use_paraphrase_instead",
        "must_not": quote_policy["must_not"],
    }


def _merge_dialogue_into_beats(
    *,
    dramatic_beats: list[dict[str, Any]],
    dialogue_plan: list[dict[str, Any]],
    expected_transition_pattern: str,
    pacing_mode: str,
) -> list[dict[str, Any]]:
    if not dialogue_plan:
        return dramatic_beats
    out = [dict(row) for row in dramatic_beats]
    next_order = len(out) + 1
    for row in dialogue_plan:
        out.append(
            {
                "beat_order": next_order,
                "beat_kind": "npc_speak_beat",


                "beat_function": row.get("intent"),
                "beat_intent": row.get("intent"),
                "owner": "npc",
                "owner_actor_id": row.get("actor_id"),
                "visibility": "visible_to_player",
                "beat_pattern_ref": row.get("beat_pattern_ref"),
                "quote_anchor_ref": row.get("quote_anchor_ref"),
                "expected_transition_pattern": expected_transition_pattern,
                "pacing_mode": pacing_mode,
                "required": bool(row.get("required")),
                "success_condition": "npc_speech_realized",
                "constraints": list(row.get("constraints") or []),
            }
        )
        next_order += 1
    return out


def _handover_policy_for_speech(
    *,
    base_policy: dict[str, Any],
    speech_policy: dict[str, Any],
    dialogue_plan: list[dict[str, Any]],
    dramatic_beats: list[dict[str, Any]],
) -> dict[str, Any]:
    if not dialogue_plan:
        return base_policy
    has_chain = any(_as_dict(row.get("forces_response_chain")).get("target_actor_id") for row in dialogue_plan)
    policy = "offer_player_action_after_dialogue_chain" if has_chain else "offer_player_action_after_dialogue"
    return {
        **base_policy,
        "policy": policy,
        "requires_player_affordance": True,
        "handover_after_beat_order": dramatic_beats[-1]["beat_order"] if dramatic_beats else 0,
        "success_condition": f"{policy}_available",
        "speech_function": speech_policy.get("speech_function"),
    }
