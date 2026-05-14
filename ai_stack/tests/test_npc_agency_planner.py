"""Tests for deterministic Pi7 NPC agency planning."""

from __future__ import annotations

from ai_stack.npc_agency_contracts import (
    NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS,
    NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
    NPC_AGENCY_PLAN_PARTIAL_STATUS,
    NPC_AGENCY_PLANNER_SCOPE_INDEPENDENT,
    NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS,
    NPC_AGENCY_SIMULATION_SCHEMA_VERSION,
    npc_actor_ids_from_context,
)
from ai_stack.npc_agency_planner import (
    NPC_AGENCY_PLANNER_CONTRACT,
    NPC_AGENCY_SIMULATION_PLANNER_CONTRACT,
    build_npc_agency_plan,
    build_npc_agency_simulation,
)
from ai_stack.npc_agency_realization import (
    build_npc_agency_closure,
    validate_npc_initiative_realization,
)


def _planner_fixture() -> dict:
    actors = {
        "primary": "veronique_vallon",
        "secondary": "michel_longstreet",
        "optional": "alain_reille",
        "human": "annette_reille",
        "visitor": "visitor",
    }
    responders = [
        {"actor_id": actors["primary"], "role": "primary_responder", "preferred_reaction_order": 0},
        {"actor_id": actors["secondary"], "role": "secondary_reactor", "preferred_reaction_order": 1},
        {"actor_id": actors["optional"], "role": "interruption_candidate", "preferred_reaction_order": 2},
    ]
    minds = [
        {"runtime_actor_id": row["actor_id"], "tactical_posture": row["role"], "pressure_response_bias": row["role"]}
        for row in responders
    ]
    return {
        "actors": actors,
        "responders": responders,
        "minds": minds,
        "actor_lane_context": {
            "human_actor_id": actors["human"],
            "ai_forbidden_actor_ids": [actors["human"]],
            "ai_allowed_actor_ids": [row["actor_id"] for row in responders],
            "npc_actor_ids": [row["actor_id"] for row in responders],
        },
        "semantic_move_record": {"move_type": "scene_pressure"},
        "social_state_record": {"social_pressure_shift": "contested"},
    }


def _actor_ids(rows: list[dict]) -> list[str]:
    return [row["actor_id"] for row in rows]


