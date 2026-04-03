"""Tests for W2.0.1 canonical story runtime models."""

import pytest
from pydantic import ValidationError

from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaType,
    DeltaValidationStatus,
    EventLogEntry,
    GuardOutcome,
    SessionState,
    SessionStatus,
    StateDelta,
    TurnState,
    TurnStatus,
)


class TestSessionStatusEnum:
    """Tests for SessionStatus enum."""

    def test_session_status_values(self):
        """Verify all session status enum values exist."""
        assert SessionStatus.ACTIVE == "active"
        assert SessionStatus.PAUSED == "paused"
        assert SessionStatus.ENDED == "ended"
        assert SessionStatus.CRASHED == "crashed"


class TestSessionState:
    """Tests for SessionState model."""

    def test_session_state_defaults(self):
        """Construct SessionState with required fields and verify defaults."""
        state = SessionState(
            module_id="god_of_carnage",
            module_version="0.1.0",
            current_scene_id="phase_1",
        )
        assert state.session_id is not None
        assert len(state.session_id) == 32  # uuid4().hex format
        assert state.module_id == "god_of_carnage"
        assert state.module_version == "0.1.0"
        assert state.current_scene_id == "phase_1"
        assert state.status == SessionStatus.ACTIVE
        assert state.turn_counter == 0
        assert state.canonical_state == {}
        assert state.seed is None
        assert state.metadata == {}
        assert state.created_at is not None
        assert state.updated_at is not None

    def test_session_state_required_fields(self):
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            SessionState(module_version="0.1.0", current_scene_id="phase_1")
        assert "module_id" in str(exc_info.value)

    def test_session_state_unique_ids(self):
        """Two SessionState instances have different IDs."""
        state1 = SessionState(
            module_id="god_of_carnage",
            module_version="0.1.0",
            current_scene_id="phase_1",
        )
        state2 = SessionState(
            module_id="god_of_carnage",
            module_version="0.1.0",
            current_scene_id="phase_1",
        )
        assert state1.session_id != state2.session_id

    def test_session_state_custom_status(self):
        """SessionState accepts custom status."""
        state = SessionState(
            module_id="god_of_carnage",
            module_version="0.1.0",
            current_scene_id="phase_1",
            status=SessionStatus.PAUSED,
        )
        assert state.status == SessionStatus.PAUSED

    def test_session_state_with_seed(self):
        """SessionState can be constructed with reproducibility seed."""
        state = SessionState(
            module_id="god_of_carnage",
            module_version="0.1.0",
            current_scene_id="phase_1",
            seed="reproducibility_seed_12345",
        )
        assert state.seed == "reproducibility_seed_12345"


class TestTurnStatusEnum:
    """Tests for TurnStatus enum."""

    def test_turn_status_values(self):
        """Verify all turn status enum values exist."""
        assert TurnStatus.PENDING == "pending"
        assert TurnStatus.RUNNING == "running"
        assert TurnStatus.COMPLETED == "completed"
        assert TurnStatus.FAILED == "failed"


