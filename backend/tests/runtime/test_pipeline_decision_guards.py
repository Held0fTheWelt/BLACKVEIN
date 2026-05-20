"""Tests for pipeline_decision_guards.py."""
from unittest.mock import MagicMock, patch

import pytest

from app.runtime.validation.pipeline_decision_guards import (
    DecisionValidationResult,
    validate_decision_gates,
    _apply_delta_safely,
    _check_decision_validity,
    _validate_decision_context,
)


class TestDecisionValidationResult:
    """Tests for DecisionValidationResult dataclass."""

    def test_decision_validation_result_valid(self):
        """Test creating a valid validation result."""
        result = DecisionValidationResult(
            valid=True,
            reason="Decision structure valid",
            errors=[],
        )

        assert result.valid is True
        assert result.reason == "Decision structure valid"
        assert result.errors == []

    def test_decision_validation_result_invalid(self):
        """Test creating an invalid validation result."""
        result = DecisionValidationResult(
            valid=False,
            reason="Missing mandatory fields",
            errors=["Decision missing 'proposed_deltas' field"],
        )

        assert result.valid is False
        assert result.reason == "Missing mandatory fields"
        assert len(result.errors) == 1
        assert "proposed_deltas" in result.errors[0]

    def test_decision_validation_result_multiple_errors(self):
        """Test result with multiple errors."""
        result = DecisionValidationResult(
            valid=False,
            reason="Multiple validation failures",
            errors=["Error 1", "Error 2", "Error 3"],
        )

        assert result.valid is False
        assert len(result.errors) == 3

    def test_decision_validation_result_immutable(self):
        """Test that DecisionValidationResult is immutable (frozen)."""
        result = DecisionValidationResult(
            valid=True,
            reason="Test",
            errors=[],
        )

        with pytest.raises(AttributeError):
            result.valid = False


class TestCheckDecisionValidity:
    """Tests for _check_decision_validity function."""

    def test_check_decision_validity_valid_decision(self):
        """Test validating a decision with required fields."""
        decision = MagicMock(proposed_deltas=["delta1", "delta2"])

        result = _check_decision_validity(decision)

        assert result.valid is True
        assert result.reason == "Decision structure valid"
        assert result.errors == []

    def test_check_decision_validity_missing_proposed_deltas(self):
        """Test validation fails when proposed_deltas is missing."""
        decision = MagicMock(spec=[])

        result = _check_decision_validity(decision)

        assert result.valid is False
        assert "proposed_deltas" in result.reason or "proposed_deltas" in str(result.errors)

    def test_check_decision_validity_proposed_deltas_not_list(self):
        """Test validation fails when proposed_deltas is not a list."""
        decision = MagicMock(proposed_deltas="not a list")

        result = _check_decision_validity(decision)

        assert result.valid is False
        assert "list" in str(result.errors).lower()

    def test_check_decision_validity_empty_proposed_deltas(self):
        """Test validation fails when proposed_deltas is empty."""
        decision = MagicMock(proposed_deltas=[])

        result = _check_decision_validity(decision)

        assert result.valid is False
        assert "at least one" in result.reason.lower() or "No deltas" in result.reason

    def test_check_decision_validity_single_delta(self):
        """Test validation passes with single delta."""
        decision = MagicMock(proposed_deltas=["delta1"])

        result = _check_decision_validity(decision)

        assert result.valid is True

    def test_check_decision_validity_multiple_deltas(self):
        """Test validation passes with multiple deltas."""
        decision = MagicMock(proposed_deltas=["delta1", "delta2", "delta3"])

        result = _check_decision_validity(decision)

        assert result.valid is True


class TestValidateDecisionContext:
    """Tests for _validate_decision_context function."""

    def test_validate_decision_context_valid(self):
        """Test validating a decision with valid context."""
        decision = MagicMock(
            proposed_scene_id="scene_123",
            proposed_ending_id=None,
            detected_triggers=[],
        )
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is True
        assert result.reason == "Decision context valid"

    def test_validate_decision_context_invalid_scene_id_type(self):
        """Test validation fails when proposed_scene_id is not a string."""
        decision = MagicMock(proposed_scene_id=123)
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False
        assert "proposed_scene_id" in str(result.errors)

    def test_validate_decision_context_empty_scene_id(self):
        """Test validation fails when proposed_scene_id is empty."""
        decision = MagicMock(proposed_scene_id="   ")
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False
        assert "empty" in str(result.errors).lower()

    def test_validate_decision_context_invalid_ending_id_type(self):
        """Test validation fails when proposed_ending_id is not a string."""
        decision = MagicMock(
            proposed_scene_id="scene_123",
            proposed_ending_id=456,
        )
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False
        assert "proposed_ending_id" in str(result.errors)

    def test_validate_decision_context_empty_ending_id(self):
        """Test validation fails when proposed_ending_id is empty."""
        decision = MagicMock(
            proposed_scene_id="scene_123",
            proposed_ending_id="",
        )
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False

    def test_validate_decision_context_invalid_triggers_type(self):
        """Test validation fails when detected_triggers is not a list."""
        decision = MagicMock(
            proposed_scene_id="scene_123",
            detected_triggers="not a list",
        )
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False
        assert "detected_triggers" in str(result.errors)

    def test_validate_decision_context_no_scene_or_ending(self):
        """Test validation passes when scene and ending are not provided."""
        decision = MagicMock(spec=["detected_triggers"], detected_triggers=[])
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is True

    def test_validate_decision_context_multiple_errors(self):
        """Test validation accumulates multiple errors."""
        decision = MagicMock(
            proposed_scene_id=123,  # Invalid type
            proposed_ending_id="",  # Empty
            detected_triggers="not a list",  # Invalid type
        )
        session = MagicMock()

        result = _validate_decision_context(decision, session)

        assert result.valid is False
        assert len(result.errors) >= 2


