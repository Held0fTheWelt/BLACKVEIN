"""Tests for inspector_turn_projection_sections_semantic.py - Semantic decision flow."""

from unittest.mock import MagicMock, patch
import pytest

from ai_stack.contracts.dramatic_effect_contract import SemanticPlannerSupportLevel
from app.services.inspector_turn_projection_sections_semantic import (
    build_semantic_decision_flow,
    support_posture,
)


class TestSupportPosture:
    """Tests for support_posture function."""

    def test_support_posture_valid_module_full_goc(self):
        """Test support posture for valid full GoC module."""
        with patch("app.services.inspector_turn_projection_sections_semantic.support_level_for_module") as mock_level:
            with patch("app.services.inspector_turn_projection_sections_semantic.resolve_dramatic_effect_evaluator") as mock_eval:
                mock_level.return_value = SemanticPlannerSupportLevel.full_goc
                mock_evaluator = MagicMock()
                mock_evaluator.__class__.__name__ = "GoCAffectEvaluator"
                mock_eval.return_value = mock_evaluator

                result = support_posture(module_id="god_of_carnage")

                assert result is not None
                assert result["semantic_planner_support_level"] == "full_goc"
                assert result["dramatic_effect_evaluator_class"] == "GoCAffectEvaluator"
                assert "Full GoC" in result["support_note"]

    def test_support_posture_valid_module_non_goc_waived(self):
        """Test support posture for valid non-GoC waived module."""
        with patch("app.services.inspector_turn_projection_sections_semantic.support_level_for_module") as mock_level:
            with patch("app.services.inspector_turn_projection_sections_semantic.resolve_dramatic_effect_evaluator") as mock_eval:
                mock_level.return_value = SemanticPlannerSupportLevel.non_goc_waived
                mock_evaluator = MagicMock()
                mock_evaluator.__class__.__name__ = "CanonicalEvaluator"
                mock_eval.return_value = mock_evaluator

                result = support_posture(module_id="other_module")

                assert result is not None
                assert result["semantic_planner_support_level"] == "non_goc_waived"
                assert "Non-GoC" in result["support_note"]

    def test_support_posture_with_whitespace(self):
        """Test support posture with module_id containing whitespace."""
        with patch("app.services.inspector_turn_projection_sections_semantic.support_level_for_module") as mock_level:
            with patch("app.services.inspector_turn_projection_sections_semantic.resolve_dramatic_effect_evaluator") as mock_eval:
                mock_level.return_value = SemanticPlannerSupportLevel.full_goc
                mock_eval.return_value = MagicMock(__class__=MagicMock(__name__="Evaluator"))

                result = support_posture(module_id="  module_id  ")

                assert result is not None
                mock_level.assert_called_once_with("module_id")

    def test_support_posture_none_module_id(self):
        """Test support posture with None module_id."""
        result = support_posture(module_id=None)
        assert result is None

    def test_support_posture_empty_string_module_id(self):
        """Test support posture with empty string module_id."""
        result = support_posture(module_id="")
        assert result is None

    def test_support_posture_whitespace_only_module_id(self):
        """Test support posture with whitespace-only module_id."""
        result = support_posture(module_id="   ")
        assert result is None

    def test_support_posture_non_string_module_id(self):
        """Test support posture with non-string module_id."""
        result = support_posture(module_id=123)
        assert result is None
        result = support_posture(module_id=["module"])
        assert result is None
        result = support_posture(module_id={"module": "id"})
        assert result is None


