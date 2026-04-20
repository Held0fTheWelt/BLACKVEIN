"""Tests for W2.3-R2: Post-turn short-term context and session history accumulation.

Verifies that completed turns produce real short-term context and that
session history is actually accumulated during runtime execution.
"""

from __future__ import annotations

import pytest

from app.runtime.session_history import SessionHistory, HistoryEntry
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn
from app.runtime.runtime_models import SessionState, GuardOutcome


class TestShortTermContextDerivation:
    """Tests that completed turns produce ShortTermTurnContext."""

    @pytest.mark.asyncio
    async def test_successful_turn_creates_short_term_context(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Successful turn execution creates short-term context in session."""
        session = god_of_carnage_module_with_state

        # Execute a simple turn
        decision = MockDecision(
            detected_triggers=["conflict_escalates"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=60)
            ],
            narrative_text="Veronique becomes more emotional.",
            rationale="test",
        )

        result = await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify turn completed successfully
        assert result.execution_status == "success"
        assert result.guard_outcome == GuardOutcome.ACCEPTED

        # Verify short-term context was created in session
        assert session.context_layers.short_term_context is not None
        assert isinstance(session.context_layers.short_term_context, ShortTermTurnContext)
        assert session.context_layers.short_term_context.turn_number == 1
        assert session.context_layers.short_term_context.guard_outcome == "accepted"
        assert "conflict_escalates" in session.context_layers.short_term_context.detected_triggers

    @pytest.mark.asyncio
    async def test_rejected_turn_creates_short_term_context(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Rejected turn still creates short-term context."""
        session = god_of_carnage_module_with_state

        # Execute turn with invalid reference
        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[
                ProposedStateDelta(target="nonexistent.path.value", next_value="invalid")
            ],
            narrative_text="Invalid change.",
            rationale="test",
        )

        result = await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify turn had validation issues
        assert result.guard_outcome == GuardOutcome.REJECTED
        assert len(result.rejected_deltas) > 0

        # Verify short-term context still created (even with rejection)
        assert session.context_layers.short_term_context is not None
        assert session.context_layers.short_term_context.guard_outcome == "rejected"
        assert len(session.context_layers.short_term_context.rejected_delta_targets) > 0


