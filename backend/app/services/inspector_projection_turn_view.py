"""Per-turn view extraction for inspector timeline/comparison projections."""

from __future__ import annotations

import hashlib
from typing import Any

from ai_stack.semantic_planner.semantic_planner_effect_surface import support_level_for_module


def planner_slice(row: dict[str, Any]) -> dict[str, Any]:
    graph = row.get("graph")
    if isinstance(graph, dict):
        psp = graph.get("planner_state_projection")
        if isinstance(psp, dict):
            return psp
    return {}


def semantic_move_record(row: dict[str, Any]) -> dict[str, Any] | None:
    sm = row.get("semantic_move_record")
    if isinstance(sm, dict):
        return sm
    ps = planner_slice(row)
    inner = ps.get("semantic_move_record")
    return inner if isinstance(inner, dict) else None


def dramatic_review(row: dict[str, Any]) -> dict[str, Any]:
    graph = row.get("graph")
    if not isinstance(graph, dict):
        return {}
    dr = graph.get("dramatic_review")
    return dr if isinstance(dr, dict) else {}


def visible_narration_fingerprint(row: dict[str, Any]) -> str | None:
    vo = row.get("visible_output_bundle")
    if not isinstance(vo, dict):
        return None
    narr = vo.get("gm_narration")
    if not isinstance(narr, list):
        return None
    parts = [str(x) for x in narr if x is not None]
    if not parts:
        return None
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def extract_turn_view(row: dict[str, Any], idx: int, *, module_id: Any) -> dict[str, Any]:
    validation = row.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate, dict):
        gate = {}
    model_route = row.get("model_route")
    if not isinstance(model_route, dict):
        model_route = {}
    graph = row.get("graph")
    if not isinstance(graph, dict):
        graph = {}

    sm = semantic_move_record(row)
    move_type = sm.get("move_type") if isinstance(sm, dict) else None
    scene_risk_band = sm.get("scene_risk_band") if isinstance(sm, dict) else None

    trace = gate.get("diagnostic_trace")
    trace_codes: list[str] = []
    if isinstance(trace, list):
        for step in trace[:12]:
            if isinstance(step, dict) and step.get("code") is not None:
                trace_codes.append(str(step.get("code")))

    mid = module_id if isinstance(module_id, str) else ""
    support_level = support_level_for_module(mid).value

    return {
        "turn_index": idx + 1,
        "turn_number": row.get("turn_number") if isinstance(row.get("turn_number"), int) else idx + 1,
        "trace_id": row.get("trace_id"),
        "gate_result": gate.get("gate_result"),
        "validation_status": validation.get("status"),
        "validation_reason": validation.get("reason"),
        "dramatic_effect_weak_signal": validation.get("dramatic_effect_weak_signal"),
        "fallback_path_taken": bool(graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached")),
        "execution_health": graph.get("execution_health"),
        "selected_scene_function": row.get("selected_scene_function"),
        "route_mode": model_route.get("route_mode"),
        "route_reason_code": model_route.get("route_reason_code") or model_route.get("route_reason"),
        "semantic_move_type": move_type,
        "scene_risk_band": scene_risk_band,
        "empty_fluency_risk": gate.get("empty_fluency_risk"),
        "character_plausibility_posture": gate.get("character_plausibility_posture"),
        "continuity_support_posture": gate.get("continuity_support_posture"),
        "continues_or_changes_pressure": gate.get("continues_or_changes_pressure"),
        "supports_scene_function": gate.get("supports_scene_function"),
        "legacy_fallback_used": gate.get("legacy_fallback_used"),
        "effect_rationale_codes": list(gate["effect_rationale_codes"])
        if isinstance(gate.get("effect_rationale_codes"), list)
        else None,
        "gate_diagnostic_trace_codes": trace_codes or None,
        "accepted_weak_signal": bool(gate.get("gate_result") == "accepted_with_weak_signal"),
        "semantic_planner_support_level": support_level,
    }
