"""Themen-Splits für ``build_inspector_projection_sections_filled`` (DS-047)."""

from __future__ import annotations

from typing import Any

from ai_stack.semantic_planner_effect_surface import support_level_for_module

from app.contracts.inspector_turn_projection import (
    make_supported_section,
    make_unavailable_section,
    make_unsupported_section,
)
from app.services.inspector_turn_projection_sections_gate_payload import gate_projection_payload
from app.services.inspector_turn_projection_sections_constants import COMPARISON_RESERVED_FIELDS
from app.services.inspector_turn_projection_sections_provenance import build_provenance_entries
from app.services.inspector_turn_projection_sections_semantic import build_semantic_decision_flow, support_posture


def build_planner_projection_section(
    *,
    canonical_record: dict[str, Any],
    module_id: Any,
) -> dict[str, Any]:
    posture = support_posture(module_id=module_id)
    planner_data: dict[str, Any] = {
        "semantic_move_record": canonical_record.get("semantic_move_record"),
        "social_state_record": canonical_record.get("social_state_record"),
        "character_mind_records": canonical_record.get("character_mind_records"),
        "scene_plan_record": canonical_record.get("scene_plan_record"),
        "interpreted_move": canonical_record.get("interpreted_move"),
        "scene_assessment": canonical_record.get("scene_assessment"),
        "selected_responder_set": canonical_record.get("selected_responder_set"),
        "selected_scene_function": canonical_record.get("selected_scene_function"),
        "pacing_mode": canonical_record.get("pacing_mode"),
        "silence_brevity_decision": canonical_record.get("silence_brevity_decision"),
    }
    if posture is not None:
        planner_data["support_posture"] = posture
    _core_keys = (
        "semantic_move_record",
        "social_state_record",
        "character_mind_records",
        "scene_plan_record",
        "interpreted_move",
        "scene_assessment",
        "selected_responder_set",
        "selected_scene_function",
        "pacing_mode",
        "silence_brevity_decision",
    )
    _core_empty = not any(planner_data.get(k) is not None for k in _core_keys)
    if _core_empty and posture is None:
        return make_unavailable_section(
            reason="planner_surface_not_emitted_by_runtime_diagnostics_event",
            data=planner_data,
        )
    return make_supported_section(planner_data)


def build_graph_routing_flow_context(
    canonical_record: dict[str, Any],
    bundle: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Any], list[dict[str, str]]]:
    graph = canonical_record.get("graph_diagnostics_summary")
    if not isinstance(graph, dict):
        graph = {}
    routing = canonical_record.get("routing")
    if not isinstance(routing, dict):
        routing = {}
    nodes = graph.get("nodes_executed") if isinstance(graph.get("nodes_executed"), list) else []
    flow_edges: list[dict[str, str]] = []
    for idx in range(len(nodes) - 1):
        src = nodes[idx]
        dst = nodes[idx + 1]
        if isinstance(src, str) and isinstance(dst, str):
            flow_edges.append({"from": src, "to": dst})
    return graph, routing, nodes, flow_edges


