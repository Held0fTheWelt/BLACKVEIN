"""Unit tests for scene presenter models and functions."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.runtime.scene_presenter import (
    CharacterPanelOutput,
    ConflictPanelOutput,
    ConflictTrendSignal,
    RelationshipMovement,
)


class TestRelationshipMovementModel:
    """Tests for RelationshipMovement Pydantic model."""

    def test_relationship_movement_creation(self):
        """RelationshipMovement can be created with valid fields."""
        movement = RelationshipMovement(
            other_character_id="veronique",
            signal_type="tension",
            recent_change="escalating",
            salience_score=0.85,
        )
        assert movement.other_character_id == "veronique"
        assert movement.signal_type == "tension"
        assert movement.recent_change == "escalating"
        assert movement.salience_score == 0.85

    def test_relationship_movement_serialization(self):
        """RelationshipMovement serializes to dict."""
        movement = RelationshipMovement(
            other_character_id="giuseppe",
            signal_type="alliance",
            recent_change="stable",
            salience_score=0.5,
        )
        data = movement.model_dump()
        assert data["other_character_id"] == "giuseppe"
        assert data["signal_type"] == "alliance"


class TestCharacterPanelOutputModel:
    """Tests for CharacterPanelOutput Pydantic model."""

    def test_character_panel_output_with_name_and_movements(self):
        """CharacterPanelOutput can be created with all fields."""
        movement = RelationshipMovement(
            other_character_id="veronique",
            signal_type="tension",
            recent_change="escalating",
            salience_score=0.85,
        )
        output = CharacterPanelOutput(
            character_id="giuseppe",
            character_name="Giuseppe",
            overall_trajectory="escalating",
            top_relationship_movements=[movement],
        )
        assert output.character_id == "giuseppe"
        assert output.character_name == "Giuseppe"
        assert output.overall_trajectory == "escalating"
        assert len(output.top_relationship_movements) == 1

    def test_character_panel_output_without_name(self):
        """CharacterPanelOutput allows character_name to be None."""
        output = CharacterPanelOutput(
            character_id="veronique",
            character_name=None,
            overall_trajectory="stable",
            top_relationship_movements=[],
        )
        assert output.character_name is None
        assert output.overall_trajectory == "stable"

    def test_character_panel_output_max_two_relationships(self):
        """CharacterPanelOutput top_relationship_movements bounded to 2."""
        movements = [
            RelationshipMovement(
                other_character_id=f"char{i}",
                signal_type="tension",
                recent_change="escalating",
                salience_score=0.9 - (i * 0.1),
            )
            for i in range(2)
        ]
        output = CharacterPanelOutput(
            character_id="test",
            character_name=None,
            overall_trajectory="escalating",
            top_relationship_movements=movements,
        )
        assert len(output.top_relationship_movements) == 2

    def test_character_panel_output_trajectory_values(self):
        """CharacterPanelOutput overall_trajectory accepts valid values."""
        valid_trajectories = ["escalating", "stable", "de-escalating", "mixed", "unknown"]
        for trajectory in valid_trajectories:
            output = CharacterPanelOutput(
                character_id="test",
                character_name=None,
                overall_trajectory=trajectory,
                top_relationship_movements=[],
            )
            assert output.overall_trajectory == trajectory


class TestConflictTrendSignalModel:
    """Tests for ConflictTrendSignal Pydantic model."""

    def test_conflict_trend_signal_creation(self):
        """ConflictTrendSignal can be created with signal and source_basis."""
        signal = ConflictTrendSignal(
            signal="escalating",
            source_basis=["guard_outcomes", "relationship_tension"],
        )
        assert signal.signal == "escalating"
        assert "guard_outcomes" in signal.source_basis
        assert "relationship_tension" in signal.source_basis

    def test_conflict_trend_signal_single_source(self):
        """ConflictTrendSignal source_basis can be a single item."""
        signal = ConflictTrendSignal(
            signal="stable",
            source_basis=["guard_outcomes"],
        )
        assert len(signal.source_basis) == 1

    def test_conflict_trend_signal_serialization(self):
        """ConflictTrendSignal serializes to dict."""
        signal = ConflictTrendSignal(
            signal="de-escalating",
            source_basis=["pressure_change"],
        )
        data = signal.model_dump()
        assert data["signal"] == "de-escalating"
        assert isinstance(data["source_basis"], list)


class TestConflictPanelOutputModel:
    """Tests for ConflictPanelOutput Pydantic model."""

    def test_conflict_panel_output_with_pressure_and_trend(self):
        """ConflictPanelOutput can be created with all fields."""
        trend = ConflictTrendSignal(
            signal="escalating",
            source_basis=["guard_outcomes"],
        )
        output = ConflictPanelOutput(
            current_pressure=75,
            current_escalation_status="high",
            recent_trend=trend,
            turning_point_risk=True,
        )
        assert output.current_pressure == 75
        assert output.current_escalation_status == "high"
        assert output.recent_trend is not None
        assert output.turning_point_risk is True

    def test_conflict_panel_output_without_pressure(self):
        """ConflictPanelOutput allows current_pressure to be None."""
        output = ConflictPanelOutput(
            current_pressure=None,
            current_escalation_status="unknown",
            recent_trend=None,
            turning_point_risk=None,
        )
        assert output.current_pressure is None
        assert output.current_escalation_status == "unknown"

    def test_conflict_panel_output_escalation_status_values(self):
        """ConflictPanelOutput escalation_status accepts valid values."""
        valid_statuses = ["low", "medium", "high", "unknown"]
        for status in valid_statuses:
            output = ConflictPanelOutput(
                current_pressure=50,
                current_escalation_status=status,
                recent_trend=None,
                turning_point_risk=None,
            )
            assert output.current_escalation_status == status

    def test_conflict_panel_output_serialization(self):
        """ConflictPanelOutput serializes to JSON-compatible dict."""
        trend = ConflictTrendSignal(
            signal="stable",
            source_basis=["guard_outcomes"],
        )
        output = ConflictPanelOutput(
            current_pressure=40,
            current_escalation_status="medium",
            recent_trend=trend,
            turning_point_risk=False,
        )
        data = output.model_dump(mode="json")
        assert data["current_pressure"] == 40
        assert data["recent_trend"]["signal"] == "stable"


from app.runtime.scene_presenter import (
    present_character_panel,
)
from app.runtime.w2_models import (
    SessionState,
    SessionContextLayers,
)
from app.runtime.relationship_context import (
    RelationshipAxisContext,
    SalientRelationshipAxis,
)


class TestPresentCharacterPanel:
    """Tests for present_character_panel function."""

    def test_present_character_panel_no_relationships(self):
        """Character with no relationship axes returns unknown trajectory and empty movements."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {"veronique": {"name": "Veronique"}}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext()
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_id == "veronique"
        assert result.character_name == "Veronique"
        assert result.overall_trajectory == "unknown"
        assert len(result.top_relationship_movements) == 0

    def test_present_character_panel_single_escalating_axis(self):
        """Character with 1 escalating axis returns escalating trajectory."""
        axis = SalientRelationshipAxis(
            character_a="veronique",
            character_b="giuseppe",
            salience_score=0.85,
            recent_change_direction="escalating",
            signal_type="tension",
            involved_in_recent_triggers=["accusation_veronique_giuseppe"],
            last_involved_turn=5,
        )
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {"veronique": {"name": "Veronique"}}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(
                    salient_axes=[axis]
                )
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_id == "veronique"
        assert result.overall_trajectory == "escalating"
        assert len(result.top_relationship_movements) == 1
        assert result.top_relationship_movements[0].other_character_id == "giuseppe"
        assert result.top_relationship_movements[0].recent_change == "escalating"

    def test_present_character_panel_multiple_axes_top_two(self):
        """Character with 3+ axes returns top 2 by salience_score."""
        axes = [
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="giuseppe",
                salience_score=0.9,
                recent_change_direction="escalating",
                signal_type="tension",
                involved_in_recent_triggers=[],
                last_involved_turn=5,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="barbara",
                salience_score=0.7,
                recent_change_direction="stable",
                signal_type="alliance",
                involved_in_recent_triggers=[],
                last_involved_turn=3,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="philip",
                salience_score=0.5,
                recent_change_direction="de-escalating",
                signal_type="stable",
                involved_in_recent_triggers=[],
                last_involved_turn=1,
            ),
        ]
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=axes)
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert len(result.top_relationship_movements) == 2
        assert result.top_relationship_movements[0].salience_score == 0.9
        assert result.top_relationship_movements[1].salience_score == 0.7

    def test_present_character_panel_mixed_trajectory(self):
        """Character with mixed escalation/stable axes returns 'mixed' trajectory."""
        axes = [
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="giuseppe",
                salience_score=0.8,
                recent_change_direction="escalating",
                signal_type="tension",
                involved_in_recent_triggers=[],
                last_involved_turn=5,
            ),
            SalientRelationshipAxis(
                character_a="veronique",
                character_b="barbara",
                salience_score=0.6,
                recent_change_direction="stable",
                signal_type="alliance",
                involved_in_recent_triggers=[],
                last_involved_turn=3,
            ),
        ]
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=axes)
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.overall_trajectory == "mixed"

    def test_present_character_panel_character_not_in_canonical_state(self):
        """Character missing from canonical_state returns character_name=None."""
        axis = SalientRelationshipAxis(
            character_a="veronique",
            character_b="giuseppe",
            salience_score=0.85,
            recent_change_direction="escalating",
            signal_type="tension",
            involved_in_recent_triggers=[],
            last_involved_turn=5,
        )
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"characters": {}},
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(salient_axes=[axis])
            ),
        )

        result = present_character_panel(session_state, "veronique")

        assert result.character_name is None
        assert result.overall_trajectory == "escalating"
