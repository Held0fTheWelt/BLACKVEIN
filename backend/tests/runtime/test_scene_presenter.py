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
from app.runtime.runtime_models import SessionState, SessionContextLayers
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext, SalientRelationshipAxis


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
from app.runtime.runtime_models import (
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


from app.runtime.scene_presenter import present_conflict_panel
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.short_term_context import ShortTermTurnContext


class TestPresentConflictPanel:
    """Tests for present_conflict_panel function."""

    def test_present_conflict_panel_pressure_low(self):
        """Low pressure (20) returns escalation_status='low'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 20}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 20
        assert result.current_escalation_status == "low"

    def test_present_conflict_panel_pressure_medium(self):
        """Medium pressure (50) returns escalation_status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 50}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 50
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_high(self):
        """High pressure (75) returns escalation_status='high'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 75}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 75
        assert result.current_escalation_status == "high"

    def test_present_conflict_panel_no_pressure(self):
        """Missing pressure returns current_pressure=None and status='unknown'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure is None
        assert result.current_escalation_status == "unknown"

    def test_present_conflict_panel_guard_outcomes_escalating(self):
        """More rejections than acceptances → signal='escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 50}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                progression_summary=ProgressionSummary(
                    first_turn_covered=1,
                    last_turn_covered=5,
                    total_turns_in_source=5,
                    current_scene_id="scene-1",
                    most_recent_guard_outcomes=["rejected", "rejected", "accepted"],
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is not None
        assert result.recent_trend.signal == "escalating"
        assert "guard_outcomes" in result.recent_trend.source_basis

    def test_present_conflict_panel_relationship_escalation_markers(self):
        """Relationship escalation markers → signal='escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 40}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is not None
        assert result.recent_trend.signal == "escalating"
        assert "relationship_tension" in result.recent_trend.source_basis

    def test_present_conflict_panel_stable_signal(self):
        """Stable overall_stability_signal → signal='stable'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 30}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    overall_stability_signal="stable",
                    has_escalation_markers=False,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is not None
        assert result.recent_trend.signal == "stable"
        assert "stability_signal" in result.recent_trend.source_basis

    def test_present_conflict_panel_de_escalating_signal(self):
        """De-escalating overall_stability_signal → signal='de-escalating'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 25}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    overall_stability_signal="de-escalating",
                    has_escalation_markers=False,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is not None
        assert result.recent_trend.signal == "de-escalating"
        assert "stability_signal" in result.recent_trend.source_basis

    def test_present_conflict_panel_pressure_boundary_33(self):
        """Pressure at boundary 33 → status='low'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 33}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 33
        assert result.current_escalation_status == "low"

    def test_present_conflict_panel_pressure_boundary_34(self):
        """Pressure at boundary 34 → status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 34}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 34
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_boundary_66(self):
        """Pressure at boundary 66 → status='medium'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 66}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 66
        assert result.current_escalation_status == "medium"

    def test_present_conflict_panel_pressure_boundary_67(self):
        """Pressure at boundary 67 → status='high'."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 67}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.current_pressure == 67
        assert result.current_escalation_status == "high"

    def test_present_conflict_panel_turning_point_risk_true(self):
        """Escalation markers present → turning_point_risk=True."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.turning_point_risk is True

    def test_present_conflict_panel_turning_point_risk_false(self):
        """No escalation markers → turning_point_risk=False."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=False,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.turning_point_risk is False

    def test_present_conflict_panel_missing_context_layers(self):
        """Missing context layers → recent_trend=None, turning_point_risk=None."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={},
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is None
        assert result.turning_point_risk is None

    def test_present_conflict_panel_multiple_sources(self):
        """Multiple sources contributing → source_basis includes all."""
        session_state = SessionState(
            session_id="test-session",
            module_id="god_of_carnage",
            module_version="1.0",
            current_scene_id="scene-1",
            canonical_state={"conflict_state": {"pressure": 60}},
            context_layers=SessionContextLayers(
                short_term_context=ShortTermTurnContext(
                    turn_number=1,
                    scene_id="scene-1",
                    guard_outcome="accepted",
                ),
                progression_summary=ProgressionSummary(
                    first_turn_covered=1,
                    last_turn_covered=5,
                    total_turns_in_source=5,
                    current_scene_id="scene-1",
                    most_recent_guard_outcomes=["rejected", "rejected", "accepted"],
                ),
                relationship_axis_context=RelationshipAxisContext(
                    has_escalation_markers=True,
                ),
            ),
        )
        result = present_conflict_panel(session_state)
        assert result.recent_trend is not None
        assert "guard_outcomes" in result.recent_trend.source_basis
        assert "relationship_tension" in result.recent_trend.source_basis


class TestPresentAllCharacters:
    """Tests for present_all_characters bulk presenter function."""

    def test_present_all_characters_empty_canonical_state(self):
        """present_all_characters returns empty list when canonical_state is missing."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={},
            context_layers=SessionContextLayers(),
        )
        result = present_all_characters(session_state)
        assert result == []

    def test_present_all_characters_single_character_with_full_data(self):
        """present_all_characters returns list with one CharacterPanelOutput for single character."""
        from app.runtime.scene_presenter import present_all_characters

        salient_axis = SalientRelationshipAxis(
            character_a="protagonist",
            character_b="antagonist",
            signal_type="tension",
            recent_change_direction="escalating",
            salience_score=0.9,
        )

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "protagonist": {"name": "Alice"},
                    "antagonist": {"name": "Bob"},
                }
            },
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(
                    salient_axes=[salient_axis],
                    has_escalation_markers=False,
                    overall_stability_signal="escalating",
                )
            ),
        )
        result = present_all_characters(session_state)
        assert len(result) == 2
        assert result[0].character_id == "antagonist"  # alphabetical order
        assert result[1].character_id == "protagonist"
        assert result[0].character_name == "Bob"
        assert result[1].character_name == "Alice"

    def test_present_all_characters_multiple_characters_deterministic_order(self):
        """present_all_characters orders characters deterministically by character_id."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "zara": {"name": "Zara"},
                    "alice": {"name": "Alice"},
                    "bob": {"name": "Bob"},
                }
            },
            context_layers=SessionContextLayers(),
        )
        result = present_all_characters(session_state)
        assert len(result) == 3
        assert [c.character_id for c in result] == ["alice", "bob", "zara"]

    def test_present_all_characters_missing_name_uses_character_id(self):
        """present_all_characters falls back to character_id when name is missing."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "char_1": {},  # No name field
                    "char_2": {"name": "Named Character"},
                }
            },
            context_layers=SessionContextLayers(),
        )
        result = present_all_characters(session_state)
        assert len(result) == 2
        assert result[0].character_id == "char_1"
        assert result[0].character_name is None
        assert result[1].character_id == "char_2"
        assert result[1].character_name == "Named Character"

    def test_present_all_characters_missing_relationships(self):
        """present_all_characters handles missing relationships gracefully."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "isolated": {"name": "Isolated Character"},
                }
            },
            context_layers=SessionContextLayers(
                relationship_axis_context=RelationshipAxisContext(
                    salient_axes=[],
                    has_escalation_markers=False,
                    overall_stability_signal="unknown",
                )
            ),
        )
        result = present_all_characters(session_state)
        assert len(result) == 1
        assert result[0].character_id == "isolated"
        assert result[0].overall_trajectory == "unknown"
        assert result[0].top_relationship_movements == []

    def test_present_all_characters_missing_context_layers(self):
        """present_all_characters returns characters even with empty context layers."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={
                "characters": {
                    "char_a": {"name": "Character A"},
                    "char_b": {"name": "Character B"},
                }
            },
            context_layers=SessionContextLayers(),
        )
        result = present_all_characters(session_state)
        assert len(result) == 2
        assert result[0].character_id == "char_a"
        assert result[1].character_id == "char_b"
        assert result[0].overall_trajectory == "unknown"
        assert result[1].overall_trajectory == "unknown"

    def test_present_all_characters_empty_characters_dict(self):
        """present_all_characters returns empty list when characters dict is empty."""
        from app.runtime.scene_presenter import present_all_characters

        session_state = SessionState(
            session_id="test-session",
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene_1",
            turn_counter=0,
            status="active",
            canonical_state={"characters": {}},
            context_layers=SessionContextLayers(),
        )
        result = present_all_characters(session_state)
        assert result == []
