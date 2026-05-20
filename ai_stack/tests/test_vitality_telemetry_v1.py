"""Phase 5 vitality telemetry schema and semantics tests."""

from __future__ import annotations

from ai_stack.actor_survival_telemetry import build_actor_survival_telemetry
from ai_stack.story_runtime.npc_agency.npc_agency_contracts import (
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
)
from ai_stack.story_runtime.turn.runtime_turn_contracts import VITALITY_TELEMETRY_REQUIRED_FIELDS, VITALITY_TELEMETRY_SCHEMA_VERSION


def _base_state() -> dict:
    return {
        "turn_number": 7,
        "trace_id": "trace-v1",
        "raw_input": "...",
        "selected_responder_set": [
            {"actor_id": "veronique_vallon", "role": "primary_responder", "preferred_reaction_order": 0},
            {"actor_id": "michel_longstreet", "role": "secondary_reactor", "preferred_reaction_order": 1},
        ],
        "responder_id": "veronique_vallon",
        "secondary_responder_ids": ["michel_longstreet"],
        "spoken_lines": [
            {"speaker_id": "veronique_vallon", "text": "No."},
            {"speaker_id": "michel_longstreet", "text": "Listen."},
        ],
        "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
        "initiative_events": [{"actor_id": "michel_longstreet", "type": "interrupt", "target_id": "veronique_vallon"}],
        "generation": {
            "metadata": {
                "structured_output": {
                    "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "No."}],
                    "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
                    "initiative_events": [{"actor_id": "michel_longstreet", "type": "interrupt", "target_id": "veronique_vallon"}],
                }
            }
        },
        "visible_output_bundle": {
            "spoken_lines": [{"speaker_id": "veronique_vallon", "text": "No."}],
            "action_lines": [{"actor_id": "veronique_vallon", "text": "leans forward"}],
        },
        "pacing_mode": "thin_edge",
        "silence_brevity_decision": {"mode": "withheld"},
        "prior_planner_truth": {"carry_forward_tension_notes": "unresolved accusation"},
        "quality_class": "degraded",
        "degradation_signals": ["fallback_used", "retry_exhausted"],
    }


def test_vitality_telemetry_v1_contains_required_fields():
    telemetry = build_actor_survival_telemetry(
        _base_state(),
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=True,
    )
    vitality = telemetry["vitality_telemetry_v1"]
    assert vitality["schema_version"] == VITALITY_TELEMETRY_SCHEMA_VERSION
    missing = [field for field in VITALITY_TELEMETRY_REQUIRED_FIELDS if field not in vitality]
    assert not missing, f"Missing required vitality telemetry fields: {missing}"


def test_selected_realized_rendered_semantics_distinct_and_initiative_only_not_realized():
    state = _base_state()
    selected_actor_ids = [row["actor_id"] for row in state["selected_responder_set"]]
    primary_actor_id = selected_actor_ids[0]
    secondary_actor_ids = selected_actor_ids[1:]
    # Make secondary appear only in initiative; it should not be counted as realized actor.
    state["generation"]["metadata"]["structured_output"]["spoken_lines"] = [
        {"speaker_id": primary_actor_id, "text": "No."}
    ]
    state["generation"]["metadata"]["structured_output"]["action_lines"] = [
        {"actor_id": primary_actor_id, "text": "leans forward"}
    ]
    state["visible_output_bundle"]["spoken_lines"] = [{"speaker_id": primary_actor_id, "text": "No."}]
    state["visible_output_bundle"]["action_lines"] = [{"actor_id": primary_actor_id, "text": "leans forward"}]

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["selected_secondary_responder_ids"] == secondary_actor_ids
    for actor_id in secondary_actor_ids:
        assert actor_id not in vitality["realized_actor_ids"]
    assert vitality["realized_secondary_responder_ids"] == []
    assert vitality["rendered_actor_ids"] == [primary_actor_id]
    assert vitality["preferred_reaction_order_ids"] == selected_actor_ids
    assert vitality["reaction_order_divergence"] == "secondary_responder_nominated_not_realized_in_output"


