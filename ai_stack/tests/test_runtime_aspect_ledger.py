from __future__ import annotations

import json

from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_INPUT,
    ASPECT_KEYS,
    ASPECT_NPC_AGENCY,
    build_runtime_intelligence_projection,
    initialize_runtime_aspect_ledger,
    set_aspect_record,
    stable_ledger_json,
)


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
