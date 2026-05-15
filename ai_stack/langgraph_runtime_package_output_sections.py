"""
Thematic sections for package_output (DS-037) — dramatic review and
planner projection.
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import GOC_MODULE_ID
from ai_stack.langgraph_runtime_package_output_dramatic_review import build_dramatic_review_section
from ai_stack.langgraph_runtime_state import RuntimeTurnState


def append_goc_validation_reject_failure_marker(
    *,
    module_id: str,
    validation: dict[str, Any],
    failure_markers: list[Any],
) -> None:
    """Describe what ``append_goc_validation_reject_failure_marker`` does
    in one line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        validation: ``validation`` (dict[str, Any]); meaning follows the type and call sites.
        failure_markers: ``failure_markers`` (list[Any]); meaning follows the type and call sites.
    """
    if module_id != GOC_MODULE_ID or validation.get("status") != "rejected":
        return
    if any(isinstance(m, dict) and m.get("failure_class") == "validation_reject" for m in failure_markers):
        return
    failure_markers.append(
        {
            "failure_class": "validation_reject",
            "closure_impacting": False,
            "note": "goc_validation_rejected_truth_safe_visible",
            "validation_reason": validation.get("reason"),
        }
    )


def compute_experiment_preview_for_package_output(
    *,
    state: RuntimeTurnState,
    module_id: str,
    validation: dict[str, Any],
    committed: dict[str, Any],
    failure_markers: list[Any],
) -> bool:
    """Describe what ``compute_experiment_preview_for_package_output`` does
    in one line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        validation: ``validation`` (dict[str, Any]); meaning follows the type and call sites.
        committed: ``committed`` (dict[str, Any]); meaning follows the type and call sites.
        failure_markers: ``failure_markers`` (list[Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    experiment_preview = True
    if state.get("force_experiment_preview"):
        experiment_preview = True
    elif module_id != GOC_MODULE_ID:
        experiment_preview = True
    elif validation.get("status") == "waived":
        experiment_preview = True
    elif validation.get("status") != "approved":
        experiment_preview = True
    elif not state.get("goc_slice_active"):
        experiment_preview = True
    else:
        experiment_preview = False

    if module_id == GOC_MODULE_ID and validation.get("status") == "approved" and not committed.get("commit_applied"):
        pass

    for fm in failure_markers:
        fc = fm.get("failure_class") if isinstance(fm, dict) else None
        if fc in ("scope_breach", "graph_error"):
            experiment_preview = True

    return experiment_preview


def build_planner_state_projection(state: RuntimeTurnState) -> dict[str, Any]:
    """Describe what ``build_planner_state_projection`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        state: ``state`` (RuntimeTurnState); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "semantic_move_record": state.get("semantic_move_record"),
        "social_state_record": state.get("social_state_record"),
        "character_mind_records": state.get("character_mind_records"),
        "character_voice_profiles": state.get("character_voice_profiles"),
        "voice_consistency_validation": state.get("voice_consistency_validation"),
        "scene_plan_record": state.get("scene_plan_record"),
        "scene_energy_target": state.get("scene_energy_target"),
        "scene_energy_transition": state.get("scene_energy_transition"),
        "scene_energy_validation": state.get("scene_energy_validation"),
        "pacing_rhythm_state": state.get("pacing_rhythm_state"),
        "pacing_rhythm_target": state.get("pacing_rhythm_target"),
        "pacing_rhythm_validation": state.get("pacing_rhythm_validation"),
        "note": "Derived projection of RuntimeTurnState planner fields — not a second truth surface.",
    }


def _bounded_str(value: Any, *, max_chars: int = 220) -> str | None:
    if not isinstance(value, str):
        return None
    text = " ".join(value.strip().split())
    if not text:
        return None
    return text[:max_chars].rstrip()


def _bounded_str_list(value: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = _bounded_str(str(item), max_chars=80)
        if text and text not in out:
            out.append(text)
        if len(out) >= limit:
            break
    return out


def _primary_responder_id(state: RuntimeTurnState) -> str | None:
    responders = state.get("selected_responder_set")
    if isinstance(responders, list) and responders and isinstance(responders[0], dict):
        actor_id = _bounded_str(responders[0].get("actor_id"))
        if actor_id:
            return actor_id
    return _bounded_str(state.get("responder_id"))


def build_bounded_dramatic_context_summary(state: RuntimeTurnState) -> dict[str, Any]:
    """Build the compact dramatic context carried across output surfaces."""
    scene = state.get("scene_assessment") if isinstance(state.get("scene_assessment"), dict) else {}
    social = state.get("social_state_record") if isinstance(state.get("social_state_record"), dict) else {}
    semantic = state.get("semantic_move_record") if isinstance(state.get("semantic_move_record"), dict) else {}
    retrieval = state.get("retrieval") if isinstance(state.get("retrieval"), dict) else {}
    continuity_query = (
        retrieval.get("continuity_query_signal")
        if isinstance(retrieval.get("continuity_query_signal"), dict)
        else {}
    )
    silence = (
        state.get("silence_brevity_decision")
        if isinstance(state.get("silence_brevity_decision"), dict)
        else {}
    )
    continuity_classes = [
        str(x.get("class") or x.get("continuity_class"))
        for x in (state.get("continuity_impacts") or [])
        if isinstance(x, dict) and (x.get("class") or x.get("continuity_class"))
    ]

    return {
        "contract": "bounded_dramatic_context.v1",
        "source": "runtime_turn_state.package_output",
        "module_id": state.get("module_id"),
        "module_scope": {
            "runtime_scope": "module_specific",
            "supported_live_module_ids": [GOC_MODULE_ID],
            "requested_module_supported": state.get("module_id") == GOC_MODULE_ID,
        },
        "current_scene_id": state.get("current_scene_id"),
        "selected_scene_function": state.get("selected_scene_function"),
        "function_type": state.get("function_type"),
        "responder": {
            "responder_id": _primary_responder_id(state),
            "responder_scope": _bounded_str_list(
                [
                    r.get("actor_id") or r.get("responder_id")
                    for r in (state.get("selected_responder_set") or [])
                    if isinstance(r, dict)
                ]
            ),
        },
        "pacing": {
            "pacing_mode": state.get("pacing_mode"),
            "silence_mode": silence.get("mode"),
        },
        "scene_energy": {
            "target": state.get("scene_energy_target")
            if isinstance(state.get("scene_energy_target"), dict)
            else {},
            "transition": state.get("scene_energy_transition")
            if isinstance(state.get("scene_energy_transition"), dict)
            else {},
            "validation_status": (
                state.get("scene_energy_validation", {}).get("status")
                if isinstance(state.get("scene_energy_validation"), dict)
                else None
            ),
        },
        "pacing_rhythm": {
            "state": state.get("pacing_rhythm_state")
            if isinstance(state.get("pacing_rhythm_state"), dict)
            else {},
            "target": state.get("pacing_rhythm_target")
            if isinstance(state.get("pacing_rhythm_target"), dict)
            else {},
            "validation_status": (
                state.get("pacing_rhythm_validation", {}).get("status")
                if isinstance(state.get("pacing_rhythm_validation"), dict)
                else None
            ),
        },
        "scene_assessment": {
            "pressure_state": scene.get("pressure_state"),
            "thread_pressure_state": scene.get("thread_pressure_state"),
            "assessment_summary": _bounded_str(scene.get("assessment_summary")),
            "continuity_carry_forward_note": _bounded_str(scene.get("continuity_carry_forward_note")),
        },
        "semantic_move": {
            "move_class": semantic.get("move_class") or semantic.get("semantic_move_class"),
            "intent": _bounded_str(semantic.get("intent"), max_chars=120),
        },
        "social_state": {
            "scene_pressure_state": social.get("scene_pressure_state"),
            "social_risk_band": social.get("social_risk_band"),
            "responder_asymmetry_code": social.get("responder_asymmetry_code"),
            "social_continuity_status": social.get("social_continuity_status"),
            "prior_social_state_fingerprint": social.get("prior_social_state_fingerprint"),
        },
        "dramatic_outcome": {
            "social_outcome": state.get("social_outcome"),
            "dramatic_direction": state.get("dramatic_direction"),
            "continuity_classes": _bounded_str_list(continuity_classes),
        },
        "retrieval_context": {
            "continuity_query_attached": bool(continuity_query.get("attached")),
            "continuity_query_sources": _bounded_str_list(continuity_query.get("sources")),
            "retrieval_status": retrieval.get("status"),
            "retrieval_route": retrieval.get("retrieval_route"),
        },
        "visibility": {
            "visibility_class_markers": _bounded_str_list(state.get("visibility_class_markers")),
            "player_visible_shell_context": True,
            "operator_detail_available": True,
        },
    }
