"""Helper utilities for inspector assembly (DS-006 refactor)."""

from __future__ import annotations

from typing import Any


def extract_dict_safe(value: Any, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Extract dictionary or return safe default.

    Args:
        value: Value to check.
        default: Default dict if value is not a dict (default: empty dict).

    Returns:
        Dictionary value or default.
    """
    if default is None:
        default = {}
    return value if isinstance(value, dict) else default


def extract_list_safe(value: Any, default: list[Any] | None = None) -> list[Any]:
    """Extract list or return safe default.

    Args:
        value: Value to check.
        default: Default list if value is not a list (default: empty list).

    Returns:
        List value or default.
    """
    if default is None:
        default = []
    return value if isinstance(value, list) else default


def extract_turn_metadata(canonical_record: dict[str, Any]) -> dict[str, Any]:
    """Extract turn metadata from canonical record.

    Args:
        canonical_record: The canonical event record.

    Returns:
        Turn metadata dictionary (guaranteed dict).
    """
    return extract_dict_safe(canonical_record.get("turn_metadata"))


def extract_validation_payload(canonical_record: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Extract validation outcome and gate outcome from canonical record.

    Args:
        canonical_record: The canonical event record.

    Returns:
        Tuple of (validation_dict, gate_outcome_dict), both guaranteed dicts.
    """
    validation = extract_dict_safe(canonical_record.get("validation_outcome"))
    gate_outcome = extract_dict_safe(validation.get("dramatic_effect_gate_outcome"))
    return validation, gate_outcome


def extract_committed_result(canonical_record: dict[str, Any]) -> dict[str, Any]:
    """Extract committed result from canonical record.

    Args:
        canonical_record: The canonical event record.

    Returns:
        Committed result dictionary (guaranteed dict).
    """
    return extract_dict_safe(canonical_record.get("committed_result"))


def extract_model_generation(last_turn: dict[str, Any]) -> dict[str, Any]:
    """Extract model generation info from last turn.

    Args:
        last_turn: The previous turn's context.

    Returns:
        Generation dictionary (guaranteed dict).
    """
    model_route = extract_dict_safe(last_turn.get("model_route"))
    return extract_dict_safe(model_route.get("generation"))


def extract_graph_routing_context(
    canonical_record: dict[str, Any],
    bundle: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Any], list[dict[str, str]]]:
    """Extract and normalize graph and routing context.

    Builds flow edges from consecutive nodes in the execution path.

    Args:
        canonical_record: The canonical event record.
        bundle: The event bundle (used for fallback metadata).

    Returns:
        Tuple of (graph_dict, routing_dict, nodes_list, flow_edges_list).
        All collections are guaranteed safe types.
    """
    graph = extract_dict_safe(canonical_record.get("graph_diagnostics_summary"))
    routing = extract_dict_safe(canonical_record.get("routing"))
    nodes = extract_list_safe(graph.get("nodes_executed"))

    # Build flow edges from node execution sequence
    flow_edges: list[dict[str, str]] = []
    for idx in range(len(nodes) - 1):
        src = nodes[idx]
        dst = nodes[idx + 1]
        if isinstance(src, str) and isinstance(dst, str):
            flow_edges.append({"from": src, "to": dst})

    return graph, routing, nodes, flow_edges


def extract_committed_effect_count(committed: dict[str, Any]) -> int:
    """Extract committed effect count safely.

    Args:
        committed: Committed result dictionary.

    Returns:
        Count of committed effects (0 if not a valid list).
    """
    effects = committed.get("committed_effects")
    return len(effects) if isinstance(effects, list) else 0


