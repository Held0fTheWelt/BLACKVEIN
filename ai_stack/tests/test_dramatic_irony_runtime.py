from __future__ import annotations

import json

from ai_stack.contracts.dramatic_irony_contracts import (
    DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
    DRAMATIC_IRONY_STATUS_SELECTED,
    DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
    DRAMATIC_IRONY_VIOLATION_FORBIDDEN_SURFACE_MODE,
    DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO,
)
from ai_stack.dramatic_irony_runtime import (
    DIRECT_HIDDEN_INTENT_VIOLATION,
    build_dramatic_irony_record,
    compact_dramatic_irony_context,
    validate_dramatic_irony_realization,
)


def _runtime_private_plan_simulation() -> dict:
    actor_ids = ["actor_primary", "actor_secondary"]
    selected_plan_id = f"{actor_ids[0]}:private_plan:fixture_turn"
    withheld_plan_id = f"{actor_ids[1]}:private_plan:fixture_turn"
    return {
        "schema_version": "npc_agency_simulation.v1",
        "candidate_actor_ids": actor_ids,
        "ordered_actor_ids": actor_ids,
        "npc_private_plans": [
            {
                "schema_version": "npc_private_plan.v1",
                "private_plan_id": selected_plan_id,
                "actor_id": actor_ids[0],
                "intent": "claim_scene_pressure",
                "target_actor_id": actor_ids[1],
                "required": True,
                "requirement_scope": "primary_required",
                "visible_resolution_policy": "visible_spoken_or_action_lane_required",
                "private_plan_visibility": "resolver_may_surface_visible_lane",
            },
            {
                "schema_version": "npc_private_plan.v1",
                "private_plan_id": withheld_plan_id,
                "actor_id": actor_ids[1],
                "intent": "react_to_primary_or_scene_pressure",
                "target_actor_id": actor_ids[0],
                "required": False,
                "requirement_scope": "optional_selected_responder",
                "visible_resolution_policy": "optional_visible_or_initiative_event",
                "private_plan_visibility": "resolver_may_surface_visible_lane",
            },
        ],
        "npc_plan_conflict_resolution": {
            "schema_version": "npc_plan_conflict_resolution.v1",
            "selected_private_plan_ids": [selected_plan_id],
            "withheld_private_plan_ids": [withheld_plan_id],
            "visible_actor_ids": [actor_ids[0]],
        },
    }


def test_dramatic_irony_record_derives_opportunities_from_selected_private_plans() -> None:
    simulation = _runtime_private_plan_simulation()
    actor_ids = list(simulation["candidate_actor_ids"])

    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": actor_ids},
        selected_responder_set=[{"actor_id": actor_id} for actor_id in actor_ids],
        social_state_record={"social_risk_band": "high"},
        semantic_move_record={"move_type": "pressure_response"},
        selected_scene_function="probe_motive",
        npc_agency_simulation=simulation,
    )

    selected_private_plan_ids = set(
        simulation["npc_plan_conflict_resolution"]["selected_private_plan_ids"]
    )
    selected_fact_plan_ids = {
        fact["provenance"]["private_plan_id"] for fact in record["facts"]
    }
    assert record["status"] == DRAMATIC_IRONY_STATUS_SELECTED
    assert selected_fact_plan_ids == selected_private_plan_ids
    assert {fact["source"] for fact in record["facts"]} == {
        DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED
    }
    assert record["selected_opportunity_ids"]

    facts_by_id = {fact["fact_id"]: fact for fact in record["facts"]}
    for opportunity in record["opportunities"]:
        fact = facts_by_id[opportunity["fact_id"]]
        assert opportunity["ignorant_actor_id"] in fact["unknown_to_actor_ids"]
        assert opportunity["ignorant_actor_id"] not in fact["known_by_actor_ids"]
        assert opportunity["allowed_surface_mode"] in record["policy"]["allowed_surface_modes"]


def test_dramatic_irony_validation_rejects_direct_hidden_intent_reveal() -> None:
    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": _runtime_private_plan_simulation()["candidate_actor_ids"]},
        selected_responder_set=[
            {"actor_id": actor_id}
            for actor_id in _runtime_private_plan_simulation()["candidate_actor_ids"]
        ],
        npc_agency_simulation=_runtime_private_plan_simulation(),
    )
    known_actor = record["facts"][0]["known_by_actor_ids"][0]
    generation = {
        "content": f"{known_actor} secretly plans to use the room as leverage."
    }

    validation = validate_dramatic_irony_realization(
        record=record,
        generation=generation,
        proposed_state_effects=[],
    )

    assert validation["status"] == "rejected"
    assert DIRECT_HIDDEN_INTENT_VIOLATION in validation["violation_codes"]
    assert validation["leak_blocked"] is True
    assert validation["contract_pass"] is False


