"""Tests for W2.3.1 short-term turn context derivation.

Tests verify that:
- short-term context can be derived from a recent turn sequence
- context remains bounded
- current scene and immediate turn-relevant state are present
- irrelevant older details are not treated as short-term context
- no regressions in existing runtime tests
"""

from __future__ import annotations

import pytest

from app.runtime.short_term_context import (
    ShortTermTurnContext,
    build_short_term_context,
)
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn


class TestShortTermContextBuilding:
    """Unit tests for building context from turn results."""

    def test_build_from_accepted_turn(self, god_of_carnage_module_with_state):
        """Valid delta decision → guard_outcome=='accepted'."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
            narrative_text="Test",
            rationale="Test valid delta",
        )

        # Synchronous execution would need to be wrapped, but we're just testing
        # the context derivation function, which is pure.
        # For this test, we'll create a mock result.
        # Actually, we need async for execute_turn. Let me restructure this.
        # For now, use a simpler approach: test with a direct result object.
        from app.runtime.runtime_models import GuardOutcome, StateDelta, DeltaType, DeltaValidationStatus

        # Create a mock result
        accepted_delta = StateDelta(
            id="delta_1",
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            target_entity="veronique",
            previous_value=25,
            next_value=50,
            source="ai_proposal",
            validation_status=DeltaValidationStatus.ACCEPTED,
            turn_number=1,
        )

        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[accepted_delta],
            rejected_deltas=[],
            updated_canonical_state={"conflict_state": {"pressure": 30}},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.ACCEPTED,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.turn_number == 1
        assert context.guard_outcome == "accepted"
        assert context.accepted_delta_targets == ["characters.veronique.emotional_state"]
        assert context.rejected_delta_targets == []
        assert context.scene_id == "act_1_scene_1"

    def test_build_from_rejected_turn(self, god_of_carnage_module_with_state):
        """Invalid reference decision → guard_outcome=='rejected'."""
        from app.runtime.runtime_models import GuardOutcome, StateDelta, DeltaType, DeltaValidationStatus
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[
                ProposedStateDelta(target="characters.nonexistent.emotional_state", next_value=50)
            ],
            narrative_text="Test",
            rationale="Test invalid reference",
        )

        rejected_delta = StateDelta(
            id="delta_1",
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.nonexistent.emotional_state",
            target_entity="nonexistent",
            previous_value=None,
            next_value=50,
            source="ai_proposal",
            validation_status=DeltaValidationStatus.REJECTED,
            turn_number=1,
        )

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=["Reference validation failed: unknown_character"],
            accepted_deltas=[],
            rejected_deltas=[rejected_delta],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.REJECTED,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.guard_outcome == "rejected"
        assert context.accepted_delta_targets == []
        assert context.rejected_delta_targets == ["characters.nonexistent.emotional_state"]

    def test_build_from_empty_decision(self):
        """Empty proposed_deltas → guard_outcome=='structurally_invalid'."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[],
            narrative_text="Empty",
            rationale="No changes",
        )

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.guard_outcome == "structurally_invalid"

    def test_scene_id_populated(self):
        """result.updated_scene_id is captured in context.scene_id."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_2",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.scene_id == "act_1_scene_2"

    def test_detected_triggers_captured(self):
        """decision.detected_triggers appear in context.detected_triggers."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(
            detected_triggers=["trigger_1", "trigger_2"],
            proposed_deltas=[],
            narrative_text="",
            rationale="",
        )

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.detected_triggers == ["trigger_1", "trigger_2"]


