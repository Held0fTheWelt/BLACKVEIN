"""Tests for W2.3.2 session-history layer.

Tests verify that:
- session history accumulates across multiple turns
- ordering is correct and deterministic
- history remains bounded when window limit is exceeded
- short-term context and session history remain distinct
- history does not degrade into raw event log replay
- no regressions in existing runtime tests
"""

from __future__ import annotations

import pytest

from app.runtime.session_history import HistoryEntry, SessionHistory
from app.runtime.short_term_context import ShortTermTurnContext, build_short_term_context
from app.runtime.turn_executor import MockDecision, ProposedStateDelta, execute_turn
from app.runtime.runtime_models import GuardOutcome


class TestHistoryEntry:
    """Unit tests for HistoryEntry creation."""

    def test_create_from_short_term_context(self):
        """HistoryEntry derives cleanly from ShortTermTurnContext."""
        context = ShortTermTurnContext(
            turn_number=5,
            scene_id="act_2_scene_3",
            detected_triggers=["trigger_alpha", "trigger_beta"],
            accepted_delta_targets=["characters.veronique.emotion"],
            rejected_delta_targets=[],
            guard_outcome="accepted",
            scene_changed=True,
            prior_scene_id="act_1_scene_5",
            ending_reached=False,
            ending_id=None,
            conflict_pressure=42,
        )

        entry = HistoryEntry.from_short_term_context(context)

        assert entry.turn_number == 5
        assert entry.scene_id == "act_2_scene_3"
        assert entry.guard_outcome == "accepted"
        assert entry.detected_triggers == ["trigger_alpha", "trigger_beta"]
        assert entry.scene_changed is True
        assert entry.prior_scene_id == "act_1_scene_5"
        assert entry.ending_reached is False

    def test_history_entry_excludes_conflict_pressure(self):
        """HistoryEntry does not duplicate conflict_pressure (short-term context concern)."""
        context = ShortTermTurnContext(
            turn_number=1,
            scene_id="start",
            guard_outcome="accepted",
            conflict_pressure=100,
        )

        entry = HistoryEntry.from_short_term_context(context)

        # Entry is lighter than context - no conflict_pressure field
        assert not hasattr(entry, "conflict_pressure")

    def test_history_entry_excludes_delta_targets(self):
        """HistoryEntry does not include delta target paths (not needed for history)."""
        context = ShortTermTurnContext(
            turn_number=1,
            scene_id="start",
            accepted_delta_targets=["characters.a.state", "characters.b.state"],
            guard_outcome="accepted",
        )

        entry = HistoryEntry.from_short_term_context(context)

        # Entry does not carry delta details
        assert not hasattr(entry, "accepted_delta_targets")
        assert not hasattr(entry, "rejected_delta_targets")


class TestSessionHistoryAccumulation:
    """Tests for history accumulation across turns."""

    def test_session_history_empty_at_start(self):
        """New SessionHistory starts with no entries."""
        history = SessionHistory()
        assert history.size == 0
        assert history.last_entry is None
        assert history.entries == []

    def test_add_single_entry(self):
        """Can add a single entry to history."""
        history = SessionHistory()
        entry = HistoryEntry(
            turn_number=1,
            scene_id="start",
            guard_outcome="accepted",
        )

        history.add_entry(entry)

        assert history.size == 1
        assert history.last_entry == entry
        assert history.entries[0].turn_number == 1

    def test_accumulate_multiple_entries(self):
        """History accumulates entries in order."""
        history = SessionHistory()

        for turn in range(1, 6):
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"scene_{turn}",
                guard_outcome="accepted",
            )
            history.add_entry(entry)

        assert history.size == 5
        assert history.entries[0].turn_number == 1
        assert history.entries[-1].turn_number == 5

    def test_add_from_short_term_context(self):
        """Can add directly from ShortTermTurnContext."""
        history = SessionHistory()

        context = ShortTermTurnContext(
            turn_number=3,
            scene_id="middle",
            guard_outcome="partially_accepted",
            detected_triggers=["trigger_x"],
        )

        history.add_from_short_term_context(context)

        assert history.size == 1
        assert history.last_entry.turn_number == 3
        assert history.last_entry.detected_triggers == ["trigger_x"]


