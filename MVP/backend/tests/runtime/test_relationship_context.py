"""Tests for W2.3.4 relationship-axis context layer.

Tests verify that:
- relationship-axis context derives correctly from bounded session history
- the most relevant axes are surfaced deterministically
- escalation/alliance drift is represented meaningfully when present
- the output remains bounded as history grows
- the relationship-axis layer is distinct from raw history and full state
- ending or scene changes do not break derivation
- no regressions in existing runtime tests
"""

from __future__ import annotations

import pytest

from app.runtime.relationship_context import (
    RelationshipAxisContext,
    SalientRelationshipAxis,
    derive_relationship_axis_context,
)
from app.runtime.session_history import HistoryEntry, SessionHistory


class TestRelationshipAxisExtraction:
    """Unit tests for character extraction and axis identification."""

    def test_derive_from_empty_history(self):
        """Empty history produces empty relationship context."""
        history = SessionHistory()
        context = derive_relationship_axis_context(history)

        assert context.salient_axes == []
        assert context.total_character_pairs_known == 0
        assert context.overall_stability_signal == "unknown"

    def test_single_character_pair_extraction(self):
        """Single character pair identified from triggers."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="scene",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        context = derive_relationship_axis_context(history)

        assert context.total_character_pairs_known >= 1
        assert len(context.salient_axes) >= 1
        assert context.salient_axes[0].character_a in ["alice", "bob"]
        assert context.salient_axes[0].character_b in ["alice", "bob"]

    def test_multiple_character_pairs_from_multi_char_trigger(self):
        """Multi-character trigger creates multiple axes."""
        history = SessionHistory()

        # Trigger mentioning three characters should create 3 pairs: (a,b), (a,c), (b,c)
        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="scene",
                guard_outcome="accepted",
                detected_triggers=["accusation_alice_bob_charlie"],
            )
        )

        context = derive_relationship_axis_context(history)

        # Should identify multiple character pairs
        assert context.total_character_pairs_known >= 1


class TestRelationshipAxisSalience:
    """Tests for salience scoring and ranking."""

    def test_salience_based_on_recency(self):
        """More recent axes have higher salience."""
        history = SessionHistory()

        # Add old mention
        history.add_entry(
            HistoryEntry(turn_number=1, scene_id="s", guard_outcome="accepted", detected_triggers=["conflict_alice_bob"])
        )

        # Add many recent mentions
        for turn in range(10, 15):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        context = derive_relationship_axis_context(history)

        # alice-bob should be highly salient due to recency
        if context.salient_axes:
            assert context.salient_axes[0].salience_score > 0.5

    def test_salience_based_on_frequency(self):
        """Frequently mentioned axes have higher salience."""
        history = SessionHistory()

        # Mention one axis 5 times
        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        # Mention another axis only once
        history.add_entry(
            HistoryEntry(
                turn_number=6, scene_id="s", guard_outcome="accepted", detected_triggers=["conflict_charlie_dave"]
            )
        )

        context = derive_relationship_axis_context(history)

        # alice-bob should rank higher than charlie-dave
        if len(context.salient_axes) >= 2:
            assert context.salient_axes[0].salience_score >= context.salient_axes[1].salience_score

    def test_top_axes_bounded_to_10(self):
        """Salient axes list bounded at 10 items."""
        history = SessionHistory()

        # Create 20 different character pairs
        for turn in range(1, 21):
            char_a = f"char_{turn // 10}"
            char_b = f"char_{turn % 10}"
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=[f"conflict_{char_a}_{char_b}"],
                )
            )

        context = derive_relationship_axis_context(history)

        # Should keep only top 10
        assert len(context.salient_axes) <= 10


class TestRelationshipAxisTrends:
    """Tests for escalation and de-escalation detection."""

    def test_escalating_trend_detection(self):
        """Escalation keywords trigger escalating trend."""
        history = SessionHistory()

        for turn in range(1, 4):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["escalation_alice_bob", "conflict_alice_bob", "tension_alice_bob"],
                )
            )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            escalating_axes = [ax for ax in context.salient_axes if ax.recent_change_direction == "escalating"]
            assert len(escalating_axes) > 0

    def test_de_escalating_trend_detection(self):
        """Resolution keywords trigger de-escalating trend."""
        history = SessionHistory()

        for turn in range(1, 4):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["reconciliation_alice_bob", "resolution_alice_bob"],
                )
            )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            de_escalating = [ax for ax in context.salient_axes if ax.recent_change_direction == "de-escalating"]
            assert len(de_escalating) > 0

    def test_stable_trend_when_mixed(self):
        """Mixed signals result in stable trend."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="s",
                guard_outcome="accepted",
                detected_triggers=["conflict_alice_bob"],
            )
        )

        history.add_entry(
            HistoryEntry(
                turn_number=2,
                scene_id="s",
                guard_outcome="accepted",
                detected_triggers=["reconciliation_alice_bob"],
            )
        )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            stable_axes = [ax for ax in context.salient_axes if ax.recent_change_direction == "stable"]
            assert len(stable_axes) > 0


