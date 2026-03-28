"""Tests for W2.3.3 progression summary layer.

Tests verify that:
- progression summary derives correctly from SessionHistory
- summary remains bounded as history grows
- summary captures scene progression meaningfully
- summary captures trigger/progression markers meaningfully
- summary distinguishes itself from raw history replay
- ending state is reflected correctly
- no regressions in existing runtime tests
"""

from __future__ import annotations

import pytest

from app.runtime.progression_summary import ProgressionSummary, derive_progression_summary
from app.runtime.session_history import HistoryEntry, SessionHistory


class TestProgressionSummaryDerivation:
    """Unit tests for deriving progression summary from history."""

    def test_derive_from_empty_history(self):
        """Empty history produces minimal summary."""
        history = SessionHistory()
        summary = derive_progression_summary(history)

        assert summary.first_turn_covered == 0
        assert summary.last_turn_covered == 0
        assert summary.total_turns_in_source == 0
        assert summary.current_scene_id == ""
        assert summary.session_phase == "early"
        assert summary.ending_reached is False

    def test_derive_from_single_entry(self):
        """Single history entry produces valid summary."""
        history = SessionHistory()
        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="start",
                guard_outcome="accepted",
                detected_triggers=["alpha"],
            )
        )

        summary = derive_progression_summary(history)

        assert summary.first_turn_covered == 1
        assert summary.last_turn_covered == 1
        assert summary.total_turns_in_source == 1
        assert summary.current_scene_id == "start"
        assert "alpha" in summary.unique_triggers_in_period
        assert summary.guard_outcome_distribution["accepted"] == 1

    def test_derive_turn_span(self):
        """Summary correctly reflects turn span."""
        history = SessionHistory()

        for turn in range(5, 11):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id=f"scene_{turn}", guard_outcome="accepted")
            )

        summary = derive_progression_summary(history)

        assert summary.first_turn_covered == 5
        assert summary.last_turn_covered == 10
        assert summary.total_turns_in_source == 6


