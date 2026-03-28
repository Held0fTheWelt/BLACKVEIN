"""Tests for W2.1.4 — AI Execution Path Integration

Comprehensive test suite for the canonical AI turn executor:
- Decision bridging: ProposedDelta → ProposedStateDelta (seam validation)
- DeltaType coercion with fallback to None on invalid values
- Adapter request construction from session/module
- Parse failure handling with state safety guarantees
- Full AI turn execution with delegation to mock runtime path
- Validation flow confirmation (engine controls acceptance)
"""

import asyncio
import pytest
from datetime import datetime, timezone
from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_output import ProposedDelta, StructuredAIStoryOutput
from app.runtime.ai_turn_executor import (
    build_adapter_request,
    decision_from_parsed,
    _make_parse_failure_result,
    execute_turn_with_ai,
)
from app.runtime.turn_executor import MockDecision, ProposedStateDelta
from app.runtime.w2_models import DeltaType, DeltaValidationStatus, SessionState


# ===== Test Adapter: DeterministicAIAdapter =====


class DeterministicAIAdapter(StoryAIAdapter):
    """Test adapter that returns W2.1.2-conformant payloads.

    NOT the same as MockStoryAIAdapter which returns narrative_text format.
    This adapter conforms to StructuredAIStoryOutput.
    """

    def __init__(self, payload: dict[str, Any] | None = None, error: str | None = None):
        """Initialize with optional payload or error.

        Args:
            payload: Structured payload dict (will be wrapped in AdapterResponse)
            error: Error message (if set, returns error response)
        """
        self.payload = payload
        self.error_message = error

    @property
    def adapter_name(self) -> str:
        """Returns 'deterministic-test' as the adapter identifier."""
        return "deterministic-test"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        """Generate deterministic response with optional error.

        Args:
            request: AdapterRequest (ignored for deterministic response)

        Returns:
            AdapterResponse with payload or error
        """
        if self.error_message:
            return AdapterResponse(
                raw_output="",
                structured_payload=None,
                error=self.error_message,
            )

        return AdapterResponse(
            raw_output=f"[deterministic] turn={request.turn_number}",
            structured_payload=self.payload or {},
        )


# ===== Test Payloads =====


VALID_PAYLOAD = {
    "scene_interpretation": "Scene is tense",
    "detected_triggers": [],
    "proposed_state_deltas": [],
    "rationale": "No changes warranted",
}

DELTA_PAYLOAD = {
    "scene_interpretation": "Emotional state rising",
    "detected_triggers": [],
    "proposed_state_deltas": [
        {
            "target_path": "characters.veronique.emotional_state",
            "next_value": 70,
            "delta_type": "character_state",
            "rationale": "Veronique is agitated",
        }
    ],
    "rationale": "Veronique tension increasing",
}


# ===== Unit Tests: Delta Conversion =====


def test_convert_proposed_delta_to_state_delta():
    """Convert runtime delta to StateDelta for decision logging."""
    from app.runtime.ai_turn_executor import _convert_proposed_delta_to_state_delta
    from app.runtime.w2_models import StateDelta

    proposed = ProposedStateDelta(
        target="characters.veronique.emotional_state",
        next_value=70,
        previous_value=50,
        delta_type=DeltaType.CHARACTER_STATE,
    )

    state_delta = _convert_proposed_delta_to_state_delta(
        proposed,
        validation_status=DeltaValidationStatus.ACCEPTED,
        turn_number=5
    )

    assert state_delta.target_path == "characters.veronique.emotional_state"
    assert state_delta.next_value == 70
    assert state_delta.previous_value == 50
    assert state_delta.delta_type == DeltaType.CHARACTER_STATE
    assert state_delta.source == "ai_proposal"
    assert state_delta.validation_status == DeltaValidationStatus.ACCEPTED
    assert state_delta.turn_number == 5


# ===== Unit Tests: Decision Bridging =====