class TestTurnState:
    """Tests for TurnState model."""

    def test_turn_state_defaults(self):
        """Construct TurnState with required fields and verify defaults."""
        turn = TurnState(
            turn_number=1,
            session_id="session_abc123",
        )
        assert turn.turn_number == 1
        assert turn.session_id == "session_abc123"
        assert turn.input_payload == {}
        assert turn.pre_turn_snapshot is None
        assert turn.post_turn_result is None
        assert turn.status == TurnStatus.PENDING
        assert turn.started_at is None
        assert turn.completed_at is None
        assert turn.duration_ms is None

    def test_turn_state_required_fields(self):
        """Missing required field raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            TurnState(session_id="session_abc123")
        assert "turn_number" in str(exc_info.value)

    def test_turn_state_with_snapshots(self):
        """TurnState can include pre- and post-turn snapshots."""
        pre_snapshot = {"characters": {"veronique": {"emotional_state": 50}}}
        post_snapshot = {"characters": {"veronique": {"emotional_state": 60}}}
        turn = TurnState(
            turn_number=2,
            session_id="session_abc123",
            pre_turn_snapshot=pre_snapshot,
            post_turn_result=post_snapshot,
        )
        assert turn.pre_turn_snapshot == pre_snapshot
        assert turn.post_turn_result == post_snapshot


class TestEventLogEntry:
    """Tests for EventLogEntry model."""

    def test_event_log_entry_auto_id(self):
        """Two EventLogEntry instances have different IDs."""
        entry1 = EventLogEntry(
            event_type="turn_completed",
            order_index=1,
            summary="Turn 1 completed successfully",
            session_id="session_abc123",
        )
        entry2 = EventLogEntry(
            event_type="turn_completed",
            order_index=2,
            summary="Turn 2 completed successfully",
            session_id="session_abc123",
        )
        assert entry1.id != entry2.id
        assert len(entry1.id) == 32  # uuid4().hex format

    def test_event_log_entry_required_fields(self):
        """Missing summary raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            EventLogEntry(
                event_type="turn_completed",
                order_index=1,
                session_id="session_abc123",
            )
        assert "summary" in str(exc_info.value)

    def test_event_log_entry_defaults(self):
        """EventLogEntry defaults are correct."""
        entry = EventLogEntry(
            event_type="session_started",
            order_index=0,
            summary="Session started",
            session_id="session_abc123",
        )
        assert entry.payload == {}
        assert entry.turn_number is None
        assert entry.occurred_at is not None

    def test_event_log_entry_session_level(self):
        """Session-level event has no turn number."""
        entry = EventLogEntry(
            event_type="session_started",
            order_index=0,
            summary="Session started",
            session_id="session_abc123",
        )
        assert entry.turn_number is None

    def test_event_log_entry_turn_level(self):
        """Turn-level event includes turn number."""
        entry = EventLogEntry(
            event_type="turn_completed",
            order_index=1,
            summary="Turn 1 completed",
            session_id="session_abc123",
            turn_number=1,
        )
        assert entry.turn_number == 1


class TestDeltaTypeEnum:
    """Tests for DeltaType enum."""

    def test_delta_type_values(self):
        """Verify all delta type enum values exist."""
        assert DeltaType.CHARACTER_STATE == "character_state"
        assert DeltaType.RELATIONSHIP == "relationship"
        assert DeltaType.SCENE == "scene"
        assert DeltaType.TRIGGER == "trigger"
        assert DeltaType.METADATA == "metadata"


class TestDeltaValidationStatusEnum:
    """Tests for DeltaValidationStatus enum."""

    def test_delta_validation_status_values(self):
        """Verify all delta validation status enum values exist."""
        assert DeltaValidationStatus.PENDING == "pending"
        assert DeltaValidationStatus.ACCEPTED == "accepted"
        assert DeltaValidationStatus.REJECTED == "rejected"
        assert DeltaValidationStatus.MODIFIED == "modified"


class TestStateDelta:
    """Tests for StateDelta model."""

    def test_state_delta_defaults(self):
        """Construct StateDelta with required fields and verify defaults."""
        delta = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            source="ai_proposal",
        )
        assert delta.id is not None
        assert len(delta.id) == 32
        assert delta.delta_type == DeltaType.CHARACTER_STATE
        assert delta.target_path == "characters.veronique.emotional_state"
        assert delta.target_entity is None
        assert delta.previous_value is None
        assert delta.next_value is None
        assert delta.source == "ai_proposal"
        assert delta.validation_status == DeltaValidationStatus.PENDING
        assert delta.turn_number is None

    def test_state_delta_with_values(self):
        """StateDelta can include before/after values."""
        delta = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            target_entity="veronique",
            previous_value=50,
            next_value=65,
            source="ai_proposal",
        )
        assert delta.target_entity == "veronique"
        assert delta.previous_value == 50
        assert delta.next_value == 65

    def test_state_delta_unique_ids(self):
        """Two StateDelta instances have different IDs."""
        delta1 = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            source="ai_proposal",
        )
        delta2 = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            source="ai_proposal",
        )
        assert delta1.id != delta2.id

    def test_state_delta_enum_validation(self):
        """StateDelta validates enum values."""
        delta = StateDelta(
            delta_type=DeltaType.RELATIONSHIP,
            target_path="relationships.axis1.veronique_michel",
            source="engine",
            validation_status=DeltaValidationStatus.ACCEPTED,
        )
        assert delta.delta_type == DeltaType.RELATIONSHIP
        assert delta.validation_status == DeltaValidationStatus.ACCEPTED


