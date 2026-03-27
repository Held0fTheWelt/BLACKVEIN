"""Tests for W2.1.2 canonical structured AI story output contract.

Verifies that:
- All models have correct shape and constraints
- Field validation works as expected
- Required and optional fields are correct
- Output is compatible with runtime validation
"""

from __future__ import annotations

import pytest

from app.runtime.ai_output import (
    ConflictVector,
    DialogueImpulse,
    ProposedDelta,
    StructuredAIStoryOutput,
)


class TestProposedDelta:
    """Test ProposedDelta model for AI-proposed state changes."""

    def test_proposed_delta_required_fields(self):
        """ProposedDelta requires target_path and next_value."""
        delta = ProposedDelta(
            target_path="characters.veronique.emotional_state",
            next_value=75,
        )

        assert delta.target_path == "characters.veronique.emotional_state"
        assert delta.next_value == 75

    def test_proposed_delta_optional_delta_type_defaults_none(self):
        """ProposedDelta.delta_type defaults to None."""
        delta = ProposedDelta(
            target_path="characters.veronique.emotional_state",
            next_value=75,
        )

        assert delta.delta_type is None

    def test_proposed_delta_optional_rationale_defaults_empty(self):
        """ProposedDelta.rationale defaults to empty string."""
        delta = ProposedDelta(
            target_path="characters.veronique.emotional_state",
            next_value=75,
        )

        assert delta.rationale == ""

    def test_proposed_delta_accepts_any_next_value_type(self):
        """ProposedDelta.next_value accepts any type (int, str, float, dict, list)."""
        deltas = [
            ProposedDelta(target_path="a", next_value=42),
            ProposedDelta(target_path="b", next_value="text"),
            ProposedDelta(target_path="c", next_value=3.14),
            ProposedDelta(target_path="d", next_value={"key": "val"}),
            ProposedDelta(target_path="e", next_value=[1, 2, 3]),
        ]

        assert len(deltas) == 5
        assert all(isinstance(d, ProposedDelta) for d in deltas)


class TestDialogueImpulse:
    """Test DialogueImpulse model for character impulses."""

    def test_dialogue_impulse_required_fields(self):
        """DialogueImpulse requires character_id and impulse_text."""
        impulse = DialogueImpulse(
            character_id="veronique",
            impulse_text="I can't believe this is happening!",
        )

        assert impulse.character_id == "veronique"
        assert impulse.impulse_text == "I can't believe this is happening!"

    def test_dialogue_impulse_intensity_defaults_to_0_5(self):
        """DialogueImpulse.intensity defaults to 0.5."""
        impulse = DialogueImpulse(
            character_id="veronique",
            impulse_text="Some text",
        )

        assert impulse.intensity == 0.5

    def test_dialogue_impulse_intensity_accepts_boundary_values(self):
        """DialogueImpulse.intensity accepts 0.0 and 1.0."""
        impulse_min = DialogueImpulse(
            character_id="veronique",
            impulse_text="Mild",
            intensity=0.0,
        )
        impulse_max = DialogueImpulse(
            character_id="veronique",
            impulse_text="Extreme",
            intensity=1.0,
        )

        assert impulse_min.intensity == 0.0
        assert impulse_max.intensity == 1.0

    def test_dialogue_impulse_intensity_rejects_out_of_range(self):
        """DialogueImpulse.intensity rejects values outside [0.0, 1.0]."""
        with pytest.raises(ValueError, match="intensity must be in"):
            DialogueImpulse(
                character_id="veronique",
                impulse_text="Text",
                intensity=-0.1,
            )

        with pytest.raises(ValueError, match="intensity must be in"):
            DialogueImpulse(
                character_id="veronique",
                impulse_text="Text",
                intensity=1.5,
            )


class TestConflictVector:
    """Test ConflictVector model for narrative tension."""

    def test_conflict_vector_required_field(self):
        """ConflictVector requires primary_axis."""
        vector = ConflictVector(primary_axis="trust")

        assert vector.primary_axis == "trust"

    def test_conflict_vector_intensity_defaults_to_0_5(self):
        """ConflictVector.intensity defaults to 0.5."""
        vector = ConflictVector(primary_axis="trust")

        assert vector.intensity == 0.5

    def test_conflict_vector_notes_defaults_to_none(self):
        """ConflictVector.notes defaults to None."""
        vector = ConflictVector(primary_axis="trust")

        assert vector.notes is None

    def test_conflict_vector_intensity_validates_range(self):
        """ConflictVector.intensity enforces [0.0, 1.0] range."""
        vector_valid = ConflictVector(primary_axis="guilt", intensity=0.7)
        assert vector_valid.intensity == 0.7

        with pytest.raises(ValueError, match="intensity must be in"):
            ConflictVector(primary_axis="guilt", intensity=1.5)

        with pytest.raises(ValueError, match="intensity must be in"):
            ConflictVector(primary_axis="guilt", intensity=-0.5)


