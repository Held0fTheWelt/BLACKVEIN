"""Narrative scene function, pressure function, target, and obligation selection."""

from __future__ import annotations

from typing import Any

from .continuity import _feature_snapshot, _is_setup_context, _semantic_subtext
from .mappings import (
    _NARRATIVE_SCENE_FUNCTION_BY_MOVE_TYPE,
    _NARRATIVE_SCENE_FUNCTION_BY_SCENE_FUNCTION,
    _PRESSURE_FUNCTION_BY_AXIS,
    _REALIZATION_MODE_BY_NARRATIVE_FUNCTION,
    _TARGET_EFFECT_BY_NARRATIVE_FUNCTION,
    _TARGET_FUNCTION_BY_NARRATIVE_FUNCTION,
    _TARGET_KIND_BY_NARRATIVE_FUNCTION,
)
from .utils import _append_unique, _clean


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
