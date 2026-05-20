"""Bounded semantic scene planner for the GoC runtime.

The existing director still owns the first-pass deterministic scene-function
and responder choice. This module turns that selection plus semantic/social
records into a richer, inspectable short-horizon plan. It remains advisory
until the validation and commit seams authorize any runtime truth.
"""

from __future__ import annotations

from typing import Any, Final

from ai_stack.director.capabilities_manager.director_capability_manager import (
    DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION,
    audit_director_capability_paths,
)
from ai_stack.capabilities.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_OBJECT_STATE_DESCRIBE,
    NARRATOR_OPENING_EVENT_REALIZE,
    NARRATOR_PERCEPTION_RESULT_DESCRIBE,
    NARRATOR_SCENE_CONTEXT_ESTABLISH,
)
from ai_stack.goc_frozen_vocab import CONTINUITY_CLASSES, TRANSITION_PATTERNS

SEMANTIC_SCENE_PLANNER_VERSION: Final[str] = "goc_semantic_scene_planner_v1"

_CONTINUITY_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "situational_pressure",
    "escalate_conflict": "situational_pressure",
    "probe_motive": "situational_pressure",
    "repair_or_stabilize": "repair_attempt",
    "withhold_or_evade": "silent_carry",
    "reveal_surface": "revealed_fact",
    "redirect_blame": "blame_pressure",
    "scene_pivot": "alliance_shift",
}

_PRESSURE_AXIS_BY_MOVE_TYPE: Final[dict[str, str]] = {
    "off_scope_containment": "boundary",
    "silence_withdrawal": "withholding",
    "repair_attempt": "repair",
    "direct_accusation": "accountability",
    "indirect_provocation": "provocation",
    "evasive_deflection": "deflection",
    "humiliating_exposure": "dignity",
    "alliance_reposition": "alliance",
    "probe_inquiry": "motive",
    "escalation_threat": "rupture",
    "reveal_surface": "exposure",
    "establish_situational_pressure": "situational",
    "competing_repair_and_reveal": "repair_vs_exposure",
}

_PRESSURE_AXIS_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "situational",
    "escalate_conflict": "rupture",
    "probe_motive": "motive",
    "repair_or_stabilize": "repair",
    "withhold_or_evade": "withholding",
    "reveal_surface": "exposure",
    "redirect_blame": "accountability",
    "scene_pivot": "alliance",
}

_BEAT_INTENTS_BY_SCENE_FUNCTION: Final[dict[str, tuple[str, ...]]] = {
    "establish_pressure": ("anchor_scene_pressure", "invite_specific_response"),
    "escalate_conflict": (
        "raise_pressure",
        "force_visible_reaction",
        "leave_tension_unresolved",
    ),
    "probe_motive": ("press_for_motive", "preserve_ambiguity"),
    "repair_or_stabilize": ("test_repair_sincerity", "allow_partial_release"),
    "withhold_or_evade": ("mark_withheld_response", "preserve_negative_space"),
    "reveal_surface": ("surface_allowed_information", "register_social_cost"),
    "redirect_blame": ("shift_accountability", "carry_blame_forward"),
    "scene_pivot": ("change_pressure_axis", "preserve_scene_boundary"),
}

_NARRATIVE_SCENE_FUNCTION_BY_MOVE_TYPE: Final[dict[str, str]] = {
    "off_scope_containment": "contain_out_of_scope",
    "silence_withdrawal": "preserve_negative_space",
    "repair_attempt": "test_repair_sincerity",
    "direct_accusation": "force_accountability",
    "indirect_provocation": "raise_pressure",
    "evasive_deflection": "narrate_evasion",
    "humiliating_exposure": "force_accountability",
    "alliance_reposition": "shift_social_arrangement",
    "probe_inquiry": "probe_motive",
    "escalation_threat": "raise_pressure",
    "reveal_surface": "surface_information",
    "establish_situational_pressure": "establish_scene_pressure",
    "competing_repair_and_reveal": "test_repair_sincerity",
}

_NARRATIVE_SCENE_FUNCTION_BY_SCENE_FUNCTION: Final[dict[str, str]] = {
    "establish_pressure": "establish_scene_pressure",
    "escalate_conflict": "raise_pressure",
    "probe_motive": "probe_motive",
    "repair_or_stabilize": "test_repair_sincerity",
    "withhold_or_evade": "narrate_evasion",
    "reveal_surface": "surface_information",
    "redirect_blame": "force_accountability",
    "scene_pivot": "shift_social_arrangement",
}

_PRESSURE_FUNCTION_BY_AXIS: Final[dict[str, str]] = {
    "accountability": "force_accountability",
    "alliance": "test_alliance_position",
    "boundary": "contain_boundary",
    "deflection": "mark_deflection",
    "dignity": "register_dignity_cost",
    "exposure": "force_disclosure_pressure",
    "motive": "probe_motive",
    "provocation": "raise_provocation",
    "repair": "test_repair_sincerity",
    "repair_vs_exposure": "hold_repair_exposure_tension",
    "rupture": "escalate_rupture",
    "situational": "seed_initial_pressure",
    "withholding": "preserve_withholding",
}

_REALIZATION_MODE_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "mixed_narration_and_npc_action",
    "contain_out_of_scope": "narration",
    "establish_scene_anchor": "narration",
    "establish_scene_pressure": "mixed_narration_and_npc_action",
    "force_accountability": "npc_dialogue_and_visible_reaction",
    "narrate_consequence": "narration",
    "narrate_evasion": "npc_action_or_narration",
    "narrate_sensory_focus": "narration",
    "preserve_negative_space": "silence_and_visible_reaction",
    "probe_motive": "npc_dialogue_and_visible_reaction",
    "raise_pressure": "npc_dialogue_and_visible_reaction",
    "shift_social_arrangement": "mixed_narration_and_npc_action",
    "surface_information": "npc_dialogue_or_visible_evidence",
    "test_repair_sincerity": "npc_dialogue_and_visible_reaction",
}

_TARGET_FUNCTION_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "create_playable_setup",
    "contain_out_of_scope": "return_to_scene_scope",
    "establish_scene_anchor": "anchor_room_and_cast",
    "establish_scene_pressure": "seed_initial_pressure",
    "force_accountability": "force_reaction",
    "narrate_consequence": "render_action_consequence",
    "narrate_evasion": "make_evasion_visible",
    "narrate_sensory_focus": "render_perceptual_detail",
    "preserve_negative_space": "hold_silence_and_invite_visibility",
    "probe_motive": "draw_out_motive",
    "raise_pressure": "intensify_visible_conflict",
    "shift_social_arrangement": "reposition_relationship_axis",
    "surface_information": "surface_allowed_information",
    "test_repair_sincerity": "test_repair_sincerity",
}

_TARGET_EFFECT_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "playable_setup_ready",
    "contain_out_of_scope": "scene_scope_restored",
    "establish_scene_anchor": "scene_anchor_visible",
    "establish_scene_pressure": "initial_pressure_visible",
    "force_accountability": "accountability_reaction_visible",
    "narrate_consequence": "player_action_consequence_visible",
    "narrate_evasion": "evasion_cost_visible",
    "narrate_sensory_focus": "perceptual_detail_available",
    "preserve_negative_space": "withholding_visible_without_forced_speech",
    "probe_motive": "motive_pressure_visible",
    "raise_pressure": "conflict_pressure_raised",
    "shift_social_arrangement": "relationship_axis_repositioned",
    "surface_information": "allowed_information_surfaced",
    "test_repair_sincerity": "repair_offer_tested",
}