class TestShortTermContextSceneTransition:
    """Tests for scene transition detection in context."""

    def test_scene_changed_when_prior_differs(self):
        """prior_scene_id != updated_scene_id → scene_changed=True."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_2",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result, prior_scene_id="act_1_scene_1")

        assert context.scene_changed is True
        assert context.prior_scene_id == "act_1_scene_1"

    def test_scene_unchanged_when_same(self):
        """prior_scene_id == updated_scene_id → scene_changed=False."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result, prior_scene_id="act_1_scene_1")

        assert context.scene_changed is False
        assert context.prior_scene_id is None

    def test_no_scene_change_without_prior(self):
        """prior_scene_id=None → scene_changed=False."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_2",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result, prior_scene_id=None)

        assert context.scene_changed is False
        assert context.prior_scene_id is None


class TestShortTermContextBounds:
    """Tests for context boundedness."""

    def test_no_full_canonical_state(self):
        """Context has no canonical_state or updated_canonical_state field."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={"characters": {"veronique": {"emotional_state": 50}}},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert not hasattr(context, "canonical_state")
        assert not hasattr(context, "updated_canonical_state")

    def test_delta_targets_are_strings_not_objects(self):
        """accepted_delta_targets is list[str], not list[StateDelta]."""
        from app.runtime.runtime_models import GuardOutcome, StateDelta, DeltaType, DeltaValidationStatus
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        delta = StateDelta(
            id="delta_1",
            delta_type=DeltaType.CHARACTER_STATE,
            target_path="characters.veronique.emotional_state",
            target_entity="veronique",
            previous_value=25,
            next_value=50,
            source="ai_proposal",
            validation_status=DeltaValidationStatus.ACCEPTED,
            turn_number=1,
        )

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[delta],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.ACCEPTED,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert all(isinstance(target, str) for target in context.accepted_delta_targets)
        assert context.accepted_delta_targets == ["characters.veronique.emotional_state"]

    def test_context_bounded_to_single_turn(self):
        """No field references multiple turns or contains history list."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=5,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        # Verify single-turn scope
        assert context.turn_number == 5
        assert not hasattr(context, "prior_turns")
        assert not hasattr(context, "turn_history")
        assert not hasattr(context, "recent_events")


class TestShortTermContextIntegration:
    """Integration tests using real turn execution."""

    @pytest.mark.asyncio
    async def test_derived_from_real_turn(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Run execute_turn() with fixtures, build context, assert structure."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
            narrative_text="Integration test",
            rationale="Test real turn",
        )

        result = await execute_turn(session, 1, decision, god_of_carnage_module)

        context = build_short_term_context(result, prior_scene_id=session.current_scene_id)

        assert isinstance(context, ShortTermTurnContext)
        assert context.turn_number == 1
        assert context.scene_id == result.updated_scene_id
        assert context.guard_outcome in ["accepted", "partially_accepted", "rejected", "structurally_invalid"]

    def test_conflict_pressure_extraction(self):
        """If canonical_state has conflict_state.pressure, it appears in context."""
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult
        from datetime import datetime

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")

        result = TurnExecutionResult(
            turn_number=1,
            session_id="test_session",
            execution_status="success",
            decision=decision,
            validation_outcome=None,
            validation_errors=[],
            accepted_deltas=[],
            rejected_deltas=[],
            updated_canonical_state={"conflict_state": {"pressure": 45}},
            updated_scene_id="act_1_scene_1",
            updated_ending_id=None,
            guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
            failure_reason="none",
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=10.0,
            events=[],
        )

        context = build_short_term_context(result)

        assert context.conflict_pressure == 45


class TestBuildShortTermContextSessionState:
    """W3: session_state.metadata["ai_decision_logs"] -> ai_decision_log_full."""

    def _base_result(self):
        from datetime import datetime
        from app.runtime.runtime_models import GuardOutcome
        from app.runtime.turn_executor import TurnExecutionResult

        decision = MockDecision(proposed_deltas=[], narrative_text="", rationale="")
        return TurnExecutionResult(
            turn_number=1,
            session_id="s",
            execution_status="success",
            decision=decision,
            updated_canonical_state={"conflict_state": "not_a_dict"},
            updated_scene_id="scene_a",
            guard_outcome=GuardOutcome.ACCEPTED,
            started_at=datetime.now(),
            completed_at=datetime.now(),
            duration_ms=1.0,
            events=[],
        )

    def test_conflict_state_non_dict_skips_pressure(self):
        ctx = build_short_term_context(self._base_result())
        assert ctx.conflict_pressure is None

    def test_ai_decision_log_from_pydantic_model(self):
        from pydantic import BaseModel
        from types import SimpleNamespace

        class LogEntry(BaseModel):
            kind: str = "decision"

        result = self._base_result()
        session_state = SimpleNamespace(
            metadata={"ai_decision_logs": [LogEntry(kind="x")]}
        )
        ctx = build_short_term_context(result, session_state=session_state)
        assert ctx.ai_decision_log_full == {"kind": "x"}

    def test_ai_decision_log_plain_dict(self):
        from types import SimpleNamespace

        result = self._base_result()
        session_state = SimpleNamespace(
            metadata={"ai_decision_logs": [{"raw": True}]}
        )
        ctx = build_short_term_context(result, session_state=session_state)
        assert ctx.ai_decision_log_full == {"raw": True}

    def test_ai_decision_log_exception_falls_back_to_none(self):
        from types import SimpleNamespace

        class BadLog:
            def model_dump(self, mode="json"):
                raise RuntimeError("fail dump")

        result = self._base_result()
        session_state = SimpleNamespace(
            metadata={"ai_decision_logs": [BadLog()]}
        )
        ctx = build_short_term_context(result, session_state=session_state)
        assert ctx.ai_decision_log_full is None
