"""Tests for debug_presenter_sections.py."""
from datetime import datetime
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.runtime.presentation.debug_presenter_sections import (
    degradation_marker_values,
    empty_short_term_panel_output,
    full_diagnostics_from_short_term,
    primary_diagnostic_from_short_term,
    recent_pattern_from_history,
)


class TestDegradationMarkerValues:
    """Tests for degradation_marker_values function."""

    def test_degradation_marker_values_with_active_markers(self):
        """Test extracting marker values when markers are active."""
        marker1 = MagicMock(value="FALLBACK_ACTIVE")
        marker2 = MagicMock(value="REDUCED_CONTEXT_ACTIVE")
        degraded_state = MagicMock(active_markers=[marker1, marker2])
        session_state = MagicMock(degraded_state=degraded_state)

        result = degradation_marker_values(session_state)

        assert result == ["FALLBACK_ACTIVE", "REDUCED_CONTEXT_ACTIVE"]

    def test_degradation_marker_values_no_degraded_state(self):
        """Test when there's no degraded state."""
        session_state = MagicMock(degraded_state=None)

        result = degradation_marker_values(session_state)

        assert result == []

    def test_degradation_marker_values_empty_markers(self):
        """Test when degraded state has no active markers."""
        degraded_state = MagicMock(active_markers=None)
        session_state = MagicMock(degraded_state=degraded_state)

        result = degradation_marker_values(session_state)

        assert result == []

    def test_degradation_marker_values_empty_markers_list(self):
        """Test when degraded state has empty markers list."""
        degraded_state = MagicMock(active_markers=[])
        session_state = MagicMock(degraded_state=degraded_state)

        result = degradation_marker_values(session_state)

        assert result == []


class TestEmptyShortTermPanelOutput:
    """Tests for empty_short_term_panel_output function."""

    def test_empty_short_term_panel_output_creation(self):
        """Test creating empty panel output."""
        session_state = MagicMock(current_scene_id="scene_123")
        degradation_markers = ["MARKER_1"]

        result = empty_short_term_panel_output(session_state, degradation_markers)

        assert result.primary_diagnostic is not None
        assert result.primary_diagnostic.summary.turn_number == 0
        assert result.primary_diagnostic.summary.scene_id == "scene_123"
        assert result.primary_diagnostic.summary.guard_outcome == "unknown"
        assert result.primary_diagnostic.summary.scene_changed is False
        assert result.primary_diagnostic.summary.ending_reached is False
        assert result.primary_diagnostic.detailed.accepted_delta_target_count == 0
        assert result.primary_diagnostic.detailed.rejected_delta_target_count == 0
        assert result.recent_pattern_context == []
        assert result.degradation_markers == ["MARKER_1"]
        assert result.full_diagnostics is None

    def test_empty_short_term_panel_output_no_markers(self):
        """Test creating empty panel output without markers."""
        session_state = MagicMock(current_scene_id="scene_456")
        degradation_markers = []

        result = empty_short_term_panel_output(session_state, degradation_markers)

        assert result.degradation_markers == []
        assert result.primary_diagnostic.summary.scene_id == "scene_456"

    def test_empty_short_term_panel_output_created_at_is_datetime(self):
        """Test that created_at is a datetime object."""
        session_state = MagicMock(current_scene_id="scene_789")
        degradation_markers = []

        result = empty_short_term_panel_output(session_state, degradation_markers)

        assert isinstance(result.primary_diagnostic.summary.created_at, datetime)