def check_core_planner_data_empty(planner_data: dict[str, Any]) -> bool:
    """Check if core planner data is completely empty.

    Args:
        planner_data: Dictionary of planner data fields.

    Returns:
        True if all core fields are None/missing.
    """
    core_keys = (
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
    return not any(planner_data.get(k) is not None for k in core_keys)


def build_flow_nodes_list(nodes: list[Any]) -> list[str]:
    """Extract only string nodes from node list.

    Args:
        nodes: Raw nodes list.

    Returns:
        List of string nodes only.
    """
    return [node for node in nodes if isinstance(node, str)]


def build_turn_identity_data(
    bundle: dict[str, Any],
    turn_meta: dict[str, Any],
) -> dict[str, Any]:
    """Build turn identity projection data.

    Args:
        bundle: The event bundle.
        turn_meta: Turn metadata.

    Returns:
        Turn identity data dictionary.
    """
    return {
        "backend_session_id": bundle.get("backend_session_id"),
        "world_engine_story_session_id": bundle.get("world_engine_story_session_id"),
        "module_id": bundle.get("module_id"),
        "current_scene_id": bundle.get("current_scene_id"),
        "turn_number_backend": bundle.get("turn_counter_backend"),
        "turn_number_world_engine": turn_meta.get("turn_number"),
        "turn_trace_id": turn_meta.get("trace_id"),
    }


def build_decision_trace_data(
    graph: dict[str, Any],
    routing: dict[str, Any],
    nodes: list[Any],
    flow_edges: list[dict[str, str]],
    bundle: dict[str, Any],
    semantic_flow: Any,
) -> dict[str, Any]:
    """Build decision trace projection data.

    Args:
        graph: Graph diagnostics.
        routing: Routing information.
        nodes: Node execution list.
        flow_edges: Flow edges list.
        bundle: Event bundle.
        semantic_flow: Semantic decision flow.

    Returns:
        Decision trace data dictionary.
    """
    flow_nodes = build_flow_nodes_list(nodes)
    observability_path_summary = (
        bundle.get("last_turn_observability_path_summary")
        if isinstance(bundle.get("last_turn_observability_path_summary"), dict)
        else {}
    )
    intent_evidence = {
        "player_input_kind": observability_path_summary.get("player_input_kind"),
        "player_action_committed": observability_path_summary.get("player_action_committed"),
        "player_speech_committed": observability_path_summary.get("player_speech_committed"),
        "narrator_response_expected": observability_path_summary.get("narrator_response_expected"),
        "npc_response_expected": observability_path_summary.get("npc_response_expected"),
        "semantic_move_kind": observability_path_summary.get("semantic_move_kind"),
        "scene_director_selection_source": observability_path_summary.get(
            "scene_director_selection_source"
        ),
        "planner_rationale_codes": observability_path_summary.get("planner_rationale_codes"),
        "legacy_keyword_scene_candidates_used": observability_path_summary.get(
            "legacy_keyword_scene_candidates_used"
        ),
        "npc_narrated_player_action_violation": observability_path_summary.get(
            "npc_narrated_player_action_violation"
        ),
        "intent_surface_contract_pass": observability_path_summary.get(
            "intent_surface_contract_pass"
        ),
        "player_input_attribution_pass": observability_path_summary.get(
            "player_input_attribution_pass"
        ),
        "semantic_move_alignment_pass": observability_path_summary.get(
            "semantic_move_alignment_pass"
        ),
        "npc_action_narration_boundary_pass": observability_path_summary.get(
            "npc_action_narration_boundary_pass"
        ),
    }
    return {
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
        "intent_surface_evidence": intent_evidence,
        "semantic_decision_flow": semantic_flow,
        "graph_execution_flow": {
            "flow_nodes": flow_nodes,
            "flow_edges": flow_edges,
        },
        "flow_nodes": flow_nodes,
        "flow_edges": flow_edges,
    }


def build_validation_projection_data(
    validation: dict[str, Any],
    canonical_record: dict[str, Any],
    observability_path_summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build validation projection data.

    Args:
        validation: Validation outcome dictionary.

    Returns:
        Validation projection data.
    """
    intent_surface = extract_dict_safe(canonical_record.get("interpreted_input"))
    intent_diag = extract_dict_safe(validation.get("intent_surface_diagnostics"))
    path_summary = extract_dict_safe(observability_path_summary)
    planner_rationale = canonical_record.get("planner_rationale_codes")
    if not isinstance(planner_rationale, list):
        planner_rationale = path_summary.get("planner_rationale_codes")
    if not isinstance(planner_rationale, list):
        planner_rationale = []
    return {
        "status": validation.get("status"),
        "reason": validation.get("reason"),
        "validator_lane": validation.get("validator_lane"),
        "dramatic_quality_gate": validation.get("dramatic_quality_gate"),
        "dramatic_effect_weak_signal": validation.get("dramatic_effect_weak_signal"),
        "intent_surface_diagnostics": intent_diag,
        "npc_narrated_player_action_violation": bool(intent_diag.get("npc_narrated_player_action_violation")),
        "player_input_kind": canonical_record.get("player_input_kind")
        or intent_surface.get("player_input_kind"),
        "player_action_committed": bool(canonical_record.get("player_action_committed"))
        or bool(intent_surface.get("player_action_committed")),
        "player_speech_committed": bool(canonical_record.get("player_speech_committed"))
        or bool(intent_surface.get("player_speech_committed")),
        "narrator_response_expected": bool(canonical_record.get("narrator_response_expected"))
        or bool(intent_surface.get("narrator_response_expected")),
        "npc_response_expected": bool(canonical_record.get("npc_response_expected"))
        or bool(intent_surface.get("npc_response_expected")),
        "semantic_move_kind": canonical_record.get("semantic_move_kind")
        or path_summary.get("semantic_move_kind"),
        "scene_director_selection_source": canonical_record.get("scene_director_selection_source")
        or path_summary.get("scene_director_selection_source"),
        "planner_rationale_codes": planner_rationale,
        "legacy_keyword_scene_candidates_used": (
            canonical_record.get("legacy_keyword_scene_candidates_used")
            if canonical_record.get("legacy_keyword_scene_candidates_used") is not None
            else path_summary.get("legacy_keyword_scene_candidates_used")
        ),
        "intent_surface_contract_pass": path_summary.get("intent_surface_contract_pass"),
        "player_input_attribution_pass": path_summary.get("player_input_attribution_pass"),
        "semantic_move_alignment_pass": path_summary.get("semantic_move_alignment_pass"),
        "npc_action_narration_boundary_pass": path_summary.get(
            "npc_action_narration_boundary_pass"
        ),
    }


def build_authority_projection_data(
    committed: dict[str, Any],
    canonical_record: dict[str, Any],
) -> dict[str, Any]:
    """Build authority projection data.

    Args:
        committed: Committed result dictionary.
        canonical_record: The canonical event record.

    Returns:
        Authority projection data.
    """
    return {
        "authoritative_surface": "world_engine_session_commit_state",
        "commit_applied": committed.get("commit_applied"),
        "committed_effect_count": extract_committed_effect_count(committed),
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


def build_fallback_projection_data(
    graph: dict[str, Any],
    routing: dict[str, Any],
    generation: dict[str, Any],
    gate_outcome: dict[str, Any],
) -> dict[str, Any]:
    """Build fallback projection data.

    Args:
        graph: Graph diagnostics.
        routing: Routing information.
        generation: Model generation info.
        gate_outcome: Gate outcome dictionary.

    Returns:
        Fallback projection data.
    """
    return {
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


def build_provenance_projection_data(
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, Any]:
    """Build provenance projection data.

    Requires build_provenance_entries to be imported separately.

    Args:
        canonical_record: The canonical event record.
        last_turn: The previous turn's context.

    Returns:
        Provenance projection data with entries key (caller must populate).
    """
    return {
        "note": "deterministic projections only; no narrative synthesis",
    }