class TestAIValidationOutcomeEnum:
    """Tests for AIValidationOutcome enum."""

    def test_ai_validation_outcome_values(self):
        """Verify all AI validation outcome enum values exist."""
        assert AIValidationOutcome.ACCEPTED == "accepted"
        assert AIValidationOutcome.REJECTED == "rejected"
        assert AIValidationOutcome.PARTIAL == "partial"
        assert AIValidationOutcome.ERROR == "error"


class TestAIDecisionLog:
    """Tests for AIDecisionLog model."""

    def test_ai_decision_log_defaults(self):
        """Construct AIDecisionLog with required fields and verify defaults."""
        decision = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            guard_outcome=GuardOutcome.ACCEPTED,
        )
        assert decision.id is not None
        assert len(decision.id) == 32
        assert decision.session_id == "session_abc123"
        assert decision.turn_number == 1
        assert decision.raw_output is None
        assert decision.parsed_output is None
        assert decision.validation_outcome == AIValidationOutcome.ACCEPTED
        assert decision.accepted_deltas == []
        assert decision.rejected_deltas == []
        assert decision.guard_notes is None
        assert decision.recovery_notes is None
        assert decision.created_at is not None

    def test_ai_decision_log_with_deltas(self):
        """AIDecisionLog can include accepted/rejected deltas."""
        delta_accepted = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            source="ai_proposal",
            validation_status=DeltaValidationStatus.ACCEPTED,
        )
        delta_rejected = StateDelta(
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.michel.emotional_state",
            source="ai_proposal",
            validation_status=DeltaValidationStatus.REJECTED,
        )
        decision = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            accepted_deltas=[delta_accepted],
            rejected_deltas=[delta_rejected],
            guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
        )
        assert len(decision.accepted_deltas) == 1
        assert len(decision.rejected_deltas) == 1
        assert decision.accepted_deltas[0].target_path == "characters.veronique.emotional_state"
        assert decision.rejected_deltas[0].target_path == "characters.michel.emotional_state"

    def test_ai_decision_log_unique_ids(self):
        """Two AIDecisionLog instances have different IDs."""
        decision1 = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            guard_outcome=GuardOutcome.ACCEPTED,
        )
        decision2 = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            guard_outcome=GuardOutcome.ACCEPTED,
        )
        assert decision1.id != decision2.id

    def test_ai_decision_log_with_guard_notes(self):
        """AIDecisionLog can include guard intervention notes."""
        decision = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            validation_outcome=AIValidationOutcome.PARTIAL,
            guard_notes="Emotion escalation exceeded bounds",
            recovery_notes="Clamped to valid range",
            guard_outcome=GuardOutcome.PARTIALLY_ACCEPTED,
        )
        assert decision.validation_outcome == AIValidationOutcome.PARTIAL
        assert decision.guard_notes == "Emotion escalation exceeded bounds"
        assert decision.recovery_notes == "Clamped to valid range"

    def test_ai_decision_log_with_raw_output(self):
        """AIDecisionLog can include raw AI output."""
        raw_text = "The scene is tense. Veronique's emotions escalate to 75."
        parsed = {"scene_tension": "high", "character_veronique_emotion": 75}
        decision = AIDecisionLog(
            session_id="session_abc123",
            turn_number=1,
            raw_output=raw_text,
            parsed_output=parsed,
            guard_outcome=GuardOutcome.ACCEPTED,
        )
        assert decision.raw_output == raw_text
        assert decision.parsed_output == parsed
