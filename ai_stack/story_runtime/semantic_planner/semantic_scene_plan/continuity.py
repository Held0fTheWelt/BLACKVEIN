"""Continuity class, transition, subtext, and pressure helpers."""

from __future__ import annotations

from typing import Any

from .mappings import (
    CONTINUITY_CLASSES,
    TRANSITION_PATTERNS,
    _CONTINUITY_BY_SCENE_FUNCTION,
    _HARD_TRANSITION_SCENE_FUNCTIONS,
    _PRESSURE_AXIS_BY_MOVE_TYPE,
    _PRESSURE_AXIS_BY_SCENE_FUNCTION,
)
from .utils import _append_unique, _clean


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
