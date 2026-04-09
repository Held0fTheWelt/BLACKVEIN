"""Canonical read-only Inspector Suite projection assembly for one turn."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_turn_seams import build_operator_canonical_turn_record

from app.contracts.inspector_turn_projection import (
    build_inspector_turn_projection_root,
    make_supported_section,
    make_unavailable_section,
    make_unsupported_section,
)
from app.services.ai_stack_evidence_service import build_session_evidence_bundle

_COMPARISON_RESERVED_FIELDS: tuple[str, ...] = (
    "timeline_alignment",
    "cross_run_delta",
    "candidate_matrix",
    "coverage_heatmap",
)


def _last_turn_from_bundle(bundle: dict[str, Any]) -> dict[str, Any] | None:
    diagnostics = bundle.get("world_engine_diagnostics")
    if not isinstance(diagnostics, dict):
        return None
    rows = diagnostics.get("diagnostics")
    if not isinstance(rows, list) or not rows:
        return None
    tail = rows[-1]
    return tail if isinstance(tail, dict) else None


def _projectable_state(
    *,
    bundle: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, Any]:
    model_route = last_turn.get("model_route")
    routing = {}
    generation = {}
    if isinstance(model_route, dict):
        generation = model_route.get("generation") if isinstance(model_route.get("generation"), dict) else {}
        routing = {k: v for k, v in model_route.items() if k != "generation"}
    module_id = bundle.get("module_id")
    current_scene_id = bundle.get("current_scene_id")
    world_engine_story_session_id = bundle.get("world_engine_story_session_id")
    turn_number = last_turn.get("turn_number")
    return {
        "session_id": world_engine_story_session_id,
        "trace_id": last_turn.get("trace_id"),
        "module_id": module_id,
        "current_scene_id": current_scene_id,
        "turn_number": turn_number if isinstance(turn_number, int) else None,
        "retrieval": last_turn.get("retrieval") if isinstance(last_turn.get("retrieval"), dict) else {},
        "routing": routing,
        "generation": generation,
        "graph_diagnostics": last_turn.get("graph") if isinstance(last_turn.get("graph"), dict) else {},
        "visible_output_bundle": last_turn.get("visible_output_bundle"),
        "diagnostics_refs": last_turn.get("diagnostics_refs"),
        "experiment_preview": last_turn.get("experiment_preview"),
        "validation_outcome": (
            last_turn.get("validation_outcome")
            if isinstance(last_turn.get("validation_outcome"), dict)
            else {}
        ),
        "committed_result": (
            last_turn.get("committed_result") if isinstance(last_turn.get("committed_result"), dict) else {}
        ),
        "selected_scene_function": last_turn.get("selected_scene_function"),
    }


def _build_provenance_entries(canonical_record: dict[str, Any], last_turn: dict[str, Any]) -> list[dict[str, Any]]:
    val = canonical_record.get("validation_outcome")
    if not isinstance(val, dict):
        val = {}
    com = canonical_record.get("committed_result")
    if not isinstance(com, dict):
        com = {}
    graph = canonical_record.get("graph_diagnostics_summary")
    if not isinstance(graph, dict):
        graph = {}
    routing = canonical_record.get("routing")
    if not isinstance(routing, dict):
        routing = {}
    selected_scene_function = canonical_record.get("selected_scene_function")
    pacing_mode = canonical_record.get("pacing_mode")
    dramatic = val.get("dramatic_effect_gate_outcome")
    if not isinstance(dramatic, dict):
        dramatic = {}

    entries: list[dict[str, Any]] = []

    def add_entry(
        *,
        field: str,
        value: Any,
        source_kind: str,
        source_ref: str,
        derivation_rule: str,
        code_path: str,
        influence_targets: list[str],
        decision_effect: str,
        rejected_alternatives: list[Any] | None = None,
    ) -> None:
        if value is None:
            entries.append(
                {
                    "field": field,
                    "status": "unavailable",
                    "value": None,
                    "source_kind": source_kind,
                    "source_ref": source_ref,
                    "derivation_rule": derivation_rule,
                    "code_path": code_path,
                    "influence_targets": influence_targets,
                    "decision_effect": decision_effect,
                    "rejected_alternatives": rejected_alternatives or [],
                    "status_reason": f"unavailable:{field}",
                }
            )
            return
        entries.append(
            {
                "field": field,
                "status": "supported",
                "value": value,
                "source_kind": source_kind,
                "source_ref": source_ref,
                "derivation_rule": derivation_rule,
                "code_path": code_path,
                "influence_targets": influence_targets,
                "decision_effect": decision_effect,
                "rejected_alternatives": rejected_alternatives or [],
                "status_reason": None,
            }
        )

    add_entry(
        field="selected_scene_function",
        value=selected_scene_function,
        source_kind="runtime_derived",
        source_ref="diagnostics.selected_scene_function",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["validation_projection", "authority_projection"],
        decision_effect="drives scene-function framing for turn diagnostics",
    )
    add_entry(
        field="pacing_mode",
        value=pacing_mode,
        source_kind="runtime_derived",
        source_ref="operator_canonical_turn_record.pacing_mode",
        derivation_rule="pass_through_from_runtime_state_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["planner_state_projection"],
        decision_effect="informs pacing-related planner posture",
    )
    add_entry(
        field="validation_status",
        value=val.get("status"),
        source_kind="runtime_derived",
        source_ref="diagnostics.validation_outcome.status",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["validation_projection", "authority_projection"],
        decision_effect="determines approval/rejection presentation",
        rejected_alternatives=dramatic.get("rejection_reasons") if isinstance(dramatic.get("rejection_reasons"), list) else [],
    )
    add_entry(
        field="commit_applied",
        value=com.get("commit_applied"),
        source_kind="runtime_derived",
        source_ref="diagnostics.committed_result.commit_applied",
        derivation_rule="pass_through_single_turn_event",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["authority_projection", "fallback_projection"],
        decision_effect="marks whether authoritative commit was applied",
    )
    add_entry(
        field="execution_health",
        value=graph.get("execution_health"),
        source_kind="runtime_derived",
        source_ref="diagnostics.graph.execution_health",
        derivation_rule="graph_summary_projection",
        code_path="ai_stack/goc_turn_seams.py:build_operator_canonical_turn_record",
        influence_targets=["decision_trace_projection", "fallback_projection"],
        decision_effect="surfaces degraded or healthy runtime path",
    )
    legacy_fallback = dramatic.get("legacy_fallback_used")
    add_entry(
        field="legacy_fallback_used",
        value=legacy_fallback,
        source_kind="legacy_fallback",
        source_ref="diagnostics.validation_outcome.dramatic_effect_gate_outcome.legacy_fallback_used",
        derivation_rule="pass_through_if_supported_by_gate_outcome",
        code_path="ai_stack/goc_turn_seams.py:run_validation_seam",
        influence_targets=["fallback_projection", "gate_projection"],
        decision_effect="shows if legacy dramatic fallback affected gate posture",
    )
    add_entry(
        field="routing_fallback_stage_reached",
        value=routing.get("fallback_stage_reached"),
        source_kind="fallback_default",
        source_ref="diagnostics.model_route.fallback_stage_reached",
        derivation_rule="routing_projection_from_model_route",
        code_path="world-engine/app/story_runtime/manager.py:execute_turn.event",
        influence_targets=["fallback_projection", "decision_trace_projection"],
        decision_effect="shows fallback chain depth for selected route",
    )
    return entries


def _build_sections(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any] | None,
    last_turn: dict[str, Any] | None,
) -> dict[str, dict[str, Any]]:
    if canonical_record is None or last_turn is None:
        missing_reason = "no_turn_diagnostics_for_session"
        return {
            "turn_identity": make_unavailable_section(reason=missing_reason),
            "planner_state_projection": make_unavailable_section(reason=missing_reason),
            "decision_trace_projection": make_unavailable_section(reason=missing_reason),
            "gate_projection": make_unavailable_section(reason=missing_reason),
            "validation_projection": make_unavailable_section(reason=missing_reason),
            "authority_projection": make_unavailable_section(reason=missing_reason),
            "fallback_projection": make_unavailable_section(reason=missing_reason),
            "provenance_projection": make_unavailable_section(reason=missing_reason),
            "comparison_ready_fields": make_supported_section(
                {
                    "supported_now": [],
                    "reserved_for_future": list(_COMPARISON_RESERVED_FIELDS),
                    "status_note": "comparison engine not implemented in m1",
                }
            ),
        }

    turn_meta = canonical_record.get("turn_metadata")
    if not isinstance(turn_meta, dict):
        turn_meta = {}
    planner_data = {
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
    if not any(v is not None for v in planner_data.values()):
        planner_section = make_unavailable_section(
            reason="planner_surface_not_emitted_by_runtime_diagnostics_event",
            data=planner_data,
        )
    else:
        planner_section = make_supported_section(planner_data)

    graph = canonical_record.get("graph_diagnostics_summary")
    if not isinstance(graph, dict):
        graph = {}
    routing = canonical_record.get("routing")
    if not isinstance(routing, dict):
        routing = {}
    nodes = graph.get("nodes_executed") if isinstance(graph.get("nodes_executed"), list) else []
    flow_edges = []
    for idx in range(len(nodes) - 1):
        src = nodes[idx]
        dst = nodes[idx + 1]
        if isinstance(src, str) and isinstance(dst, str):
            flow_edges.append({"from": src, "to": dst})

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

    gate_data = {
        "gate_result": gate_outcome.get("gate_result"),
        "dominant_rejection_category": gate_outcome.get("dominant_rejection_category"),
        "rejection_codes": gate_outcome.get("rejection_reasons") if isinstance(gate_outcome.get("rejection_reasons"), list) else [],
        "legacy_fallback_used": gate_outcome.get("legacy_fallback_used"),
        "scene_function_mismatch_score": gate_outcome.get("scene_function_mismatch_score"),
        "character_implausibility_score": gate_outcome.get("character_implausibility_score"),
        "continuity_pressure_score": gate_outcome.get("continuity_pressure_score"),
        "fluency_risk_score": gate_outcome.get("fluency_risk_score"),
    }
    gate_section = (
        make_supported_section(gate_data)
        if gate_outcome
        else make_unavailable_section(
            reason="gate_outcome_not_present_in_validation_payload",
            data=gate_data,
        )
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
                "graph_path_summary": (
                    bundle.get("last_turn_repro_metadata") or {}
                ).get("graph_path_summary"),
                "adapter_invocation_mode": (
                    bundle.get("last_turn_repro_metadata") or {}
                ).get("adapter_invocation_mode"),
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
                    gate_outcome.get("legacy_fallback_reason")
                    or gate_outcome.get("legacy_fallback_rationale")
                ),
            }
        ),
        "provenance_projection": make_supported_section(
            {
                "entries": _build_provenance_entries(canonical_record=canonical_record, last_turn=last_turn),
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
                    "dominant_rejection_category": gate_data.get("dominant_rejection_category"),
                    "commit_applied": committed.get("commit_applied"),
                    "selected_scene_function": canonical_record.get("selected_scene_function"),
                    "pacing_mode": canonical_record.get("pacing_mode"),
                },
                "reserved_for_future": list(_COMPARISON_RESERVED_FIELDS),
            }
        ),
    }
    if gate_section["status"] == "unavailable":
        section_data["gate_projection"] = make_unsupported_section(
            reason="dramatic_gate_not_supported_for_this_turn_payload",
            data=gate_data,
        )
    return section_data


def build_inspector_turn_projection(
    *,
    session_id: str,
    trace_id: str,
    mode: str = "canonical",
) -> dict[str, Any]:
    """Return canonical single-turn projection and optional raw evidence envelope."""
    bundle = build_session_evidence_bundle(session_id=session_id, trace_id=trace_id)
    if bundle.get("error") == "backend_session_not_found":
        return bundle

    last_turn = _last_turn_from_bundle(bundle)
    canonical_record: dict[str, Any] | None = None
    if isinstance(last_turn, dict):
        canonical_record = build_operator_canonical_turn_record(
            _projectable_state(bundle=bundle, last_turn=last_turn)
        )

    sections = _build_sections(bundle=bundle, canonical_record=canonical_record, last_turn=last_turn)
    projection_status = "ok" if last_turn is not None else "partial"
    if bundle.get("world_engine_story_session_id") in (None, ""):
        projection_status = "partial"

    payload = build_inspector_turn_projection_root(
        trace_id=bundle.get("trace_id"),
        backend_session_id=str(bundle.get("backend_session_id") or session_id),
        world_engine_story_session_id=bundle.get("world_engine_story_session_id"),
        projection_status=projection_status,
        sections=sections,
        warnings=list(bundle.get("degraded_path_signals") or []),
        raw_evidence_refs={
            "source": "world_engine_diagnostics_session_bridge",
            "mode": mode,
        },
    )
    if mode == "raw":
        payload["raw_evidence"] = {
            "world_engine_state": bundle.get("world_engine_state"),
            "world_engine_diagnostics": bundle.get("world_engine_diagnostics"),
            "execution_truth": bundle.get("execution_truth"),
            "cross_layer_classifiers": bundle.get("cross_layer_classifiers"),
            "bridge_errors": bundle.get("bridge_errors"),
        }
    return payload