class TestSessionHistoryBounds:
    """Tests for bounded retention behavior."""

    def test_default_max_size(self):
        """SessionHistory has default max_size of 100."""
        history = SessionHistory()
        assert history.max_size == 100

    def test_custom_max_size(self):
        """Can set custom max_size."""
        history = SessionHistory(max_size=10)
        assert history.max_size == 10

    def test_trimming_oldest_entries(self):
        """Oldest entries are removed when max_size is exceeded."""
        history = SessionHistory(max_size=5)

        for turn in range(1, 12):
            entry = HistoryEntry(turn_number=turn, scene_id=f"scene_{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        # Should keep only the 5 most recent
        assert history.size == 5
        assert history.entries[0].turn_number == 7  # Oldest kept
        assert history.entries[-1].turn_number == 11  # Newest

    def test_trimming_is_deterministic(self):
        """Trimming follows consistent FIFO order."""
        history1 = SessionHistory(max_size=3)
        history2 = SessionHistory(max_size=3)

        for turn in range(1, 6):
            entry = HistoryEntry(turn_number=turn, scene_id=f"scene_{turn}", guard_outcome="accepted")
            history1.add_entry(entry)
            history2.add_entry(entry)

        # Both should have identical entries
        assert len(history1.entries) == len(history2.entries)
        assert [e.turn_number for e in history1.entries] == [e.turn_number for e in history2.entries]
        assert [e.turn_number for e in history1.entries] == [3, 4, 5]

    def test_is_full_property(self):
        """is_full reflects whether at or over capacity."""
        history = SessionHistory(max_size=3)

        assert not history.is_full

        for turn in range(1, 4):
            history.add_entry(HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted"))
        assert history.is_full

        history.add_entry(HistoryEntry(turn_number=4, scene_id="s4", guard_outcome="accepted"))
        assert history.is_full  # Still at capacity


class TestSessionHistoryOrdering:
    """Tests for ordering and progression markers."""

    def test_ordering_is_oldest_to_newest(self):
        """Entries are ordered oldest to newest."""
        history = SessionHistory()

        for turn in [5, 2, 8, 1, 9]:
            entry = HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        # Retrieve in order added, not turn number order
        assert [e.turn_number for e in history.entries] == [5, 2, 8, 1, 9]

    def test_get_recent_entries(self):
        """get_recent_entries returns N newest entries."""
        history = SessionHistory()

        for turn in range(1, 11):
            entry = HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        recent = history.get_recent_entries(3)

        assert len(recent) == 3
        assert [e.turn_number for e in recent] == [8, 9, 10]

    def test_get_recent_entries_respects_size(self):
        """get_recent_entries doesn't return more than available."""
        history = SessionHistory()

        for turn in range(1, 4):
            entry = HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        recent = history.get_recent_entries(10)

        assert len(recent) == 3
        assert [e.turn_number for e in recent] == [1, 2, 3]

    def test_get_entries_since_turn(self):
        """get_entries_since_turn returns from specified turn onwards."""
        history = SessionHistory()

        for turn in range(1, 11):
            entry = HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        since = history.get_entries_since_turn(7)

        assert len(since) == 4
        assert [e.turn_number for e in since] == [7, 8, 9, 10]

    def test_get_scene_transitions(self):
        """get_scene_transitions returns only entries with scene_changed."""
        history = SessionHistory()

        turns_with_transition = {3, 7, 9}

        for turn in range(1, 11):
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"s{turn}",
                guard_outcome="accepted",
                scene_changed=(turn in turns_with_transition),
            )
            history.add_entry(entry)

        transitions = history.get_scene_transitions()

        assert len(transitions) == 3
        assert [e.turn_number for e in transitions] == [3, 7, 9]

    def test_get_endings_reached(self):
        """get_endings_reached returns only entries with ending_reached."""
        history = SessionHistory()

        endings = {5, 8}

        for turn in range(1, 11):
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"s{turn}",
                guard_outcome="accepted",
                ending_reached=(turn in endings),
                ending_id=(f"ending_{turn}" if turn in endings else None),
            )
            history.add_entry(entry)

        reached = history.get_endings_reached()

        assert len(reached) == 2
        assert [e.turn_number for e in reached] == [5, 8]
        assert [e.ending_id for e in reached] == ["ending_5", "ending_8"]


