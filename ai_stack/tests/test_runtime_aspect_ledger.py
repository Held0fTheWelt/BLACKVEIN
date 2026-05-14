from __future__ import annotations

import json

from ai_stack.runtime_aspect_ledger import (
    ASPECT_ACTION_RESOLUTION,
    ASPECT_INPUT,
    ASPECT_KEYS,
    initialize_runtime_aspect_ledger,
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
