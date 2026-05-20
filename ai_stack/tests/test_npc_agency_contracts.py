"""Tests for shared Pi7 NPC agency contracts and input adapters."""

from __future__ import annotations

from ai_stack.contracts.npc_agency_contracts import (
    normalize_npc_agency_plan,
)
from ai_stack.story_runtime.npc_agency.npc_agency_realization import validate_npc_initiative_realization


def _actor_fixture() -> dict[str, str]:
    return {
        "primary": "veronique_vallon",
        "secondary": "michel_longstreet",
        "human": "annette_reille",
        "visitor": "visitor",
    }


def test_normalize_rejects_old_initiatives_alias() -> None:
    actors = _actor_fixture()
    initiative_rows = [
        {
            "actor_id": actors["primary"],
            "intent": "press_scene_pressure",
            "resolved": False,
            "motivation_intensity": 0.8,
        },
        {
            "actor_id": actors["secondary"],
            "intent": "counter_scene_pressure",
            "resolved": True,
            "motivation_intensity": 0.4,
        },
    ]

    normalized = normalize_npc_agency_plan({"initiatives": initiative_rows})

    assert normalized is None


def test_normalize_excludes_human_and_visitor_from_planned_npc_actors() -> None:
    actors = _actor_fixture()
    actor_lane_context = {
        "human_actor_id": actors["human"],
        "ai_forbidden_actor_ids": [actors["human"]],
    }
    plan = {
        "primary_responder_id": actors["human"],
        "secondary_responder_ids": [actors["primary"], actors["visitor"]],
        "npc_initiatives": [
            {"actor_id": actors["human"], "intent": "forbidden"},
            {"actor_id": actors["primary"], "intent": "allowed"},
            {"actor_id": actors["visitor"], "intent": "forbidden"},
        ],
    }

    normalized = normalize_npc_agency_plan(plan, actor_lane_context=actor_lane_context)

    assert normalized is not None
    planned_actor_ids = [row["actor_id"] for row in normalized["npc_initiatives"]]
    forbidden_actor_ids = [actors["human"], actors["visitor"]]
    assert all(actor_id not in planned_actor_ids for actor_id in forbidden_actor_ids)
    assert actors["primary"] in planned_actor_ids
    assert normalized["primary_responder_id"] == actors["primary"]


def test_validate_rejects_missing_required_npc_initiative() -> None:
    actors = _actor_fixture()
    planned_actor_ids = [actors["primary"], actors["secondary"]]
    plan = normalize_npc_agency_plan(
        {},
        selected_primary_responder_id=planned_actor_ids[0],
        selected_secondary_responder_ids=planned_actor_ids[1:],
        preferred_reaction_order_ids=planned_actor_ids,
    )
    structured_output = {
        "spoken_lines": [{"speaker_id": actors["primary"], "text": "No."}],
        "action_lines": [],
        "initiative_events": [],
    }

    validation = validate_npc_initiative_realization(plan, structured_output)

    realized_actor_ids = [row["speaker_id"] for row in structured_output["spoken_lines"]]
    expected_missing = [
        actor_id for actor_id in plan["required_actor_ids"] if actor_id not in realized_actor_ids
    ]
    assert validation["status"] == "rejected"
    assert "npc_initiative_missing_required" in validation["error_codes"]
    assert validation["missing_required_actor_ids"] == expected_missing
    assert validation["npc_initiative_realization_v1"]["not_full_multi_agent_simulation"] is True


def test_validate_allows_npc_to_npc_target_when_required_actors_realize() -> None:
    actors = _actor_fixture()
    plan = normalize_npc_agency_plan(
        {
            "primary_responder_id": actors["primary"],
            "secondary_responder_ids": [actors["secondary"]],
            "npc_initiatives": [
                {"actor_id": actors["primary"], "target_actor_id": actors["secondary"], "required": True},
                {"actor_id": actors["secondary"], "target_actor_id": actors["primary"], "required": True},
            ],
        }
    )
    structured_output = {
        "spoken_lines": [
            {"speaker_id": row["actor_id"], "text": "Visible beat."}
            for row in plan["npc_initiatives"]
        ],
        "action_lines": [],
        "initiative_events": [],
    }

    validation = validate_npc_initiative_realization(plan, structured_output)

    planned_targets = [row["target_actor_id"] for row in plan["npc_initiatives"]]
    assert validation["status"] == "approved"
    assert validation["contract_pass"] is True
    assert planned_targets == [actors["secondary"], actors["primary"]]
