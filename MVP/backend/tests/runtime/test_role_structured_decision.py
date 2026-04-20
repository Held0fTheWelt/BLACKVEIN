"""Tests for W2.4.3 role-structured parsing and normalization."""

import pytest
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.role_structured_decision import (
    ParsedRoleAwareDecision,
    _is_role_structured_payload,
    parse_role_contract,
)
from app.runtime.role_contract import (
    InterpreterSection,
    DirectorSection,
    ResponderSection,
)


def test_parsed_role_aware_decision_creation():
    """ParsedRoleAwareDecision wraps ParsedAIDecision with role sections."""
    parsed_decision = ParsedAIDecision(
        scene_interpretation="Scene",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,
        rationale="Rationale",
        raw_output="raw",
        parsed_source="structured_payload",
    )

    interpreter = InterpreterSection(
        scene_reading="Reading",
        detected_tensions=[],
        trigger_candidates=[],
    )
    director = DirectorSection(
        conflict_steering="Steering",
        escalation_level=5,
        recommended_direction="hold",
    )
    responder = ResponderSection()

    role_aware = ParsedRoleAwareDecision(
        parsed_decision=parsed_decision,
        interpreter=interpreter,
        director=director,
        responder=responder,
    )

    assert role_aware.parsed_decision == parsed_decision
    assert role_aware.interpreter == interpreter
    assert role_aware.director == director
    assert role_aware.responder == responder


def test_is_role_structured_payload_strict_keys():
    assert _is_role_structured_payload(None) is False
    assert _is_role_structured_payload({"interpreter": {}}) is False
    assert (
        _is_role_structured_payload(
            {"interpreter": {}, "director": {}, "responder": {}}
        )
        is True
    )


def test_parse_role_contract_invalid_payload_raises_value_error():
    with pytest.raises(ValueError, match="Failed to parse AIRoleContract"):
        parse_role_contract({"interpreter": "not_a_dict"}, "raw")


def test_parse_role_contract_normalizes_responder_fields():
    payload = {
        "interpreter": {
            "scene_reading": "Reading",
            "detected_tensions": [],
            "trigger_candidates": [],
        },
        "director": {
            "conflict_steering": "Steer",
            "escalation_level": 3,
            "recommended_direction": "hold",
        },
        "responder": {
            "response_impulses": [
                {
                    "character_id": "alice",
                    "impulse_type": "dialogue_urge",
                    "intensity": 0,
                    "rationale": "say this",
                },
                {
                    "character_id": "bob",
                    "impulse_type": "emotional_reaction",
                    "intensity": 10,
                    "rationale": "feel",
                },
            ],
            "state_change_candidates": [
                {
                    "target_path": "characters.alice.emotional_state",
                    "proposed_value": 22,
                    "rationale": "shift",
                }
            ],
            "trigger_assertions": ["t1"],
            "scene_transition_candidate": "next_scene",
        },
    }
    out = parse_role_contract(payload, "raw output")
    assert out.parsed_decision.scene_interpretation == "Reading"
    assert out.parsed_decision.rationale == "Steer"
    assert out.parsed_decision.detected_triggers == ["t1"]
    assert out.parsed_decision.proposed_scene_id == "next_scene"
    assert len(out.parsed_decision.proposed_deltas) == 1
    assert out.parsed_decision.proposed_deltas[0].target_path == "characters.alice.emotional_state"
    assert len(out.parsed_decision.dialogue_impulses) == 1
    impulse = out.parsed_decision.dialogue_impulses[0]
    assert impulse.character_id == "alice"
    assert impulse.impulse_text == "say this"
    assert impulse.intensity == 0.0

    payload["responder"]["response_impulses"][0]["intensity"] = 5
    out2 = parse_role_contract(payload, "raw2")
    assert out2.parsed_decision.dialogue_impulses[0].intensity == pytest.approx(0.5)
