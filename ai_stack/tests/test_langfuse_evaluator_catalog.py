"""Tests for canonical Langfuse categorical evaluator catalog."""

from ai_stack.langfuse_evaluator_catalog import (
    GATE_OVERRIDE_WARNING,
    JUDGE_TO_REPAIR_CARD,
    MATRIX_JUDGE_COLUMN_KEYS,
    WOS_CATEGORICAL_JUDGES_ORDER,
    get_categorical_evaluator_spec,
)


def test_player_action_resolution_judge_catalog_entry():
    spec = get_categorical_evaluator_spec("player_action_resolution_judge")
    assert spec is not None
    assert spec.score_type == "categorical"
    assert spec.categories == ("resolved_well", "partially_resolved", "misresolved", "not_resolved")
    assert spec.allow_multiple_matches is False
    assert spec.qualitative_only is True
    assert spec.runtime_gate is False
    assert spec.replaces_deterministic_gates is False
    assert "qualitative review signal only" in spec.prompt.lower()
    assert spec.issue_categories == frozenset({"partially_resolved", "misresolved", "not_resolved"})
    assert spec.repair_card == "TURN-ACTION-RESOLUTION-01"
    assert spec.matrix_column_key == "player_action_resolution_category"
    assert "ADR-0033" in GATE_OVERRIDE_WARNING or "actor_lane_safety_pass" in GATE_OVERRIDE_WARNING
    assert spec.langfuse_observation_filters["Name"] == ["story.model.generation"]
    assert spec.trace_metadata_filters.get("opening_turn") is False
    assert spec.legacy_trace_names == ("world-engine.turn.execute",)


def test_opening_judge_langfuse_filters_match_opening_trace():
    spec = get_categorical_evaluator_spec("opening_experience_judge")
    assert spec is not None
    assert spec.langfuse_observation_filters["Trace Name"] == ["world-engine.session.create"]
    assert spec.langfuse_observation_filters["Name"] == ["story.model.generation"]
    assert spec.trace_metadata_filters["opening_turn"] is True
    assert spec.trace_metadata_filters["turn_number"] == 0
    assert spec.legacy_trace_names == ("world-engine.session.create",)


def test_player_action_resolution_judge_in_order_and_maps():
    assert "player_action_resolution_judge" in WOS_CATEGORICAL_JUDGES_ORDER
    assert JUDGE_TO_REPAIR_CARD["player_action_resolution_judge"] == "TURN-ACTION-RESOLUTION-01"
    assert MATRIX_JUDGE_COLUMN_KEYS["player_action_resolution_judge"] == "player_action_resolution_category"