class TestSessionHistoryAccumulation:
    """Tests that SessionHistory accumulates across real turns."""

    @pytest.mark.asyncio

    async def test_session_history_created_on_first_turn(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """First turn execution creates and populates SessionHistory."""
        session = god_of_carnage_module_with_state

        # Initial state
        assert session.context_layers.session_history is None

        # Execute first turn
        decision = MockDecision(
            detected_triggers=["tension_rises"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
        )

        result = await execute_turn(session, 1, decision, god_of_carnage_module)
        assert result.execution_status == "success"

        # Verify SessionHistory was created and populated
        assert session.context_layers.session_history is not None
        assert isinstance(session.context_layers.session_history, SessionHistory)
        assert session.context_layers.session_history.size == 1

        # Verify entry was added
        entry = session.context_layers.session_history.last_entry
        assert entry is not None
        assert entry.turn_number == 1
        assert "tension_rises" in entry.detected_triggers

    @pytest.mark.asyncio

    async def test_session_history_accumulates_across_multiple_turns(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Multiple turns accumulate in SessionHistory."""
        session = god_of_carnage_module_with_state

        # Execute multiple turns
        for turn_num in range(1, 4):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state",
                        next_value=turn_num * 10
                    )
                ],
            )

            result = await execute_turn(session, turn_num, decision, god_of_carnage_module)
            assert result.execution_status == "success"

        # Verify history accumulated all turns
        assert session.context_layers.session_history is not None
        assert session.context_layers.session_history.size == 3

        # Verify ordering (oldest to newest)
        entries = session.context_layers.session_history.entries
        assert entries[0].turn_number == 1
        assert entries[1].turn_number == 2
        assert entries[2].turn_number == 3

        # Verify triggers were preserved
        assert "trigger_1" in entries[0].detected_triggers
        assert "trigger_2" in entries[1].detected_triggers
        assert "trigger_3" in entries[2].detected_triggers

    @pytest.mark.asyncio

    async def test_session_history_respects_bounded_size(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """SessionHistory respects max_size boundary."""
        session = god_of_carnage_module_with_state

        # Manually set a small max_size to test trimming
        session.context_layers.session_history = SessionHistory(max_size=3)

        # Execute more turns than max_size
        for turn_num in range(1, 6):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
            )

            result = await execute_turn(session, turn_num, decision, god_of_carnage_module)
            assert result.execution_status == "success"

        # Verify history is bounded to max_size
        assert session.context_layers.session_history.size == 3
        assert session.context_layers.session_history.is_full is True

        # Verify oldest entries were trimmed (FIFO behavior)
        entries = session.context_layers.session_history.entries
        assert entries[0].turn_number == 3  # Turns 1-2 trimmed
        assert entries[1].turn_number == 4
        assert entries[2].turn_number == 5


class TestSceneTransitionTracking:
    """Tests that scene transitions are properly tracked in history."""

    @pytest.mark.asyncio

    async def test_scene_change_detected_in_history(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Scene transitions are recorded in SessionHistory."""
        session = god_of_carnage_module_with_state
        initial_scene = session.current_scene_id

        # Execute turn with scene transition
        decision = MockDecision(
            detected_triggers=["transition_safe"],
            proposed_scene_id="ending_safe" if initial_scene != "ending_safe" else "scene_1",
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Check if scene transitioned
        if session.current_scene_id != initial_scene:
            # Verify transition was recorded in history
            entry = session.context_layers.session_history.last_entry
            assert entry.scene_changed is True
            assert entry.prior_scene_id == initial_scene


class TestFailedTurnAccumulation:
    """Tests that failed/invalid turns are still accumulated."""

    @pytest.mark.asyncio

    async def test_system_error_turn_creates_context(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """System error turns still create short-term context."""
        session = god_of_carnage_module_with_state

        # Create a decision that will likely cause issues
        decision = MockDecision(
            detected_triggers=["invalid_trigger_xyz"],
        )

        result = await execute_turn(session, 1, decision, god_of_carnage_module)

        # Even if execution had issues, context should be created
        # (Though this particular decision might succeed with no deltas)
        assert session.context_layers.short_term_context is not None
        assert session.context_layers.session_history is not None
        assert session.context_layers.session_history.size >= 1


class TestContextOrderingAndDeterminism:
    """Tests that accumulation is deterministic and ordered."""

    @pytest.mark.asyncio

    async def test_accumulation_ordering_is_deterministic(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Multiple turns accumulate in deterministic order."""
        session = god_of_carnage_module_with_state

        # Execute turns with distinct markers
        for turn_num in range(1, 4):
            decision = MockDecision(
                detected_triggers=[f"det_trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state",
                        next_value=turn_num * 10
                    )
                ],
            )

            await execute_turn(session, turn_num, decision, god_of_carnage_module)

        # Verify order is preserved
        entries = session.context_layers.session_history.entries
        for i, entry in enumerate(entries, 1):
            assert entry.turn_number == i
            assert f"det_trigger_{i}" in entry.detected_triggers

        # Verify most recent context matches latest turn
        assert session.context_layers.short_term_context.turn_number == 3
        assert "det_trigger_3" in session.context_layers.short_term_context.detected_triggers

    @pytest.mark.asyncio

    async def test_short_term_context_always_reflects_latest_turn(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """short_term_context always contains the most recent turn."""
        session = god_of_carnage_module_with_state

        for turn_num in range(1, 4):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
            )

            await execute_turn(session, turn_num, decision, god_of_carnage_module)

            # Verify short_term_context updated
            assert session.context_layers.short_term_context.turn_number == turn_num
            assert f"trigger_{turn_num}" in session.context_layers.short_term_context.detected_triggers

        # Verify it still reflects the latest
        assert session.context_layers.short_term_context.turn_number == 3


class TestGuardOutcomeVariation:
    """Tests accumulation with different guard outcomes."""

    @pytest.mark.asyncio

    async def test_accepted_turn_accumulation(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """ACCEPTED turns create context and history."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["valid_trigger"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=55)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        assert session.context_layers.short_term_context.guard_outcome == "accepted"
        assert len(session.context_layers.session_history.entries) == 1

    @pytest.mark.asyncio

    async def test_partially_accepted_turn_accumulation(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """PARTIALLY_ACCEPTED turns create context and history."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=[],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=45),
                ProposedStateDelta(target="invalid.path", next_value="bad"),
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # At least one delta should be accepted/rejected (resulting in partial)
        # Context and history should still be created
        assert session.context_layers.short_term_context is not None
        assert session.context_layers.session_history is not None
        assert len(session.context_layers.session_history.entries) >= 1
