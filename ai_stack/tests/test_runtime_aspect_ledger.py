from __future__ import annotations

import json

from ai_stack.dramatic_irony_contracts import (
    DRAMATIC_IRONY_SCHEMA_VERSION,
    DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED,
    DRAMATIC_IRONY_SURFACE_MISREAD_REACTION,
)
from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_DRAMATIC_IRONY,
    ASPECT_INPUT,
    ASPECT_KEYS,
    ASPECT_NPC_AGENCY,
    ASPECT_SCENE_ENERGY,
    build_runtime_intelligence_projection,
    initialize_runtime_aspect_ledger,
    set_aspect_record,
    stable_ledger_json,
)
from ai_stack.scene_energy_contracts import SCENE_ENERGY_FAILURE_CODES


def _scene_energy_missing_pressure_code() -> str:
    for code in SCENE_ENERGY_FAILURE_CODES:
        if code.endswith("missing_required_pressure"):
            return code
    raise AssertionError("scene_energy_contract_missing_pressure_failure_code")


def test_runtime_aspect_ledger_serializes_stably() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=1,
        turn_kind="player",
        raw_player_input="Ich nehme ein Bier aus dem Kuehlschrank",
        input_kind="action",
        turn_id="t1",
        trace_id="trace1",
    )

    first = stable_ledger_json(ledger)
    second = stable_ledger_json(json.loads(first))

    assert first == second
    parsed = json.loads(first)
    assert parsed["schema_version"] == "turn_aspect_ledger.v1"
    assert parsed["record_version"] == "runtime_aspect_ledger.v1"
    assert list(parsed["turn_aspect_ledger"].keys()) == sorted(ASPECT_KEYS)
    assert parsed["turn_aspect_ledger"][ASPECT_INPUT]["status"] == "passed"


def test_opening_marks_player_action_as_not_applicable() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=0,
        turn_kind="opening",
        raw_player_input="",
    )

    action = ledger["turn_aspect_ledger"][ASPECT_ACTION_RESOLUTION]
    assert action["applicable"] is False
    assert action["status"] == "not_applicable"
    assert action["reasons"] == ["opening_turn_not_player_action_evidence_lane"]


def test_runtime_projection_exposes_npc_agency_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich widerspreche.",
    )
    expected_actual = {
        "planned_actor_ids": ["npc_primary", "npc_secondary"],
        "realized_actor_ids": ["npc_primary"],
        "missing_required_actor_ids": ["npc_secondary"],
        "error_codes": ["npc_initiative_missing_required"],
        "multi_npc_initiative_realized": False,
        "not_full_multi_agent_simulation": True,
        "contract_status": "partial_runtime_projection",
        "long_horizon_state_present": True,
        "intention_threads_active": 2,
        "private_plan_resolution_present": True,
        "private_plan_visibility_respected": True,
        "selected_private_plan_ids": ["npc_primary:private_plan:2"],
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_NPC_AGENCY,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "contract_status": expected_actual["contract_status"],
                "not_full_multi_agent_simulation": True,
            },
            "actual": expected_actual,
            "reasons": expected_actual["error_codes"],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": expected_actual["error_codes"][0],
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    npc_agency = projection[ASPECT_NPC_AGENCY]
    assert npc_agency["contract_status"] == expected_actual["contract_status"]
    assert npc_agency["planned_actor_ids"] == expected_actual["planned_actor_ids"]
    assert npc_agency["realized_actor_ids"] == expected_actual["realized_actor_ids"]
    assert npc_agency["missing_required_actor_ids"] == expected_actual["missing_required_actor_ids"]
    assert npc_agency["error_codes"] == expected_actual["error_codes"]
    assert npc_agency["not_full_multi_agent_simulation"] is expected_actual["not_full_multi_agent_simulation"]
    assert npc_agency["long_horizon_state_present"] is True
    assert npc_agency["intention_threads_active"] == expected_actual["intention_threads_active"]
    assert npc_agency["private_plan_resolution_present"] is True
    assert npc_agency["private_plan_visibility_respected"] is True
    assert npc_agency["selected_private_plan_ids"] == expected_actual["selected_private_plan_ids"]


