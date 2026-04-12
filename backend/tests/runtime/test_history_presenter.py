"""Tests for history_presenter.py."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.runtime.history_presenter import (
    HistoryPanelOutput,
    HistorySummary,
    RecentHistoryEntry,
    present_history_panel,
)


class TestHistorySummary:
    """Tests for HistorySummary model."""

    def test_history_summary_creation(self):
        """Test creating a history summary."""
        summary = HistorySummary(
            session_phase="middle",
            total_turns_covered=10,
            first_turn_number=1,
            last_turn_number=10,
            scene_transition_count=3,
            ending_reached=False,
        )

        assert summary.session_phase == "middle"
        assert summary.total_turns_covered == 10
        assert summary.first_turn_number == 1
        assert summary.last_turn_number == 10
        assert summary.scene_transition_count == 3
        assert summary.ending_reached is False

    def test_history_summary_with_optional_fields(self):
        """Test history summary with optional fields."""
        summary = HistorySummary(
            session_phase="ended",
            total_turns_covered=50,
            first_turn_number=1,
            last_turn_number=50,
            scene_transition_count=10,
            recent_scene_ids=["s1", "s2", "s3"],
            unique_triggers_detected=["trigger1", "trigger2"],
            guard_outcome_summary={"ACCEPTED": 40, "REJECTED": 10},
            ending_reached=True,
            ending_id="ending_123",
        )

        assert summary.recent_scene_ids == ["s1", "s2", "s3"]
        assert summary.unique_triggers_detected == ["trigger1", "trigger2"]
        assert summary.guard_outcome_summary == {"ACCEPTED": 40, "REJECTED": 10}
        assert summary.ending_reached is True
        assert summary.ending_id == "ending_123"

    def test_history_summary_default_values(self):
        """Test that optional fields default to empty."""
        summary = HistorySummary(
            session_phase="early",
            total_turns_covered=0,
            first_turn_number=0,
            last_turn_number=0,
            scene_transition_count=0,
            ending_reached=False,
        )

        assert summary.recent_scene_ids == []
        assert summary.unique_triggers_detected == []
        assert summary.guard_outcome_summary == {}
        assert summary.ending_id is None


class TestRecentHistoryEntry:
    """Tests for RecentHistoryEntry model."""

    def test_recent_history_entry_creation(self):
        """Test creating a recent history entry."""
        now = datetime.now()
        entry = RecentHistoryEntry(
            turn_number=5,
            scene_id="scene_5",
            guard_outcome="ACCEPTED",
            scene_changed=True,
            ending_reached=False,
            created_at=now,
        )

        assert entry.turn_number == 5
        assert entry.scene_id == "scene_5"
        assert entry.guard_outcome == "ACCEPTED"
        assert entry.scene_changed is True
        assert entry.ending_reached is False
        assert entry.created_at == now

    def test_recent_history_entry_with_optional_fields(self):
        """Test entry with optional fields."""
        now = datetime.now()
        entry = RecentHistoryEntry(
            turn_number=10,
            scene_id="scene_10",
            guard_outcome="REJECTED",
            detected_triggers=["trigger1", "trigger2"],
            scene_changed=False,
            prior_scene_id="scene_9",
            ending_reached=True,
            ending_id="ending_456",
            created_at=now,
        )

        assert entry.detected_triggers == ["trigger1", "trigger2"]
        assert entry.prior_scene_id == "scene_9"
        assert entry.ending_reached is True
        assert entry.ending_id == "ending_456"

    def test_recent_history_entry_default_triggers(self):
        """Test that detected_triggers defaults to empty list."""
        now = datetime.now()
        entry = RecentHistoryEntry(
            turn_number=1,
            scene_id="scene_1",
            guard_outcome="ACCEPTED",
            scene_changed=False,
            ending_reached=False,
            created_at=now,
        )

        assert entry.detected_triggers == []
        assert entry.prior_scene_id is None
        assert entry.ending_id is None


class TestHistoryPanelOutput:
    """Tests for HistoryPanelOutput model."""

    @pytest.fixture
    def sample_summary(self):
        """Create a sample history summary."""
        return HistorySummary(
            session_phase="middle",
            total_turns_covered=10,
            first_turn_number=1,
            last_turn_number=10,
            scene_transition_count=2,
            ending_reached=False,
        )

    def test_history_panel_output_creation(self, sample_summary):
        """Test creating history panel output."""
        output = HistoryPanelOutput(
            history_summary=sample_summary,
            recent_entries=[],
            entry_count=10,
        )

        assert output.history_summary == sample_summary
        assert output.recent_entries == []
        assert output.entry_count == 10

    def test_history_panel_output_with_entries(self, sample_summary):
        """Test panel output with history entries."""
        now = datetime.now()
        entries = [
            RecentHistoryEntry(
                turn_number=1,
                scene_id="s1",
                guard_outcome="ACCEPTED",
                scene_changed=False,
                ending_reached=False,
                created_at=now,
            ),
            RecentHistoryEntry(
                turn_number=2,
                scene_id="s2",
                guard_outcome="ACCEPTED",
                scene_changed=True,
                ending_reached=False,
                created_at=now,
            ),
        ]

        output = HistoryPanelOutput(
            history_summary=sample_summary,
            recent_entries=entries,
            entry_count=2,
        )

        assert len(output.recent_entries) == 2
        assert output.recent_entries[0].turn_number == 1
        assert output.recent_entries[1].turn_number == 2


class TestPresentHistoryPanel:
    """Tests for present_history_panel function."""

    def test_present_history_panel_empty_session(self):
        """Test presenting history when session has no history or progression."""
        session_state = MagicMock()
        session_state.context_layers.session_history = None
        session_state.context_layers.progression_summary = None

        result = present_history_panel(session_state)

        assert result is not None
        assert isinstance(result, HistoryPanelOutput)
        assert result.history_summary.session_phase == "early"
        assert result.history_summary.total_turns_covered == 0
        assert result.recent_entries == []
        assert result.entry_count == 0

    def test_present_history_panel_with_progression(self):
        """Test presenting history with progression summary."""
        progression = MagicMock(
            session_phase="middle",
            total_turns_in_source=15,
            first_turn_covered=1,
            last_turn_covered=15,
            scene_transition_count=4,
            recent_scene_ids=["s1", "s2", "s3", "s4", "s5"],
            unique_triggers_in_period={"t1", "t2", "t3"},
            guard_outcome_distribution={"ACCEPTED": 12, "REJECTED": 3},
            ending_reached=False,
            ending_id=None,
        )

        session_state = MagicMock()
        session_state.context_layers.session_history = None
        session_state.context_layers.progression_summary = progression

        result = present_history_panel(session_state)

        assert result.history_summary.session_phase == "middle"
        assert result.history_summary.total_turns_covered == 15
        assert result.history_summary.first_turn_number == 1
        assert result.history_summary.last_turn_number == 15
        assert result.history_summary.scene_transition_count == 4
        assert result.history_summary.ending_reached is False

    def test_present_history_panel_with_history_entries(self):
        """Test presenting history with history entries."""
        now = datetime.now()

        # Create history entries
        entries = [
            MagicMock(
                turn_number=i,
                scene_id=f"scene_{i}",
                guard_outcome="ACCEPTED",
                detected_triggers=[],
                scene_changed=i > 0,
                prior_scene_id=f"scene_{i-1}" if i > 0 else None,
                ending_reached=False,
                ending_id=None,
                created_at=now,
            )
            for i in range(1, 6)
        ]

        history = MagicMock(entries=entries, size=5)

        session_state = MagicMock()
        session_state.context_layers.session_history = history
        session_state.context_layers.progression_summary = None

        result = present_history_panel(session_state)

        assert len(result.recent_entries) == 5
        assert result.entry_count == 5
        assert result.recent_entries[0].turn_number == 1
        assert result.recent_entries[-1].turn_number == 5

    def test_present_history_panel_truncates_to_20_entries(self):
        """Test that only last 20 entries are returned."""
        now = datetime.now()

        # Create 30 history entries
        entries = [
            MagicMock(
                turn_number=i,
                scene_id=f"scene_{i}",
                guard_outcome="ACCEPTED",
                detected_triggers=[],
                scene_changed=False,
                prior_scene_id=None,
                ending_reached=False,
                ending_id=None,
                created_at=now,
            )
            for i in range(1, 31)
        ]

        history = MagicMock(entries=entries, size=30)

        session_state = MagicMock()
        session_state.context_layers.session_history = history
        session_state.context_layers.progression_summary = None

        result = present_history_panel(session_state)

        # Only last 20 entries should be returned
        assert len(result.recent_entries) == 20
        # Should be from turn 11-30
        assert result.recent_entries[0].turn_number == 11
        assert result.recent_entries[-1].turn_number == 30
        # But entry_count should reflect total
        assert result.entry_count == 30

    def test_present_history_panel_with_progression_and_history(self):
        """Test presenting history with both progression and history."""
        now = datetime.now()

        progression = MagicMock(
            session_phase="late",
            total_turns_in_source=25,
            first_turn_covered=1,
            last_turn_covered=25,
            scene_transition_count=8,
            recent_scene_ids=["s20", "s21", "s22"],
            unique_triggers_in_period={"t1", "t2", "t3", "t4"},
            guard_outcome_distribution={"ACCEPTED": 20, "REJECTED": 5},
            ending_reached=False,
            ending_id=None,
        )

        # Create history with 25 entries
        entries = [
            MagicMock(
                turn_number=i,
                scene_id=f"scene_{i}",
                guard_outcome="ACCEPTED" if i % 5 != 0 else "REJECTED",
                detected_triggers=[] if i % 3 != 0 else ["trigger1"],
                scene_changed=i % 3 == 0,
                prior_scene_id=f"scene_{i-1}" if i > 1 else None,
                ending_reached=False,
                ending_id=None,
                created_at=now,
            )
            for i in range(1, 26)
        ]

        history = MagicMock(entries=entries, size=25)

        session_state = MagicMock()
        session_state.context_layers.session_history = history
        session_state.context_layers.progression_summary = progression

        result = present_history_panel(session_state)

        # Should use progression summary
        assert result.history_summary.session_phase == "late"
        assert result.history_summary.total_turns_covered == 25
        # Should include last 20 entries (turns 6-25)
        assert len(result.recent_entries) == 20
        assert result.entry_count == 25

    def test_present_history_panel_with_ending(self):
        """Test presenting history when ending is reached."""
        now = datetime.now()

        progression = MagicMock(
            session_phase="ended",
            total_turns_in_source=30,
            first_turn_covered=1,
            last_turn_covered=30,
            scene_transition_count=10,
            recent_scene_ids=["s28", "s29"],
            unique_triggers_in_period={"t1"},
            guard_outcome_distribution={"ACCEPTED": 28, "REJECTED": 2},
            ending_reached=True,
            ending_id="ending_final",
        )

        session_state = MagicMock()
        session_state.context_layers.session_history = None
        session_state.context_layers.progression_summary = progression

        result = present_history_panel(session_state)

        assert result.history_summary.session_phase == "ended"
        assert result.history_summary.ending_reached is True
        assert result.history_summary.ending_id == "ending_final"

    def test_present_history_panel_determinism(self):
        """Test that present_history_panel produces consistent output."""
        now = datetime.now()

        progression = MagicMock(
            session_phase="early",
            total_turns_in_source=5,
            first_turn_covered=1,
            last_turn_covered=5,
            scene_transition_count=1,
            recent_scene_ids=["s1"],
            unique_triggers_in_period=set(),
            guard_outcome_distribution={"ACCEPTED": 5},
            ending_reached=False,
            ending_id=None,
        )

        session_state = MagicMock()
        session_state.context_layers.session_history = None
        session_state.context_layers.progression_summary = progression

        result1 = present_history_panel(session_state)
        result2 = present_history_panel(session_state)

        # Should produce identical output
        assert result1.history_summary.session_phase == result2.history_summary.session_phase
        assert result1.history_summary.total_turns_covered == result2.history_summary.total_turns_covered
        assert len(result1.recent_entries) == len(result2.recent_entries)
