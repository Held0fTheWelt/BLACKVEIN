"""Tests for Pi7 long-horizon NPC agency and claim readiness contracts."""

from __future__ import annotations

from ai_stack.npc_agency_claim_readiness import assess_npc_agency_claim_readiness
from ai_stack.npc_agency_contracts import (
    NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS,
    NPC_AGENCY_CLAIM_FULL_LONG_HORIZON_READY_STATUS,
    NPC_AGENCY_CLAIM_READINESS_SCHEMA_VERSION,
    NPC_AGENCY_CLOSURE_CLOSED_STATUS,
    NPC_AGENCY_CLOSURE_SCHEMA_VERSION,
    NPC_AGENCY_CLOSURE_SUPERSEDED_STATUS,
    NPC_INTENTION_THREAD_ACTIVE_STATUS,
    NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
    NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION,
    NPC_PRIVATE_PLAN_SCHEMA_VERSION,
)
from ai_stack.npc_agency_long_horizon import build_npc_long_horizon_state
from ai_stack.npc_agency_planner import build_npc_agency_simulation
from ai_stack.npc_agency_realization import (
    build_npc_agency_closure,
    validate_npc_initiative_realization,
)


def _actor_lane_context(actor_ids: list[str]) -> dict:
    return {
        "human_actor_id": "human_player",
        "ai_forbidden_actor_ids": ["human_player"],
        "npc_actor_ids": actor_ids,
        "ai_allowed_actor_ids": actor_ids,
    }


def _simulation(actor_ids: list[str]) -> dict:
    simulation = build_npc_agency_simulation(
        selected_responder_set=[
            {"actor_id": actor_id, "role": "primary_responder" if index == 0 else "secondary_reactor"}
            for index, actor_id in enumerate(actor_ids)
        ],
        actor_lane_context=_actor_lane_context(actor_ids),
        turn_number=7,
    )
    assert simulation is not None
    return simulation


def test_simulation_emits_long_horizon_private_plan_and_conflict_contracts() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    simulation = _simulation(actor_ids)

    long_state = simulation["npc_long_horizon_state"]
    private_plans = simulation["npc_private_plans"]
    conflict = simulation["npc_plan_conflict_resolution"]

    assert long_state["schema_version"] == NPC_LONG_HORIZON_STATE_SCHEMA_VERSION
    assert [row["actor_id"] for row in long_state["actor_states"]] == simulation["candidate_actor_ids"]
    assert len(long_state["intention_threads"]) == len(simulation["candidate_actor_ids"])
    assert {row["schema_version"] for row in private_plans} == {NPC_PRIVATE_PLAN_SCHEMA_VERSION}
    assert {row["actor_id"] for row in private_plans} == set(simulation["candidate_actor_ids"])
    assert conflict["schema_version"] == NPC_PLAN_CONFLICT_RESOLUTION_SCHEMA_VERSION
    assert set(conflict["visible_actor_ids"]).issubset(set(simulation["required_actor_ids"]))


def test_long_horizon_state_carries_prior_intention_threads() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    prior_thread_id = "npc_primary:intention:6"
    prior = {
        "npc_long_horizon_state": {
            "schema_version": NPC_LONG_HORIZON_STATE_SCHEMA_VERSION,
            "actor_states": [
                {
                    "actor_id": actor_ids[0],
                    "active_intention_thread_ids": [prior_thread_id],
                    "durable_goal_codes": ["prior_goal"],
                }
            ],
            "intention_threads": [
                {
                    "schema_version": "npc_intention_thread.v1",
                    "thread_id": prior_thread_id,
                    "actor_id": actor_ids[0],
                    "status": NPC_INTENTION_THREAD_ACTIVE_STATUS,
                }
            ],
        }
    }

    state = build_npc_long_horizon_state(
        _simulation(actor_ids),
        prior_planner_truth=prior,
        actor_lane_context=_actor_lane_context(actor_ids),
        turn_number=8,
    )

    assert state is not None
    actor_state = state["actor_states"][0]
    thread_ids = [row["thread_id"] for row in state["intention_threads"]]
    assert prior_thread_id in actor_state["active_intention_thread_ids"]
    assert prior_thread_id in thread_ids
    assert len(actor_state["active_intention_thread_ids"]) >= 2


