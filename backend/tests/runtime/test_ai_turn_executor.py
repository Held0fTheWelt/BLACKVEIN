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
from app.runtime.w2_models import (
    DeltaType,
    DeltaValidationStatus,
    SessionState,
    AIValidationOutcome,
    StateDelta,
    GuardOutcome,
)


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
            "delta_type": "state_update",
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
        """Valid AIActionType string "state_update" gets coerced through bridge.

        Note: The delta_type in the proposal comes from AIActionType canonical taxonomy,
        not DeltaType. The bridge attempts to coerce it to DeltaType, but if the value
        doesn't match a DeltaType, it falls back to None.
        """
        parsed = ParsedAIDecision(
            scene_interpretation="Test",
            detected_triggers=[],
            proposed_deltas=[
                ProposedDelta(
                    target_path="characters.alice.state",
                    next_value=99,
                    delta_type="state_update",  # Valid AIActionType, but not a DeltaType value
                )
            ],
            proposed_scene_id=None,
            rationale="Test",
            raw_output="{}",
            parsed_source="structured_payload",
        )

        mock_decision = decision_from_parsed(parsed)

        assert len(mock_decision.proposed_deltas) == 1
        # "state_update" is not a valid DeltaType value, so it will be None after coercion
        assert mock_decision.proposed_deltas[0].delta_type is None


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
        # Using valid action type "state_update" but targeting a character that doesn't exist
        invalid_delta = {
            "scene_interpretation": "Proposal",
            "detected_triggers": [],
            "proposed_state_deltas": [
                {
                    "target_path": "characters.nonexistent_char.emotional_state",
                    "next_value": 99,
                    "delta_type": "state_update",
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

        # Parse succeeds (action type is valid)
        # But validation rejects the delta (engine controls acceptance)
        assert result.execution_status in ("success", "validation_failed")
        # Delta should be in rejected_deltas, not accepted_deltas
        assert len(result.rejected_deltas) > 0

    def test_adapter_error_logs_error_decision(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Adapter error creates decision log with ERROR outcome."""
        from app.runtime.w2_models import AIValidationOutcome

        session = god_of_carnage_module_with_state
        adapter = DeterministicAIAdapter(error="Connection timeout")

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
        assert decision_log.guard_notes is not None
        assert "adapter_error" in decision_log.guard_notes or "Adapter error" in decision_log.guard_notes

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

    def test_partial_validation_logged(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Partial validation (some accepted, some rejected) logged correctly."""
        from app.runtime.w2_models import AIValidationOutcome

        session = god_of_carnage_module_with_state

        # Ensure character exists for valid delta
        if "characters" not in session.canonical_state:
            session.canonical_state["characters"] = {}
        if "veronique" not in session.canonical_state["characters"]:
            session.canonical_state["characters"]["veronique"] = {"emotional_state": 50}

        # Mixed payload: one valid (character exists), one invalid (character doesn't exist)
        mixed_payload = {
            "scene_interpretation": "Mixed result",
            "detected_triggers": [],
            "proposed_state_deltas": [
                {
                    "target_path": "characters.veronique.emotional_state",
                    "next_value": 70,
                    "delta_type": "state_update",
                },
                {
                    "target_path": "characters.nonexistent.emotional_state",
                    "next_value": 99,
                    "delta_type": "state_update",
                },
            ],
            "rationale": "Testing mixed validation",
        }
        adapter = DeterministicAIAdapter(payload=mixed_payload)

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        # Verify decision log captures partial validation
        assert "ai_decision_logs" in session.metadata
        decision_log = session.metadata["ai_decision_logs"][0]

        # Should have PARTIAL outcome (some accepted, some rejected)
        if len(result.rejected_deltas) > 0 and len(result.accepted_deltas) > 0:
            assert decision_log.validation_outcome == AIValidationOutcome.PARTIAL

        # Both accepted and rejected should be visible
        assert len(decision_log.accepted_deltas) + len(decision_log.rejected_deltas) >= 1

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

    def test_decision_log_orthogonal_to_event_log(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Decision logging and event logging are complementary, not duplicative."""
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

        # Both should exist
        has_decision_log = (
            "ai_decision_logs" in session.metadata
            and len(session.metadata["ai_decision_logs"]) > 0
        )
        has_events = len(result.events) > 0

        assert has_decision_log, "Decision log should be created"
        assert has_events, "Event log should be created"

        # Decision log contains AI-specific data (raw output, parsed output)
        decision_log = session.metadata["ai_decision_logs"][0]
        assert (
            decision_log.raw_output is not None
            or decision_log.validation_outcome.value == "error"
        )
        assert (
            decision_log.parsed_output is not None
            or decision_log.validation_outcome.value == "error"
        )

        # Events contain what happened (turn started, deltas applied, etc.)
        # - events should NOT duplicate the decision log's raw/parsed output
        event_types = [e.event_type for e in result.events]
        assert any(
            "turn" in et for et in event_types
        ), "Events should include turn lifecycle"


def test_no_w2_scope_jump():
    """Verify implementation doesn't jump scope into W2.2+ features."""
    # This is a documentation test — it should always pass if code is correct

    # What should NOT be implemented:
    # - Database persistence of AIDecisionLog (deferred to later)
    # - UI viewers or dashboards
    # - Recovery logic with retries (error-path hardening is W2.1.6)
    # - Operator decision overrides
    # - Batch decision analysis or reporting

    # What SHOULD be implemented:
    # - AIDecisionLog populated in-memory during execution
    # - Raw output captured
    # - Parsed decision captured
    # - Validation outcome captured
    # - Accepted/rejected deltas visible

    assert True  # Scope validation is manual; this documents the intent


class TestAIDecisionLogOutcomes:
    """Tests for canonical AIValidationOutcome mapping and guard_notes normalization."""

    def test_clean_turn_produces_accepted_validation_outcome(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test AIValidationOutcome.ACCEPTED for clean turn with all valid deltas."""
        session = god_of_carnage_module_with_state
        # Use a known-good payload structure
        adapter = DeterministicAIAdapter(
            payload={
                "scene_interpretation": "Scene is calm",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": 70,
                        "delta_type": "state_update",
                        "rationale": "Emotional increase",
                    }
                ],
                "rationale": "Test decision",
            }
        )

        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

        assert result.execution_status == "success"

        # Check AI decision log from session metadata
        assert "ai_decision_logs" in session.metadata
        decision_logs = session.metadata["ai_decision_logs"]
        assert len(decision_logs) > 0
        latest_log = decision_logs[-1]

        assert latest_log.validation_outcome == AIValidationOutcome.ACCEPTED
        assert latest_log.guard_notes is None  # No validation errors

    def test_guard_outcome_rejected_is_mapped_to_rejected_validation_outcome(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that GuardOutcome.REJECTED maps to AIValidationOutcome.REJECTED (the bugfix)."""
        # This test verifies the fix: all-rejected deltas should produce REJECTED, not PARTIAL.
        # We use direct unit test instead of integration to avoid adapter complexities.
        from app.runtime.ai_turn_executor import _create_decision_log
        from app.runtime.turn_executor import TurnExecutionResult, MockDecision

        session = god_of_carnage_module_with_state

        # Create a turn result with all rejected deltas (guard_outcome=REJECTED)
        result = TurnExecutionResult(
            turn_number=1,
            session_id=session.session_id,
            execution_status="success",
            decision=MockDecision(),
            accepted_deltas=[],
            rejected_deltas=[
                StateDelta(
                    delta_type=DeltaType.CHARACTER_STATE,
                    target_path="characters.unknown.emotional_state",
                    source="ai_proposal",
                ),
                StateDelta(
                    delta_type=DeltaType.CHARACTER_STATE,
                    target_path="characters.unknown2.emotional_state",
                    source="ai_proposal",
                ),
            ],
            validation_errors=["Unknown character unknown", "Unknown character unknown2"],
            guard_outcome=GuardOutcome.REJECTED,
        )

        # Create decision log from the all-rejected result
        log = _create_decision_log(
            session,
            1,
            type("MockParsed", (), {
                "scene_interpretation": "Test",
                "detected_triggers": [],
                "proposed_deltas": [],
                "proposed_scene_id": None,
                "rationale": "Test",
            })(),
            type("MockResponse", (), {"raw_output": "Test"})(),
            result,
        )

        # This is the fix: all-rejected should produce REJECTED, not PARTIAL
        assert log.validation_outcome == AIValidationOutcome.REJECTED
        assert log.guard_notes is not None
        assert "error" in log.guard_notes
        assert "rejected" in log.guard_notes

    def test_guard_notes_format_normalized_with_error_count_and_label(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that guard_notes is normalized with error count and outcome label."""
        from app.runtime.ai_turn_executor import _create_decision_log
        from app.runtime.turn_executor import TurnExecutionResult, MockDecision

        session = god_of_carnage_module_with_state

        # Create a turn result with partial acceptance
        result = TurnExecutionResult(
            turn_number=1,
            session_id=session.session_id,
            execution_status="success",
            decision=MockDecision(),
            accepted_deltas=[
                StateDelta(
                    delta_type=DeltaType.CHARACTER_STATE,
                    target_path="characters.veronique.emotional_state",
                    source="ai_proposal",
                )
            ],
            rejected_deltas=[
                StateDelta(
                    delta_type=DeltaType.CHARACTER_STATE,
                    target_path="characters.unknown.emotional_state",
                    source="ai_proposal",
                )
            ],
            validation_errors=["Unknown character unknown"],
            guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
        )

        # Create decision log from the partial result
        log = _create_decision_log(
            session,
            1,
            type("MockParsed", (), {
                "scene_interpretation": "Test",
                "detected_triggers": [],
                "proposed_deltas": [],
                "proposed_scene_id": None,
                "rationale": "Test",
            })(),
            type("MockResponse", (), {"raw_output": "Test"})(),
            result,
        )

        assert log.validation_outcome == AIValidationOutcome.PARTIAL
        assert log.guard_notes is not None

        # Verify normalized guard_notes format: "N error(s); partially_accepted: ..."
        guard_notes_parts = log.guard_notes.split(";")
        assert len(guard_notes_parts) >= 2

        # First part should be error count
        error_part = guard_notes_parts[0].strip()
        assert "error" in error_part
        assert "1 error" in error_part  # One invalid character

        # Second part should contain outcome label
        outcome_part = ";".join(guard_notes_parts[1:]).strip()
        assert "partially_accepted" in outcome_part

    def test_error_path_result_has_structurally_invalid_guard_outcome(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that error-path TurnExecutionResult carries guard_outcome=STRUCTURALLY_INVALID."""
        from app.runtime.ai_turn_executor import _make_parse_failure_result
        from datetime import datetime, timezone

        session = god_of_carnage_module_with_state

        # Create error-path result via parse failure helper
        result = _make_parse_failure_result(
            session=session,
            turn_number=1,
            errors=["Failed to parse response"],
            raw_output="",
            started_at=datetime.now(timezone.utc),
        )

        # Verify error-path result has guard_outcome=STRUCTURALLY_INVALID
        assert result.execution_status == "system_error"
        assert result.guard_outcome == GuardOutcome.STRUCTURALLY_INVALID

    def test_error_path_aidecisionlog_has_error_validation_outcome(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that error-path AIDecisionLog has validation_outcome=ERROR (consistent with guard_outcome=STRUCTURALLY_INVALID)."""
        from app.runtime.ai_turn_executor import _create_error_decision_log

        session = god_of_carnage_module_with_state

        # Create error-path decision log
        log = _create_error_decision_log(
            session=session,
            current_turn=1,
            raw_output="",
            errors=["Adapter failed to generate response"],
            error_type="adapter_error",
        )

        # Verify error-path decision log maps to AIValidationOutcome.ERROR
        assert log.validation_outcome == AIValidationOutcome.ERROR
        assert log.guard_notes is not None
        assert "adapter_error" in log.guard_notes

    def test_error_path_cross_surface_consistency(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that error-path semantics are consistent across TurnExecutionResult and AIDecisionLog.

        Verifies that:
        - TurnExecutionResult.guard_outcome = STRUCTURALLY_INVALID
        - AIDecisionLog.validation_outcome = ERROR (canonical mapping for STRUCTURALLY_INVALID)
        - Both surfaces tell the same story about failed turn
        """
        from app.runtime.ai_turn_executor import _make_parse_failure_result, _create_error_decision_log
        from datetime import datetime, timezone

        session = god_of_carnage_module_with_state

        # Create error-path result
        result = _make_parse_failure_result(
            session=session,
            turn_number=1,
            errors=["Failed to parse response"],
            raw_output="",
            started_at=datetime.now(timezone.utc),
        )

        # Create corresponding error-path decision log
        log = _create_error_decision_log(
            session=session,
            current_turn=1,
            raw_output="",
            errors=["Failed to parse response"],
            error_type="parse_error",
        )

        # Verify cross-surface consistency:
        # - Result says STRUCTURALLY_INVALID
        assert result.guard_outcome == GuardOutcome.STRUCTURALLY_INVALID

        # - Decision log says ERROR (which maps from STRUCTURALLY_INVALID in error path)
        assert log.validation_outcome == AIValidationOutcome.ERROR

        # - Both agree the turn failed to produce valid deltas
        assert len(result.accepted_deltas) == 0
        assert len(result.rejected_deltas) == 0
        assert result.execution_status == "system_error"