def test_dramatic_irony_validation_blocks_source_derived_private_plan_echo() -> None:
    simulation = _runtime_private_plan_simulation()
    actor_ids = simulation["candidate_actor_ids"]
    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": actor_ids},
        selected_responder_set=[{"actor_id": actor_id} for actor_id in actor_ids],
        npc_agency_simulation=simulation,
    )
    selected_plan_id = simulation["npc_plan_conflict_resolution"]["selected_private_plan_ids"][0]
    selected_plan = next(
        row
        for row in simulation["npc_private_plans"]
        if row["private_plan_id"] == selected_plan_id
    )
    known_actor = record["facts"][0]["known_by_actor_ids"][0]
    intent_phrase = selected_plan["intent"].replace("_", " ")
    generation = {
        "content": f"{known_actor} plans to {intent_phrase}.",
    }

    validation = validate_dramatic_irony_realization(
        record=record,
        generation=generation,
        proposed_state_effects=[],
    )

    assert validation["status"] == "rejected"
    assert DRAMATIC_IRONY_VIOLATION_HIDDEN_FACT_ECHO in validation["violation_codes"]
    assert validation["leak_blocked"] is True
    assert validation["hidden_fact_echo_absent"] is False


def test_dramatic_irony_realization_accepts_structured_bounded_reference() -> None:
    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": _runtime_private_plan_simulation()["candidate_actor_ids"]},
        selected_responder_set=[
            {"actor_id": actor_id}
            for actor_id in _runtime_private_plan_simulation()["candidate_actor_ids"]
        ],
        npc_agency_simulation=_runtime_private_plan_simulation(),
    )
    selected_id = record["selected_opportunity_ids"][0]
    generation = {
        "metadata": {
            "structured_output": {
                "dramatic_irony_opportunity_ids": [selected_id],
                "dramatic_irony_surface_mode": DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
                "spoken_lines": [
                    {
                        "speaker_id": record["facts"][0]["known_by_actor_ids"][0],
                        "text": "Not yet.",
                    }
                ],
            }
        }
    }

    validation = validate_dramatic_irony_realization(
        record=record,
        generation=generation,
        proposed_state_effects=[],
    )
    compact = compact_dramatic_irony_context(record)

    assert validation["status"] == "approved"
    assert validation["realized_opportunity_ids"] == [selected_id]
    assert validation["surface_mode_contract_pass"] is True
    assert compact["selected_opportunity_ids"] == record["selected_opportunity_ids"]
    assert compact["surface_rule"]


def test_dramatic_irony_rejects_forbidden_surface_mode_from_policy() -> None:
    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": _runtime_private_plan_simulation()["candidate_actor_ids"]},
        selected_responder_set=[
            {"actor_id": actor_id}
            for actor_id in _runtime_private_plan_simulation()["candidate_actor_ids"]
        ],
        npc_agency_simulation=_runtime_private_plan_simulation(),
    )
    selected_id = record["selected_opportunity_ids"][0]
    forbidden_mode = record["policy"]["forbidden_surface_modes"][0]
    generation = {
        "metadata": {
            "structured_output": {
                "dramatic_irony_opportunity_ids": [selected_id],
                "dramatic_irony_surface_mode": forbidden_mode,
                "narrative_response": "Visible pressure shifts.",
            }
        }
    }

    validation = validate_dramatic_irony_realization(
        record=record,
        generation=generation,
        proposed_state_effects=[],
    )

    assert validation["status"] == "rejected"
    assert DRAMATIC_IRONY_VIOLATION_FORBIDDEN_SURFACE_MODE in validation["violation_codes"]
    assert validation["surface_mode_contract_pass"] is False


def test_dramatic_irony_compact_context_omits_hidden_fact_summary() -> None:
    simulation = _runtime_private_plan_simulation()
    actor_ids = simulation["candidate_actor_ids"]
    record = build_dramatic_irony_record(
        actor_lane_context={"npc_actor_ids": actor_ids},
        selected_responder_set=[{"actor_id": actor_id} for actor_id in actor_ids],
        npc_agency_simulation=simulation,
    )
    selected_plan_id = simulation["npc_plan_conflict_resolution"]["selected_private_plan_ids"][0]
    selected_plan = next(
        row
        for row in simulation["npc_private_plans"]
        if row["private_plan_id"] == selected_plan_id
    )

    compact = compact_dramatic_irony_context(record)
    compact_json = json.dumps(compact, sort_keys=True)

    assert compact["model_context_visibility"] == record["policy"]["model_context_visibility"]
    assert "facts" not in compact
    assert selected_plan["intent"] not in compact_json
    assert record["facts"][0]["summary"] not in compact_json
