"""Canonical path, content frame, and speech-policy assembly."""

from __future__ import annotations

from typing import Any

from .utils import (
    _access_decisions_for_targets,
    _active_canonical_step,
    _actor_id_index,
    _ai_forbidden_actor_ids,
    _append_unique,
    _as_dict,
    _as_list,
    _clean,
    _location_rows,
    _object_rows,
    _resolve_actor_id,
    _unique_clean,
)


def _quote_anchor_ref(anchor_id: Any, quote_anchor_refs: list[str]) -> str | None:
    aid = _clean(anchor_id)
    if not aid:
        return None
    for ref in quote_anchor_refs:
        if ref.endswith(f"#{aid}") or ref.endswith(aid):
            return ref
    return f"knowledge/opening_quote_anchors.yaml#{aid}"


def _quote_anchor_policy(opening_quote_anchors: dict[str, Any] | None) -> dict[str, Any]:
    anchors = _as_dict(opening_quote_anchors)
    policy = _as_dict(anchors.get("copyright_policy"))
    return {
        "quote_usage": policy.get("quote_usage") or "short_anchor_only",
        "max_words_per_runtime_quote": int(policy.get("max_words_per_runtime_quote") or 5),
        "must_not": list(policy.get("must_not") or []) if isinstance(policy.get("must_not"), list) else [],
    }


def _mandatory_beats(step: dict[str, Any]) -> list[dict[str, Any]]:
    return [dict(row) for row in _as_list(step.get("mandatory_beats")) if isinstance(row, dict)]


def _beat_instruction(beat: dict[str, Any]) -> dict[str, Any]:
    return _as_dict(beat.get("director_instruction"))


