"""Bounded semantic scene planner for the GoC runtime.

The existing director still owns the first-pass deterministic scene-function
and responder choice. This module turns that selection plus semantic/social
records into a richer, inspectable short-horizon plan. It remains advisory
until the validation and commit seams authorize any runtime truth.
"""

from __future__ import annotations

from typing import Any, Final

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
    actor_directives = _actor_directives(
        selected_responder_set=selected_responder_set,
        narrative_scene_function=narrative_scene_function,
        scene_target=scene_target,
        silence_brevity_decision=silence,
    )
    handover_policy = _handover_policy(
        narrative_scene_function=narrative_scene_function,
        dramatic_beats=beats,
        expected_transition_pattern=transition,
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
        "continuity_obligation": obligation,
        "expected_transition_pattern": transition,
        "planner_rationale_codes": rationale_codes,
    }