class TestProgressionSummarySceneTracking:
    """Tests for scene progression capture."""

    def test_recent_scene_ids_captures_movement(self):
        """Recent scenes show progression pattern."""
        history = SessionHistory()

        scene_sequence = ["start", "middle", "middle", "ending", "ending", "epilogue"]
        for turn, scene in enumerate(scene_sequence, start=1):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id=scene, guard_outcome="accepted")
            )

        summary = derive_progression_summary(history)

        # Recent unique scenes in order (deduped)
        assert summary.recent_scene_ids == ["start", "middle", "ending", "epilogue"]

    def test_scene_transition_count(self):
        """Transition count reflects scene changes."""
        history = SessionHistory()

        for turn in range(1, 8):
            # Transition on turns 2, 4, 6
            scene_id = ["a", "b", "b", "c", "c", "d", "d"][turn - 1]
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id=scene_id,
                    guard_outcome="accepted",
                    scene_changed=(turn in [2, 4, 6]),
                )
            )

        summary = derive_progression_summary(history)

        assert summary.scene_transition_count == 3

    def test_current_scene_is_most_recent(self):
        """Current scene always reflects last entry."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id=f"scene_{turn}", guard_outcome="accepted")
            )

        summary = derive_progression_summary(history)

        assert summary.current_scene_id == "scene_5"

    def test_recent_scenes_bounded_to_10(self):
        """Recent scenes list stays at most 10."""
        history = SessionHistory()

        # Create 20 unique scenes
        for turn in range(1, 21):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id=f"scene_{turn}", guard_outcome="accepted")
            )

        summary = derive_progression_summary(history)

        # Should only keep last 10 unique
        assert len(summary.recent_scene_ids) == 10
        assert summary.recent_scene_ids[0] == "scene_11"  # Oldest of recent
        assert summary.recent_scene_ids[-1] == "scene_20"  # Newest


class TestProgressionSummaryTriggerTracking:
    """Tests for trigger activity aggregation."""

    def test_unique_triggers_collected(self):
        """All unique triggers are included."""
        history = SessionHistory()

        trigger_sets = [
            ["alpha", "beta"],
            ["alpha", "gamma"],
            ["delta"],
            ["beta", "epsilon"],
        ]

        for turn, triggers in enumerate(trigger_sets, start=1):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="test",
                    guard_outcome="accepted",
                    detected_triggers=triggers,
                )
            )

        summary = derive_progression_summary(history)

        expected = {"alpha", "beta", "gamma", "delta", "epsilon"}
        assert set(summary.unique_triggers_in_period) == expected

    def test_trigger_frequency_ranking(self):
        """Triggers ranked by frequency."""
        history = SessionHistory()

        # alpha: 3 times, beta: 2 times, gamma: 1 time
        trigger_sets = [
            ["alpha", "beta"],
            ["alpha", "gamma"],
            ["alpha", "beta"],
        ]

        for turn, triggers in enumerate(trigger_sets, start=1):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="test",
                    guard_outcome="accepted",
                    detected_triggers=triggers,
                )
            )

        summary = derive_progression_summary(history)

        # Should rank by frequency
        assert summary.trigger_frequency["alpha"] == 3
        assert summary.trigger_frequency["beta"] == 2
        assert summary.trigger_frequency.get("gamma", 0) == 1

    def test_top_triggers_bounded_to_10(self):
        """Top triggers list bounded at 10 items."""
        history = SessionHistory()

        # Create 20 unique triggers with varying frequency
        for turn in range(1, 21):
            trigger = f"trigger_{turn % 20}"
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="test",
                    guard_outcome="accepted",
                    detected_triggers=[trigger],
                )
            )

        summary = derive_progression_summary(history)

        # Top 10 by frequency
        assert len(summary.trigger_frequency) <= 10

    def test_all_unique_triggers_bounded_to_50(self):
        """All unique triggers list bounded at 50."""
        history = SessionHistory()

        # Create 60 unique triggers
        for turn in range(1, 61):
            trigger = f"trigger_{turn}"
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="test",
                    guard_outcome="accepted",
                    detected_triggers=[trigger],
                )
            )

        summary = derive_progression_summary(history)

        # All unique but bounded to 50
        assert len(summary.unique_triggers_in_period) <= 50


class TestProgressionSummaryGuardPatterns:
    """Tests for guard outcome aggregation."""

    def test_outcome_distribution(self):
        """Guard outcomes are counted by type."""
        history = SessionHistory()

        outcomes = ["accepted", "accepted", "partially_accepted", "rejected", "accepted"]

        for turn, outcome in enumerate(outcomes, start=1):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id="test", guard_outcome=outcome)
            )

        summary = derive_progression_summary(history)

        assert summary.guard_outcome_distribution["accepted"] == 3
        assert summary.guard_outcome_distribution["partially_accepted"] == 1
        assert summary.guard_outcome_distribution["rejected"] == 1

    def test_recent_guard_outcomes(self):
        """Recent outcomes show latest pattern."""
        history = SessionHistory()

        outcomes = ["accepted", "rejected", "accepted", "rejected", "accepted", "accepted", "rejected"]

        for turn, outcome in enumerate(outcomes, start=1):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id="test", guard_outcome=outcome)
            )

        summary = derive_progression_summary(history)

        # Last 5 outcomes (all 7 outcomes, but capped at 5)
        assert summary.most_recent_guard_outcomes == ["accepted", "rejected", "accepted", "accepted", "rejected"]

    def test_recent_outcomes_bounded_to_5(self):
        """Recent outcomes list stays at most 5."""
        history = SessionHistory()

        for turn in range(1, 20):
            outcome = "accepted" if turn % 2 == 0 else "rejected"
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id="test", guard_outcome=outcome)
            )

        summary = derive_progression_summary(history)

        assert len(summary.most_recent_guard_outcomes) <= 5


class TestProgressionSummaryEndingState:
    """Tests for ending detection and tracking."""

    def test_no_ending_in_normal_session(self):
        """Normal session has no ending."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="scene",
                    guard_outcome="accepted",
                    ending_reached=False,
                )
            )

        summary = derive_progression_summary(history)

        assert summary.ending_reached is False
        assert summary.ending_id is None

    def test_ending_detected_when_present(self):
        """Ending is detected and recorded."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="scene",
                    guard_outcome="accepted",
                    ending_reached=(turn == 5),
                    ending_id="ending_good" if turn == 5 else None,
                )
            )

        summary = derive_progression_summary(history)

        assert summary.ending_reached is True
        assert summary.ending_id == "ending_good"

    def test_last_ending_wins(self):
        """If multiple endings, last one is recorded."""
        history = SessionHistory()

        endings = [
            (3, "ending_a"),
            (5, "ending_b"),
            (7, "ending_c"),
        ]

        for turn in range(1, 10):
            ending_reached = any(turn == e[0] for e in endings)
            ending_id = next((e[1] for e in endings if turn == e[0]), None)

            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="scene",
                    guard_outcome="accepted",
                    ending_reached=ending_reached,
                    ending_id=ending_id,
                )
            )

        summary = derive_progression_summary(history)

        assert summary.ending_id == "ending_c"


class TestProgressionSummarySessionPhase:
    """Tests for session phase classification."""

    def test_early_phase_for_short_sessions(self):
        """Sessions under 15 turns classified as early."""
        history = SessionHistory()

        for turn in range(1, 10):
            history.add_entry(HistoryEntry(turn_number=turn, scene_id="scene", guard_outcome="accepted"))

        summary = derive_progression_summary(history)

        assert summary.session_phase == "early"

    def test_middle_phase_for_moderate_sessions(self):
        """Sessions 15-50 turns classified as middle."""
        history = SessionHistory()

        for turn in range(1, 35):
            history.add_entry(HistoryEntry(turn_number=turn, scene_id="scene", guard_outcome="accepted"))

        summary = derive_progression_summary(history)

        assert summary.session_phase == "middle"

    def test_late_phase_for_long_sessions(self):
        """Sessions over 50 turns classified as late."""
        history = SessionHistory()

        for turn in range(1, 65):
            history.add_entry(HistoryEntry(turn_number=turn, scene_id="scene", guard_outcome="accepted"))

        summary = derive_progression_summary(history)

        assert summary.session_phase == "late"

    def test_ended_phase_overrides_other_phases(self):
        """Ending forces session_phase to 'ended' regardless of turn count."""
        history = SessionHistory()

        for turn in range(1, 8):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="scene",
                    guard_outcome="accepted",
                    ending_reached=(turn == 5),
                    ending_id="ending" if turn == 5 else None,
                )
            )

        summary = derive_progression_summary(history)

        assert summary.session_phase == "ended"


class TestProgressionSummaryDistinctness:
    """Tests ensuring summary is distinct from history/logs."""

    def test_summary_much_smaller_than_history(self):
        """Summary is significantly more compact than history."""
        history = SessionHistory(max_size=100)

        for turn in range(1, 101):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id=f"scene_{turn % 10}",
                    guard_outcome=("accepted" if turn % 2 == 0 else "rejected"),
                    detected_triggers=[f"trigger_{turn % 5}"],
                )
            )

        summary = derive_progression_summary(history)

        # History has 100 entries, summary has bounded fields
        assert len(history.entries) == 100
        # Summary compresses to much smaller footprint
        assert len(summary.recent_scene_ids) <= 10
        assert len(summary.trigger_frequency) <= 10
        assert len(summary.most_recent_guard_outcomes) <= 5

    def test_summary_not_raw_log_replay(self):
        """Summary doesn't replay full turn-by-turn detail."""
        history = SessionHistory()

        for turn in range(1, 20):
            history.add_entry(
                HistoryEntry(turn_number=turn, scene_id=f"s{turn}", guard_outcome="accepted")
            )

        summary = derive_progression_summary(history)

        # Summary has aggregated fields, not per-turn replay
        assert not hasattr(summary, "all_scenes")
        assert not hasattr(summary, "all_outcomes")
        assert len(summary.recent_scene_ids) < len(history.entries)

    def test_summary_is_deterministic(self):
        """Same history produces identical summary every time."""
        history = SessionHistory()

        for turn in range(1, 10):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id=f"scene_{turn}",
                    guard_outcome="accepted",
                    detected_triggers=["alpha", "beta"],
                )
            )

        summary1 = derive_progression_summary(history)
        summary2 = derive_progression_summary(history)

        assert summary1 == summary2