def test_claim_readiness_requires_live_staging_before_full_claim() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    simulation = _simulation(actor_ids)
    structured_output = {
        "spoken_lines": [{"speaker_id": actor_id, "text": "contract evidence"} for actor_id in simulation["required_actor_ids"]],
        "action_lines": [],
        "initiative_events": [],
    }
    validation = validate_npc_initiative_realization(
        simulation,
        structured_output,
        actor_lane_context=_actor_lane_context(actor_ids),
    )
    closure = build_npc_agency_closure(
        simulation,
        validation=validation,
        actor_lane_context=_actor_lane_context(actor_ids),
        turn_number=7,
    )
    assert closure is not None
    assert closure["schema_version"] == NPC_AGENCY_CLOSURE_SCHEMA_VERSION
    assert closure["closure_status"] == NPC_AGENCY_CLOSURE_CLOSED_STATUS

    local_readiness = assess_npc_agency_claim_readiness(
        simulation=simulation,
        closure=closure,
        runtime_aspect={
            "independent_planning_used": True,
            "forbidden_actor_absent": True,
            "long_horizon_state_present": True,
            "private_plan_resolution_present": True,
            "private_plan_visibility_respected": True,
        },
        operator_evidence={"operator_npc_agency_breakdown_present": True},
        mcp_evidence={"runtime_aspect_matrix_present": True},
    )

    assert local_readiness["schema_version"] == NPC_AGENCY_CLAIM_READINESS_SCHEMA_VERSION
    assert local_readiness["claim_status"] == NPC_AGENCY_CLAIM_BOUNDED_RUNTIME_STATUS
    assert local_readiness["implementation_ready"] is True
    assert local_readiness["full_claim_allowed"] is False
    assert "live_staging_evidence_missing" in local_readiness["blockers"]

    live_readiness = assess_npc_agency_claim_readiness(
        simulation=simulation,
        closure=closure,
        runtime_aspect={
            "independent_planning_used": True,
            "forbidden_actor_absent": True,
            "long_horizon_state_present": True,
            "private_plan_resolution_present": True,
            "private_plan_visibility_respected": True,
        },
        live_trace_evidence={
            "live_trace_present": True,
            "non_mock_generation_pass": True,
            "fallback_used": False,
        },
        operator_evidence={"operator_npc_agency_breakdown_present": True},
        mcp_evidence={"runtime_aspect_matrix_present": True},
        replay_evidence={"player_visible_replay_present": True},
    )

    assert live_readiness["claim_status"] == NPC_AGENCY_CLAIM_FULL_LONG_HORIZON_READY_STATUS
    assert live_readiness["full_claim_allowed"] is True
    assert live_readiness["blockers"] == []


def test_selected_private_plan_actor_is_required_for_validation() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    simulation = _simulation(actor_ids)
    selected_actor_ids = simulation["npc_plan_conflict_resolution"]["visible_actor_ids"]
    structured_output = {
        "spoken_lines": [{"speaker_id": selected_actor_ids[0], "text": "contract evidence"}],
        "action_lines": [],
        "initiative_events": [],
    }

    validation = validate_npc_initiative_realization(
        simulation,
        structured_output,
        actor_lane_context=_actor_lane_context(actor_ids),
    )

    expected_missing = [actor_id for actor_id in selected_actor_ids if actor_id != selected_actor_ids[0]]
    assert validation["status"] == "rejected"
    assert validation["unrealized_selected_private_plan_actor_ids"] == expected_missing
    assert "npc_private_plan_selected_actor_unrealized" in validation["error_codes"]
    assert validation["private_plan_resolution_present"] is True


def test_closure_can_supersede_missing_required_actor_without_carry_forward() -> None:
    actor_ids = ["npc_primary", "npc_secondary"]
    simulation = _simulation(actor_ids)
    structured_output = {
        "spoken_lines": [{"speaker_id": simulation["required_actor_ids"][0], "text": "contract evidence"}],
        "action_lines": [],
        "initiative_events": [],
    }
    validation = validate_npc_initiative_realization(
        simulation,
        structured_output,
        actor_lane_context=_actor_lane_context(actor_ids),
    )
    superseded_actor_ids = validation["missing_required_actor_ids"]
    closure = build_npc_agency_closure(
        simulation,
        validation=validation,
        actor_lane_context=_actor_lane_context(actor_ids),
        turn_number=8,
        closure_context={"superseded_actor_ids": superseded_actor_ids},
    )

    assert closure is not None
    assert closure["closure_status"] == NPC_AGENCY_CLOSURE_SUPERSEDED_STATUS
    assert closure["superseded_actor_ids"] == superseded_actor_ids
    assert closure["unresolved_actor_ids"] == []
    assert closure["durable_carry_forward_required"] is False