def _npc_speak_rows(step: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for beat in _mandatory_beats(step):
        instruction = _beat_instruction(beat)
        npc_speak = _as_dict(instruction.get("npc_speak"))
        if npc_speak:
            rows.append({"beat": beat, "instruction": instruction, "npc_speak": npc_speak})
    return rows


def _quote_anchor_refs_from_step(step: dict[str, Any]) -> list[str]:
    refs = list(_as_list(step.get("quote_anchor_refs")))
    for row in _npc_speak_rows(step):
        anchor = _clean(_as_dict(row.get("npc_speak")).get("quote_anchor"))


        if anchor:
            refs.append(anchor)
    return _unique_clean(refs)


def _required_fact_tokens(value: Any) -> list[Any]:
    facts: list[Any] = []
    for item in _as_list(value):
        if isinstance(item, dict):
            facts.extend(f"{key}:{val}" for key, val in item.items())
        elif _clean(item):
            facts.append(item)
    return facts


def _beat_pattern_ref_for_npc_speak(npc_speak: dict[str, Any]) -> str:
    intent = _clean(npc_speak.get("intent")).lower()
    minimum = _clean(npc_speak.get("minimum_visible")).lower()
    if "single_word" in intent or "single word" in minimum:
        return "single_word_challenge"
    return "paraphrase_required_with_facts"


def _quote_anchor_id_from_ref(ref: Any) -> str | None:
    anchor = _clean(ref)
    if not anchor:
        return None
    return anchor.rsplit("#", 1)[-1]


def _dialogue_profile_from_mandatory_beats(step: dict[str, Any]) -> dict[str, Any]:
    rows = _npc_speak_rows(step)
    if not rows:
        return {}
    beats: list[dict[str, Any]] = []
    previous_forced_actor = ""
    first_intent = ""
    for row in rows:
        npc_speak = _as_dict(row.get("npc_speak"))
        actor_ref = _clean(npc_speak.get("actor"))
        intent = _clean(npc_speak.get("intent"))
        if not first_intent and intent:
            first_intent = intent
        instruction = _as_dict(row.get("instruction"))
        chain_src = _as_dict(npc_speak.get("forces_response_from")) or _as_dict(
            instruction.get("forces_response_from")
        )
        chain = {}
        if chain_src:
            chain = {
                "target_actor_ref": chain_src.get("actor"),
                "target_intent": chain_src.get("intent"),
                "required_state_change": chain_src.get("required_state_change"),
                "max_delay_seconds": chain_src.get("max_delay_seconds") or 6,
            }
        beats.append(
            {
                "beat_pattern_ref": _beat_pattern_ref_for_npc_speak(npc_speak),
                "actor_ref": actor_ref,
                "intent": intent or "content_guided_dialogue",
                "quote_anchor_id": _quote_anchor_id_from_ref(npc_speak.get("quote_anchor")),
                "quote_use": "exact_anchor_allowed"
                if _clean(npc_speak.get("paraphrase_policy")) == "short_anchor_quote_allowed"
                else "paraphrase_or_transform",
                "paraphrase_policy": npc_speak.get("paraphrase_policy") or "structural_paraphrase_required",
                "minimum_visible": npc_speak.get("minimum_visible"),
                "required_facts": _required_fact_tokens(npc_speak.get("required_facts")),
                "forced_by_previous_beat": bool(actor_ref and actor_ref == previous_forced_actor),
                "forces_response_chain": chain,
                "required": True,
            }
        )


        previous_forced_actor = _clean(chain.get("target_actor_ref"))
    return {
        "speech_required": True,
        "speech_function": first_intent or "content_guided_dialogue",
        "line_shape": "canonical_mandatory_beats",
        "beats": beats,
    }


def _present_refs_from_step(step: dict[str, Any]) -> list[str]:
    present = _as_dict(step.get("present"))
    refs = _as_list(present.get("named_characters"))
    if not refs:
        refs = _as_list(_as_dict(_as_dict(step.get("path_point")).get("present")).get("named_characters"))
    return _unique_clean(refs)


def _present_actor_ids_from_step(step: dict[str, Any]) -> list[str]:
    present = _as_dict(step.get("present"))
    actor_ids = _as_list(present.get("actor_ids"))
    if not actor_ids:
        actor_ids = _as_list(_as_dict(_as_dict(step.get("path_point")).get("present")).get("actor_ids"))
    return _unique_clean(actor_ids)


def _action_beats_from_step(step: dict[str, Any]) -> list[str]:
    beats = _as_list(_as_dict(step.get("path_point")).get("action_beats"))
    if beats:
        return _unique_clean(beats)
    values: list[str] = []
    for beat in _mandatory_beats(step):
        beat_id = _clean(beat.get("id"))
        instruction = _beat_instruction(beat)
        npc_intent = _clean(_as_dict(instruction.get("npc_speak")).get("intent"))
        if beat_id and npc_intent:
            values.append(f"{beat_id}:{npc_intent}")
        elif beat_id:
            values.append(beat_id)
    return _unique_clean(values)


def _player_windows_from_step(step: dict[str, Any]) -> list[str]:
    windows = _as_list(_as_dict(step.get("path_point")).get("player_windows"))
    if windows:
        return _unique_clean(windows)
    allowed: list[str] = []
    for window in _as_list(step.get("player_intrusion_windows")):
        if isinstance(window, dict):
            allowed.extend(_as_list(window.get("allowed")))
    return _unique_clean(allowed)


def _narrator_tasks_from_step(step: dict[str, Any]) -> list[str]:
    tasks = _as_list(_as_dict(step.get("path_point")).get("narrator_tasks"))
    if tasks:
        return _unique_clean(tasks)
    out: list[str] = []
    for beat in _mandatory_beats(step):
        instruction = _beat_instruction(beat)
        out.extend(_as_list(instruction.get("narrator_perception_only")))
    return _unique_clean(out)


def _must_not_from_step(step: dict[str, Any]) -> list[str]:
    values = _as_list(_as_dict(step.get("path_point")).get("must_not"))
    for row in _npc_speak_rows(step):
        values.extend(_as_list(_as_dict(row.get("npc_speak")).get("forbidden_drift")))
    for window in _as_list(step.get("player_intrusion_windows")):
        if isinstance(window, dict):
            values.extend(_as_list(window.get("forbidden")))
    return _unique_clean(values)


def _content_frame(
    *,
    canonical_path: dict[str, Any] | None,
    scene_graph: dict[str, Any] | None,
    locations: dict[str, Any] | None,
    objects: dict[str, Any] | None,
    character_documents: dict[str, Any] | None,
    content_access_policy: dict[str, Any] | None,
    scene_assessment: dict[str, Any] | None,
    environment_state: dict[str, Any] | None,
    current_scene_id: str,
    narrative_scene_function: str,
    selection_source: str,
) -> dict[str, Any]:
    step, node = _active_canonical_step(
        canonical_path=canonical_path,
        scene_graph=scene_graph,
        scene_assessment=scene_assessment,
        current_scene_id=current_scene_id,
        narrative_scene_function=narrative_scene_function,
        selection_source=selection_source,
    )
    scene = _as_dict(scene_assessment)
    env = _as_dict(environment_state)
    loc_ref = _as_dict(step.get("location_ref"))
    location_id = _clean(
        scene.get("location_id")
        or node.get("location_id")
        or loc_ref.get("location_id")
        or env.get("current_room_id")
        or env.get("current_area")
    )
    object_refs = [dict(row) for row in _as_list(step.get("object_refs")) if isinstance(row, dict)]
    object_ids = [_clean(row.get("object_id")) for row in object_refs if _clean(row.get("object_id"))]
    if not object_ids and location_id:
        loc = _location_rows(locations).get(location_id, {})
        object_ids = [_clean(item) for item in _as_list(loc.get("inventory_object_ids")) if _clean(item)]
    actor_id_by_ref = _actor_id_index(character_documents)
    present_refs = _present_refs_from_step(step)
    explicit_present_actor_ids = _present_actor_ids_from_step(step)
    present_actor_ids = explicit_present_actor_ids or [
        actor_id
        for actor_id in (_resolve_actor_id(ref, actor_id_by_ref) for ref in present_refs)
        if actor_id
    ]
    target_ids = [location_id, *object_ids]

    return {
        "canonical_path_step_id": step.get("id"),
        "canonical_path_sequence": step.get("sequence"),
        "canonical_path_mode": step.get("mode"),
        "canonical_path_name": step.get("name"),
        "scene_node_id": node.get("id") or None,
        "phase_id": node.get("phase_id") or scene.get("phase_id") or None,
        "location_id": location_id or None,
        "location_source_ref": loc_ref.get("source"),
        "object_focus_ids": object_ids,
        "object_refs": object_refs,
        "quote_anchor_refs": _quote_anchor_refs_from_step(step),
        "dialogue_profile": _as_dict(step.get("dialogue_profile")) or _dialogue_profile_from_mandatory_beats(step),
        "theme_threads": _unique_clean(_as_list(step.get("theme_threads"))),
        "action_beats": _action_beats_from_step(step),
        "player_windows": _player_windows_from_step(step),
        "narrator_tasks": _narrator_tasks_from_step(step),
        "must_not": _must_not_from_step(step),
        "present_actor_refs": present_refs,
        "present_actor_ids": present_actor_ids,
        "next_step_id": _as_dict(step.get("next_point")).get("step_id"),
        "next_transition": _as_dict(step.get("next_point")).get("transition") or _as_dict(step.get("next_point")).get("handoff"),
        "carry_forward_markers": _unique_clean(_as_list(_as_dict(step.get("next_point")).get("carry_forward"))),
        "access_decisions": _access_decisions_for_targets(


            content_access_policy=content_access_policy,
            target_ids=target_ids,
        ),
        "authority_refs": {
            "canonical_path": "canonical_path/",
            "locations": "locations/",
            "objects": "objects/",
            "access_policy": "knowledge/content_access_policy.yaml",
        },
    }


def _speech_cues(content_frame: dict[str, Any]) -> list[str]:
    cues: list[str] = []
    for key in ("action_beats", "player_windows", "narrator_tasks", "theme_threads"):
        for value in _as_list(content_frame.get(key)):
            text = _clean(value).lower()
            if any(
                token in text
                for token in (
                    "ask",
                    "answer",
                    "challenge",
                    "word",
                    "statement",
                    "spoken",
                    "quote",
                    "small_talk",
                    "courtesy",
                    "community",
                    "compliment",
                    "refuse",
                    "accept",
                    "say",
                )
            ):
                _append_unique(cues, f"{key}:{value}")
    if content_frame.get("quote_anchor_refs"):
        _append_unique(cues, "quote_anchor_refs_present")
    return cues[:8]


def _speech_profile_for_frame(
    *,
    content_frame: dict[str, Any],
    narrative_scene_function: str,
    selected_responder_set: list[dict[str, Any]] | None,
    actor_lane_context: dict[str, Any] | None,
    opening_quote_anchors: dict[str, Any] | None,
) -> dict[str, Any]:
    profile = _as_dict(content_frame.get("dialogue_profile"))
    mode = _clean(content_frame.get("canonical_path_mode")).lower()
    cues = _speech_cues(content_frame)
    quote_refs = _as_list(content_frame.get("quote_anchor_refs"))
    forbidden = _ai_forbidden_actor_ids(actor_lane_context)
    present = [
        actor_id
        for actor_id in _as_list(content_frame.get("present_actor_ids"))
        if _clean(actor_id) and _clean(actor_id) not in forbidden
    ]
    responder_ids = [
        _clean(row.get("actor_id") or row.get("responder_id"))
        for row in selected_responder_set or []
        if isinstance(row, dict) and _clean(row.get("actor_id") or row.get("responder_id"))
    ]
    speech_required = bool(profile.get("speech_required"))
    if not speech_required:
        speech_required = (
            any(token in mode for token in ("procedure", "pressure", "civility", "intrusion"))
            or (bool(quote_refs) and bool(cues) and narrative_scene_function not in {"narrate_sensory_focus", "contain_out_of_scope"})
        )
    speech_recommended = speech_required or bool(quote_refs and cues)


    quote_policy = _quote_anchor_policy(opening_quote_anchors)
    return {
        "speech_required": speech_required,
        "speech_recommended": speech_recommended,
        "speech_function": profile.get("speech_function") or (
            "content_guided_dialogue" if speech_recommended else "none"
        ),
        "npc_speech_allowed": bool(present or responder_ids),
        "player_speech_allowed": bool(content_frame.get("player_windows")),
        "player_speech_must_not_be_forced": True,
        "line_shape": profile.get("line_shape") or ("short_content_exchange" if speech_recommended else "none"),
        "quote_policy": (
            "moment_locked_short_anchor"
            if quote_refs and speech_recommended
            else "default_paraphrase_or_transform"
        ),
        "speaker_candidates": _unique_clean([*responder_ids, *present]),
        "suppressed_actor_ids": sorted(forbidden),
        "speech_cues": cues,
        "quote_anchor_refs": _unique_clean(quote_refs),
        "max_exact_quote_words": quote_policy["max_words_per_runtime_quote"],
        "constraints": [
            "do_not_force_player_speech",
            "do_not_use_npc_speech_as_world_exposition",
            "do_not_replace_required_narration_with_dialogue",
            "short_anchor_only_when_exact_quote_is_used",
        ],
    }