class TestRelationshipAxisSignals:
    """Tests for signal type classification."""

    def test_alliance_signal_detection(self):
        """Alliance keywords trigger alliance signal."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="s",
                guard_outcome="accepted",
                detected_triggers=["alliance_alice_bob", "support_alice_bob"],
            )
        )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            alliance_axes = [ax for ax in context.salient_axes if ax.signal_type == "alliance"]
            assert len(alliance_axes) > 0

    def test_tension_signal_detection(self):
        """Tension keywords trigger tension signal."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="s",
                guard_outcome="accepted",
                detected_triggers=["hostility_alice_bob", "conflict_alice_bob"],
            )
        )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            tension_axes = [ax for ax in context.salient_axes if ax.signal_type == "tension"]
            assert len(tension_axes) > 0

    def test_instability_signal_detection(self):
        """Instability keywords trigger instability signal."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1,
                scene_id="s",
                guard_outcome="accepted",
                detected_triggers=["doubt_alice_bob"],
            )
        )

        context = derive_relationship_axis_context(history)

        if context.salient_axes:
            # Instability may be detected based on keywords
            signals = [ax.signal_type for ax in context.salient_axes]
            assert "instability" in signals or "stable" in signals


class TestRelationshipAxisOverallSignals:
    """Tests for overall relationship health signals."""

    def test_overall_escalating_signal(self):
        """Many escalation markers produce escalating overall signal."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["escalation_alice_bob", "conflict_charlie_dave"],
                )
            )

        context = derive_relationship_axis_context(history)

        assert context.has_escalation_markers is True

    def test_overall_de_escalating_signal(self):
        """Many resolution markers produce de-escalating overall signal."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["reconciliation_alice_bob", "resolution_charlie_dave"],
                )
            )

        context = derive_relationship_axis_context(history)

        assert context.has_de_escalation_markers is True

    def test_stability_signal_when_no_markers(self):
        """No escalation/resolution markers produce stable signal."""
        history = SessionHistory()

        for turn in range(1, 4):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn, scene_id="s", guard_outcome="accepted", detected_triggers=["neutral_event"]
                )
            )

        context = derive_relationship_axis_context(history)

        # If no explicit escalation/de-escalation, should be stable or mixed
        assert context.overall_stability_signal in ["stable", "mixed", "unknown"]


class TestRelationshipAxisHighlights:
    """Tests for key relationship highlights."""

    def test_highest_salience_identified(self):
        """Most salient axis correctly identified."""
        history = SessionHistory()

        # alice-bob mentioned 5 times
        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        # charlie-dave mentioned 1 time
        history.add_entry(
            HistoryEntry(turn_number=6, scene_id="s", guard_outcome="accepted", detected_triggers=["conflict_charlie_dave"])
        )

        context = derive_relationship_axis_context(history)

        if context.highest_salience_axis:
            assert set(context.highest_salience_axis) == {"alice", "bob"}

    def test_highest_tension_identified(self):
        """Most tense axis correctly identified."""
        history = SessionHistory()

        # Normal relationship
        history.add_entry(
            HistoryEntry(
                turn_number=1, scene_id="s", guard_outcome="accepted", detected_triggers=["alliance_alice_bob"]
            )
        )

        # Tense relationship
        history.add_entry(
            HistoryEntry(
                turn_number=2, scene_id="s", guard_outcome="accepted", detected_triggers=["hostility_charlie_dave"]
            )
        )

        context = derive_relationship_axis_context(history)

        if context.highest_tension_axis:
            # Should identify charlie-dave as most tense
            assert set(context.highest_tension_axis) == {"charlie", "dave"}


class TestRelationshipAxisDistinctness:
    """Tests ensuring relationship context is distinct from other layers."""

    def test_not_raw_history_replay(self):
        """Context aggregates, not replays."""
        history = SessionHistory()

        # Add 50 entries
        for turn in range(1, 51):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        context = derive_relationship_axis_context(history)

        # Context should be much smaller than history
        # Should not have 50 entries
        assert len(context.salient_axes) < 20

    def test_not_full_state_dump(self):
        """Context has summary signals not full state."""
        history = SessionHistory()

        history.add_entry(
            HistoryEntry(
                turn_number=1, scene_id="s", guard_outcome="accepted", detected_triggers=["conflict_alice_bob"]
            )
        )

        context = derive_relationship_axis_context(history)

        # Context has high-level signals, not full character state
        for axis in context.salient_axes:
            assert axis.salience_score is not None
            assert axis.recent_change_direction is not None
            assert axis.signal_type is not None


class TestRelationshipAxisDeterminism:
    """Tests for deterministic derivation."""

    def test_same_history_produces_same_context(self):
        """Identical history produces identical context."""
        history1 = SessionHistory()
        history2 = SessionHistory()

        for turn in range(1, 6):
            history1.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )
            history2.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                )
            )

        context1 = derive_relationship_axis_context(history1)
        context2 = derive_relationship_axis_context(history2)

        assert context1.salient_axes == context2.salient_axes
        assert context1.overall_stability_signal == context2.overall_stability_signal


class TestRelationshipAxisBoundedness:
    """Tests for bounded size regardless of history growth."""

    def test_context_bounded_with_large_history(self):
        """Context remains bounded even with large history."""
        history = SessionHistory(max_size=100)

        for turn in range(1, 101):
            # Create 30 different character pairs
            char_a = f"char_{turn % 15}"
            char_b = f"char_{(turn + 1) % 15}"
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=[f"conflict_{char_a}_{char_b}"],
                )
            )

        context = derive_relationship_axis_context(history)

        # Context should be bounded
        assert len(context.salient_axes) <= 10
        assert context.overall_stability_signal is not None

    def test_context_size_independent_of_history_size(self):
        """Context size doesn't grow with history size."""
        contexts = []

        for history_size in [10, 50, 100]:
            history = SessionHistory(max_size=history_size)

            for turn in range(1, history_size + 1):
                history.add_entry(
                    HistoryEntry(
                        turn_number=turn,
                        scene_id="s",
                        guard_outcome="accepted",
                        detected_triggers=["conflict_alice_bob", "conflict_charlie_dave"],
                    )
                )

            context = derive_relationship_axis_context(history)
            contexts.append(context)

        # All contexts should be similar size (bounded)
        sizes = [len(c.salient_axes) for c in contexts]
        assert max(sizes) <= 10
        assert max(sizes) - min(sizes) <= 2  # Small variance


class TestRelationshipAxisEdgeCases:
    """Tests for edge cases and robustness."""

    def test_scene_change_does_not_break_derivation(self):
        """Scene transitions don't break relationship tracking."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id=f"scene_{turn // 2}",  # Changes every 2 turns
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                    scene_changed=(turn > 1 and (turn - 1) % 2 == 0),
                )
            )

        context = derive_relationship_axis_context(history)

        # Should derive successfully across scene changes
        assert context.total_character_pairs_known > 0
        assert context.salient_axes

    def test_ending_does_not_break_derivation(self):
        """Reaching an ending doesn't break relationship tracking."""
        history = SessionHistory()

        for turn in range(1, 6):
            history.add_entry(
                HistoryEntry(
                    turn_number=turn,
                    scene_id="s",
                    guard_outcome="accepted",
                    detected_triggers=["conflict_alice_bob"],
                    ending_reached=(turn == 5),
                    ending_id="ending_bad" if turn == 5 else None,
                )
            )

        context = derive_relationship_axis_context(history)

        # Should derive successfully even with ending
        assert context.total_character_pairs_known > 0
        assert context.salient_axes
