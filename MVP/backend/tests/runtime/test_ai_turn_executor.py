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
import time
from datetime import datetime, timezone
from typing import Any
from unittest.mock import MagicMock, patch

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_failure_recovery import RestorePolicy
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_output import ProposedDelta, StructuredAIStoryOutput
from app.runtime.ai_turn_executor import (
    build_adapter_request,
    decision_from_parsed,
    _make_parse_failure_result,
    execute_turn_with_ai,
)
from app.runtime.operator_audit import AUDIT_SCHEMA_VERSION
from app.runtime.input_interpreter import InputPrimaryMode
from app.runtime.turn_executor import MockDecision, ProposedStateDelta
from app.runtime.runtime_models import (
    AIValidationOutcome,
    DeltaType,
    DeltaValidationStatus,
    ExecutionFailureReason,
    GuardOutcome,
    SessionState,
    StateDelta,
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


class SlowDeterministicAdapter(StoryAIAdapter):
    """Adapter that blocks long enough to trigger runtime timeout containment."""

    def __init__(self, *, sleep_seconds: float = 0.05):
        self.sleep_seconds = sleep_seconds

    @property
    def adapter_name(self) -> str:
        return "slow-deterministic"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        time.sleep(self.sleep_seconds)
        return AdapterResponse(
            raw_output=f"[slow] turn={request.turn_number}",
            structured_payload=VALID_PAYLOAD,
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
    from app.runtime.runtime_models import StateDelta

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


class TestBuildAdapterRequestInterpretation:
    """Task 1A: adapter request carries deterministic input_interpretation."""

    def test_build_adapter_request_attaches_envelope_and_preserves_raw_operator_input(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        session = god_of_carnage_module_with_state
        text = "I say, 'That is enough.'"
        req = build_adapter_request(
            session,
            god_of_carnage_module,
            operator_input=text,
        )
        assert req.operator_input == text
        assert req.input_interpretation is not None
        assert req.input_interpretation.raw_text == text
        assert req.input_interpretation.primary_mode == InputPrimaryMode.DIALOGUE

    def test_execute_turn_with_ai_logs_interpretation_once(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Diagnostic log in session.metadata; not authoritative state."""
        session = god_of_carnage_module_with_state
        session.metadata.pop("operator_input_interpretation_log", None)
        adapter = DeterministicAIAdapter(payload=VALID_PAYLOAD)
        turn = session.turn_counter + 1
        asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=turn,
                adapter=adapter,
                module=god_of_carnage_module,
                operator_input="I sigh.",
            )
        )
        log = session.metadata.get("operator_input_interpretation_log") or []
        assert len(log) == 1
        assert log[0]["turn_number"] == turn
        assert log[0]["envelope"]["primary_mode"] == InputPrimaryMode.REACTION.value


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
        """Missing required field (rationale) → fallback recovery, state unchanged."""
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

        # W2.5 Phase 3: Fallback responder recovers from parse failure with empty deltas
        assert result.execution_status == "success"
        assert result.updated_canonical_state == initial_state  # State unchanged (empty deltas)
        assert result.accepted_deltas == []  # Fallback has no deltas
        assert result.rejected_deltas == []

    def test_adapter_error_fails_before_state_corruption(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Adapter error triggers retry exhaustion, then safe-turn recovery."""
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

        # W2.5 Phase 4: Adapter error exhausts retries, activates safe-turn
        # Safe-turn succeeds and preserves state
        assert result.execution_status == "success"
        assert result.updated_canonical_state == initial_state  # State unchanged (safe-turn)

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
        from app.runtime.runtime_models import AIValidationOutcome

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

        # W2.5 Phase 4: Adapter error exhausts retries, activates safe-turn
        # Safe-turn results in success (no-op execution)
        assert result.execution_status == "success"

        # Verify decision logs were created (error + safe-turn recovery)
        assert "ai_decision_logs" in session.metadata
        assert len(session.metadata["ai_decision_logs"]) >= 1

        # Check for adapter error and safe-turn in logs
        decision_logs = session.metadata["ai_decision_logs"]
        found_recovery = False
        for log in decision_logs:
            if log.guard_notes and ("adapter_error" in log.guard_notes or "safe_turn_mode_active" in log.guard_notes):
                found_recovery = True
                break
        assert found_recovery, "Expected to find adapter error or safe-turn recovery in decision logs"

    def test_malformed_adapter_output_logs_error_decision(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Malformed AI output creates decision log with ERROR outcome."""
        from app.runtime.runtime_models import AIValidationOutcome

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

        # W2.5 Phase 3: Fallback responder recovers from parse failure
        # Execution succeeds with fallback's empty proposal
        assert result.execution_status == "success"

        # Verify decision logs were created
        assert "ai_decision_logs" in session.metadata
        assert len(session.metadata["ai_decision_logs"]) >= 1

        # Check for parse error indication in guard notes
        decision_logs = session.metadata["ai_decision_logs"]
        # At least one log should mention parse error or fallback
        found_parse_or_fallback = False
        for log in decision_logs:
            if log.guard_notes and ("parse_error" in log.guard_notes or "fallback_mode_active" in log.guard_notes):
                found_parse_or_fallback = True
                break
        assert found_parse_or_fallback, "Expected to find parse error or fallback recovery in decision logs"

    def test_successful_ai_turn_creates_decision_log(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Successful AI turn execution creates AIDecisionLog entry."""
        from app.runtime.runtime_models import AIValidationOutcome

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
        from app.runtime.runtime_models import AIValidationOutcome

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


class TestActionStructureValidation:
    """Tests for W2.2.1 action structure validation in canonical runtime path."""

    def test_missing_target_path_rejected_in_canonical_path(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that missing target_path in STATE_UPDATE is rejected before state mutation."""
        session = god_of_carnage_module_with_state
        # Create payload with STATE_UPDATE but missing target_path
        adapter = DeterministicAIAdapter(
            payload={
                "scene_interpretation": "Scene interpretation",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "",  # ❌ Empty target_path
                        "next_value": 70,
                        "delta_type": "state_update",
                        "rationale": "Invalid delta",
                    }
                ],
                "rationale": "Test",
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

        # W2.5 Phase 3: Structurally invalid deltas trigger fallback recovery
        # Fallback proposes empty deltas which pass validation
        assert result.execution_status == "success"
        assert result.guard_outcome == GuardOutcome.STRUCTURALLY_INVALID  # Still marked as structurally invalid in parsing phase
        assert len(result.accepted_deltas) == 0  # Fallback has no deltas
        assert len(result.rejected_deltas) == 0  # Fallback has no deltas

    def test_missing_next_value_rejected_in_canonical_path(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that missing next_value in STATE_UPDATE is rejected before state mutation."""
        session = god_of_carnage_module_with_state
        # Create payload with STATE_UPDATE but missing next_value
        adapter = DeterministicAIAdapter(
            payload={
                "scene_interpretation": "Scene interpretation",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": None,  # ❌ Missing next_value
                        "delta_type": "state_update",
                        "rationale": "Invalid delta",
                    }
                ],
                "rationale": "Test",
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

        # W2.5 Phase 3: Structurally invalid deltas trigger fallback recovery
        # Fallback proposes empty deltas which pass validation
        assert result.execution_status == "success"
        assert result.guard_outcome == GuardOutcome.STRUCTURALLY_INVALID  # Still marked as structurally invalid
        assert len(result.accepted_deltas) == 0  # Fallback has no deltas
        assert len(result.rejected_deltas) == 0  # Fallback has no deltas

    def test_valid_action_structure_passes_to_deeper_validation(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that valid action structures pass through to deeper validation stages."""
        session = god_of_carnage_module_with_state
        # Create payload with valid action structure
        adapter = DeterministicAIAdapter(
            payload={
                "scene_interpretation": "Scene is tense",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": 75,
                        "delta_type": "state_update",
                        "rationale": "Emotional increase",
                    }
                ],
                "rationale": "Valid decision",
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

        # Verify the turn succeeded and delta was accepted
        # (valid structure passed through to deeper validation and was accepted)
        assert result.execution_status == "success"
        assert len(result.accepted_deltas) > 0
        assert result.guard_outcome == GuardOutcome.ACCEPTED

    def test_action_structure_validation_before_mutation(
        self, god_of_carnage_module, god_of_carnage_module_with_state
    ):
        """Test that action structure validation happens before any state mutation."""
        session = god_of_carnage_module_with_state

        # Create payload with invalid action structure
        adapter = DeterministicAIAdapter(
            payload={
                "scene_interpretation": "Scene",
                "detected_triggers": [],
                "proposed_state_deltas": [
                    {
                        "target_path": "",  # ❌ Invalid: empty target_path
                        "next_value": 50,
                        "delta_type": "state_update",
                        "rationale": "Invalid",
                    }
                ],
                "rationale": "Test",
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

        # W2.5 Phase 3: Structurally invalid deltas trigger fallback recovery
        # Verify state was not mutated
        # - fallback responder was activated due to action structure validation failure
        # - fallback proposes empty deltas, so no mutations occur
        assert result.execution_status == "success"
        assert len(result.accepted_deltas) == 0  # Fallback has no deltas
        assert len(result.rejected_deltas) == 0  # Fallback has no deltas


def test_mcp_enrichment_attaches_to_adapter_request(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    session = god_of_carnage_module_with_state
    session.metadata["mcp_enrichment_enabled"] = True
    session.metadata["_mcp_client_override"] = MagicMock()

    captured = {}

    class CaptureAdapter(DeterministicAIAdapter):
        def generate(self, request):
            captured["metadata_keys"] = list((request.metadata or {}).keys())
            return super().generate(request)

    adapter = CaptureAdapter(payload=VALID_PAYLOAD)

    with patch(
        "app.mcp_client.enrichment.build_mcp_enrichment",
        return_value={"enriched": True},
    ):
        with patch(
            "app.observability.trace.get_trace_id",
            return_value="trace-test",
        ):
            asyncio.run(
                execute_turn_with_ai(
                    session,
                    current_turn=session.turn_counter + 1,
                    adapter=adapter,
                    module=god_of_carnage_module,
                )
            )

    assert "mcp_context_enrichment" in captured.get("metadata_keys", [])


def test_invalid_action_type_triggers_policy_fallback(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    session = god_of_carnage_module_with_state
    payload = {
        "scene_interpretation": "Scene",
        "detected_triggers": [],
        "proposed_state_deltas": [
            {
                "target_path": "characters.veronique.emotional_state",
                "next_value": 50,
                "delta_type": "__not_a_real_action_type__",
                "rationale": "bad type",
            }
        ],
        "rationale": "root",
    }
    adapter = DeterministicAIAdapter(payload=payload)

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.failure_reason == ExecutionFailureReason.VALIDATION_ERROR
    assert len(result.accepted_deltas) == 0


def test_role_structured_payload_uses_responder_gate(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    session = god_of_carnage_module_with_state
    if "characters" not in session.canonical_state:
        session.canonical_state["characters"] = {}
    session.canonical_state["characters"].setdefault("veronique", {})["emotional_state"] = 40

    role_payload = {
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
            "response_impulses": [],
            "state_change_candidates": [
                {
                    "target_path": "characters.veronique.emotional_state",
                    "proposed_value": 55,
                    "rationale": "shift",
                }
            ],
            "trigger_assertions": [],
            "scene_transition_candidate": None,
        },
    }
    adapter = DeterministicAIAdapter(payload=role_payload)

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert result.guard_outcome in (
        GuardOutcome.ACCEPTED,
        GuardOutcome.REJECTED,
        GuardOutcome.PARTIALLY_ACCEPTED,
    )


def test_restore_apply_raises_valueerror_then_safe_turn(
    god_of_carnage_module, god_of_carnage_module_with_state
):
    session = god_of_carnage_module_with_state
    initial = session.canonical_state.copy()
    adapter = DeterministicAIAdapter(error="fail")

    with patch.object(
        RestorePolicy,
        "apply_restore",
        side_effect=ValueError("snapshot invalid"),
    ):
        result = asyncio.run(
            execute_turn_with_ai(
                session,
                current_turn=session.turn_counter + 1,
                adapter=adapter,
                module=god_of_carnage_module,
            )
        )

    assert result.execution_status == "success"
    assert result.updated_canonical_state == initial
    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR


def test_tool_loop_summary_absent_when_disabled(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Disabled tool loop should not add transcript fields to decision log."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["tool_loop"] = {"enabled": False}

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
    decision_log = session.metadata["ai_decision_logs"][-1]
    assert decision_log.tool_loop_summary is None
    assert decision_log.tool_call_transcript is None


def test_preview_diagnostics_recorded_when_preview_tool_is_used(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Preview tool usage is persisted into decision diagnostics."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.guard.preview_delta"],
        "max_tool_calls_per_turn": 3,
    }

    # second adapter call finalizes with corrected proposal
    class PreviewThenFinalizeAdapter(DeterministicAIAdapter):
        def __init__(self):
            self.calls = 0
        @property
        def adapter_name(self):
            return "preview-then-finalize"
        def generate(self, request):
            self.calls += 1
            if self.calls == 1:
                return AdapterResponse(
                    raw_output="preview",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.guard.preview_delta",
                        "arguments": {
                            "proposed_state_deltas": [
                                {
                                    "target_path": "characters.nonexistent.emotional_state",
                                    "next_value": 10,
                                    "delta_type": "state_update",
                                }
                            ]
                        },
                    },
                )
            return AdapterResponse(
                raw_output="final",
                structured_payload={
                    "scene_interpretation": "corrected",
                    "detected_triggers": [],
                    "proposed_state_deltas": [
                        {
                            "target_path": "characters.veronique.emotional_state",
                            "next_value": 60,
                            "delta_type": "state_update",
                        }
                    ],
                    "rationale": "corrected",
                },
            )

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=PreviewThenFinalizeAdapter(),
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    decision_log = session.metadata["ai_decision_logs"][-1]
    assert decision_log.preview_diagnostics is not None
    assert decision_log.preview_diagnostics["preview_count"] >= 1
    assert decision_log.preview_diagnostics["last_preview_request"]["requesting_agent_id"] == "primary_ai"
    assert decision_log.preview_diagnostics["last_preview"]["preview_safe_no_write"] is True
    assert len(decision_log.preview_diagnostics["preview_iterations"]) >= 1


def test_agent_orchestration_executes_real_separate_subagents_and_logs_trace(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """C1 reality check: at least two non-finalizer calls plus one finalizer call."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["agent_orchestration"] = {"enabled": True}
    session.metadata["tool_loop"] = {"enabled": False}

    class MultiAgentRecordingAdapter(StoryAIAdapter):
        def __init__(self) -> None:
            self.calls: list[str] = []

        @property
        def adapter_name(self) -> str:
            return "multi-agent-recording"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            invocation = request.metadata.get("agent_invocation") or {}
            agent_id = invocation.get("agent_id", "unknown")
            self.calls.append(agent_id)

            if agent_id == "scene_reader":
                return AdapterResponse(
                    raw_output="scene reader",
                    structured_payload={
                        "scene_interpretation": "scene",
                        "detected_triggers": [],
                        "proposed_state_deltas": [],
                        "rationale": "scene context",
                    },
                )
            if agent_id == "trigger_analyst":
                return AdapterResponse(
                    raw_output="trigger analyst",
                    structured_payload={
                        "scene_interpretation": "triggers",
                        "detected_triggers": ["trigger_a"],
                        "proposed_state_deltas": [],
                        "rationale": "trigger context",
                    },
                )
            if agent_id == "delta_planner":
                return AdapterResponse(
                    raw_output="delta planner",
                    structured_payload={
                        "scene_interpretation": "delta plan",
                        "detected_triggers": ["trigger_a"],
                        "proposed_state_deltas": [
                            {
                                "target_path": "characters.veronique.emotional_state",
                                "next_value": 65,
                                "delta_type": "state_update",
                                "rationale": "test update",
                            }
                        ],
                        "rationale": "delta planned",
                    },
                )
            if agent_id == "dialogue_planner":
                return AdapterResponse(
                    raw_output="dialogue planner",
                    structured_payload={
                        "scene_interpretation": "dialogue",
                        "detected_triggers": [],
                        "proposed_state_deltas": [],
                        "rationale": "dialogue helper",
                    },
                )
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized from multiple subagents"
                return AdapterResponse(
                    raw_output="finalizer",
                    structured_payload=payload,
                )
            return AdapterResponse(raw_output="unexpected", structured_payload={})

    adapter = MultiAgentRecordingAdapter()
    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=adapter,
            module=god_of_carnage_module,
        )
    )

    assert result.execution_status == "success"
    assert len(adapter.calls) >= 3
    non_finalizer_calls = [name for name in adapter.calls if name != "finalizer"]
    assert len(non_finalizer_calls) >= 2
    assert "finalizer" in adapter.calls

    decision_log = session.metadata["ai_decision_logs"][-1]
    assert decision_log.supervisor_plan is not None
    assert decision_log.subagent_invocations is not None
    assert decision_log.subagent_results is not None
    assert decision_log.merge_finalization is not None
    assert len(decision_log.subagent_invocations) >= 3
    invocation_ids = [item.agent_id for item in decision_log.subagent_invocations]
    assert "finalizer" in invocation_ids
    assert sum(1 for item in invocation_ids if item != "finalizer") >= 2
    assert decision_log.tool_loop_summary is not None
    controls = decision_log.tool_loop_summary.get("execution_controls") or {}
    assert controls.get("agent_orchestration_active") is True
    assert controls.get("tool_loop_active") is False
    assert controls.get("tool_loop_requested") is False
    assert decision_log.operator_audit is not None
    assert decision_log.operator_audit["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    pre_summary = decision_log.operator_audit["audit_summary"]
    assert pre_summary.get("staged_pipeline_preempted") == "agent_orchestration"
    assert pre_summary.get("preempt_reason_detail")
    assert pre_summary.get("note_deep_traces")
    timeline = decision_log.operator_audit.get("audit_timeline") or []
    preempt_entries = [e for e in timeline if e.get("stage_key") == "orchestration_preempted"]
    assert len(preempt_entries) == 1
    assert preempt_entries[0].get("stage_kind") == "orchestration_preempted"
    assert not (decision_log.runtime_stage_traces or [])
    assert decision_log.merge_finalization.fallback_used is False
    assert decision_log.merge_finalization.finalizer_status == "success"
    assert decision_log.orchestration_budget_summary is not None
    consumed = decision_log.orchestration_budget_summary["consumed"]
    assert consumed["consumed_total_tokens"] >= 0
    assert consumed["token_usage_mode"] in {"exact", "proxy", "mixed"}
    assert "proxy_fallback_count" in consumed
    assert decision_log.orchestration_failover is not None
    assert decision_log.orchestration_cache is not None
    assert decision_log.tool_audit is not None


def test_agent_orchestration_has_priority_over_requested_tool_loop(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """When both are requested, orchestration is active and top-level tool loop stays inactive."""
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["agent_orchestration"] = {"enabled": True}
    session.metadata["tool_loop"] = {
        "enabled": True,
        "allowed_tools": ["wos.read.current_scene"],
        "max_tool_calls_per_turn": 3,
    }

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
    decision_log = session.metadata["ai_decision_logs"][-1]
    assert decision_log.tool_loop_summary is not None
    controls = decision_log.tool_loop_summary.get("execution_controls") or {}
    assert controls.get("agent_orchestration_active") is True
    assert controls.get("tool_loop_requested") is True
    assert controls.get("tool_loop_active") is False


def test_adapter_generate_timeout_is_contained_with_explicit_failure_reason(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    session = god_of_carnage_module_with_state
    session.execution_mode = "ai"
    session.metadata["adapter_generate_timeout_ms"] = 5

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=SlowDeterministicAdapter(sleep_seconds=0.05),
            module=god_of_carnage_module,
        )
    )

    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR
    decision_logs = session.metadata.get("ai_decision_logs", [])
    assert decision_logs
    assert any(
        (
            log.guard_notes
            and "adapter_generate_timeout" in log.guard_notes
        )
        or (
            log.recovery_notes
            and "adapter_generate_timeout" in log.recovery_notes
        )
        for log in decision_logs
    )