_TARGET_KIND_BY_NARRATIVE_FUNCTION: Final[dict[str, str]] = {
    "arrange_scene": "setup",
    "contain_out_of_scope": "scene",
    "establish_scene_anchor": "room",
    "establish_scene_pressure": "setup",
    "narrate_consequence": "player_affordance",
    "narrate_sensory_focus": "room",
    "shift_social_arrangement": "relationship",
    "surface_information": "information",
}

_BEAT_TEMPLATES_BY_NARRATIVE_FUNCTION: Final[
    dict[str, tuple[tuple[str, str, str, str], ...]]
] = {
    "arrange_scene": (
        ("setup_beat", "establish_arrangement", "stage_room_and_present_cast", "director"),
        ("npc_action_beat", "force_initial_npc_position", "stage_npc_presence", "npc"),
        ("player_handover_beat", "offer_playable_opening", "handover_control_to_player", "director"),
    ),
    "contain_out_of_scope": (
        ("narration_beat", "mark_boundary", "preserve_scene_scope", "narrator"),
        ("player_handover_beat", "return_to_scene", "handover_control_to_player", "director"),
    ),
    "establish_scene_anchor": (
        ("environment_beat", "anchor_room", "anchor_scene_space", "narrator"),
        ("setup_beat", "make_cast_position_visible", "stage_present_cast", "director"),
        ("player_handover_beat", "offer_playable_opening", "handover_control_to_player", "director"),
    ),
    "establish_scene_pressure": (
        ("setup_beat", "seed_initial_pressure", "anchor_scene_pressure", "director"),
        ("npc_action_beat", "force_visible_reaction", "invite_specific_response", "npc"),
    ),
    "force_accountability": (
        ("npc_dialogue_beat", "force_accountability", "shift_accountability", "npc"),
        ("relationship_shift_beat", "register_social_cost", "carry_blame_forward", "director"),
    ),
    "narrate_consequence": (
        ("narration_beat", "render_action_consequence", "show_consequence", "narrator"),
        ("player_handover_beat", "return_control", "handover_control_to_player", "director"),
    ),
    "narrate_evasion": (
        ("npc_action_beat", "mark_evasion", "mark_withheld_response", "npc"),
        ("silence_beat", "preserve_gap", "preserve_negative_space", "director"),
    ),
    "narrate_sensory_focus": (
        ("environment_beat", "focus_sensory_detail", "narrate_sensory_focus", "narrator"),
        ("information_beat", "surface_available_cue", "surface_allowed_information", "narrator"),
    ),
    "preserve_negative_space": (
        ("silence_beat", "hold_silence", "mark_withheld_response", "director"),
        ("npc_action_beat", "force_visible_reaction_without_speech", "preserve_negative_space", "npc"),
    ),
    "probe_motive": (
        ("npc_dialogue_beat", "probe_motive", "press_for_motive", "npc"),
        ("silence_beat", "preserve_ambiguity", "preserve_ambiguity", "director"),
    ),
    "raise_pressure": (
        ("npc_dialogue_beat", "raise_pressure", "raise_pressure", "npc"),
        ("npc_action_beat", "force_visible_reaction", "force_visible_reaction", "npc"),
        ("transition_beat", "leave_tension_unresolved", "leave_tension_unresolved", "director"),
    ),
    "shift_social_arrangement": (
        ("setup_beat", "reposition_relationship_axis", "change_pressure_axis", "director"),
        ("interruption_beat", "force_npc_interruption", "stage_interruption", "npc"),
        ("transition_beat", "preserve_scene_boundary", "preserve_scene_boundary", "director"),
    ),
    "surface_information": (
        ("information_beat", "surface_allowed_information", "surface_allowed_information", "npc"),
        ("relationship_shift_beat", "register_social_cost", "register_social_cost", "director"),
    ),
    "test_repair_sincerity": (
        ("npc_dialogue_beat", "test_repair_sincerity", "test_repair_sincerity", "npc"),
        ("recovery_beat", "allow_partial_release", "allow_partial_release", "director"),
    ),
}

_HARD_TRANSITION_SCENE_FUNCTIONS: Final[frozenset[str]] = frozenset(
    {"escalate_conflict", "redirect_blame", "reveal_surface"}
)

def _clean(value: Any) -> str:
    return str(value or "").strip()


def _append_unique(out: list[str], value: str) -> None:
    text = _clean(value)
    if text and text not in out:
        out.append(text)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _unique_clean(values: list[Any] | tuple[Any, ...]) -> list[str]:
    out: list[str] = []
    for value in values:
        _append_unique(out, str(value))
    return out


def _actor_id_index(character_documents: dict[str, Any] | None) -> dict[str, str]:
    out: dict[str, str] = {}
    for key, row in _as_dict(character_documents).items():
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id") or row.get("runtime_actor_id"))
        if not actor_id:
            continue
        for ref in (
            key,
            row.get("id"),
            row.get("canonical_id"),
            row.get("character_id"),
            actor_id,
            row.get("runtime_actor_id"),
        ):
            cleaned = _clean(ref)
            if cleaned:
                out.setdefault(cleaned, actor_id)
    return out


def _resolve_actor_id(actor_ref_or_id: Any, actor_id_by_ref: dict[str, str]) -> str:
    value = _clean(actor_ref_or_id)
    if not value:
        return ""
    return actor_id_by_ref.get(value, value if value in actor_id_by_ref.values() else "")


def _ai_forbidden_actor_ids(actor_lane_context: dict[str, Any] | None) -> set[str]:
    ctx = _as_dict(actor_lane_context)
    forbidden = {_clean(ctx.get("human_actor_id"))}
    for actor_id in _as_list(ctx.get("ai_forbidden_actor_ids")):
        forbidden.add(_clean(actor_id))
    return {actor_id for actor_id in forbidden if actor_id}


def _step_rows(canonical_path: dict[str, Any] | None) -> list[dict[str, Any]]:
    path = _as_dict(canonical_path)
    return [dict(row) for row in _as_list(path.get("steps")) if isinstance(row, dict)]


def _step_by_id(canonical_path: dict[str, Any] | None, step_id: str) -> dict[str, Any]:
    sid = _clean(step_id)
    if not sid:
        return {}
    for step in _step_rows(canonical_path):
        if _clean(step.get("id")) == sid:
            return step
    return {}


def _scene_nodes(scene_graph: dict[str, Any] | None) -> list[dict[str, Any]]:
    graph = _as_dict(scene_graph)
    return [dict(row) for row in _as_list(graph.get("nodes")) if isinstance(row, dict)]


def _scene_node_by_id(scene_graph: dict[str, Any] | None, node_id: str) -> dict[str, Any]:
    nid = _clean(node_id)
    if not nid:
        return {}
    for node in _scene_nodes(scene_graph):
        if _clean(node.get("id")) == nid:
            return node
    return {}