class TestStructuredAIStoryOutput:
    """Test StructuredAIStoryOutput main contract model."""

    def test_structured_output_required_fields(self):
        """StructuredAIStoryOutput requires all four mandatory fields."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Tension is rising between characters",
            detected_triggers=["anger", "betrayal"],
            proposed_state_deltas=[],
            rationale="Characters are in escalating conflict",
        )

        assert output.scene_interpretation == "Tension is rising between characters"
        assert output.detected_triggers == ["anger", "betrayal"]
        assert output.proposed_state_deltas == []
        assert output.rationale == "Characters are in escalating conflict"

    def test_structured_output_proposed_scene_id_defaults_none(self):
        """StructuredAIStoryOutput.proposed_scene_id defaults to None."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        assert output.proposed_scene_id is None

    def test_structured_output_dialogue_impulses_defaults_empty(self):
        """StructuredAIStoryOutput.dialogue_impulses defaults to empty list."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        assert output.dialogue_impulses == []

    def test_structured_output_conflict_vector_defaults_none(self):
        """StructuredAIStoryOutput.conflict_vector defaults to None."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        assert output.conflict_vector is None

    def test_structured_output_confidence_defaults_none(self):
        """StructuredAIStoryOutput.confidence defaults to None."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
        )

        assert output.confidence is None

    def test_structured_output_accepts_empty_lists(self):
        """StructuredAIStoryOutput accepts empty detected_triggers and proposed_state_deltas."""
        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="No changes needed",
        )

        assert output.detected_triggers == []
        assert output.proposed_state_deltas == []

    def test_structured_output_full_payload(self):
        """StructuredAIStoryOutput accepts fully populated payload."""
        deltas = [
            ProposedDelta(
                target_path="characters.veronique.emotional_state",
                next_value=85,
                rationale="Rising tension",
            ),
        ]
        impulses = [
            DialogueImpulse(
                character_id="veronique",
                impulse_text="This is unacceptable!",
                intensity=0.9,
            ),
        ]
        conflict = ConflictVector(
            primary_axis="trust",
            intensity=0.8,
            notes="Veronique doubts everyone",
        )

        output = StructuredAIStoryOutput(
            scene_interpretation="Conflict escalating",
            detected_triggers=["anger", "betrayal"],
            proposed_state_deltas=deltas,
            rationale="Characters must escalate",
            proposed_scene_id="phase_2",
            dialogue_impulses=impulses,
            conflict_vector=conflict,
            confidence=0.85,
        )

        assert output.proposed_scene_id == "phase_2"
        assert len(output.dialogue_impulses) == 1
        assert output.conflict_vector is not None
        assert output.confidence == 0.85

    def test_structured_output_confidence_validates_range(self):
        """StructuredAIStoryOutput.confidence enforces [0.0, 1.0] if provided."""
        output_valid = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=[],
            proposed_state_deltas=[],
            rationale="Rationale",
            confidence=0.75,
        )
        assert output_valid.confidence == 0.75

        with pytest.raises(ValueError, match="confidence must be in"):
            StructuredAIStoryOutput(
                scene_interpretation="Scene",
                detected_triggers=[],
                proposed_state_deltas=[],
                rationale="Rationale",
                confidence=1.5,
            )

        with pytest.raises(ValueError, match="confidence must be in"):
            StructuredAIStoryOutput(
                scene_interpretation="Scene",
                detected_triggers=[],
                proposed_state_deltas=[],
                rationale="Rationale",
                confidence=-0.1,
            )


class TestOutputImmutability:
    """Test that output structures preserve field values."""

    def test_structured_output_immutability(self):
        """StructuredAIStoryOutput preserves all field values."""
        original_deltas = [ProposedDelta(target_path="path", next_value="val")]
        original_impulses = [
            DialogueImpulse(character_id="char", impulse_text="text")
        ]

        output = StructuredAIStoryOutput(
            scene_interpretation="Scene",
            detected_triggers=["trigger1", "trigger2"],
            proposed_state_deltas=original_deltas,
            rationale="Rationale",
            proposed_scene_id="phase_2",
            dialogue_impulses=original_impulses,
            confidence=0.9,
        )

        # Verify all fields are preserved exactly
        assert output.scene_interpretation == "Scene"
        assert output.detected_triggers == ["trigger1", "trigger2"]
        assert len(output.proposed_state_deltas) == 1
        assert output.proposed_state_deltas[0].target_path == "path"
        assert output.rationale == "Rationale"
        assert output.proposed_scene_id == "phase_2"
        assert len(output.dialogue_impulses) == 1
        assert output.dialogue_impulses[0].character_id == "char"
        assert output.confidence == 0.9

    def test_proposed_delta_immutability(self):
        """ProposedDelta preserves field values."""
        delta = ProposedDelta(
            target_path="characters.veronique.emotional_state",
            next_value=75,
            delta_type="character_state",
            rationale="Rising tension causes increased emotion",
        )

        assert delta.target_path == "characters.veronique.emotional_state"
        assert delta.next_value == 75
        assert delta.delta_type == "character_state"
        assert delta.rationale == "Rising tension causes increased emotion"