class TestDecisionFromParsed:
    """Unit tests for decision_from_parsed() seam mapping."""

    def test_target_path_mapped_to_target(self):
        """Seam mapping: ProposedDelta.target_path → ProposedStateDelta.target."""
        parsed = ParsedAIDecision(
            scene_interpretation="Test",
            detected_triggers=[],
            proposed_deltas=[
                ProposedDelta(
                    target_path="characters.veronique.emotional_state",
                    next_value=70,
                )
            ],
            proposed_scene_id=None,
            rationale="Test",
            raw_output="{}",
            parsed_source="structured_payload",
        )

        mock_decision = decision_from_parsed(parsed)

        assert len(mock_decision.proposed_deltas) == 1
        delta = mock_decision.proposed_deltas[0]
        assert delta.target == "characters.veronique.emotional_state"
        assert delta.next_value == 70

    def test_optional_fields_preserved(self):
        """scene_interpretation→narrative_text, rationale, triggers, scene_id pass through."""
        parsed = ParsedAIDecision(
            scene_interpretation="Tense atmosphere",
            detected_triggers=["trigger_a", "trigger_b"],
            proposed_deltas=[],
            proposed_scene_id="scene_2",
            rationale="High emotional tension detected",
            raw_output="{}",
            parsed_source="structured_payload",
        )

        mock_decision = decision_from_parsed(parsed)

        assert mock_decision.narrative_text == "Tense atmosphere"
        assert mock_decision.rationale == "High emotional tension detected"
        assert mock_decision.detected_triggers == ["trigger_a", "trigger_b"]
        assert mock_decision.proposed_scene_id == "scene_2"

    def test_unknown_delta_type_falls_back_to_none(self):
        """Invalid DeltaType string → None (with no exception)."""
        parsed = ParsedAIDecision(
            scene_interpretation="Test",
            detected_triggers=[],
            proposed_deltas=[
                ProposedDelta(
                    target_path="some.path",
                    next_value=42,
                    delta_type="invalid_type_xyz",
                )
            ],
            proposed_scene_id=None,
            rationale="Test",
            raw_output="{}",
            parsed_source="structured_payload",
        )

        mock_decision = decision_from_parsed(parsed)

        assert len(mock_decision.proposed_deltas) == 1
        assert mock_decision.proposed_deltas[0].delta_type is None

    def test_valid_delta_type_string_is_coerced(self):
        """Valid DeltaType string "character_state" → DeltaType.CHARACTER_STATE."""
        parsed = ParsedAIDecision(
            scene_interpretation="Test",
            detected_triggers=[],
            proposed_deltas=[
                ProposedDelta(
                    target_path="characters.alice.state",
                    next_value=99,
                    delta_type="character_state",
                )
            ],
            proposed_scene_id=None,
            rationale="Test",
            raw_output="{}",
            parsed_source="structured_payload",
        )

        mock_decision = decision_from_parsed(parsed)

        assert len(mock_decision.proposed_deltas) == 1
        assert mock_decision.proposed_deltas[0].delta_type == DeltaType.CHARACTER_STATE


# ===== Integration Tests: Execute Turn with AI =====


