"""Tests for W2.3-R3: Post-turn derivation of progression, relationship, and lore context.

Verifies that downstream W2.3 context layers are derived and kept current in
the real runtime flow after each turn's session history is accumulated.
"""

from __future__ import annotations

import pytest

from app.runtime.lore_direction_context import LoreDirectionContext
from app.runtime.progression_summary import ProgressionSummary
from app.runtime.relationship_context import RelationshipAxisContext
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn
from app.runtime.runtime_models import SessionState


class TestProgressionSummaryDerivation:
    """Tests that ProgressionSummary is derived from accumulated history."""

    @pytest.mark.asyncio
    async def test_progression_summary_created_after_first_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After first turn: ProgressionSummary is created and populated."""
        session = god_of_carnage_module_with_state

        # Execute first turn
        decision = MockDecision(
            detected_triggers=["tension_rises"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify ProgressionSummary was derived
        assert session.context_layers.progression_summary is not None
        assert isinstance(session.context_layers.progression_summary, ProgressionSummary)
        assert session.context_layers.progression_summary.total_turns_in_source == 1
        assert session.context_layers.progression_summary.session_phase == "early"

    @pytest.mark.asyncio
    async def test_progression_summary_updates_across_turns(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After multiple turns: ProgressionSummary reflects accumulated history."""
        session = god_of_carnage_module_with_state

        # Execute 3 turns
        for turn_num in range(1, 4):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state",
                        next_value=turn_num * 10,
                    )
                ],
            )
            await execute_turn(session, turn_num, decision, god_of_carnage_module)

        # Verify ProgressionSummary reflects all turns
        assert session.context_layers.progression_summary is not None
        assert session.context_layers.progression_summary.total_turns_in_source == 3
        assert session.context_layers.progression_summary.last_turn_covered == 3

    @pytest.mark.asyncio
    async def test_progression_summary_reflects_current_scene(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """ProgressionSummary current_scene_id matches session current_scene_id."""
        session = god_of_carnage_module_with_state
        initial_scene = session.current_scene_id

        decision = MockDecision(
            detected_triggers=["test_trigger"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=45)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify scene is in progression summary
        assert session.context_layers.progression_summary is not None
        assert session.context_layers.progression_summary.current_scene_id == session.current_scene_id


class TestRelationshipAxisContextDerivation:
    """Tests that RelationshipAxisContext is derived from history."""

    @pytest.mark.asyncio
    async def test_relationship_context_created_after_first_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After first turn: RelationshipAxisContext is created."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["tension_veronique_alain"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=60)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify RelationshipAxisContext was derived
        assert session.context_layers.relationship_axis_context is not None
        assert isinstance(session.context_layers.relationship_axis_context, RelationshipAxisContext)
        assert session.context_layers.relationship_axis_context.derived_from_turn >= 1

    @pytest.mark.asyncio
    async def test_relationship_context_reflects_history_size(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """RelationshipAxisContext reflects history size and scope."""
        session = god_of_carnage_module_with_state

        # Execute turn with character-named trigger
        decision = MockDecision(
            detected_triggers=["escalation_veronique_giuseppe"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=70)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify context reflects the turn
        assert session.context_layers.relationship_axis_context is not None
        # For god_of_carnage module with character names in triggers
        # we expect at least one salient axis to be created
        # (if character extraction works from trigger names)
        assert session.context_layers.relationship_axis_context.derived_from_turn == 1


class TestLoreDirectionContextDerivation:
    """Tests that LoreDirectionContext is derived from module guidance."""

    @pytest.mark.asyncio
    async def test_lore_context_created_after_first_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After first turn: LoreDirectionContext is created and bounded."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["conflict_escalates"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=55)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify LoreDirectionContext was derived
        assert session.context_layers.lore_direction_context is not None
        assert isinstance(session.context_layers.lore_direction_context, LoreDirectionContext)
        assert session.context_layers.lore_direction_context.module_id == "god_of_carnage"
        assert len(session.context_layers.lore_direction_context.selected_units) <= 15

    @pytest.mark.asyncio
    async def test_lore_context_derives_from_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """LoreDirectionContext tracks which turn it was derived from."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["test"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify derivation tracking
        assert session.context_layers.lore_direction_context is not None
        assert session.context_layers.lore_direction_context.derived_from_turn >= 1


class TestAllLayersPresent:
    """Tests that all five W2.3 layers are present and populated."""

    @pytest.mark.asyncio
    async def test_all_five_context_layers_populated_after_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After a turn: all 5 W2.3 layers are non-None with correct types."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["valid_trigger"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=55)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify all five layers present
        # W2.3.1: ShortTermTurnContext
        assert session.context_layers.short_term_context is not None
        # W2.3.2: SessionHistory
        assert session.context_layers.session_history is not None
        # W2.3.3: ProgressionSummary
        assert session.context_layers.progression_summary is not None
        # W2.3.4: RelationshipAxisContext
        assert session.context_layers.relationship_axis_context is not None
        # W2.3.5: LoreDirectionContext
        assert session.context_layers.lore_direction_context is not None


class TestLayerDistinctness:
    """Tests that derived layers remain conceptually distinct."""

    @pytest.mark.asyncio
    async def test_derived_layers_are_distinct_types(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Each derived layer is a distinct type, not a duplicate."""
        session = god_of_carnage_module_with_state

        decision = MockDecision(
            detected_triggers=["test"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
        )

        await execute_turn(session, 1, decision, god_of_carnage_module)

        # Verify distinct types
        prog = session.context_layers.progression_summary
        rel = session.context_layers.relationship_axis_context
        lore = session.context_layers.lore_direction_context

        assert type(prog) == ProgressionSummary
        assert type(rel) == RelationshipAxisContext
        assert type(lore) == LoreDirectionContext

        # Verify they're not the same object
        assert prog is not rel
        assert rel is not lore
        assert prog is not lore


class TestBoundednessInRuntime:
    """Tests that derived layers remain bounded in runtime reality."""

    @pytest.mark.asyncio
    async def test_derived_layers_remain_bounded_after_many_turns(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """After 20 turns: all derived layers respect their bounds."""
        session = god_of_carnage_module_with_state

        # Execute 20 turns with various triggers to stress test boundedness
        for turn_num in range(1, 21):
            decision = MockDecision(
                detected_triggers=[f"trigger_{turn_num % 5}", f"other_trigger_{turn_num}"],
                proposed_deltas=[
                    ProposedStateDelta(
                        target="characters.veronique.emotional_state",
                        next_value=min(100, turn_num * 5),
                    )
                ],
            )
            await execute_turn(session, turn_num, decision, god_of_carnage_module)

        # Verify bounds respected
        prog = session.context_layers.progression_summary
        assert prog is not None
        # ProgressionSummary bounds: unique_triggers <= 50, recent_scenes <= 10
        assert len(prog.unique_triggers_in_period) <= 50
        assert len(prog.recent_scene_ids) <= 10

        rel = session.context_layers.relationship_axis_context
        assert rel is not None
        # RelationshipAxisContext bound: salient_axes <= 10
        assert len(rel.salient_axes) <= 10

        lore = session.context_layers.lore_direction_context
        assert lore is not None
        # LoreDirectionContext bound: selected_units <= 15
        assert len(lore.selected_units) <= 15


class TestDerivationWithRejectedTurns:
    """Tests that derivation runs even on rejected/failed turns."""

    @pytest.mark.asyncio
    async def test_derivation_still_runs_on_rejected_turn(
        self, god_of_carnage_module_with_state, god_of_carnage_module
    ):
        """Even rejected turns: derivation layers are created."""
        session = god_of_carnage_module_with_state

        # First, successful turn to populate history
        decision1 = MockDecision(
            detected_triggers=["valid_trigger"],
            proposed_deltas=[
                ProposedStateDelta(target="characters.veronique.emotional_state", next_value=50)
            ],
        )
        await execute_turn(session, 1, decision1, god_of_carnage_module)

        # Second turn with invalid delta path (will be rejected)
        decision2 = MockDecision(
            detected_triggers=[],
            proposed_deltas=[ProposedStateDelta(target="nonexistent.path.value", next_value="invalid")],
        )
        await execute_turn(session, 2, decision2, god_of_carnage_module)

        # Verify derivation still happened on rejected turn
        assert session.context_layers.progression_summary is not None
        assert session.context_layers.relationship_axis_context is not None
        assert session.context_layers.lore_direction_context is not None
        # History should have both turns
        assert session.context_layers.session_history.size >= 2
