"""Unit tests for inspector_turn_projection_assembly_helpers."""

from app.services.inspector_turn_projection_assembly_helpers import (
    build_decision_trace_data,
    build_validation_projection_data,
)


def test_build_validation_projection_data_includes_intent_surface_fields() -> None:
    validation = {
        "status": "approved",
        "reason": "ok",
        "validator_lane": "goc_rule_engine_v1",
        "dramatic_quality_gate": "effect_gate_pass",
        "intent_surface_diagnostics": {"npc_narrated_player_action_violation": True},
    }
    canonical = {
        "player_input_kind": "action",
        "player_action_committed": True,
        "player_speech_committed": False,
        "narrator_response_expected": True,
        "npc_response_expected": False,
    }
    out = build_validation_projection_data(validation, canonical)
    assert out["status"] == "approved"
    assert out["player_input_kind"] == "action"
    assert out["player_action_committed"] is True
    assert out["player_speech_committed"] is False
    assert out["narrator_response_expected"] is True
    assert out["npc_response_expected"] is False
    assert out["npc_narrated_player_action_violation"] is True


def test_build_validation_projection_data_falls_back_to_interpreted_input() -> None:
    validation = {}
    canonical = {
        "interpreted_input": {
            "player_input_kind": "perception",
            "player_action_committed": True,
            "player_speech_committed": False,
            "narrator_response_expected": True,
            "npc_response_expected": False,
        }
    }
    out = build_validation_projection_data(validation, canonical)
    assert out["player_input_kind"] == "perception"
    assert out["player_action_committed"] is True
    assert out["player_speech_committed"] is False
    assert out["narrator_response_expected"] is True
    assert out["npc_response_expected"] is False


def test_build_validation_projection_data_includes_observability_contract_flags() -> None:
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    rule = rule_spec_for_subtext("probe_inquiry")
    validation = {}
    canonical = {
        "semantic_move_kind": "observe",
        "scene_director_selection_source": "semantic_move",
    }
    path_summary = {
        "subtext_surface_mode": rule["surface_mode"],
        "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
        "subtext_function": rule["subtext_function"],
        "subtext_sincerity_band": rule["sincerity_band"],
        "subtext_policy_rule_id": "probe_inquiry",
        "subtext_contract_pass": 1,
        "intent_surface_contract_pass": 1,
        "player_input_attribution_pass": 1,
        "semantic_move_alignment_pass": 1,
        "npc_action_narration_boundary_pass": 1,
        "planner_rationale_codes": ["player_perception_requires_environmental_feedback"],
        "legacy_keyword_scene_candidates_used": False,
    }
    out = build_validation_projection_data(validation, canonical, path_summary)
    assert out["semantic_move_kind"] == "observe"
    assert out["scene_director_selection_source"] == "semantic_move"
    assert out["subtext_surface_mode"] == rule["surface_mode"]
    assert out["subtext_hidden_intent_hypothesis"] == rule["hidden_intent_hypothesis"]
    assert out["subtext_function"] == rule["subtext_function"]
    assert out["subtext_sincerity_band"] == rule["sincerity_band"]
    assert out["subtext_policy_rule_id"] == "probe_inquiry"
    assert out["planner_rationale_codes"] == ["player_perception_requires_environmental_feedback"]
    assert out["legacy_keyword_scene_candidates_used"] is False
    assert out["intent_surface_contract_pass"] == 1
    assert out["subtext_contract_pass"] == 1
    assert out["player_input_attribution_pass"] == 1
    assert out["semantic_move_alignment_pass"] == 1
    assert out["npc_action_narration_boundary_pass"] == 1


def test_build_decision_trace_data_includes_intent_surface_evidence() -> None:
    from ai_stack.goc_subtext_policy import rule_spec_for_subtext

    rule = rule_spec_for_subtext("direct_accusation")
    out = build_decision_trace_data(
        graph={},
        routing={},
        nodes=[],
        flow_edges=[],
        bundle={
            "last_turn_observability_path_summary": {
                "player_input_kind": "action",
                "semantic_move_kind": "move_to_room",
                "scene_director_selection_source": "intent_surface",
                "subtext_surface_mode": rule["surface_mode"],
                "subtext_hidden_intent_hypothesis": rule["hidden_intent_hypothesis"],
                "subtext_function": rule["subtext_function"],
                "subtext_sincerity_band": rule["sincerity_band"],
                "subtext_policy_rule_id": "direct_accusation",
                "intent_surface_contract_pass": 1,
                "subtext_contract_pass": 1,
            }
        },
        semantic_flow={},
    )
    intent = out["intent_surface_evidence"]
    assert intent["player_input_kind"] == "action"
    assert intent["semantic_move_kind"] == "move_to_room"
    assert intent["scene_director_selection_source"] == "intent_surface"
    assert intent["subtext_surface_mode"] == rule["surface_mode"]
    assert intent["subtext_hidden_intent_hypothesis"] == rule["hidden_intent_hypothesis"]
    assert intent["subtext_function"] == rule["subtext_function"]
    assert intent["subtext_sincerity_band"] == rule["sincerity_band"]
    assert intent["subtext_policy_rule_id"] == "direct_accusation"
    assert intent["intent_surface_contract_pass"] == 1
    assert intent["subtext_contract_pass"] == 1