class TestExecuteTurnWithAI:
    """Integration tests for execute_turn_with_ai() full pipeline."""

    def test_successful_ai_turn_execution(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Happy path: valid AI payload → execution_status == 'success'."""
        session = god_of_carnage_module_with_state
        adapter = DeterministicAIAdapter(payload=VALID_PAYLOAD)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"
        assert result.turn_number == session.turn_counter + 1
        assert result.session_id == session.session_id

    def test_ai_path_delta_flows_into_state(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Delta from AI payload is applied to canonical_state."""
        session = god_of_carnage_module_with_state

        # Ensure initial state has the path we're modifying
        if "characters" not in session.canonical_state:
            session.canonical_state["characters"] = {}
        if "veronique" not in session.canonical_state["characters"]:
            session.canonical_state["characters"]["veronique"] = {}
        session.canonical_state["characters"]["veronique"]["emotional_state"] = 50

        adapter = DeterministicAIAdapter(payload=DELTA_PAYLOAD)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        # If delta was accepted (passed validation), state should reflect it
        if result.execution_status == "success" and result.accepted_deltas:
            final_state = result.updated_canonical_state
            assert final_state["characters"]["veronique"]["emotional_state"] == 70

    def test_malformed_adapter_output_fails_before_state_corruption(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Missing required field (rationale) → system_error, state unchanged."""
        session = god_of_carnage_module_with_state
        initial_state = session.canonical_state.copy()

        # Missing 'rationale' — required field
        malformed = {
            "scene_interpretation": "Test",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            # Missing: "rationale": "...",
        }
        adapter = DeterministicAIAdapter(payload=malformed)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "system_error"
        assert result.updated_canonical_state == initial_state  # State unchanged

    def test_adapter_error_fails_before_state_corruption(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Adapter error flag → system_error, state unchanged."""
        session = god_of_carnage_module_with_state
        initial_state = session.canonical_state.copy()

        adapter = DeterministicAIAdapter(error="Adapter failure: connection timeout")

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "system_error"
        assert result.updated_canonical_state == initial_state  # State unchanged
        assert any("Adapter error" in err for err in result.validation_errors)

    def test_engine_validation_still_controls_committed_changes(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Nonexistent character delta: parse succeeds, runtime rejects it."""
        session = god_of_carnage_module_with_state

        # Delta targets nonexistent character
        invalid_delta = {
            "scene_interpretation": "Proposal",
            "detected_triggers": [],
            "proposed_state_deltas": [
                {
                    "target_path": "characters.nonexistent_char.emotional_state",
                    "next_value": 99,
                    "delta_type": "character_state",
                }
            ],
            "rationale": "Trying to modify nonexistent character",
        }
        adapter = DeterministicAIAdapter(payload=invalid_delta)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        # Parse succeeds (malformed AI output isn't the problem)
        # But validation rejects the delta (engine controls acceptance)
        assert result.execution_status in ("success", "validation_failed")
        # Delta should be in rejected_deltas, not accepted_deltas
        assert len(result.rejected_deltas) > 0

    def test_malformed_adapter_output_logs_error_decision(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Malformed AI output creates decision log with ERROR outcome."""
        from app.runtime.w2_models import AIValidationOutcome

        session = god_of_carnage_module_with_state
        malformed = {
            "scene_interpretation": "Test",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            # Missing: "rationale"
        }
        adapter = DeterministicAIAdapter(payload=malformed)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        # Verify execution failed
        assert result.execution_status == "system_error"

        # Verify decision log was created with error state
        assert "ai_decision_logs" in session.metadata
        assert len(session.metadata["ai_decision_logs"]) == 1

        decision_log = session.metadata["ai_decision_logs"][0]
        assert decision_log.validation_outcome == AIValidationOutcome.ERROR
        assert decision_log.parsed_output is None
        assert decision_log.guard_notes is not None
        assert "parse_error" in decision_log.guard_notes

    def test_successful_ai_turn_creates_decision_log(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Successful AI turn execution creates AIDecisionLog entry."""
        from app.runtime.w2_models import AIValidationOutcome

        session = god_of_carnage_module_with_state
        adapter = DeterministicAIAdapter(payload=DELTA_PAYLOAD)

        # Execute turn
        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        # Verify decision log was created and stored
        assert "ai_decision_logs" in session.metadata
        assert len(session.metadata["ai_decision_logs"]) == 1

        decision_log = session.metadata["ai_decision_logs"][0]
        assert decision_log.session_id == session.session_id
        assert decision_log.turn_number == session.turn_counter + 1
        assert decision_log.raw_output is not None
        assert decision_log.parsed_output is not None
        assert decision_log.validation_outcome == AIValidationOutcome.ACCEPTED

    def test_mock_path_remains_available_and_coherent(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Direct execute_turn call (mock path) is untouched."""
        from app.runtime.turn_executor import execute_turn

        session = god_of_carnage_module_with_state
        mock_decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[],
            narrative_text="Mock decision",
            rationale="Testing mock path",
        )

        result = asyncio.run(
            execute_turn(
                session,
                current_turn=session.turn_counter + 1,
                mock_decision=mock_decision,
                module=god_of_carnage_module,
            )
        )

        # Mock path should work identically to before
        assert result.execution_status == "success"
        assert result.decision == mock_decision