def test_planner_builds_partial_plan_from_responder_and_mind_surfaces() -> None:
    fixture = _planner_fixture()
    expected_actor_ids = _actor_ids(fixture["responders"])

    plan = build_npc_agency_plan(
        selected_responder_set=fixture["responders"],
        turn_number=fixture["turn_number"] if "turn_number" in fixture else 3,
        character_mind_records=fixture["minds"],
        semantic_move_record=fixture["semantic_move_record"],
        social_state_record=fixture["social_state_record"],
        selected_scene_function="escalate_conflict",
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert plan is not None
    initiatives = plan["npc_initiatives"]
    assert plan["planner_contract"] == NPC_AGENCY_PLANNER_CONTRACT
    assert plan["planner_status"] == NPC_AGENCY_PLAN_PARTIAL_STATUS
    assert plan["contract_status"] == NPC_AGENCY_PLAN_PARTIAL_STATUS
    assert plan["not_full_multi_agent_simulation"] is True
    assert [row["actor_id"] for row in initiatives] == expected_actor_ids
    assert plan["primary_responder_id"] == expected_actor_ids[0]
    assert plan["secondary_responder_ids"] == expected_actor_ids[1:]
    assert plan["required_actor_ids"] == expected_actor_ids[:2]
    assert [row["tactical_posture"] for row in initiatives] == [row["role"] for row in fixture["responders"]]


def test_planner_excludes_human_and_visitor_before_contract_normalization() -> None:
    fixture = _planner_fixture()
    actors = fixture["actors"]
    responders = [
        *fixture["responders"],
        {"actor_id": actors["human"], "role": "forbidden", "preferred_reaction_order": 3},
        {"actor_id": actors["visitor"], "role": "forbidden", "preferred_reaction_order": 4},
    ]

    plan = build_npc_agency_plan(
        selected_responder_set=responders,
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert plan is not None
    planned_actor_ids = [row["actor_id"] for row in plan["npc_initiatives"]]
    forbidden_actor_ids = [actors["human"], actors["visitor"]]
    assert all(actor_id not in planned_actor_ids for actor_id in forbidden_actor_ids)
    assert planned_actor_ids == _actor_ids(fixture["responders"])


def test_planner_marks_prior_unresolved_npc_initiative_as_required() -> None:
    fixture = _planner_fixture()
    expected_actor_ids = _actor_ids(fixture["responders"])
    carry_actor_id = expected_actor_ids[-1]
    prior = {
        "unresolved_npc_initiatives": [
            {"actor_id": carry_actor_id, "reason": "prior_required_not_realized"}
        ]
    }

    plan = build_npc_agency_plan(
        selected_responder_set=fixture["responders"],
        prior_planner_truth=prior,
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert plan is not None
    carried_rows = [row for row in plan["npc_initiatives"] if row["actor_id"] == carry_actor_id]
    assert carried_rows
    assert carry_actor_id in plan["required_actor_ids"]
    assert carried_rows[0]["required"] is True
    assert carried_rows[0]["requirement_scope"] == "carry_forward_required"
    assert "unresolved_npc_initiative_carried_forward" in plan["planner_rationale_codes"]


def test_planner_records_structural_source_evidence_without_story_text_oracles() -> None:
    fixture = _planner_fixture()
    expected_sources = {
        "selected_scene_function",
        "semantic_move_record",
        "social_state_record",
        "prior_planner_truth",
    }
    prior = {"carry_forward_tension_notes": "present"}

    plan = build_npc_agency_plan(
        selected_responder_set=fixture["responders"],
        semantic_move_record=fixture["semantic_move_record"],
        social_state_record=fixture["social_state_record"],
        selected_scene_function="probe_motive",
        prior_planner_truth=prior,
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert plan is not None
    source_names = {row["source"] for row in plan["source_evidence"]}
    initiative_source_names = {
        source["source"]
        for initiative in plan["npc_initiatives"]
        for source in initiative["source_evidence"]
    }
    assert expected_sources.issubset(source_names)
    assert source_names == initiative_source_names


def test_simulation_uses_actor_lane_roster_as_current_contract() -> None:
    fixture = _planner_fixture()
    expected_candidate_ids = npc_actor_ids_from_context(fixture["actor_lane_context"])

    simulation = build_npc_agency_simulation(
        selected_responder_set=fixture["responders"][:2],
        turn_number=3,
        character_mind_records=fixture["minds"],
        semantic_move_record=fixture["semantic_move_record"],
        social_state_record=fixture["social_state_record"],
        selected_scene_function="escalate_conflict",
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert simulation is not None
    assert simulation["schema_version"] == NPC_AGENCY_SIMULATION_SCHEMA_VERSION
    assert simulation["contract_status"] == NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
    assert simulation["planner_contract"] == NPC_AGENCY_SIMULATION_PLANNER_CONTRACT
    assert simulation["planner_scope"] == NPC_AGENCY_PLANNER_SCOPE_INDEPENDENT
    assert simulation["not_full_multi_agent_simulation"] is False
    assert simulation["independent_planning_used"] is True
    assert simulation["candidate_actor_ids"] == expected_candidate_ids
    assert {row["actor_id"] for row in simulation["npc_intent_proposals"]} == set(expected_candidate_ids)
    assert set(simulation["required_actor_ids"]).issubset(set(expected_candidate_ids))


def test_simulation_does_not_activate_from_roster_without_npc_pressure() -> None:
    fixture = _planner_fixture()

    simulation = build_npc_agency_simulation(
        selected_responder_set=[],
        character_mind_records=fixture["minds"],
        actor_lane_context=fixture["actor_lane_context"],
        npc_actor_ids=npc_actor_ids_from_context(fixture["actor_lane_context"]),
    )

    assert simulation is None


def test_simulation_respects_explicit_no_npc_response_signal() -> None:
    fixture = _planner_fixture()

    simulation = build_npc_agency_simulation(
        selected_responder_set=fixture["responders"][:2],
        character_mind_records=fixture["minds"],
        actor_lane_context=fixture["actor_lane_context"],
        npc_actor_ids=npc_actor_ids_from_context(fixture["actor_lane_context"]),
        npc_response_expected=False,
    )

    assert simulation is None


def test_simulation_carries_forward_unresolved_actor_outside_selected_responders() -> None:
    fixture = _planner_fixture()
    carry_actor_id = fixture["actors"]["optional"]
    prior = {
        "npc_agency_closure": {
            "carried_forward_npc_initiatives": [{"actor_id": carry_actor_id}]
        }
    }

    simulation = build_npc_agency_simulation(
        selected_responder_set=fixture["responders"][:2],
        character_mind_records=fixture["minds"],
        prior_planner_truth=prior,
        actor_lane_context=fixture["actor_lane_context"],
    )

    assert simulation is not None
    carried = [
        row
        for row in simulation["npc_intent_proposals"]
        if row["actor_id"] == carry_actor_id
    ]
    assert carried
    assert carry_actor_id in simulation["required_actor_ids"]
    assert carry_actor_id in simulation["carry_forward_actor_ids"]
    assert carried[0]["required"] is True
    assert carried[0]["requirement_scope"] == "carry_forward_required"


def test_simulation_validation_builds_durable_carry_forward_closure() -> None:
    fixture = _planner_fixture()
    simulation = build_npc_agency_simulation(
        selected_responder_set=fixture["responders"][:2],
        character_mind_records=fixture["minds"],
        actor_lane_context=fixture["actor_lane_context"],
    )
    assert simulation is not None
    primary_id = simulation["required_actor_ids"][0]
    structured_output = {
        "spoken_lines": [{"speaker_id": primary_id, "text": "contract fixture"}],
        "action_lines": [],
        "initiative_events": [],
    }

    validation = validate_npc_initiative_realization(
        simulation,
        structured_output,
        actor_lane_context=fixture["actor_lane_context"],
        strict_required=True,
    )
    closure = build_npc_agency_closure(
        simulation,
        validation=validation,
        actor_lane_context=fixture["actor_lane_context"],
        turn_number=4,
    )

    assert validation["contract_status"] == NPC_AGENCY_SIMULATION_IMPLEMENTED_STATUS
    assert validation["not_full_multi_agent_simulation"] is False
    assert closure is not None
    assert closure["schema_version"] == NPC_AGENCY_CLOSURE_SCHEMA_VERSION
    assert closure["closure_status"] == NPC_AGENCY_CLOSURE_CARRY_FORWARD_STATUS
    assert closure["unresolved_actor_ids"] == validation["missing_required_actor_ids"]