def test_runtime_projection_exposes_dramatic_irony_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich widerspreche.",
    )
    selected = {
        "selected_opportunity_ids": ["fact:runtime:selected:unknown_to:actor_b"],
        "selected_fact_ids": ["fact:runtime:selected"],
    }
    actual = {
        "status": "selected",
        "fact_count": len(selected["selected_fact_ids"]),
        "opportunity_count": len(selected["selected_opportunity_ids"]),
        "selected_opportunity_count": len(selected["selected_opportunity_ids"]),
        "realization_status": "realized",
        "realized_opportunity_ids": selected["selected_opportunity_ids"],
        "leak_blocked": False,
        "violation_codes": [],
        "contract_pass": True,
    }
    ledger = set_aspect_record(
        ledger,
        ASPECT_DRAMATIC_IRONY,
        {
            "applicable": True,
            "status": "passed",
            "expected": {
                "schema_version": DRAMATIC_IRONY_SCHEMA_VERSION,
                "policy_present": True,
                "policy_enabled": True,
                "allowed_sources": [DRAMATIC_IRONY_SOURCE_NPC_PRIVATE_PLAN_SELECTED],
                "allowed_surface_modes": [DRAMATIC_IRONY_SURFACE_MISREAD_REACTION],
                "direct_reveal_allowed": False,
            },
            "selected": selected,
            "actual": actual,
            "source": "validator",
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    dramatic_irony = projection[ASPECT_DRAMATIC_IRONY]
    assert dramatic_irony["policy_present"] is True
    assert dramatic_irony["selected_opportunity_ids"] == selected["selected_opportunity_ids"]
    assert dramatic_irony["selected_fact_ids"] == selected["selected_fact_ids"]
    assert dramatic_irony["opportunity_count"] == actual["opportunity_count"]
    assert dramatic_irony["realization_status"] == actual["realization_status"]
    assert dramatic_irony["leak_blocked"] is False
    assert dramatic_irony["contract_pass"] is True


def test_runtime_projection_exposes_scene_energy_aspect() -> None:
    ledger = initialize_runtime_aspect_ledger(
        session_id="s1",
        module_id="god_of_carnage",
        turn_number=2,
        turn_kind="player",
        raw_player_input="Ich bleibe am Tisch.",
    )
    target = {
        "schema_version": "scene_energy.v1",
        "energy_level": "rising",
        "pressure_vector": "social",
        "tempo": "accelerating",
        "density": "layered",
        "volatility": "unstable",
        "target_transition": "rise",
        "minimum_actor_response_count": 2,
        "maximum_visible_density_count": 8,
        "forbidden_transitions": [],
        "source_evidence": [],
        "rationale_codes": [],
    }
    missing_pressure_code = _scene_energy_missing_pressure_code()
    ledger = set_aspect_record(
        ledger,
        ASPECT_SCENE_ENERGY,
        {
            "applicable": True,
            "status": "failed",
            "expected": {
                "schema_version": target["schema_version"],
                "policy_present": True,
                "policy_enabled": True,
            },
            "selected": {
                "target": target,
                "transition": {
                    "schema_version": "scene_energy.v1",
                    "from_energy_level": None,
                    "to_energy_level": target["energy_level"],
                    "transition_intent": target["target_transition"],
                    "allowed": True,
                    "reason_codes": [],
                },
            },
            "actual": {
                "actual_actor_response_count": 1,
                "visible_density_count": 2,
                "transition_allowed": True,
                "contract_pass": False,
                "failure_codes": [missing_pressure_code],
            },
            "reasons": [missing_pressure_code],
            "failure_class": "recoverable_dramatic_failure",
            "failure_reason": missing_pressure_code,
        },
    )

    projection = build_runtime_intelligence_projection(ledger)

    scene_energy = projection[ASPECT_SCENE_ENERGY]
    assert scene_energy["schema_version"] == target["schema_version"]
    assert scene_energy["energy_level"] == target["energy_level"]
    assert scene_energy["pressure_vector"] == target["pressure_vector"]
    assert scene_energy["target_transition"] == target["target_transition"]
    assert scene_energy["minimum_actor_response_count"] == target["minimum_actor_response_count"]
    assert scene_energy["actual_actor_response_count"] == 1
    assert scene_energy["failure_codes"] == [missing_pressure_code]
    assert scene_energy["contract_pass"] is False