class TestProgressionSummaryBoundedness:
    """Tests verifying summary remains bounded as history grows."""

    def test_summary_bounded_with_large_history(self):
        """Summary fields remain bounded even with large SessionHistory."""
        history = SessionHistory(max_size=50)  # Bounded at 50

        # Add 100+ entries (only last 50 kept)
        for turn in range(1, 101):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id=f"scene_{turn % 20}",
                    guard_outcome=["accepted", "rejected", "partially_accepted"][turn % 3],
                    detected_triggers=[f"t{i}" for i in range(turn % 5)],
                )
            )

        summary = derive_progression_summary(history)

        # All summary fields remain bounded
        assert len(summary.recent_scene_ids) <= 10
        assert len(summary.trigger_frequency) <= 10
        assert len(summary.unique_triggers_in_period) <= 50
        assert len(summary.most_recent_guard_outcomes) <= 5
        assert summary.total_turns_in_source == 50  # Limited by history.max_size

    def test_summary_size_independent_of_history_growth(self):
        """Summary size doesn't grow with history size."""
        summaries = []

        for history_size in [10, 50, 100, 200]:
            history = SessionHistory(max_size=history_size)

            for turn in range(1, history_size + 1):
                history.add_entry(
                    HistoryEntry(
                        turn_number=turn,
                        scene_id=f"scene_{turn % 10}",
                        guard_outcome="accepted",
                        detected_triggers=[f"trigger_{turn % 20}"],
                    )
                )

            summary = derive_progression_summary(history)
            summaries.append(summary)

        # All summaries have bounded size regardless of history size
        for summary in summaries:
            assert len(summary.recent_scene_ids) <= 10
            assert len(summary.trigger_frequency) <= 10