class TestBuildSemanticDecisionFlow:
    """Tests for build_semantic_decision_flow function."""

    def test_build_semantic_decision_flow_returns_correct_structure(self):
        """Test that function returns correct structure."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        assert "stages" in result
        assert "edges" in result
        assert isinstance(result["stages"], list)
        assert isinstance(result["edges"], list)

    def test_build_semantic_decision_flow_player_input_raw_input_present(self):
        """Test player_input stage with raw_input present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"raw_input": "Hello world"},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["player_input"]["presence"] == "present"

    def test_build_semantic_decision_flow_player_input_raw_input_empty(self):
        """Test player_input stage with empty raw_input."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"raw_input": "   "},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["player_input"]["presence"] == "absent"

    def test_build_semantic_decision_flow_player_input_interpreted_input_present(self):
        """Test player_input stage with interpreted_input present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"interpreted_input": {"signal": "attack"}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["player_input"]["presence"] == "present"

    def test_build_semantic_decision_flow_player_input_both_absent(self):
        """Test player_input stage with no input."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["player_input"]["presence"] == "absent"

    def test_build_semantic_decision_flow_semantic_move_present(self):
        """Test semantic_move stage when present in canonical_record."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={"semantic_move_record": {"move": "attack"}},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["semantic_move"]["presence"] == "present"

    def test_build_semantic_decision_flow_semantic_move_absent(self):
        """Test semantic_move stage when absent."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["semantic_move"]["presence"] == "absent"

    def test_build_semantic_decision_flow_social_state_present(self):
        """Test social_state stage when present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={"social_state_record": {"allies": 2}},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["social_state"]["presence"] == "present"

    def test_build_semantic_decision_flow_character_mind_present_list(self):
        """Test character_mind stage with non-empty list."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={"character_mind_records": [{"char": "1"}, {"char": "2"}]},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["character_mind"]["presence"] == "present"

    def test_build_semantic_decision_flow_character_mind_absent_empty_list(self):
        """Test character_mind stage with empty list."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={"character_mind_records": []},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["character_mind"]["presence"] == "absent"

    def test_build_semantic_decision_flow_scene_plan_present(self):
        """Test scene_plan stage when present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={"scene_plan_record": {"scene": "battle"}},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["scene_plan"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_from_narrative_commit(self):
        """Test proposed_narrative stage from narrative_commit."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"narrative_commit": {"text": "The story continues..."}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_from_generation_primary_text(self):
        """Test proposed_narrative stage from generation.primary_text."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": {"generation": {"primary_text": "Generated"}}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_from_generation_text(self):
        """Test proposed_narrative stage from generation.text."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": {"generation": {"text": "Generated"}}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_from_generation_content(self):
        """Test proposed_narrative stage from generation.content."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": {"generation": {"content": "Generated"}}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_from_generation_structured_output(self):
        """Test proposed_narrative stage from generation.structured_output."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": {"generation": {"structured_output": {"data": "output"}}}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "present"

    def test_build_semantic_decision_flow_proposed_narrative_absent_empty_generation(self):
        """Test proposed_narrative stage with empty generation."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": {"generation": {}}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "absent"

    def test_build_semantic_decision_flow_dramatic_effect_gate_present(self):
        """Test dramatic_effect_gate stage when present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={"result": "accepted"},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["dramatic_effect_gate"]["presence"] == "present"

    def test_build_semantic_decision_flow_dramatic_effect_gate_absent_empty(self):
        """Test dramatic_effect_gate stage when absent."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["dramatic_effect_gate"]["presence"] == "absent"

    def test_build_semantic_decision_flow_validation_present_with_status(self):
        """Test validation stage with status present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={"status": "approved"},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["validation"]["presence"] == "present"

    def test_build_semantic_decision_flow_validation_absent_no_status(self):
        """Test validation stage without status."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["validation"]["presence"] == "absent"

    def test_build_semantic_decision_flow_commit_present(self):
        """Test commit stage when present."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={"applied": True},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["commit"]["presence"] == "present"

    def test_build_semantic_decision_flow_commit_absent_non_dict(self):
        """Test commit stage when not a dict."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed="not_a_dict",
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["commit"]["presence"] == "absent"

    def test_build_semantic_decision_flow_visible_output_dict_present(self):
        """Test visible_output stage with non-empty dict."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"visible_output_bundle": {"narration": "Hello"}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["visible_output"]["presence"] == "present"

    def test_build_semantic_decision_flow_visible_output_dict_empty(self):
        """Test visible_output stage with empty dict."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"visible_output_bundle": {}},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["visible_output"]["presence"] == "absent"

    def test_build_semantic_decision_flow_visible_output_list_present(self):
        """Test visible_output stage with non-empty list."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"visible_output_bundle": ["item1", "item2"]},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["visible_output"]["presence"] == "present"

    def test_build_semantic_decision_flow_visible_output_list_empty(self):
        """Test visible_output stage with empty list."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"visible_output_bundle": []},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["visible_output"]["presence"] == "absent"

    def test_build_semantic_decision_flow_planner_bound_stages_unsupported_non_goc_waived(self):
        """Test planner-bound stages marked unsupported for non-GoC waived."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.non_goc_waived,
            canonical_record={
                "semantic_move_record": {"move": "1"},
                "social_state_record": {"state": "2"},
                "character_mind_records": [{"char": "3"}],
                "scene_plan_record": {"plan": "4"},
            },
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        # These stages should be marked as unsupported for non-GoC waived
        assert stages["semantic_move"]["presence"] == "unsupported"
        assert stages["social_state"]["presence"] == "unsupported"
        assert stages["character_mind"]["presence"] == "unsupported"
        assert stages["scene_plan"]["presence"] == "unsupported"

    def test_build_semantic_decision_flow_planner_bound_stages_supported_full_goc(self):
        """Test planner-bound stages marked supported for full GoC."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={
                "semantic_move_record": {"move": "1"},
                "social_state_record": {"state": "2"},
                "character_mind_records": [{"char": "3"}],
                "scene_plan_record": {"plan": "4"},
            },
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        # These stages should be marked as present for full GoC
        assert stages["semantic_move"]["presence"] == "present"
        assert stages["social_state"]["presence"] == "present"
        assert stages["character_mind"]["presence"] == "present"
        assert stages["scene_plan"]["presence"] == "present"

    def test_build_semantic_decision_flow_edges_correct_count(self):
        """Test that edges list has correct count."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        # Should have n-1 edges for n stages
        assert len(result["edges"]) == len(result["stages"]) - 1

    def test_build_semantic_decision_flow_edges_sequential_connection(self):
        """Test that edges connect stages sequentially."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = result["stages"]
        edges = result["edges"]

        for i, edge in enumerate(edges):
            assert edge["from_stage"] == stages[i]["id"]
            assert edge["to_stage"] == stages[i + 1]["id"]

    def test_build_semantic_decision_flow_generation_none_model_route(self):
        """Test proposed_narrative with None model_route."""
        result = build_semantic_decision_flow(
            support_level=SemanticPlannerSupportLevel.full_goc,
            canonical_record={},
            last_turn={"model_route": None},
            gate_outcome={},
            validation={},
            committed={},
        )

        stages = {s["id"]: s for s in result["stages"]}
        assert stages["proposed_narrative"]["presence"] == "absent"