class TestPrimaryDiagnosticFromShortTerm:
    """Tests for primary_diagnostic_from_short_term function."""

    def test_primary_diagnostic_from_short_term_complete(self):
        """Test building primary diagnostic from complete short-term data."""
        short_term = MagicMock(
            turn_number=5,
            scene_id="scene_123",
            guard_outcome="passed",
            detected_triggers=["trigger1", "trigger2"],
            scene_changed=True,
            prior_scene_id="scene_122",
            ending_reached=False,
            ending_id=None,
            conflict_pressure=0.5,
            created_at=datetime.now(),
            accepted_delta_targets=["target1", "target2", "target3", "target4"],
            rejected_delta_targets=["rejected1"],
        )

        result = primary_diagnostic_from_short_term(short_term)

        assert result.summary.turn_number == 5
        assert result.summary.scene_id == "scene_123"
        assert result.summary.guard_outcome == "passed"
        assert result.summary.detected_triggers == ["trigger1", "trigger2"]
        assert result.summary.scene_changed is True
        assert result.summary.prior_scene_id == "scene_122"
        assert result.summary.ending_reached is False
        assert result.summary.ending_id is None
        assert result.summary.conflict_pressure == 0.5
        assert result.detailed.accepted_delta_target_count == 4
        assert result.detailed.rejected_delta_target_count == 1
        assert result.detailed.sample_accepted_targets == ["target1", "target2", "target3"]
        assert result.detailed.sample_rejected_targets == ["rejected1"]

    def test_primary_diagnostic_from_short_term_missing_attributes(self):
        """Test building diagnostic when short_term is missing optional attributes."""
        short_term = MagicMock(
            turn_number=1,
            scene_id="scene_1",
            guard_outcome="unknown",
            detected_triggers=None,
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=datetime.now(),
            spec=[
                "turn_number",
                "scene_id",
                "guard_outcome",
                "detected_triggers",
                "scene_changed",
                "prior_scene_id",
                "ending_reached",
                "ending_id",
                "created_at",
            ],
        )

        result = primary_diagnostic_from_short_term(short_term)

        assert result.summary.turn_number == 1
        assert result.summary.detected_triggers == []
        assert result.detailed.accepted_delta_target_count == 0
        assert result.detailed.rejected_delta_target_count == 0

    def test_primary_diagnostic_from_short_term_no_conflict_pressure(self):
        """Test when conflict_pressure is not present."""
        short_term = MagicMock(
            turn_number=2,
            scene_id="scene_2",
            guard_outcome="passed",
            detected_triggers=[],
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=datetime.now(),
            accepted_delta_targets=[],
            rejected_delta_targets=[],
        )
        # Remove conflict_pressure attribute
        del short_term.conflict_pressure

        result = primary_diagnostic_from_short_term(short_term)

        assert result.summary.conflict_pressure is None

    def test_primary_diagnostic_from_short_term_large_target_list(self):
        """Test that only first 3 targets are sampled."""
        short_term = MagicMock(
            turn_number=3,
            scene_id="scene_3",
            guard_outcome="passed",
            detected_triggers=[],
            scene_changed=False,
            prior_scene_id=None,
            ending_reached=False,
            ending_id=None,
            created_at=datetime.now(),
            accepted_delta_targets=["t1", "t2", "t3", "t4", "t5"],
            rejected_delta_targets=["r1", "r2", "r3", "r4"],
        )

        result = primary_diagnostic_from_short_term(short_term)

        assert result.detailed.accepted_delta_target_count == 5
        assert result.detailed.rejected_delta_target_count == 4
        assert len(result.detailed.sample_accepted_targets) == 3
        assert len(result.detailed.sample_rejected_targets) == 3


class TestRecentPatternFromHistory:
    """Tests for recent_pattern_from_history function."""

    def test_recent_pattern_from_history_with_entries(self):
        """Test extracting recent patterns from history with entries."""
        entries = [
            MagicMock(
                turn_number=1,
                guard_outcome="passed",
                scene_id="s1",
                scene_changed=False,
                ending_reached=False,
            ),
            MagicMock(
                turn_number=2,
                guard_outcome="failed",
                scene_id="s2",
                scene_changed=True,
                ending_reached=False,
            ),
        ]
        history = MagicMock(entries=entries)

        result = recent_pattern_from_history(history)

        assert len(result) == 2
        assert result[0].turn_number == 1
        assert result[0].guard_outcome == "passed"
        assert result[1].turn_number == 2
        assert result[1].guard_outcome == "failed"

    def test_recent_pattern_from_history_more_than_5_entries(self):
        """Test that only last 5 entries are used when more exist."""
        entries = [
            MagicMock(
                turn_number=i,
                guard_outcome="passed",
                scene_id=f"scene_{i}",
                scene_changed=False,
                ending_reached=False,
            )
            for i in range(10)
        ]
        history = MagicMock(entries=entries)

        result = recent_pattern_from_history(history)

        assert len(result) == 5
        assert result[0].turn_number == 5

    def test_recent_pattern_from_history_exactly_5_entries(self):
        """Test with exactly 5 entries."""
        entries = [
            MagicMock(
                turn_number=i,
                guard_outcome="passed",
                scene_id=f"scene_{i}",
                scene_changed=False,
                ending_reached=False,
            )
            for i in range(5)
        ]
        history = MagicMock(entries=entries)

        result = recent_pattern_from_history(history)

        assert len(result) == 5

    def test_recent_pattern_from_history_none_history(self):
        """Test with None history."""
        result = recent_pattern_from_history(None)

        assert result == []

    def test_recent_pattern_from_history_no_entries(self):
        """Test with history that has no entries."""
        history = MagicMock(entries=None)

        result = recent_pattern_from_history(history)

        assert result == []

    def test_recent_pattern_from_history_empty_entries(self):
        """Test with history that has empty entries list."""
        history = MagicMock(entries=[])

        result = recent_pattern_from_history(history)

        assert result == []