def test_npc_initiative_realization_reports_current_simulation_missing_required_secondary():
    state = _base_state()
    selected_actor_ids = [row["actor_id"] for row in state["selected_responder_set"]]
    primary_actor_id = selected_actor_ids[0]
    secondary_actor_ids = selected_actor_ids[1:]
    agency_plan_adapter = {
        "primary_responder_id": primary_actor_id,
        "secondary_responder_ids": secondary_actor_ids,
        "required_actor_ids": selected_actor_ids,
        "minimum_secondary_initiatives_required": 1 if secondary_actor_ids else 0,
        "npc_initiatives": [
            {"actor_id": actor_id, "required": True}
            for actor_id in selected_actor_ids
        ],
    }
    agency_simulation = {
        "contract": NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
        "schema_version": NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
        "contract_status": NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
        "not_full_multi_agent_simulation": False,
        "independent_planning_used": True,
        "candidate_actor_ids": selected_actor_ids,
        "required_actor_ids": selected_actor_ids,
        "npc_intent_proposals": list(agency_plan_adapter["npc_initiatives"]),
        "npc_agency_plan": agency_plan_adapter,
    }
    state["dramatic_generation_packet"] = {
        "npc_agency_simulation": agency_simulation
    }
    state["generation"]["metadata"]["structured_output"]["spoken_lines"] = [
        {"speaker_id": primary_actor_id, "text": "No."}
    ]
    state["generation"]["metadata"]["structured_output"]["action_lines"] = [
        {"actor_id": primary_actor_id, "text": "leans forward"}
    ]
    state["visible_output_bundle"]["spoken_lines"] = [{"speaker_id": primary_actor_id, "text": "No."}]
    state["visible_output_bundle"]["action_lines"] = [{"actor_id": primary_actor_id, "text": "leans forward"}]

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    realization = telemetry["vitality_telemetry_v1"]["npc_initiative_realization_v1"]
    planned_actor_ids = [row["actor_id"] for row in agency_plan_adapter["npc_initiatives"]]
    realized_actor_ids = telemetry["vitality_telemetry_v1"]["realized_actor_ids"]
    expected_missing_ids = [actor_id for actor_id in planned_actor_ids if actor_id not in realized_actor_ids]
    expected_required_missing_ids = [
        actor_id for actor_id in agency_simulation["required_actor_ids"] if actor_id not in realized_actor_ids
    ]
    expected_initiative_event_actor_ids = [
        row["actor_id"]
        for row in state["generation"]["metadata"]["structured_output"]["initiative_events"]
    ]
    expected_multi_npc_realized = len(realization["realized_initiative_actor_ids"]) >= 2

    assert realization["schema_version"] == "npc_initiative_realization_v1"
    assert realization["contract_status"] == NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
    assert realization["not_full_multi_agent_simulation"] is False
    assert realization["independent_planning_used"] is True
    assert realization["candidate_actor_ids"] == agency_simulation["candidate_actor_ids"]
    assert realization["planned_actor_ids"] == planned_actor_ids
    assert realization["realized_initiative_actor_ids"] == realized_actor_ids
    assert realization["missing_initiative_actor_ids"] == expected_missing_ids
    assert realization["required_actor_ids"] == agency_simulation["required_actor_ids"]
    assert realization["unrealized_required_initiative_actor_ids"] == expected_required_missing_ids
    assert realization["preserved_initiative_event_actor_ids"] == expected_initiative_event_actor_ids
    assert realization["initiative_event_only_actor_ids"] == expected_missing_ids
    assert realization["multi_npc_initiative_realized"] is expected_multi_npc_realized


def test_stage_counts_do_not_mix_and_quality_distinction_is_visible():
    state = _base_state()
    state["quality_class"] = "weak_but_legal"
    state["degradation_signals"] = ["weak_signal_accepted"]
    state["visible_output_bundle"]["spoken_lines"] = []

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["generated_spoken_line_count"] >= vitality["validated_spoken_line_count"]
    assert vitality["rendered_spoken_line_count"] <= vitality["validated_spoken_line_count"]
    assert vitality["quality_class"] == "weak_but_legal"
    assert "weak_signal_accepted" in vitality["degradation_signals"]
    assert vitality["fallback_used"] is False


def test_sparse_input_recovery_applied_when_sparse_input_still_gets_response():
    state = _base_state()
    state["raw_input"] = "no"
    state["visible_output_bundle"]["spoken_lines"] = [{"speaker_id": "veronique_vallon", "text": "No."}]

    telemetry = build_actor_survival_telemetry(
        state,
        generation_ok=True,
        validation_ok=True,
        commit_applied=True,
        fallback_taken=False,
    )
    vitality = telemetry["vitality_telemetry_v1"]

    assert vitality["sparse_input_detected"] is True
    assert vitality["response_present"] is True
    assert vitality["sparse_input_recovery_applied"] is True