def _location_rows(locations: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    locs = _as_dict(locations)
    places = locs.get("places")
    if isinstance(locs.get("locations"), dict):
        places = locs["locations"].get("places")
    out: dict[str, dict[str, Any]] = {}
    for row in _as_list(places):
        if not isinstance(row, dict):
            continue
        loc_id = _clean(row.get("id"))
        if loc_id:
            out[loc_id] = dict(row)
    return out


def _object_rows(objects: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    objs = _as_dict(objects)
    docs = objs.get("object_documents")
    if isinstance(objs.get("objects"), dict):
        docs = objs["objects"].get("object_documents")
    if isinstance(docs, dict):
        return {str(k): dict(v) for k, v in docs.items() if isinstance(v, dict)}
    return {}


def _access_rows(content_access_policy: dict[str, Any] | None) -> list[dict[str, Any]]:
    policy = _as_dict(content_access_policy)
    rows: list[dict[str, Any]] = []
    for key in ("blocked_entities", "gated_entities"):
        for row in _as_list(policy.get(key)):
            if isinstance(row, dict):
                rows.append({**row, "policy_bucket": key})
    return rows


def _access_decisions_for_targets(
    *,
    content_access_policy: dict[str, Any] | None,
    target_ids: list[str],
) -> list[dict[str, Any]]:
    targets = {target_id for target_id in target_ids if target_id}
    out: list[dict[str, Any]] = []
    for row in _access_rows(content_access_policy):
        if _clean(row.get("target_id")) in targets:
            out.append(
                {
                    "id": row.get("id"),
                    "scope": row.get("scope"),
                    "target_id": row.get("target_id"),
                    "decision": row.get("decision"),
                    "requirements": list(row.get("requirements") or [])
                    if isinstance(row.get("requirements"), list)
                    else [],
                    "reason_ref": row.get("reason_ref"),
                    "policy_bucket": row.get("policy_bucket"),
                }
            )
    return out


def _active_canonical_step(
    *,
    canonical_path: dict[str, Any] | None,
    scene_graph: dict[str, Any] | None,
    scene_assessment: dict[str, Any] | None,
    current_scene_id: str,
    narrative_scene_function: str,
    selection_source: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    scene = _as_dict(scene_assessment)
    for key in (
        "canonical_path_step_id",
        "active_canonical_path_step_id",
        "current_canonical_path_step_id",
    ):
        step = _step_by_id(canonical_path, _clean(scene.get(key)))
        if step:
            return step, {}
    for key in ("canonical_path_step_ids", "active_canonical_path_step_ids"):
        for step_id in _as_list(scene.get(key)):
            step = _step_by_id(canonical_path, _clean(step_id))
            if step:
                return step, {}

    scene_id = _clean(scene.get("scene_node_id") or scene.get("current_scene_node_id") or current_scene_id)
    node = _scene_node_by_id(scene_graph, scene_id)
    if node:
        step = _step_by_id(canonical_path, _clean(node.get("canonical_path_step_id")))
        if step:
            return step, node
        for step_id in _as_list(node.get("canonical_path_step_ids")):
            step = _step_by_id(canonical_path, _clean(step_id))
            if step:
                return step, node

    step = _step_by_id(canonical_path, scene_id)
    if step:
        return step, node

    if "opening" in _clean(selection_source).lower() or _clean(scene.get("scene_phase")).lower() == "opening":
        path = _as_dict(canonical_path)
        first_playable = _clean(
            _as_dict(_as_dict(path.get("paths")).get("opening")).get("first_playable_step_id")
        )
        if narrative_scene_function == "arrange_scene":
            first_playable = "opening_007_living_room_arrangement"
        step = _step_by_id(canonical_path, first_playable)
        if step:
            return step, node

    return {}, node


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


def _add_capability_step(
    steps: list[dict[str, Any]],
    *,
    capability: str,
    mode: str,
    reason: str,
    source: str,
    beat_orders: list[int] | None = None,
) -> None:
    if not capability:
        return
    for step in steps:
        if step.get("capability") == capability:
            existing_mode = _clean(step.get("mode"))
            if existing_mode != "required" and mode == "required":
                step["mode"] = "required"
            for order in beat_orders or []:
                if order not in step["activates_beat_orders"]:
                    step["activates_beat_orders"].append(order)
            _append_unique(step["reason_codes"], reason)
            return
    steps.append(
        {
            "capability": capability,
            "mode": mode,
            "reason_codes": [reason],
            "source": source,
            "activates_beat_orders": list(beat_orders or []),
        }
    )


def _director_capability_manager_plan(
    *,
    narrative_scene_function: str,
    realization_mode: str,
    content_frame: dict[str, Any],
    speech_policy: dict[str, Any],
    dialogue_plan: list[dict[str, Any]],
    dramatic_beats: list[dict[str, Any]],
    actor_directives: list[dict[str, Any]],
    turn_input_class: str,
) -> dict[str, Any]:
    steps: list[dict[str, Any]] = []
    beat_orders_by_kind: dict[str, list[int]] = {}
    for beat in dramatic_beats:
        if not isinstance(beat, dict):
            continue
        kind = _clean(beat.get("beat_kind"))
        try:
            order = int(beat.get("beat_order") or 0)
        except (TypeError, ValueError):
            order = 0
        if kind and order:
            beat_orders_by_kind.setdefault(kind, []).append(order)

    required_narration = narrative_scene_function in {
        "arrange_scene",
        "contain_out_of_scope",
        "establish_scene_anchor",
        "establish_scene_pressure",
        "narrate_consequence",
        "narrate_sensory_focus",
        "surface_information",
    }
    if narrative_scene_function in {"arrange_scene", "establish_scene_anchor", "establish_scene_pressure"}:
        _add_capability_step(
            steps,
            capability=NARRATOR_SCENE_CONTEXT_ESTABLISH,
            mode="required",
            reason=f"narrative_scene_function:{narrative_scene_function}",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("setup_beat") or beat_orders_by_kind.get("environment_beat"),
        )
    if _clean(turn_input_class).lower() == "opening" or "opening" in _clean(content_frame.get("canonical_path_step_id")):
        _add_capability_step(
            steps,
            capability=NARRATOR_OPENING_EVENT_REALIZE,
            mode="required" if narrative_scene_function == "arrange_scene" else "optional",
            reason="canonical_opening_path_active",
            source="canonical_path",
            beat_orders=beat_orders_by_kind.get("setup_beat"),
        )
    if narrative_scene_function == "narrate_sensory_focus":
        _add_capability_step(
            steps,
            capability=NARRATOR_PERCEPTION_RESULT_DESCRIBE,
            mode="required",
            reason="narrative_scene_function:narrate_sensory_focus",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("environment_beat"),
        )
    elif content_frame.get("object_focus_ids") and narrative_scene_function in {
        "arrange_scene",
        "surface_information",
        "narrate_consequence",
    }:
        _add_capability_step(
            steps,
            capability=NARRATOR_OBJECT_STATE_DESCRIBE,
            mode="required" if narrative_scene_function == "surface_information" else "optional",
            reason="content_frame:object_focus",
            source="content_frame",
            beat_orders=beat_orders_by_kind.get("information_beat") or beat_orders_by_kind.get("setup_beat"),
        )
    elif required_narration:
        _add_capability_step(
            steps,
            capability=NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
            mode="required" if narrative_scene_function in {"contain_out_of_scope", "narrate_consequence"} else "optional",
            reason=f"narrative_scene_function:{narrative_scene_function}",
            source="scene_director",
            beat_orders=beat_orders_by_kind.get("narration_beat"),
        )

    if dialogue_plan:
        _add_capability_step(
            steps,
            capability=NPC_SOCIAL_REACTION_OPTIONAL,
            mode="required" if speech_policy.get("speech_required") else "optional",
            reason=f"speech_function:{speech_policy.get('speech_function')}",
            source="speech_policy",
            beat_orders=beat_orders_by_kind.get("npc_speak_beat")
            or beat_orders_by_kind.get("npc_dialogue_beat"),
        )
        if speech_policy.get("speech_function") in {"wording_dispute", "statement_procedure"}:
            _add_capability_step(
                steps,
                capability=NPC_DIRECT_ANSWER_ALLOWED,
                mode="optional",
                reason=f"speech_function:{speech_policy.get('speech_function')}",
                source="speech_policy",
                beat_orders=beat_orders_by_kind.get("npc_speak_beat"),
            )

    if any(
        _clean(row.get("directive")) in {
            "stage_npc_presence",
            "force_npc_reaction",
            "force_secondary_reaction",
            "force_npc_interruption",
            "hold_silence",
        }
        for row in actor_directives
        if isinstance(row, dict)
    ):
        _add_capability_step(
            steps,
            capability=NPC_ACTION_GESTURE_OPTIONAL,
            mode="optional",
            reason="actor_directives:visible_npc_action",
            source="actor_directives",
            beat_orders=beat_orders_by_kind.get("npc_action_beat") or beat_orders_by_kind.get("interruption_beat"),
        )

    required = [row["capability"] for row in steps if row.get("mode") == "required"]
    optional = [row["capability"] for row in steps if row.get("mode") != "required"]
    selected = _unique_clean([*required, *optional])
    suppressed: list[str] = []
    if not dialogue_plan and not speech_policy.get("speech_recommended"):
        suppressed.append(NPC_DIRECT_ANSWER_ALLOWED)
    if narrative_scene_function in {"contain_out_of_scope", "narrate_sensory_focus"} and not dialogue_plan:
        suppressed.append(NPC_SOCIAL_REACTION_OPTIONAL)
    dispatch_audit = audit_director_capability_paths(
        selected_capabilities=selected,
        capability_steps=steps,
        suppressed_capabilities=suppressed,
    )
    executable = list(dispatch_audit.get("executable_capabilities") or [])
    required = [cap for cap in required if cap in executable]
    optional = [cap for cap in optional if cap in executable]

    return {
        "schema_version": DIRECTOR_CAPABILITY_MANAGER_PLAN_SCHEMA_VERSION,
        "manager_contract": "dramatic_capability_manager",
        "selection_source": "semantic_scene_director",
        "execution_strategy": "selective_capability_gate",
        "run_only_selected_capabilities": True,
        "dispatch_status": dispatch_audit.get("status"),
        "decision_basis": {
            "narrative_scene_function": narrative_scene_function,
            "realization_mode": realization_mode,
            "canonical_path_step_id": content_frame.get("canonical_path_step_id"),
            "canonical_path_mode": content_frame.get("canonical_path_mode"),
            "location_id": content_frame.get("location_id"),
            "object_focus_ids": list(content_frame.get("object_focus_ids") or []),
            "speech_required": bool(speech_policy.get("speech_required")),
            "speech_recommended": bool(speech_policy.get("speech_recommended")),
            "speech_function": speech_policy.get("speech_function"),
            "dialogue_beat_count": len(dialogue_plan),
            "quote_anchor_refs": list(content_frame.get("quote_anchor_refs") or []),
        },
        "selected_capabilities": executable,
        "required_capabilities": required,
        "optional_capabilities": optional,
        "suppressed_capabilities": _unique_clean(suppressed),
        "capability_steps": steps,
        "capability_dispatch_paths": list(dispatch_audit.get("paths") or []),
        "capability_dispatch_audit": dispatch_audit,
        "dispatch_queue": list(dispatch_audit.get("dispatch_queue") or []),
        "requested_capabilities_before_audit": selected,
        "requested_visible_functions": executable,
        "realization_mode": realization_mode,
        "tree_pruning": {
            "skip_unselected_runtime_branches": True,
            "recursive_dispatch_allowed": False,
            "queue_expansion_allowed": False,
            "paths_checked_individually": True,
            "reason": "scene_director_selected_minimal_visible_capability_set",
        },
    }


def _list_continuity_classes(prior_continuity_impacts: list[dict[str, Any]] | None) -> list[str]:
    out: list[str] = []
    for item in prior_continuity_impacts or []:
        if not isinstance(item, dict):
            continue
        cls = _clean(item.get("class") or item.get("continuity_class"))
        if cls in CONTINUITY_CLASSES and cls not in out:
            out.append(cls)
    return out


def _primary_responder_id(selected_responder_set: list[dict[str, Any]] | None) -> str:
    for row in selected_responder_set or []:
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id") or row.get("responder_id"))
        if actor_id:
            return actor_id
    return ""


def _matching_character_mind(
    *,
    character_mind_records: list[dict[str, Any]] | None,
    actor_id: str,
) -> dict[str, Any]:
    for row in character_mind_records or []:
        if not isinstance(row, dict):
            continue
        if _clean(row.get("runtime_actor_id") or row.get("character_key")) == actor_id:
            return row
    return {}


def _semantic_subtext(semantic_move_record: dict[str, Any] | None) -> dict[str, Any]:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    subtext = sem.get("subtext")
    return subtext if isinstance(subtext, dict) else {}


def _continuity_for_plan(
    *,
    selected_scene_function: str,
    implied_continuity_by_function: dict[str, str] | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
) -> str:
    implied = implied_continuity_by_function if isinstance(implied_continuity_by_function, dict) else {}
    continuity = _clean(implied.get(selected_scene_function))
    if continuity in CONTINUITY_CLASSES:
        return continuity

    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    move_type = _clean(sem.get("move_type"))
    if move_type == "humiliating_exposure":
        return "dignity_injury"
    if move_type == "alliance_reposition":
        return "alliance_shift"
    if move_type == "direct_accusation":
        return "blame_pressure"
    if move_type == "reveal_surface":
        return "revealed_fact"
    if move_type == "repair_attempt":
        return "repair_attempt"
    if move_type in {"silence_withdrawal", "evasive_deflection"}:
        return "silent_carry"

    social = social_state_record if isinstance(social_state_record, dict) else {}
    prior_classes = social.get("prior_continuity_classes")
    if isinstance(prior_classes, list):
        for item in prior_classes:
            cls = _clean(item)
            if cls in CONTINUITY_CLASSES:
                return cls

    return _CONTINUITY_BY_SCENE_FUNCTION.get(selected_scene_function, "situational_pressure")


def _expected_transition_pattern(
    *,
    selected_scene_function: str,
    continuity_class: str,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    pacing_mode: str,
    prior_classes: list[str],
) -> str:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    move_type = _clean(sem.get("move_type"))
    social_risk = _clean(social.get("social_risk_band") or sem.get("scene_risk_band")).lower()

    if move_type == "off_scope_containment" or pacing_mode == "containment":
        return "diagnostics_only"
    if selected_scene_function in _HARD_TRANSITION_SCENE_FUNCTIONS:
        return "hard" if social_risk == "high" or continuity_class in prior_classes else "soft"
    if selected_scene_function == "scene_pivot":
        return "soft"
    if continuity_class in prior_classes:
        return "carry_forward"
    return "soft"


def _pressure_axis(
    *,
    selected_scene_function: str,
    semantic_move_record: dict[str, Any] | None,
) -> str:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    move_type = _clean(sem.get("move_type"))
    subtext = _semantic_subtext(sem)
    subtext_function = _clean(subtext.get("subtext_function"))
    if subtext_function in {"force_accountability", "deflect_accountability"}:
        return "accountability"
    if subtext_function in {"expose_truth", "reveal_under_repair"}:
        return "exposure"
    if subtext_function == "shift_alliance":
        return "alliance"
    if subtext_function in {"probe_motive", "test_boundary"}:
        return "motive"
    if subtext_function == "preserve_relationship":
        return "repair"
    return _PRESSURE_AXIS_BY_MOVE_TYPE.get(
        move_type,
        _PRESSURE_AXIS_BY_SCENE_FUNCTION.get(selected_scene_function, "situational"),
    )


def _pressure_target(
    *,
    selected_scene_function: str,
    selected_responder_set: list[dict[str, Any]] | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    character_mind_records: list[dict[str, Any]] | None,
    pressure_axis: str,
) -> dict[str, Any]:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    actor_id = _clean(sem.get("target_actor_hint"))
    source = "semantic_target_actor_hint" if actor_id else ""
    if not actor_id:
        actor_id = _primary_responder_id(selected_responder_set)
        source = "primary_responder" if actor_id else "scene_level"
    mind = _matching_character_mind(
        character_mind_records=character_mind_records,
        actor_id=actor_id,
    )
    reason_codes: list[str] = []
    _append_unique(reason_codes, f"scene_fn:{selected_scene_function}")
    if _clean(sem.get("move_type")):
        _append_unique(reason_codes, f"semantic_move:{sem.get('move_type')}")
    subtext = _semantic_subtext(sem)
    if _clean(subtext.get("subtext_function")):
        _append_unique(reason_codes, f"subtext_function:{subtext.get('subtext_function')}")
    if _clean(social.get("responder_asymmetry_code")):
        _append_unique(reason_codes, f"social_asymmetry:{social.get('responder_asymmetry_code')}")
    if _clean(mind.get("pressure_response_bias")):
        _append_unique(reason_codes, f"mind_bias:{mind.get('pressure_response_bias')}")

    return {
        "target_kind": "actor" if actor_id else "scene",
        "target_actor_id": actor_id or None,
        "pressure_axis": pressure_axis,
        "target_source": source,
        "social_risk_band": _clean(social.get("social_risk_band") or sem.get("scene_risk_band")) or "moderate",
        "dominant_relationship_axis_id": social.get("dominant_relationship_axis_id"),
        "character_tactical_posture": mind.get("tactical_posture"),
        "reason_codes": reason_codes,
    }


def _feature_snapshot(semantic_move_record: dict[str, Any] | None) -> dict[str, Any]:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    features = sem.get("feature_snapshot")
    return features if isinstance(features, dict) else {}


def _is_setup_context(
    *,
    selection_source: str,
    scene_assessment: dict[str, Any] | None,
) -> bool:
    source = _clean(selection_source).lower()
    if "opening" in source or "setup" in source:
        return True

    scene = scene_assessment if isinstance(scene_assessment, dict) else {}
    phase = _clean(
        scene.get("scene_phase")
        or scene.get("phase")
        or scene.get("turn_input_class")
        or scene.get("opening_phase")
    ).lower()
    if phase in {"opening", "setup", "establishing"}:
        return True
    if bool(scene.get("engine_opening_turn") or scene.get("opening_scene")):
        return True

    return False


def _narrative_scene_function(
    *,
    selected_scene_function: str,
    silence_brevity_decision: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    scene_assessment: dict[str, Any] | None,
    selection_source: str,
) -> str:
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    move_type = _clean(sem.get("move_type"))
    silence_mode = _clean(silence.get("mode")).lower()

    if _is_setup_context(
        selection_source=selection_source,
        scene_assessment=scene_assessment,
    ):
        return "arrange_scene"
    if move_type == "off_scope_containment":
        return "contain_out_of_scope"
    if move_type == "silence_withdrawal" or silence_mode in {"withheld", "silence", "silent"}:
        return "preserve_negative_space"

    features = _feature_snapshot(sem)
    if bool(features.get("player_input_kind_is_perception")):
        return "narrate_sensory_focus"
    if bool(features.get("player_input_kind_is_action")) and not bool(features.get("player_input_kind_is_speech")):
        return "narrate_consequence"

    subtext = _semantic_subtext(sem)
    subtext_function = _clean(subtext.get("subtext_function"))
    if subtext_function == "force_accountability":
        return "force_accountability"
    if subtext_function in {"expose_truth", "reveal_under_repair"}:
        return "surface_information"
    if subtext_function == "shift_alliance":
        return "shift_social_arrangement"
    if subtext_function in {"probe_motive", "test_boundary"}:
        return "probe_motive"
    if subtext_function == "preserve_relationship":
        return "test_repair_sincerity"

    if move_type:
        return _NARRATIVE_SCENE_FUNCTION_BY_MOVE_TYPE.get(
            move_type,
            _NARRATIVE_SCENE_FUNCTION_BY_SCENE_FUNCTION.get(
                selected_scene_function, "establish_scene_pressure"
            ),
        )
    return _NARRATIVE_SCENE_FUNCTION_BY_SCENE_FUNCTION.get(
        selected_scene_function, "establish_scene_pressure"
    )


def _pressure_function(*, pressure_axis: str, narrative_scene_function: str) -> str:
    if narrative_scene_function in {
        "contain_out_of_scope",
        "narrate_consequence",
        "narrate_sensory_focus",
    }:
        return "none"
    if narrative_scene_function == "arrange_scene":
        return "seed_initial_pressure"
    return _PRESSURE_FUNCTION_BY_AXIS.get(pressure_axis, "seed_initial_pressure")


def _realization_mode(narrative_scene_function: str) -> str:
    return _REALIZATION_MODE_BY_NARRATIVE_FUNCTION.get(
        narrative_scene_function, "mixed_narration_and_npc_action"
    )


def _scene_target(
    *,
    selected_scene_function: str,
    narrative_scene_function: str,
    pressure_function: str,
    pressure_target: dict[str, Any],
    social_state_record: dict[str, Any] | None,
    scene_assessment: dict[str, Any] | None,
) -> dict[str, Any]:
    social = social_state_record if isinstance(social_state_record, dict) else {}
    scene = scene_assessment if isinstance(scene_assessment, dict) else {}
    actor_id = _clean(pressure_target.get("target_actor_id"))
    relationship_axis = _clean(pressure_target.get("dominant_relationship_axis_id"))
    room_id = _clean(scene.get("current_scene_id") or scene.get("scene_id"))
    target_kind = _TARGET_KIND_BY_NARRATIVE_FUNCTION.get(narrative_scene_function)
    if not target_kind:
        target_kind = "actor" if actor_id else "scene"

    target_id: str | None = None
    if target_kind == "actor":
        target_id = actor_id or None
    elif target_kind == "relationship":
        target_id = relationship_axis or _clean(social.get("dominant_relationship_axis_id")) or None
    elif target_kind in {"room", "setup", "scene"}:
        target_id = room_id or None

    reason_codes: list[str] = []
    for value in pressure_target.get("reason_codes") or []:
        _append_unique(reason_codes, str(value))
    _append_unique(reason_codes, f"narrative_scene_function:{narrative_scene_function}")
    _append_unique(reason_codes, f"target_kind:{target_kind}")

    return {
        "target_kind": target_kind,
        "target_id": target_id,
        "target_actor_id": actor_id or None,
        "target_relationship_axis_id": relationship_axis or None,
        "target_function": _TARGET_FUNCTION_BY_NARRATIVE_FUNCTION.get(
            narrative_scene_function, "seed_initial_pressure"
        ),
        "intended_effect": _TARGET_EFFECT_BY_NARRATIVE_FUNCTION.get(
            narrative_scene_function, "scene_pressure_visible"
        ),
        "narrative_scene_function": narrative_scene_function,
        "selected_scene_function": selected_scene_function,
        "pressure_axis": pressure_target.get("pressure_axis"),
        "pressure_function": pressure_function,
        "authority_scope": "planner_advisory",
        "target_source": pressure_target.get("target_source") or "scene_level",
        "reason_codes": reason_codes,
    }


def _target_obligations(
    *,
    scene_target: dict[str, Any],
    continuity_obligation: dict[str, Any],
    narrative_scene_function: str,
) -> list[dict[str, Any]]:
    target_function = _clean(scene_target.get("target_function")) or "seed_initial_pressure"
    target_id = scene_target.get("target_id") or scene_target.get("target_actor_id")
    obligations: list[dict[str, Any]] = [
        {
            "obligation_order": 1,
            "obligation_kind": "respect_commit_authority",
            "applies_to": "scene_plan",
            "required": True,
            "success_condition": "no_runtime_truth_committed_by_planner",
            "constraints": ["planner_advisory_only", "commit_seam_remains_authoritative"],
        },
        {
            "obligation_order": 2,
            "obligation_kind": "make_target_playable",
            "applies_to": target_id,
            "required": True,
            "success_condition": f"{target_function}_available_to_player",
            "constraints": ["do_not_coerce_player_action", "offer_visible_affordance"],
        },
    ]

    if continuity_obligation.get("continuity_class"):
        obligations.append(
            {
                "obligation_order": len(obligations) + 1,
                "obligation_kind": "carry_continuity_class",
                "applies_to": continuity_obligation.get("continuity_class"),
                "required": bool(continuity_obligation.get("carry_forward_required")),
                "success_condition": "continuity_pressure_visible_or_deferred",
                "constraints": ["do_not_resolve_continuity_without_commit"],
            }
        )
    if narrative_scene_function in {"arrange_scene", "establish_scene_anchor", "establish_scene_pressure"}:
        obligations.append(
            {
                "obligation_order": len(obligations) + 1,
                "obligation_kind": "establish_playable_arrangement",
                "applies_to": scene_target.get("target_id"),
                "required": True,
                "success_condition": "room_cast_and_initial_pressure_legible",
                "constraints": ["do_not_overexplain", "leave_player_action_space"],
            }
        )
    if narrative_scene_function == "preserve_negative_space":
        obligations.append(
            {
                "obligation_order": len(obligations) + 1,
                "obligation_kind": "protect_withheld_speech",
                "applies_to": scene_target.get("target_actor_id"),
                "required": True,
                "success_condition": "silence_realized_without_forced_speech",
                "constraints": ["do_not_speak_for_silent_actor", "use_visible_reaction_if_needed"],
            }
        )
    if narrative_scene_function == "surface_information":
        obligations.append(
            {
                "obligation_order": len(obligations) + 1,
                "obligation_kind": "surface_only_allowed_information",
                "applies_to": scene_target.get("target_id"),
                "required": True,
                "success_condition": "information_exposed_without_new_truth",
                "constraints": ["use_allowed_sources_only", "do_not_invent_hidden_fact"],
            }
        )
    if narrative_scene_function == "contain_out_of_scope":
        obligations.append(
            {
                "obligation_order": len(obligations) + 1,
                "obligation_kind": "return_to_scene_boundary",
                "applies_to": scene_target.get("target_id"),
                "required": True,
                "success_condition": "player_can_continue_in_current_scene",
                "constraints": ["diagnostics_only_transition", "no_world_state_mutation"],
            }
        )
    return obligations


def _directive_for_responder(
    *,
    narrative_scene_function: str,
    role: str,
    index: int,
    silence_brevity_decision: dict[str, Any] | None,
) -> str:
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    silence_mode = _clean(silence.get("mode")).lower()
    if narrative_scene_function == "arrange_scene":
        return "stage_npc_presence"
    if narrative_scene_function == "shift_social_arrangement" or role == "interruption_candidate":
        return "force_npc_interruption"
    if narrative_scene_function == "surface_information":
        return "force_npc_disclosure_pressure"
    if narrative_scene_function == "preserve_negative_space" or silence_mode in {"withheld", "silent"}:
        return "hold_silence"
    if role == "secondary_reactor" or index > 1:
        return "force_secondary_reaction"
    if narrative_scene_function in {
        "force_accountability",
        "probe_motive",
        "raise_pressure",
        "test_repair_sincerity",
        "establish_scene_pressure",
    }:
        return "force_npc_reaction"
    return "support_scene_arrangement"


def _actor_directives(
    *,
    selected_responder_set: list[dict[str, Any]] | None,
    narrative_scene_function: str,
    scene_target: dict[str, Any],
    silence_brevity_decision: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    responders = selected_responder_set or []
    directives: list[dict[str, Any]] = []
    base_constraints = [
        "do_not_speak_for_player",
        "respect_actor_lane",
        "do_not_commit_new_truth",
    ]
    for idx, row in enumerate(responders, start=1):
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id") or row.get("responder_id"))
        if not actor_id:
            continue
        role = _clean(row.get("role") or row.get("reason")) or "responder"
        directive = _directive_for_responder(
            narrative_scene_function=narrative_scene_function,
            role=role,
            index=idx,
            silence_brevity_decision=silence_brevity_decision,
        )
        directives.append(
            {
                "directive_order": idx,
                "actor_id": actor_id,
                "actor_role": role,
                "directive": directive,
                "visibility": "visible_action_or_dialogue",
                "required": idx == 1,
                "target_function": scene_target.get("target_function"),
                "constraints": list(base_constraints),
                "reason_codes": [
                    f"narrative_scene_function:{narrative_scene_function}",
                    f"responder_role:{role}",
                ],
            }
        )

    if not directives and narrative_scene_function in {
        "arrange_scene",
        "establish_scene_anchor",
        "contain_out_of_scope",
        "narrate_consequence",
        "narrate_sensory_focus",
    }:
        directive = "stage_scene_arrangement"
        if narrative_scene_function == "contain_out_of_scope":
            directive = "contain_without_forcing_npc"
        elif narrative_scene_function in {"narrate_consequence", "narrate_sensory_focus"}:
            directive = "narrate_without_forcing_npc"
        directives.append(
            {
                "directive_order": 1,
                "actor_id": None,
                "actor_role": "director",
                "directive": directive,
                "visibility": "narrated_or_structural",
                "required": True,
                "target_function": scene_target.get("target_function"),
                "constraints": list(base_constraints),
                "reason_codes": [f"narrative_scene_function:{narrative_scene_function}"],
            }
        )
    return directives


def _handover_policy(
    *,
    narrative_scene_function: str,
    dramatic_beats: list[dict[str, Any]],
    expected_transition_pattern: str,
) -> dict[str, Any]:
    if narrative_scene_function == "contain_out_of_scope":
        policy = "contain_and_return_to_scene"
        requires_affordance = True
    elif narrative_scene_function in {"arrange_scene", "establish_scene_anchor", "establish_scene_pressure"}:
        policy = "offer_player_action_after_setup"
        requires_affordance = True
    elif narrative_scene_function == "preserve_negative_space":
        policy = "preserve_player_silence"
        requires_affordance = True
    elif narrative_scene_function in {"narrate_consequence", "narrate_sensory_focus"}:
        policy = "return_control_after_narration"
        requires_affordance = True
    elif expected_transition_pattern == "hard":
        policy = "offer_response_under_tension"
        requires_affordance = True
    else:
        policy = "offer_player_action"
        requires_affordance = True

    return {
        "policy": policy,
        "player_control_preserved": True,
        "requires_player_affordance": requires_affordance,
        "handover_after_beat_order": dramatic_beats[-1]["beat_order"] if dramatic_beats else 0,
        "success_condition": f"{policy}_available",
        "constraints": ["do_not_coerce_player_action", "do_not_close_scene_without_commit"],
    }


def _dramatic_beats(
    *,
    selected_scene_function: str,
    narrative_scene_function: str,
    scene_target: dict[str, Any],
    expected_transition_pattern: str,
    pacing_mode: str,
) -> list[dict[str, Any]]:
    templates = _BEAT_TEMPLATES_BY_NARRATIVE_FUNCTION.get(
        narrative_scene_function,
        tuple(
            ("npc_dialogue_beat", intent, intent, "npc")
            for intent in _BEAT_INTENTS_BY_SCENE_FUNCTION.get(
                selected_scene_function,
                _BEAT_INTENTS_BY_SCENE_FUNCTION["establish_pressure"],
            )
        ),
    )
    actor_id = _clean(scene_target.get("target_actor_id"))
    beats: list[dict[str, Any]] = []
    for idx, (beat_kind, beat_function, beat_intent, owner) in enumerate(templates, start=1):
        owner_actor_id = actor_id if owner == "npc" and actor_id else None
        beats.append(
            {
                "beat_order": idx,
                "beat_kind": beat_kind,
                "beat_function": beat_function,
                "beat_intent": beat_intent,
                "owner": owner,
                "owner_actor_id": owner_actor_id,
                "visibility": "visible_to_player",
                "target_actor_id": actor_id or None,
                "target_function": scene_target.get("target_function"),
                "pressure_axis": scene_target.get("pressure_axis"),
                "pressure_function": scene_target.get("pressure_function"),
                "expected_transition_pattern": expected_transition_pattern,
                "pacing_mode": pacing_mode,
                "required": idx == 1 or beat_kind == "player_handover_beat",
                "success_condition": f"{beat_function}_realized",
                "constraints": [
                    "planner_advisory_only",
                    "visible_realization_required" if idx == 1 else "may_defer_if_validator_rejects",
                ],
            }
        )
    return beats


def _continuity_obligation(
    *,
    continuity_class: str,
    expected_transition_pattern: str,
    prior_classes: list[str],
    pressure_axis: str,
    selected_scene_function: str,
    prior_planner_truth: dict[str, Any] | None,
) -> dict[str, Any]:
    prior = prior_planner_truth if isinstance(prior_planner_truth, dict) else {}
    reason_codes: list[str] = []
    _append_unique(reason_codes, f"scene_fn:{selected_scene_function}")
    _append_unique(reason_codes, f"continuity_class:{continuity_class}")
    if continuity_class in prior_classes:
        _append_unique(reason_codes, "prior_continuity_class_reactivated")
    if _clean(prior.get("carry_forward_tension_notes")):
        _append_unique(reason_codes, "prior_planner_truth_tension")

    carry_forward_required = expected_transition_pattern in {"hard", "carry_forward"} or continuity_class in prior_classes
    if continuity_class == "silent_carry" and expected_transition_pattern == "soft":
        carry_forward_required = False

    return {
        "continuity_class": continuity_class,
        "pressure_axis": pressure_axis,
        "carry_forward_required": carry_forward_required,
        "prior_continuity_classes": prior_classes,
        "expected_transition_pattern": expected_transition_pattern,
        "commit_authority": "commit_seam",
        "reason_codes": reason_codes,
    }


def build_semantic_scene_plan_enrichment(
    *,
    selected_scene_function: str,
    selected_responder_set: list[dict[str, Any]] | None,
    pacing_mode: str,
    silence_brevity_decision: dict[str, Any] | None,
    semantic_move_record: dict[str, Any] | None,
    social_state_record: dict[str, Any] | None,
    character_mind_records: list[dict[str, Any]] | None,
    scene_assessment: dict[str, Any] | None = None,
    implied_continuity_by_function: dict[str, str] | None = None,
    prior_continuity_impacts: list[dict[str, Any]] | None = None,
    prior_planner_truth: dict[str, Any] | None = None,
    selection_source: str = "semantic_pipeline_v1",
    current_scene_id: str = "",
    turn_input_class: str = "",
    canonical_path: dict[str, Any] | None = None,
    scene_graph: dict[str, Any] | None = None,
    locations: dict[str, Any] | None = None,
    objects: dict[str, Any] | None = None,
    character_documents: dict[str, Any] | None = None,
    content_access_policy: dict[str, Any] | None = None,
    beat_library: dict[str, Any] | None = None,
    opening_quote_anchors: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    environment_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build bounded scene-plan fields from structured planner records."""

    prior_classes = _list_continuity_classes(prior_continuity_impacts)
    sem = semantic_move_record if isinstance(semantic_move_record, dict) else {}
    social = social_state_record if isinstance(social_state_record, dict) else {}
    scene = scene_assessment if isinstance(scene_assessment, dict) else {}
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    scene_fn = _clean(selected_scene_function) or "establish_pressure"
    pacing = _clean(pacing_mode) or "standard"

    continuity_class = _continuity_for_plan(
        selected_scene_function=scene_fn,
        implied_continuity_by_function=implied_continuity_by_function,
        semantic_move_record=sem,
        social_state_record=social,
    )
    pressure_axis = _pressure_axis(
        selected_scene_function=scene_fn,
        semantic_move_record=sem,
    )
    transition = _expected_transition_pattern(
        selected_scene_function=scene_fn,
        continuity_class=continuity_class,
        semantic_move_record=sem,
        social_state_record=social,
        pacing_mode=pacing,
        prior_classes=prior_classes,
    )
    if transition not in TRANSITION_PATTERNS:
        transition = "soft"
    target = _pressure_target(
        selected_scene_function=scene_fn,
        selected_responder_set=selected_responder_set,
        semantic_move_record=sem,
        social_state_record=social,
        character_mind_records=character_mind_records,
        pressure_axis=pressure_axis,
    )
    obligation = _continuity_obligation(
        continuity_class=continuity_class,
        expected_transition_pattern=transition,
        prior_classes=prior_classes,
        pressure_axis=pressure_axis,
        selected_scene_function=scene_fn,
        prior_planner_truth=prior_planner_truth,
    )
    narrative_scene_function = _narrative_scene_function(
        selected_scene_function=scene_fn,
        silence_brevity_decision=silence,
        semantic_move_record=sem,
        scene_assessment=scene,
        selection_source=selection_source,
    )
    pressure_function = _pressure_function(
        pressure_axis=pressure_axis,
        narrative_scene_function=narrative_scene_function,
    )
    realization_mode = _realization_mode(narrative_scene_function)
    scene_target = _scene_target(
        selected_scene_function=scene_fn,
        narrative_scene_function=narrative_scene_function,
        pressure_function=pressure_function,
        pressure_target=target,
        social_state_record=social,
        scene_assessment=scene,
    )
    target.setdefault("target_id", scene_target.get("target_id"))
    target.setdefault("target_function", scene_target.get("target_function"))
    target.setdefault("narrative_scene_function", narrative_scene_function)
    target.setdefault("pressure_function", pressure_function)
    content_frame = _content_frame(
        canonical_path=canonical_path,
        scene_graph=scene_graph,
        locations=locations,
        objects=objects,
        character_documents=character_documents,
        content_access_policy=content_access_policy,
        scene_assessment=scene,
        environment_state=environment_state,
        current_scene_id=current_scene_id or _clean(scene.get("current_scene_id") or scene.get("scene_id")),
        narrative_scene_function=narrative_scene_function,
        selection_source=selection_source,
    )
    if content_frame.get("canonical_path_step_id"):
        scene_target["canonical_path_step_id"] = content_frame.get("canonical_path_step_id")
        scene_target["canonical_path_mode"] = content_frame.get("canonical_path_mode")
        target["canonical_path_step_id"] = content_frame.get("canonical_path_step_id")
    if content_frame.get("location_id"):
        scene_target["location_id"] = content_frame.get("location_id")
    if content_frame.get("object_focus_ids"):
        scene_target["object_focus_ids"] = list(content_frame.get("object_focus_ids") or [])

    speech_policy = _speech_profile_for_frame(
        content_frame=content_frame,
        narrative_scene_function=narrative_scene_function,
        selected_responder_set=selected_responder_set,
        actor_lane_context=actor_lane_context,
        opening_quote_anchors=opening_quote_anchors,
    )
    dialogue_plan = _dialogue_plan(
        content_frame=content_frame,
        speech_policy=speech_policy,
        selected_responder_set=selected_responder_set,
        actor_lane_context=actor_lane_context,
        beat_library=beat_library,
        character_documents=character_documents,
    )
    quote_moment_policy = _quote_moment_policy(
        content_frame=content_frame,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        opening_quote_anchors=opening_quote_anchors,
    )
    if dialogue_plan and speech_policy.get("speech_required"):
        has_dialogue_chain = any(
            _as_dict(row.get("forces_response_chain")).get("target_actor_id")
            for row in dialogue_plan
            if isinstance(row, dict)
        )
        realization_mode = (
            "content_guided_dialogue_chain"
            if has_dialogue_chain
            else "content_guided_dialogue"
        )
    elif dialogue_plan and speech_policy.get("speech_recommended"):
        realization_mode = "content_guided_optional_dialogue"

    beats = _dramatic_beats(
        selected_scene_function=scene_fn,
        narrative_scene_function=narrative_scene_function,
        scene_target=scene_target,
        expected_transition_pattern=transition,
        pacing_mode=pacing,
    )
    target_obligations = _target_obligations(
        scene_target=scene_target,
        continuity_obligation=obligation,
        narrative_scene_function=narrative_scene_function,
    )
    if speech_policy.get("speech_recommended"):
        target_obligations.append(
            {
                "obligation_order": len(target_obligations) + 1,
                "obligation_kind": "realize_content_guided_speech"
                if speech_policy.get("speech_required")
                else "offer_content_guided_speech",
                "applies_to": content_frame.get("canonical_path_step_id"),
                "required": bool(speech_policy.get("speech_required")),
                "success_condition": "dialogue_plan_realized_or_safely_degraded",
                "constraints": [
                    "do_not_force_player_speech",
                    "respect_quote_moment_policy",
                    "do_not_use_dialogue_as_unbounded_exposition",
                ],
            }
        )
    actor_directives = _actor_directives(
        selected_responder_set=selected_responder_set,
        narrative_scene_function=narrative_scene_function,
        scene_target=scene_target,
        silence_brevity_decision=silence,
    )
    for row in dialogue_plan:
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id"))
        if not actor_id:
            continue
        duplicate = any(
            _clean(existing.get("actor_id")) == actor_id
            and _clean(existing.get("directive")) == "deliver_npc_speech_beat"
            for existing in actor_directives
            if isinstance(existing, dict)
        )
        if duplicate:
            continue
        actor_directives.append(
            {
                "directive_order": len(actor_directives) + 1,
                "actor_id": actor_id,
                "actor_role": "content_dialogue_speaker",
                "directive": "deliver_npc_speech_beat",
                "visibility": "spoken_line",
                "required": bool(row.get("required")),
                "target_function": scene_target.get("target_function"),
                "dialogue_order": row.get("dialogue_order"),
                "beat_pattern_ref": row.get("beat_pattern_ref"),
                "constraints": list(row.get("constraints") or []),
                "reason_codes": [
                    f"speech_function:{speech_policy.get('speech_function')}",
                    f"dialogue_intent:{row.get('intent')}",
                ],
            }
        )
    beats = _merge_dialogue_into_beats(
        dramatic_beats=beats,
        dialogue_plan=dialogue_plan,
        expected_transition_pattern=transition,
        pacing_mode=pacing,
    )
    handover_policy = _handover_policy(
        narrative_scene_function=narrative_scene_function,
        dramatic_beats=beats,
        expected_transition_pattern=transition,
    )
    handover_policy = _handover_policy_for_speech(
        base_policy=handover_policy,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        dramatic_beats=beats,
    )
    capability_manager_plan = _director_capability_manager_plan(
        narrative_scene_function=narrative_scene_function,
        realization_mode=realization_mode,
        content_frame=content_frame,
        speech_policy=speech_policy,
        dialogue_plan=dialogue_plan,
        dramatic_beats=beats,
        actor_directives=actor_directives,
        turn_input_class=turn_input_class,
    )
    rationale_codes: list[str] = [SEMANTIC_SCENE_PLANNER_VERSION]
    _append_unique(rationale_codes, f"selection_source:{selection_source}")
    _append_unique(rationale_codes, f"pressure_axis:{pressure_axis}")
    _append_unique(rationale_codes, f"pressure_function:{pressure_function}")
    _append_unique(rationale_codes, f"narrative_scene_function:{narrative_scene_function}")
    _append_unique(rationale_codes, f"scene_target:{scene_target.get('target_function')}")
    _append_unique(rationale_codes, f"continuity_class:{continuity_class}")
    _append_unique(rationale_codes, f"transition_pattern:{transition}")
    if _clean(scene.get("pressure_state")):
        _append_unique(rationale_codes, f"scene_pressure:{scene.get('pressure_state')}")
    if _clean(silence.get("mode")) and _clean(silence.get("mode")) != "normal":
        _append_unique(rationale_codes, f"silence_mode:{silence.get('mode')}")
    if _clean(content_frame.get("canonical_path_step_id")):
        _append_unique(rationale_codes, f"canonical_path_step:{content_frame.get('canonical_path_step_id')}")
    if speech_policy.get("speech_recommended"):
        _append_unique(rationale_codes, f"speech_function:{speech_policy.get('speech_function')}")
    if quote_moment_policy.get("exact_quote_allowed"):
        _append_unique(rationale_codes, "quote_moment:moment_locked_exact_anchor_allowed")
    if capability_manager_plan.get("selected_capabilities"):
        _append_unique(rationale_codes, "capability_manager:selective_capability_gate")

    return {
        "semantic_scene_planner_version": SEMANTIC_SCENE_PLANNER_VERSION,
        "narrative_scene_function": narrative_scene_function,
        "realization_mode": realization_mode,
        "pressure_function": pressure_function,
        "scene_target": scene_target,
        "pressure_target": target,
        "target_obligations": target_obligations,
        "actor_directives": actor_directives,
        "dramatic_beats": beats,
        "handover_policy": handover_policy,
        "content_frame": content_frame,
        "speech_policy": speech_policy,
        "quote_moment_policy": quote_moment_policy,
        "dialogue_plan": dialogue_plan,
        "capability_manager_plan": capability_manager_plan,
        "continuity_obligation": obligation,
        "expected_transition_pattern": transition,
        "planner_rationale_codes": rationale_codes,
    }
