"""Tests for debug_presenter.py."""
from datetime import datetime
from unittest.mock import MagicMock

import pytest

from app.runtime.presentation.debug_presenter import (
    DebugDetailedSection,
    DebugPanelOutput,
    DebugSummarySection,
    PrimaryDiagnosticOutput,
    RecentPatternIndicator,
    present_debug_panel,
)


class TestDebugSummarySection:
    """Tests for DebugSummarySection model."""

    def test_debug_summary_section_creation(self):
        """Test creating a debug summary section."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=5,
            scene_id="scene_123",
            guard_outcome="ACCEPTED",
            scene_changed=True,
            ending_reached=False,
            created_at=now,
        )

        assert summary.turn_number == 5
        assert summary.scene_id == "scene_123"
        assert summary.guard_outcome == "ACCEPTED"
        assert summary.scene_changed is True
        assert summary.ending_reached is False
        assert summary.created_at == now

    def test_debug_summary_section_with_optional_fields(self):
        """Test summary section with optional fields."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=3,
            scene_id="scene_1",
            guard_outcome="REJECTED",
            detected_triggers=["trigger1", "trigger2"],
            scene_changed=False,
            prior_scene_id="scene_0",
            ending_reached=True,
            ending_id="ending_123",
            conflict_pressure=0.75,
            created_at=now,
        )

        assert summary.detected_triggers == ["trigger1", "trigger2"]
        assert summary.prior_scene_id == "scene_0"
        assert summary.ending_id == "ending_123"
        assert summary.conflict_pressure == 0.75

    def test_debug_summary_section_default_triggers(self):
        """Test that detected_triggers defaults to empty list."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=1,
            scene_id="scene_1",
            guard_outcome="UNKNOWN",
            scene_changed=False,
            ending_reached=False,
            created_at=now,
        )

        assert summary.detected_triggers == []
        assert summary.prior_scene_id is None
        assert summary.ending_id is None
        assert summary.conflict_pressure is None


class TestDebugDetailedSection:
    """Tests for DebugDetailedSection model."""

    def test_debug_detailed_section_creation(self):
        """Test creating a detailed section."""
        detailed = DebugDetailedSection(
            accepted_delta_target_count=5,
            rejected_delta_target_count=2,
        )

        assert detailed.accepted_delta_target_count == 5
        assert detailed.rejected_delta_target_count == 2
        assert detailed.sample_accepted_targets == []
        assert detailed.sample_rejected_targets == []

    def test_debug_detailed_section_with_samples(self):
        """Test detailed section with sample targets."""
        detailed = DebugDetailedSection(
            accepted_delta_target_count=10,
            rejected_delta_target_count=3,
            sample_accepted_targets=["target1", "target2"],
            sample_rejected_targets=["bad_target1"],
        )

        assert detailed.sample_accepted_targets == ["target1", "target2"]
        assert detailed.sample_rejected_targets == ["bad_target1"]


class TestPrimaryDiagnosticOutput:
    """Tests for PrimaryDiagnosticOutput model."""

    def test_primary_diagnostic_output_creation(self):
        """Test creating primary diagnostic output."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=1,
            scene_id="s1",
            guard_outcome="ACCEPTED",
            scene_changed=False,
            ending_reached=False,
            created_at=now,
        )
        detailed = DebugDetailedSection(
            accepted_delta_target_count=0,
            rejected_delta_target_count=0,
        )
        primary = PrimaryDiagnosticOutput(summary=summary, detailed=detailed)

        assert primary.summary == summary
        assert primary.detailed == detailed

    def test_primary_diagnostic_output_composition(self):
        """Test that primary diagnostic properly composes sections."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=5,
            scene_id="s5",
            guard_outcome="REJECTED",
            detected_triggers=["trigger1"],
            scene_changed=True,
            prior_scene_id="s4",
            ending_reached=False,
            conflict_pressure=0.5,
            created_at=now,
        )
        detailed = DebugDetailedSection(
            accepted_delta_target_count=3,
            rejected_delta_target_count=1,
            sample_accepted_targets=["a1", "a2"],
            sample_rejected_targets=["r1"],
        )
        primary = PrimaryDiagnosticOutput(summary=summary, detailed=detailed)

        # Verify composition
        assert primary.summary.turn_number == 5
        assert primary.detailed.accepted_delta_target_count == 3
        assert len(primary.summary.detected_triggers) == 1


class TestRecentPatternIndicator:
    """Tests for RecentPatternIndicator model."""

    def test_recent_pattern_indicator_creation(self):
        """Test creating a recent pattern indicator."""
        pattern = RecentPatternIndicator(
            turn_number=3,
            guard_outcome="ACCEPTED",
            scene_id="scene_3",
            scene_changed=True,
            ending_reached=False,
        )

        assert pattern.turn_number == 3
        assert pattern.guard_outcome == "ACCEPTED"
        assert pattern.scene_id == "scene_3"
        assert pattern.scene_changed is True
        assert pattern.ending_reached is False

    def test_recent_pattern_indicator_ending_reached(self):
        """Test pattern indicator with ending reached."""
        pattern = RecentPatternIndicator(
            turn_number=10,
            guard_outcome="ACCEPTED",
            scene_id="final_scene",
            scene_changed=False,
            ending_reached=True,
        )

        assert pattern.ending_reached is True


class TestDebugPanelOutput:
    """Tests for DebugPanelOutput model."""

    @pytest.fixture
    def sample_output(self):
        """Create a sample debug panel output."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=1,
            scene_id="s1",
            guard_outcome="ACCEPTED",
            scene_changed=False,
            ending_reached=False,
            created_at=now,
        )
        detailed = DebugDetailedSection(
            accepted_delta_target_count=0,
            rejected_delta_target_count=0,
        )
        primary = PrimaryDiagnosticOutput(summary=summary, detailed=detailed)

        return DebugPanelOutput(
            primary_diagnostic=primary,
            recent_pattern_context=[],
            degradation_markers=[],
            full_diagnostics=None,
        )

    def test_debug_panel_output_creation(self, sample_output):
        """Test creating a debug panel output."""
        assert sample_output.primary_diagnostic is not None
        assert sample_output.recent_pattern_context == []
        assert sample_output.degradation_markers == []
        assert sample_output.full_diagnostics is None

    def test_debug_panel_output_with_patterns_and_markers(self):
        """Test panel output with recent patterns and markers."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=5,
            scene_id="s5",
            guard_outcome="REJECTED",
            scene_changed=True,
            ending_reached=False,
            created_at=now,
        )
        detailed = DebugDetailedSection(
            accepted_delta_target_count=2,
            rejected_delta_target_count=1,
        )
        primary = PrimaryDiagnosticOutput(summary=summary, detailed=detailed)

        patterns = [
            RecentPatternIndicator(
                turn_number=3,
                guard_outcome="ACCEPTED",
                scene_id="s3",
                scene_changed=False,
                ending_reached=False,
            ),
            RecentPatternIndicator(
                turn_number=4,
                guard_outcome="ACCEPTED",
                scene_id="s4",
                scene_changed=True,
                ending_reached=False,
            ),
        ]

        output = DebugPanelOutput(
            primary_diagnostic=primary,
            recent_pattern_context=patterns,
            degradation_markers=["FALLBACK_ACTIVE"],
            full_diagnostics={"key": "value"},
        )

        assert len(output.recent_pattern_context) == 2
        assert len(output.degradation_markers) == 1
        assert output.degradation_markers[0] == "FALLBACK_ACTIVE"
        assert output.full_diagnostics == {"key": "value"}

    def test_debug_panel_output_without_full_diagnostics(self):
        """Test panel output when full_diagnostics is not provided."""
        now = datetime.now()
        summary = DebugSummarySection(
            turn_number=1,
            scene_id="s1",
            guard_outcome="ACCEPTED",
            scene_changed=False,
            ending_reached=False,
            created_at=now,
        )
        detailed = DebugDetailedSection(
            accepted_delta_target_count=0,
            rejected_delta_target_count=0,
        )
        primary = PrimaryDiagnosticOutput(summary=summary, detailed=detailed)

        output = DebugPanelOutput(
            primary_diagnostic=primary,
            recent_pattern_context=[],
            degradation_markers=[],
        )

        assert output.full_diagnostics is None


class TestPresentDebugPanel:
    """Tests for present_debug_panel function."""

    def test_present_debug_panel_with_short_term_context(self):
        """Test presenting debug panel when short_term context exists."""
        now = datetime.now()

        # Create mock short-term context
        short_term = MagicMock(
            turn_number=1,
            scene_id="scene_1",
            guard_outcome="ACCEPTED",
            detected_triggers=[],
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=now,
            accepted_delta_targets=[],
            rejected_delta_targets=[],
        )

        # Create mock session state
        session_state = MagicMock(
            current_scene_id="scene_1",
            degraded_state=None,
        )
        session_state.context_layers.short_term_context = short_term
        session_state.context_layers.session_history = None

        result = present_debug_panel(session_state)

        assert result is not None
        assert isinstance(result, DebugPanelOutput)
        assert result.primary_diagnostic is not None
        assert result.primary_diagnostic.summary.turn_number == 1
        assert result.primary_diagnostic.summary.scene_id == "scene_1"

    def test_present_debug_panel_without_short_term_context(self):
        """Test presenting debug panel when short_term context is missing."""
        session_state = MagicMock(
            current_scene_id="scene_1",
            degraded_state=None,
        )
        session_state.context_layers.short_term_context = None
        session_state.context_layers.session_history = None

        result = present_debug_panel(session_state)

        assert result is not None
        assert isinstance(result, DebugPanelOutput)
        # Should return empty output with turn_number=0
        assert result.primary_diagnostic.summary.turn_number == 0

    def test_present_debug_panel_with_degradation_markers(self):
        """Test presenting debug panel with active degradation markers."""
        now = datetime.now()

        short_term = MagicMock(
            turn_number=2,
            scene_id="scene_2",
            guard_outcome="ACCEPTED",
            detected_triggers=[],
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=now,
            accepted_delta_targets=[],
            rejected_delta_targets=[],
        )

        marker = MagicMock(value="FALLBACK_ACTIVE")
        degraded_state = MagicMock(active_markers=[marker])

        session_state = MagicMock(
            current_scene_id="scene_2",
            degraded_state=degraded_state,
        )
        session_state.context_layers.short_term_context = short_term
        session_state.context_layers.session_history = None

        result = present_debug_panel(session_state)

        assert len(result.degradation_markers) == 1
        assert result.degradation_markers[0] == "FALLBACK_ACTIVE"

    def test_present_debug_panel_with_session_history(self):
        """Test presenting debug panel with session history."""
        now = datetime.now()

        short_term = MagicMock(
            turn_number=3,
            scene_id="scene_3",
            guard_outcome="ACCEPTED",
            detected_triggers=["trigger1"],
            scene_changed=True,
            prior_scene_id="scene_2",
            ending_reached=False,
            ending_id=None,
            created_at=now,
            accepted_delta_targets=["t1"],
            rejected_delta_targets=[],
        )

        # Create history with entries
        history_entry1 = MagicMock(
            turn_number=1,
            guard_outcome="ACCEPTED",
            scene_id="scene_1",
            scene_changed=False,
            ending_reached=False,
        )
        history_entry2 = MagicMock(
            turn_number=2,
            guard_outcome="ACCEPTED",
            scene_id="scene_2",
            scene_changed=True,
            ending_reached=False,
        )
        history = MagicMock(entries=[history_entry1, history_entry2])

        session_state = MagicMock(
            current_scene_id="scene_3",
            degraded_state=None,
        )
        session_state.context_layers.short_term_context = short_term
        session_state.context_layers.session_history = history

        result = present_debug_panel(session_state)

        assert result.primary_diagnostic.summary.turn_number == 3
        assert len(result.recent_pattern_context) == 2
        assert result.recent_pattern_context[0].turn_number == 1
        assert result.recent_pattern_context[1].turn_number == 2

    def test_present_debug_panel_determinism(self):
        """Test that present_debug_panel produces same output for same input."""
        now = datetime.now()

        short_term = MagicMock(
            turn_number=5,
            scene_id="scene_5",
            guard_outcome="REJECTED",
            detected_triggers=["t1", "t2"],
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=now,
            accepted_delta_targets=[],
            rejected_delta_targets=[],
        )

        session_state = MagicMock(
            current_scene_id="scene_5",
            degraded_state=None,
        )
        session_state.context_layers.short_term_context = short_term
        session_state.context_layers.session_history = None

        result1 = present_debug_panel(session_state)
        result2 = present_debug_panel(session_state)

        # Both should have same primary diagnostic details
        assert result1.primary_diagnostic.summary.turn_number == result2.primary_diagnostic.summary.turn_number
        assert result1.primary_diagnostic.summary.scene_id == result2.primary_diagnostic.summary.scene_id
        assert result1.degradation_markers == result2.degradation_markers