def assemble_filled_inspector_sections(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    turn_meta = canonical_record.get("turn_metadata")
    if not isinstance(turn_meta, dict):
        turn_meta = {}
    module_id = bundle.get("module_id")
    support_level = support_level_for_module(str(module_id if isinstance(module_id, str) else ""))
    posture = support_posture(module_id=module_id)
    planner_section = build_planner_projection_section(canonical_record=canonical_record, module_id=module_id)
    graph, routing, nodes, flow_edges = build_graph_routing_flow_context(canonical_record, bundle)

    validation = canonical_record.get("validation_outcome")
    if not isinstance(validation, dict):
        validation = {}
    gate_outcome = validation.get("dramatic_effect_gate_outcome")
    if not isinstance(gate_outcome, dict):
        gate_outcome = {}
    committed = canonical_record.get("committed_result")
    if not isinstance(committed, dict):
        committed = {}
    generation = (last_turn.get("model_route") or {}).get("generation")
    if not isinstance(generation, dict):
        generation = {}

    gate_data = gate_projection_payload(gate_outcome) if gate_outcome else {}
    gate_section = (
        make_supported_section(gate_data)
        if gate_outcome
        else make_unavailable_section(
            reason="gate_outcome_not_present_in_validation_payload",
            data=gate_data,
        )
    )

    semantic_flow = build_semantic_decision_flow(
        support_level=support_level,
        canonical_record=canonical_record,
        last_turn=last_turn,
        gate_outcome=gate_outcome,
        validation=validation,
        committed=committed,
    )

    section_data: dict[str, dict[str, Any]] = {
        "turn_identity": make_supported_section(
            {
                "backend_session_id": bundle.get("backend_session_id"),
                "world_engine_story_session_id": bundle.get("world_engine_story_session_id"),
                "module_id": bundle.get("module_id"),
                "current_scene_id": bundle.get("current_scene_id"),
                "turn_number_backend": bundle.get("turn_counter_backend"),
                "turn_number_world_engine": turn_meta.get("turn_number"),
                "turn_trace_id": turn_meta.get("trace_id"),
            }
        ),
        "planner_state_projection": planner_section,
        "decision_trace_projection": make_supported_section(
            {
                "graph_name": graph.get("graph_name"),
                "graph_version": graph.get("graph_version"),
                "execution_health": graph.get("execution_health"),
                "fallback_path_taken": graph.get("fallback_path_taken"),
                "nodes_executed": nodes,
                "node_outcomes": graph.get("node_outcomes"),
                "route_mode": routing.get("route_mode"),
                "route_reason_code": routing.get("route_reason_code") or routing.get("route_reason"),
                "fallback_chain": routing.get("fallback_chain"),
                "fallback_stage_reached": routing.get("fallback_stage_reached"),
                "graph_path_summary": (bundle.get("last_turn_repro_metadata") or {}).get("graph_path_summary"),
                "adapter_invocation_mode": (bundle.get("last_turn_repro_metadata") or {}).get(
                    "adapter_invocation_mode"
                ),
                "semantic_decision_flow": semantic_flow,
                "graph_execution_flow": {
                    "flow_nodes": [node for node in nodes if isinstance(node, str)],
                    "flow_edges": flow_edges,
                },
                "flow_nodes": [node for node in nodes if isinstance(node, str)],
                "flow_edges": flow_edges,
            }
        ),
        "gate_projection": gate_section,
        "validation_projection": make_supported_section(
            {
                "status": validation.get("status"),
                "reason": validation.get("reason"),
                "validator_lane": validation.get("validator_lane"),
                "dramatic_quality_gate": validation.get("dramatic_quality_gate"),
                "dramatic_effect_weak_signal": validation.get("dramatic_effect_weak_signal"),
            }
        ),
        "authority_projection": make_supported_section(
            {
                "authoritative_surface": "world_engine_session_commit_state",
                "commit_applied": committed.get("commit_applied"),
                "committed_effect_count": len(committed.get("committed_effects", []))
                if isinstance(committed.get("committed_effects"), list)
                else 0,
                "experiment_preview": canonical_record.get("experiment_preview"),
                "authority_boundary_note": (
                    "diagnostic projections are read-only and cannot mutate runtime truth"
                ),
                "non_authoritative_inputs": [
                    "graph_diagnostics",
                    "retrieval",
                    "model_route",
                    "visible_output_bundle",
                ],
            }
        ),
        "fallback_projection": make_supported_section(
            {
                "fallback_path_taken": graph.get("fallback_path_taken"),
                "execution_health": graph.get("execution_health"),
                "routing_fallback_chain": routing.get("fallback_chain"),
                "routing_fallback_stage_reached": routing.get("fallback_stage_reached"),
                "model_fallback_used": generation.get("fallback_used"),
                "legacy_fallback_used": gate_outcome.get("legacy_fallback_used"),
                "legacy_fallback_reason": (
                    gate_outcome.get("legacy_fallback_reason") or gate_outcome.get("legacy_fallback_rationale")
                ),
            }
        ),
        "provenance_projection": make_supported_section(
            {
                "entries": build_provenance_entries(canonical_record=canonical_record, last_turn=last_turn),
                "note": "deterministic projections only; no narrative synthesis",
            }
        ),
        "comparison_ready_fields": make_supported_section(
            {
                "supported_now": {
                    "turn_number": turn_meta.get("turn_number"),
                    "turn_trace_id": turn_meta.get("trace_id"),
                    "graph_version": graph.get("graph_version"),
                    "execution_health": graph.get("execution_health"),
                    "fallback_path_taken": graph.get("fallback_path_taken"),
                    "validation_status": validation.get("status"),
                    "validation_reason": validation.get("reason"),
                    "gate_result": gate_data.get("gate_result"),
                    "empty_fluency_risk": gate_data.get("empty_fluency_risk"),
                    "character_plausibility_posture": gate_data.get("character_plausibility_posture"),
                    "continuity_support_posture": gate_data.get("continuity_support_posture"),
                    "continues_or_changes_pressure": gate_data.get("continues_or_changes_pressure"),
                    "supports_scene_function": gate_data.get("supports_scene_function"),
                    "legacy_fallback_used": gate_data.get("legacy_fallback_used"),
                    "semantic_planner_support_level": posture.get("semantic_planner_support_level")
                    if posture
                    else None,
                    "commit_applied": committed.get("commit_applied"),
                    "selected_scene_function": canonical_record.get("selected_scene_function"),
                    "pacing_mode": canonical_record.get("pacing_mode"),
                },
                "reserved_for_future": list(COMPARISON_RESERVED_FIELDS),
            }
        ),
    }
    if gate_section["status"] == "unavailable":
        section_data["gate_projection"] = make_unsupported_section(
            reason="dramatic_gate_not_supported_for_this_turn_payload",
            data=gate_data,
        )
    return section_data
