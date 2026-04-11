"""LangGraph runtime: package_output node logic (extracted from langgraph_runtime_executor)."""

from __future__ import annotations

from ai_stack.goc_turn_seams import build_diagnostics_refs
from ai_stack.langgraph_runtime_package_output_repro import build_repro_metadata_and_health
from ai_stack.langgraph_runtime_package_output_sections import (
    append_goc_validation_reject_failure_marker,
    build_dramatic_review_section,
    build_planner_state_projection,
    compute_experiment_preview_for_package_output,
)
from ai_stack.langgraph_runtime_state import RuntimeTurnState
from ai_stack.langgraph_runtime_tracking import _track
from ai_stack.operational_profile import build_operational_cost_hints_for_runtime_graph


def package_runtime_graph_output(
    state: RuntimeTurnState,
    *,
    graph_name: str,
    graph_version: str,
) -> RuntimeTurnState:
    fallback_taken = "fallback_model" in state.get("nodes_executed", [])
    update = _track(state, node_name="package_output")
    routing = state.get("routing") or {}
    retrieval = state.get("retrieval") or {}
    generation = state.get("generation") or {}
    repro_metadata, execution_health, repro_ok = build_repro_metadata_and_health(
        state,
        graph_name=graph_name,
        graph_version=graph_version,
        fallback_taken=fallback_taken,
    )
    graph_errors = list(state.get("graph_errors", []))

    failure_markers = list(state.get("failure_markers") or [])
    module_id = state.get("module_id") or ""
    validation = state.get("validation_outcome") if isinstance(state.get("validation_outcome"), dict) else {}
    committed = state.get("committed_result") if isinstance(state.get("committed_result"), dict) else {}

    append_goc_validation_reject_failure_marker(
        module_id=module_id,
        validation=validation,
        failure_markers=failure_markers,
    )

    experiment_preview = compute_experiment_preview_for_package_output(
        state=state,
        module_id=module_id,
        validation=validation,
        committed=committed,
        failure_markers=failure_markers,
    )

    cost_hints = build_operational_cost_hints_for_runtime_graph(
        retrieval=retrieval if isinstance(retrieval, dict) else {},
        generation=generation if isinstance(generation, dict) else {},
        graph_execution_health=execution_health,
        model_prompt=state.get("model_prompt") if isinstance(state.get("model_prompt"), str) else None,
        fallback_path_taken=fallback_taken,
    )
    vo = validation
    gd = {
        "graph_name": graph_name,
        "graph_version": graph_version,
        "nodes_executed": update["nodes_executed"],
        "node_outcomes": update["node_outcomes"],
        "fallback_path_taken": fallback_taken,
        "execution_health": execution_health,
        "errors": graph_errors,
        "capability_audit": state.get("capability_audit", []),
        "repro_metadata": repro_metadata,
        "operational_cost_hints": cost_hints,
        "dramatic_review": build_dramatic_review_section(state, vo),
        "planner_state_projection": build_planner_state_projection(state),
    }
    update["graph_diagnostics"] = gd
    update["experiment_preview"] = experiment_preview
    tp = state.get("transition_pattern") or "diagnostics_only"
    alignment_note = gd["dramatic_review"]["dramatic_alignment_summary"]
    refs = build_diagnostics_refs(
        graph_diagnostics=gd,
        experiment_preview=experiment_preview,
        transition_pattern=str(tp),
        gate_hints={
            "turn_integrity": "seams_materialized_in_graph",
            "diagnostic_sufficiency": "repro_complete" if repro_ok else "repro_incomplete",
            "dramatic_quality": alignment_note,
            "slice_boundary": "no_scope_breach_marker"
            if not any(
                isinstance(m, dict) and m.get("failure_class") == "scope_breach"
                for m in (failure_markers or [])
            )
            else "scope_breach_recorded",
        },
    )
    update["diagnostics_refs"] = refs
    update["failure_markers"] = failure_markers
    routing_final = dict(state.get("routing") or {})
    routing_final["fallback_stage_reached"] = "graph_fallback_executed" if fallback_taken else "primary_only"
    update["routing"] = routing_final
    return update
