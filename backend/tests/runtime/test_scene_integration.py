"""Canonical W2.3 integration proof: all five context layers work together in real runtime.

This test suite is the integration gate for W2.3 re-evaluation. It proves:
- All five W2.3 layers exist, are correct types, and update across turns
- Layer state is detectable as changing (not static)
- FIFO trimming leaves derived layers coherent
- Boundedness and distinctness hold in runtime, not just in helper tests
- Tests fail if accumulation/derivation is removed

W2.3 is complete only when these tests pass.
"""

from __future__ import annotations

import pytest

from app.runtime.lore_direction_context import LoreDirectionContext
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.session_history import SessionHistory
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn


class TestW23CanonicalIntegration:
    """Canonical-path integration proof for all five W2.3 layers working together."""

    @pytest.mark.asyncio
    async def test_all_five_w23_layers_coherent_across_five_turns(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """All five W2.3 layers exist, update, and remain coherent across 5 real turns.

        This is the canonical integration snapshot. After 5 turns with varied triggers,
        all five layers are present, have correct types, show turn-specific data, and
        remain bounded.
        """
        session = god_of_carnage_module_with_state

        # Execute 5 turns with varied triggers (some character-named)
        for turn_num in range(1, 6):
            decision = MockDecision(
                detected_triggers=[f"tension_veronique_{turn_num}", f"escalation_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state", next_value=turn_num * 10
                    )
                ],
            )
            await execute_turn(session, turn_num, decision, god_of_carnage_module)

        # ===== W2.3.1: ShortTermTurnContext =====
        ctx = session.context_layers.short_term_context
        assert ctx is not None
        assert isinstance(ctx, ShortTermTurnContext)
        assert ctx.turn_number == 5  # Most recent turn
        assert ctx.guard_outcome == "accepted"
        assert "escalation_5" in ctx.detected_triggers

        # ===== W2.3.2: SessionHistory =====
        hist = session.context_layers.session_history
        assert hist is not None
        assert isinstance(hist, SessionHistory)
        assert hist.size == 5
        assert hist.is_full is False  # max_size=100, only 5 entries
        assert hist.entries[0].turn_number == 1
        assert hist.entries[1].turn_number == 2
        assert hist.entries[2].turn_number == 3
        assert hist.entries[3].turn_number == 4
        assert hist.entries[4].turn_number == 5

        # ===== W2.3.3: ProgressionSummary =====
        prog = session.context_layers.progression_summary
        assert prog is not None
        assert isinstance(prog, ProgressionSummary)
        assert prog.total_turns_in_source == 5  # All 5 turns
        assert prog.first_turn_covered == 1
        assert prog.last_turn_covered == 5
        assert prog.current_scene_id == session.current_scene_id
        assert prog.session_phase == "early"  # 5 turns < 15

        # ===== W2.3.4: RelationshipAxisContext =====
        rel = session.context_layers.relationship_axis_context
        assert rel is not None
        assert isinstance(rel, RelationshipAxisContext)
        assert rel.derived_from_turn == 5  # Derived from turn 5
        assert len(rel.salient_axes) <= 10  # Bounded to 10

        # ===== W2.3.5: LoreDirectionContext =====
        lore = session.context_layers.lore_direction_context
        assert lore is not None
        assert isinstance(lore, LoreDirectionContext)
        assert lore.module_id == "god_of_carnage"
        assert lore.derived_from_turn >= 1
        assert len(lore.selected_units) <= 15  # Bounded to 15

        # ===== Distinctness: All Five Layers Are Different Types =====
        assert type(ctx) == ShortTermTurnContext
        assert type(hist) == SessionHistory
        assert type(prog) == ProgressionSummary
        assert type(rel) == RelationshipAxisContext
        assert type(lore) == LoreDirectionContext

        # Verify they are not the same object
        assert ctx is not hist
        assert prog is not rel
        assert rel is not lore
        assert ctx is not prog

    @pytest.mark.asyncio
    async def test_w23_layer_state_changes_are_detectable_across_turns(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Layer state is not static—values measurably change between turn 1 and turn 5.

        This test proves the layers are actually being updated. It snapshots state after
        turn 1, continues to turn 5, and asserts values changed. Fails if wiring is removed.
        """
        session = god_of_carnage_module_with_state

        # Execute turns and snapshot after turn 1
        snap1_history_size = None
        snap1_prog_turns = None
        snap1_stc_turn = None
        snap1_rel_turn = None

        for turn_num in range(1, 6):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state", next_value=turn_num * 10
                    )
                ],
            )
            await execute_turn(session, turn_num, decision, god_of_carnage_module)

            # Snapshot after turn 1
            if turn_num == 1:
                snap1_history_size = session.context_layers.session_history.size
                snap1_prog_turns = session.context_layers.progression_summary.total_turns_in_source
                snap1_stc_turn = session.context_layers.short_term_context.turn_number
                snap1_rel_turn = session.context_layers.relationship_axis_context.derived_from_turn

        # ===== Verify Values Changed from Turn 1 to Turn 5 =====
        assert session.context_layers.session_history.size > snap1_history_size
        assert session.context_layers.session_history.size == 5  # Grew from 1 to 5

        assert session.context_layers.progression_summary.total_turns_in_source > snap1_prog_turns
        assert session.context_layers.progression_summary.total_turns_in_source == 5

        assert session.context_layers.short_term_context.turn_number > snap1_stc_turn
        assert session.context_layers.short_term_context.turn_number == 5

        assert session.context_layers.relationship_axis_context.derived_from_turn > snap1_rel_turn
        assert session.context_layers.relationship_axis_context.derived_from_turn == 5

    @pytest.mark.asyncio
    async def test_w23_history_trimming_leaves_derived_layers_coherent(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """FIFO history trimming in live session leaves all derived layers coherent.

        Pre-configures SessionHistory(max_size=3), runs 5 turns, and asserts:
        - History trims to 3 entries (turns 3-5, drops turns 1-2)
        - ProgressionSummary reflects the 3 remaining entries (total_turns==3)
        - All five layers still present and coherent
        - Boundedness maintained after trimming
        """
        session = god_of_carnage_module_with_state

        # Pre-configure small history size to force trimming
        session.context_layers.session_history = SessionHistory(max_size=3)

        # Execute 5 turns—history will trim turns 1-2
        for turn_num in range(1, 6):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state", next_value=turn_num * 10
                    )
                ],
            )
            await execute_turn(session, turn_num, decision, god_of_carnage_module)

        # ===== Verify History Trimmed Correctly (FIFO) =====
        hist = session.context_layers.session_history
        assert hist.size == 3, "History should be trimmed to max_size=3"
        assert hist.is_full is True
        assert hist.entries[0].turn_number == 3, "Oldest retained turn should be 3 (turns 1-2 trimmed)"
        assert hist.entries[1].turn_number == 4
        assert hist.entries[2].turn_number == 5, "Newest turn should be 5"

        # ===== Verify ProgressionSummary Reflects Trimmed History =====
        prog = session.context_layers.progression_summary
        assert prog.total_turns_in_source == 3, "ProgressionSummary should reflect 3 entries"
        assert prog.first_turn_covered == 3, "First turn in summary should be 3 (1-2 trimmed)"
        assert prog.last_turn_covered == 5

        # ===== Verify All Five Layers Still Present =====
        assert session.context_layers.short_term_context is not None
        assert session.context_layers.session_history is not None
        assert session.context_layers.progression_summary is not None
        assert session.context_layers.relationship_axis_context is not None
        assert session.context_layers.lore_direction_context is not None

        # ===== Verify Boundedness Maintained After Trimming =====
        rel = session.context_layers.relationship_axis_context
        assert len(rel.salient_axes) <= 10, "RelationshipAxisContext should remain bounded to 10"

        lore = session.context_layers.lore_direction_context
        assert len(lore.selected_units) <= 15, "LoreDirectionContext should remain bounded to 15"

        # ===== Verify W2.3.1 Is Still Current (Most Recent Turn) =====
        ctx = session.context_layers.short_term_context
        assert ctx.turn_number == 5, "Short-term context should be from most recent turn (5)"