class TestFullDiagnosticsFromShortTerm:
    """Tests for full_diagnostics_from_short_term function."""

    def test_full_diagnostics_from_short_term_complete(self):
        """Test building full diagnostics from complete short-term data."""
        short_term = MagicMock(
            execution_result_full={
                "validation_errors": ["error1", "error2"],
            },
            ai_decision_log_full={
                "raw_output": "raw llm output",
                "parsed_output": {"key": "value"},
                "interpreter_output": "interp output",
                "director_output": "director output",
                "responder_output": "responder output",
                "tool_loop_summary": "tool summary",
                "tool_call_transcript": ["call1", "call2"],
                "tool_influence": "influence info",
                "preview_diagnostics": "preview info",
                "supervisor_plan": "plan info",
                "subagent_invocations": ["inv1", "inv2"],
                "subagent_results": ["result1", "result2"],
                "merge_finalization": "merge info",
                "orchestration_budget_summary": "budget info",
                "orchestration_failover": ["failover1"],
                "orchestration_cache": "cache info",
                "tool_audit": ["audit1", "audit2"],
            },
        )
        degraded_state = None

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result is not None
        assert result["raw_llm_output"] == "raw llm output"
        assert result["parsed_output"] == {"key": "value"}
        assert result["validation_errors"] == ["error1", "error2"]
        assert result["recovery_action"] is None
        assert result["tool_loop_summary"] == "tool summary"
        assert result["role_diagnostics"]["interpreter"] == "interp output"
        assert result["role_diagnostics"]["director"] == "director output"
        assert result["role_diagnostics"]["responder"] == "responder output"

    def test_full_diagnostics_none_short_term(self):
        """Test when short_term is None."""
        result = full_diagnostics_from_short_term(None, None)

        assert result is None

    def test_full_diagnostics_no_execution_result_full(self):
        """Test when short_term has no execution_result_full attribute."""
        short_term = MagicMock(spec=[])

        result = full_diagnostics_from_short_term(short_term, None)

        assert result is None

    def test_full_diagnostics_with_fallback_degradation(self):
        """Test recovery action is set to fallback when marker is active."""
        marker = MagicMock(value="FALLBACK_ACTIVE")
        degraded_state = MagicMock(active_markers=[marker])
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result is not None
        assert result["recovery_action"] == "fallback_responder_used"

    def test_full_diagnostics_with_reduced_context_degradation(self):
        """Test recovery action for reduced context."""
        marker = MagicMock(value="REDUCED_CONTEXT_ACTIVE")
        degraded_state = MagicMock(active_markers=[marker])
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result["recovery_action"] == "reduced_context_retry"

    def test_full_diagnostics_with_retry_exhausted_degradation(self):
        """Test recovery action for retry exhausted."""
        marker = MagicMock(value="RETRY_EXHAUSTED")
        degraded_state = MagicMock(active_markers=[marker])
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result["recovery_action"] == "retries_exhausted_fallback"

    def test_full_diagnostics_truncates_lists(self):
        """Test that long lists are truncated to samples."""
        short_term = MagicMock(
            execution_result_full={"validation_errors": [f"error{i}" for i in range(10)]},
            ai_decision_log_full={
                "tool_call_transcript": [f"call{i}" for i in range(20)],
                "subagent_invocations": [f"inv{i}" for i in range(10)],
                "subagent_results": [f"result{i}" for i in range(10)],
                "tool_audit": [f"audit{i}" for i in range(15)],
                "orchestration_failover": [f"failover{i}" for i in range(15)],
            },
        )

        result = full_diagnostics_from_short_term(short_term, None)

        assert len(result["validation_errors"]) == 5
        assert len(result["tool_call_transcript"]) == 10
        assert len(result["subagent_invocations"]) == 8
        assert len(result["tool_audit"]) == 12
        assert len(result["failover_degradation"]) == 10

    def test_full_diagnostics_non_dict_ai_log(self):
        """Test handling when ai_decision_log_full is not a dict."""
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full="not a dict",
        )

        result = full_diagnostics_from_short_term(short_term, None)

        assert result is not None
        assert result["raw_llm_output"] is None
        # role_diagnostics is still built but with None values when ai_log is not a dict
        assert result["role_diagnostics"] == {
            "interpreter": None,
            "director": None,
            "responder": None,
        }
        assert result["tool_loop_summary"] is None

    def test_full_diagnostics_non_dict_execution_result(self):
        """Test handling when execution_result_full is not a dict."""
        short_term = MagicMock(
            execution_result_full="not a dict",
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, None)

        assert result is not None
        assert result["validation_errors"] == []

    def test_full_diagnostics_degraded_state_no_markers(self):
        """Test when degraded_state exists but has no markers."""
        degraded_state = MagicMock(active_markers=None)
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result["recovery_action"] is None

    def test_full_diagnostics_marker_without_value_attribute(self):
        """Test handling marker that doesn't have value attribute."""
        # Create a simple object without value attribute but with string representation
        class SimpleMarker:
            def __str__(self):
                return "FALLBACK_ACTIVE"

        marker = SimpleMarker()
        degraded_state = MagicMock(active_markers=[marker])
        short_term = MagicMock(
            execution_result_full={},
            ai_decision_log_full={},
        )

        result = full_diagnostics_from_short_term(short_term, degraded_state)

        assert result["recovery_action"] == "fallback_responder_used"