class TestSessionHistoryDistinctness:
    """Tests ensuring history is distinct from context and logs."""

    def test_history_entry_is_lighter_than_short_term_context(self):
        """HistoryEntry has fewer fields than ShortTermTurnContext."""
        context = ShortTermTurnContext(
            turn_number=1,
            scene_id="s1",
            detected_triggers=["t1"],
            accepted_delta_targets=["d1"],
            rejected_delta_targets=["d2"],
            guard_outcome="accepted",
            scene_changed=False,
            conflict_pressure=50,
        )

        entry = HistoryEntry.from_short_term_context(context)

        # Context has fields history doesn't
        context_field_count = len(type(context).model_fields)
        entry_field_count = len(type(entry).model_fields)

        # Entry is notably lighter
        assert entry_field_count < context_field_count

    def test_history_not_full_event_log(self):
        """HistoryEntry doesn't replicate full event log details."""
        # HistoryEntry doesn't have: created_at, validation_outcome, full events list
        entry = HistoryEntry(turn_number=1, scene_id="s", guard_outcome="accepted")

        assert not hasattr(entry, "events")
        assert not hasattr(entry, "validation_errors")
        assert not hasattr(entry, "raw_output")

    def test_session_history_is_session_level_not_turn_level(self):
        """SessionHistory maintains multiple turns, not single-turn scope."""
        history = SessionHistory()

        for turn in range(1, 6):
            entry = HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            history.add_entry(entry)

        # History spans multiple turns
        assert history.size == 5
        assert history.entries[0].turn_number != history.entries[-1].turn_number

    def test_session_history_is_observable_not_accumulated_log(self):
        """SessionHistory tracks progression without raw log replay."""
        history = SessionHistory()

        # Add 100 turns
        for turn in range(1, 101):
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"s{turn % 10}",
                guard_outcome=("accepted" if turn % 2 == 0 else "rejected"),
            )
            history.add_entry(entry)

        # History size bounded, not explosive
        assert history.size == 100
        assert history.max_size == 100


class TestSessionHistoryManagement:
    """Tests for history inspection and manipulation."""

    def test_clear_empties_history(self):
        """clear() removes all entries."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted"))

        assert history.size == 5
        history.clear()
        assert history.size == 0
        assert history.last_entry is None

    def test_empty_history_safe_queries(self):
        """Queries on empty history return safely."""
        history = SessionHistory()

        assert history.last_entry is None
        assert history.get_recent_entries(5) == []
        assert history.get_entries_since_turn(1) == []
        assert history.get_scene_transitions() == []
        assert history.get_endings_reached() == []


class TestSessionHistoryIntegration:
    """Integration tests with real turn execution."""

    @pytest.mark.asyncio
    async def test_history_from_real_turns(self, god_of_carnage_module_with_state, god_of_carnage_module):
        """Build session history from real executed turns."""
        session = god_of_carnage_module_with_state
        history = SessionHistory(max_size=50)

        # Execute a few turns
        for turn_num in range(1, 4):
            decision = MockDecision(
                detected_triggers=[],
                proposed_deltas=[
                    ProposedStateDelta(target="characters.veronique.emotional_state", next_value=turn_num * 10)
                ],
                narrative_text=f"Turn {turn_num}",
                rationale="test",
            )

            result = await execute_turn(session, turn_num, decision, god_of_carnage_module)
            context = build_short_term_context(result, prior_scene_id=session.current_scene_id)
            history.add_from_short_term_context(context)

        # History captures the progression
        assert history.size == 3
        assert history.entries[0].turn_number == 1
        assert history.entries[-1].turn_number == 3
        assert all(e.guard_outcome in ["accepted", "partially_accepted", "rejected", "structurally_invalid"] for e in history.entries)

    def test_history_with_scene_transitions(self):
        """History correctly tracks scene transition markers."""
        history = SessionHistory()

        # Build a sequence with transitions
        for turn in range(1, 6):
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"scene_{turn // 2}",  # Changes every 2 turns
                guard_outcome="accepted",
                scene_changed=(turn > 1 and (turn - 1) % 2 == 0),  # Transitions on turns 3, 5
                prior_scene_id=f"scene_{(turn - 1) // 2}" if turn > 1 and (turn - 1) % 2 == 0 else None,
            )
            history.add_entry(entry)

        transitions = history.get_scene_transitions()
        assert len(transitions) == 2
        assert [e.turn_number for e in transitions] == [3, 5]

    def test_history_preserves_trigger_sequence(self):
        """History preserves trigger firing sequence for context."""
        history = SessionHistory()

        triggers_per_turn = {
            1: ["alpha", "beta"],
            2: ["gamma"],
            3: [],
            4: ["alpha", "delta"],
        }

        for turn, triggers in triggers_per_turn.items():
            entry = HistoryEntry(
                turn_number=turn,
                scene_id=f"s{turn}",
                guard_outcome="accepted",
                detected_triggers=triggers,
            )
            history.add_entry(entry)

        # Can reconstruct trigger sequence from history
        sequence = [(e.turn_number, e.detected_triggers) for e in history.entries]
        assert sequence == [
            (1, ["alpha", "beta"]),
            (2, ["gamma"]),
            (3, []),
            (4, ["alpha", "delta"]),
        ]