class TestApplyDeltaSafely:
    """Tests for _apply_delta_safely function."""

    def test_apply_delta_safely_valid_deltas(self):
        """Test applying valid deltas to state."""
        state = {"key": "old_value"}
        delta = MagicMock(
            target_path="key",
            next_value="new_value",
            validation_status="VALID",
        )
        deltas = [delta]

        with patch(
            "app.runtime.turn.turn_executor_decision_delta.apply_deltas"
        ) as mock_apply:
            mock_apply.return_value = {"key": "new_value"}

            new_state, result = _apply_delta_safely(state, deltas, 1)

            assert result.valid is True
            assert new_state == {"key": "new_value"}
            mock_apply.assert_called_once()

    def test_apply_delta_safely_deltas_not_list(self):
        """Test that non-list deltas are rejected."""
        state = {"key": "value"}
        deltas = "not a list"

        new_state, result = _apply_delta_safely(state, deltas, 1)

        assert result.valid is False
        assert new_state == state  # Original state returned
        assert "must be a list" in str(result.errors).lower()

    def test_apply_delta_safely_missing_target_path(self):
        """Test validation fails when delta missing target_path."""
        state = {"key": "value"}
        delta = MagicMock(
            spec=["next_value", "validation_status"],
            next_value="new",
            validation_status="VALID",
        )
        deltas = [delta]

        new_state, result = _apply_delta_safely(state, deltas, 1)

        assert result.valid is False
        assert "target_path" in str(result.errors)

    def test_apply_delta_safely_missing_next_value(self):
        """Test validation fails when delta missing next_value."""
        state = {"key": "value"}
        delta = MagicMock(
            target_path="key",
            spec=["target_path", "validation_status"],
            validation_status="VALID",
        )
        deltas = [delta]

        new_state, result = _apply_delta_safely(state, deltas, 1)

        assert result.valid is False
        assert "next_value" in str(result.errors)

    def test_apply_delta_safely_missing_validation_status(self):
        """Test validation fails when delta missing validation_status."""
        state = {"key": "value"}
        delta = MagicMock(
            target_path="key",
            next_value="new",
            spec=["target_path", "next_value"],
        )
        deltas = [delta]

        new_state, result = _apply_delta_safely(state, deltas, 1)

        assert result.valid is False
        assert "validation_status" in str(result.errors)

    def test_apply_delta_safely_application_exception(self):
        """Test handling of exceptions during delta application."""
        state = {"key": "value"}
        delta = MagicMock(
            target_path="key",
            next_value="new",
            validation_status="VALID",
        )
        deltas = [delta]

        with patch(
            "app.runtime.turn.turn_executor_decision_delta.apply_deltas"
        ) as mock_apply:
            mock_apply.side_effect = Exception("Application failed")

            new_state, result = _apply_delta_safely(state, deltas, 1)

            assert result.valid is False
            assert new_state == state  # Original state returned
            assert "Application failed" in str(result.errors)

    def test_apply_delta_safely_multiple_deltas(self):
        """Test applying multiple deltas."""
        state = {"a": 1, "b": 2}
        delta1 = MagicMock(
            target_path="a",
            next_value=10,
            validation_status="VALID",
        )
        delta2 = MagicMock(
            target_path="b",
            next_value=20,
            validation_status="VALID",
        )
        deltas = [delta1, delta2]

        with patch(
            "app.runtime.turn.turn_executor_decision_delta.apply_deltas"
        ) as mock_apply:
            mock_apply.return_value = {"a": 10, "b": 20}

            new_state, result = _apply_delta_safely(state, deltas, 1)

            assert result.valid is True
            assert "2 delta" in result.reason


class TestValidateDecisionGates:
    """Tests for validate_decision_gates function."""

    def test_validate_decision_gates_all_pass(self):
        """Test when all validation gates pass."""
        decision = MagicMock(
            proposed_deltas=["delta1"],
            proposed_scene_id="scene_123",
            spec=["proposed_deltas", "proposed_scene_id"],  # Only these attributes
        )
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is True
        assert "All validation gates passed" in result.reason

    def test_validate_decision_gates_structure_fails(self):
        """Test when structure validation fails."""
        decision = MagicMock(spec=[])  # Missing proposed_deltas
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is False
        assert result.errors  # Should have errors

    def test_validate_decision_gates_context_fails(self):
        """Test when context validation fails."""
        decision = MagicMock(
            proposed_deltas=["delta1"],
            proposed_scene_id=123,  # Invalid type
        )
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is False

    def test_validate_decision_gates_returns_on_first_failure(self):
        """Test that validation returns on first failure (structure check)."""
        decision = MagicMock(spec=[])  # Structure check will fail
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is False
        # Should fail on structure check reason
        assert "Missing" in result.reason or "field" in result.reason.lower()

    def test_validate_decision_gates_empty_deltas(self):
        """Test validation with empty deltas."""
        decision = MagicMock(proposed_deltas=[])
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is False

    def test_validate_decision_gates_valid_with_all_fields(self):
        """Test validation with all fields present and valid."""
        decision = MagicMock(
            proposed_deltas=["delta1", "delta2"],
            proposed_scene_id="scene_new",
            proposed_ending_id=None,
            detected_triggers=["trigger1"],
        )
        session = MagicMock()

        result = validate_decision_gates(decision, session)

        assert result.valid is True
        assert result.errors == []
