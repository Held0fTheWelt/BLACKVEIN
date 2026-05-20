"""Provenance entry list for inspector provenance-raw projection (last diagnostics row)."""

from __future__ import annotations

from typing import Any

from ai_stack.story_runtime.semantic_planner.semantic_planner_effect_surface import (
    resolve_dramatic_effect_evaluator,
    support_level_for_module,
)


def compact_gate_diagnostic_trace(gate: dict[str, Any]) -> list[dict[str, Any]] | None:
    if not isinstance(gate.get("diagnostic_trace"), list):
        return None
    return [
        {"code": (s or {}).get("code"), "detail": str((s or {}).get("detail") or "")[:160]}
        for s in gate["diagnostic_trace"][:24]
        if isinstance(s, dict)
    ]


def _last_row_graph_slices(last: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
    validation = last.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate, dict):
        gate = {}
    model_route = last.get("model_route")
    if not isinstance(model_route, dict):
        model_route = {}
    graph = last.get("graph")
    if not isinstance(graph, dict):
        graph = {}
    return validation, gate, model_route, graph


def build_provenance_entries(*, last: dict[str, Any], bundle: dict[str, Any]) -> list[dict[str, Any]]:
    validation, gate, model_route, graph = _last_row_graph_slices(last)
    mid = bundle.get("module_id")
    mid_str = mid if isinstance(mid, str) else ""
    support_level = support_level_for_module(mid_str).value
    evaluator_class = type(resolve_dramatic_effect_evaluator(mid_str)).__name__
    trace_compact = compact_gate_diagnostic_trace(gate)

    return [
        {
            "field": "validation_status",
            "value": validation.get("status"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.status",
        },
        {
            "field": "gate_result",
            "value": gate.get("gate_result"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.gate_result",
        },
        {
            "field": "effect_rationale_codes",
            "value": list(gate["effect_rationale_codes"])
            if isinstance(gate.get("effect_rationale_codes"), list)
            else None,
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.effect_rationale_codes",
        },
        {
            "field": "dramatic_effect_diagnostic_trace",
            "value": trace_compact,
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.diagnostic_trace",
        },
        {
            "field": "legacy_fallback_used",
            "value": gate.get("legacy_fallback_used"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].validation_outcome.dramatic_effect_gate_outcome.legacy_fallback_used",
        },
        {
            "field": "semantic_planner_support_level",
            "value": support_level,
            "source_kind": "capability_metadata",
            "source_ref": "ai_stack.story_runtime.semantic_planner.semantic_planner_effect_surface.support_level_for_module",
        },
        {
            "field": "dramatic_effect_evaluator_class",
            "value": evaluator_class,
            "source_kind": "capability_metadata",
            "source_ref": "ai_stack.story_runtime.semantic_planner.semantic_planner_effect_surface.resolve_dramatic_effect_evaluator",
        },
        {
            "field": "fallback_path_taken",
            "value": bool(graph.get("fallback_path_taken") or model_route.get("fallback_stage_reached")),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].graph.fallback_path_taken|model_route.fallback_stage_reached",
        },
        {
            "field": "selected_scene_function",
            "value": last.get("selected_scene_function"),
            "source_kind": "runtime_derived",
            "source_ref": "world_engine_diagnostics.diagnostics[-1].selected_scene_function",
        },
    ]
