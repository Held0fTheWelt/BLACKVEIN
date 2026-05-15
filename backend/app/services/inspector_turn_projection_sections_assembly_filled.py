"""Themen-Splits für ``build_inspector_projection_sections_filled`` (DS-047)."""

from __future__ import annotations

from typing import Any

from ai_stack.semantic_planner_effect_surface import support_level_for_module

from app.contracts.inspector_turn_projection import (
    make_supported_section,
    make_unavailable_section,
    make_unsupported_section,
)
from app.services.inspector_turn_projection_assembly_helpers import (
    build_authority_projection_data,
    build_decision_trace_data,
    build_fallback_projection_data,
    build_flow_nodes_list,
    build_provenance_projection_data,
    build_turn_identity_data,
    build_validation_projection_data,
    check_core_planner_data_empty,
    extract_committed_result,
    extract_graph_routing_context,
    extract_model_generation,
    extract_turn_metadata,
    extract_validation_payload,
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
        "interpreted_input": canonical_record.get("interpreted_input"),
        "interpreted_move": canonical_record.get("interpreted_move"),
        "player_input_kind": canonical_record.get("player_input_kind"),
        "player_action_committed": canonical_record.get("player_action_committed"),
        "player_speech_committed": canonical_record.get("player_speech_committed"),
        "narrator_response_expected": canonical_record.get("narrator_response_expected"),
        "npc_response_expected": canonical_record.get("npc_response_expected"),
        "scene_director_selection_source": canonical_record.get("scene_director_selection_source"),
        "planner_rationale_codes": canonical_record.get("planner_rationale_codes"),
        "legacy_keyword_scene_candidates_used": canonical_record.get("legacy_keyword_scene_candidates_used"),
        "npc_narrated_player_action_violation": canonical_record.get(
            "npc_narrated_player_action_violation"
        ),
        "intent_surface_diagnostics": canonical_record.get("intent_surface_diagnostics"),
        "semantic_move_kind": canonical_record.get("semantic_move_kind"),
        "scene_assessment": canonical_record.get("scene_assessment"),
        "selected_responder_set": canonical_record.get("selected_responder_set"),
        "selected_scene_function": canonical_record.get("selected_scene_function"),
        "pacing_mode": canonical_record.get("pacing_mode"),
        "silence_brevity_decision": canonical_record.get("silence_brevity_decision"),
        "scene_energy_target": canonical_record.get("scene_energy_target"),
        "scene_energy_transition": canonical_record.get("scene_energy_transition"),
        "scene_energy_validation": canonical_record.get("scene_energy_validation"),
    }
    if posture is not None:
        planner_data["support_posture"] = posture
    if check_core_planner_data_empty(planner_data) and posture is None:
        return make_unavailable_section(
            reason="planner_surface_not_emitted_by_runtime_diagnostics_event",
            data=planner_data,
        )
    return make_supported_section(planner_data)


def build_graph_routing_flow_context(
    canonical_record: dict[str, Any],
    bundle: dict[str, Any],
) -> tuple[dict[str, Any], dict[str, Any], list[Any], list[dict[str, str]]]:
    return extract_graph_routing_context(canonical_record, bundle)


def assemble_filled_inspector_sections(
    *,
    bundle: dict[str, Any],
    canonical_record: dict[str, Any],
    last_turn: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    turn_meta = extract_turn_metadata(canonical_record)
    module_id = bundle.get("module_id")
    support_level = support_level_for_module(str(module_id if isinstance(module_id, str) else ""))
    posture = support_posture(module_id=module_id)
    planner_section = build_planner_projection_section(canonical_record=canonical_record, module_id=module_id)
    graph, routing, nodes, flow_edges = build_graph_routing_flow_context(canonical_record, bundle)

    validation, gate_outcome = extract_validation_payload(canonical_record)
    committed = extract_committed_result(canonical_record)
    generation = extract_model_generation(last_turn)

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
        "turn_identity": make_supported_section(build_turn_identity_data(bundle, turn_meta)),
        "planner_state_projection": planner_section,
        "decision_trace_projection": make_supported_section(
            build_decision_trace_data(graph, routing, nodes, flow_edges, bundle, semantic_flow)
        ),
        "gate_projection": gate_section,
        "validation_projection": make_supported_section(
            build_validation_projection_data(
                validation,
                canonical_record,
                (bundle.get("last_turn_observability_path_summary") or {})
                if isinstance(bundle.get("last_turn_observability_path_summary"), dict)
                else {},
            )
        ),
        "authority_projection": make_supported_section(build_authority_projection_data(committed, canonical_record)),
        "fallback_projection": make_supported_section(
            build_fallback_projection_data(graph, routing, generation, gate_outcome)
        ),
        "provenance_projection": make_supported_section(
            {
                "entries": build_provenance_entries(canonical_record=canonical_record, last_turn=last_turn),
                **build_provenance_projection_data(canonical_record, last_turn),
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
                    "scene_energy_level": (
                        canonical_record.get("scene_energy_target", {}).get("energy_level")
                        if isinstance(canonical_record.get("scene_energy_target"), dict)
                        else None
                    ),
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
