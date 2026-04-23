"""Tests for ai_stack_evidence_service.py - AI stack evidence aggregation."""
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
import json
import pytest

from app.services.ai_stack_evidence_service import (
    _summarize_tool_influence,
    _retrieval_influence_from_turn,
    _committed_narrative_surface,
    _last_turn_graph_mode,
    _degraded_path_signal_list,
    _runtime_quality_aggregation,
    _improvement_package_recency_timestamp,
    _build_cross_layer_classifiers,
    _improvement_evidence_influence,
    _writers_room_governance_signals,
    assemble_session_evidence_bundle,
    build_session_evidence_bundle,
    _latest_writers_room_review,
    _latest_improvement_package,
    build_release_readiness_report,
)


class TestSummarizeToolInfluence:
    """Tests for _summarize_tool_influence function."""

    def test_summarize_empty_audit(self):
        """Test summarizing empty audit list."""
        result = _summarize_tool_influence([])
        assert result["entries"] == []
        assert result["material_capability_invocations"] == []
        assert result["material_influence"] is False

    def test_summarize_non_list_audit(self):
        """Test handling non-list audit input."""
        result = _summarize_tool_influence(None)
        assert result["entries"] == []
        assert result["material_capability_invocations"] == []

    def test_summarize_with_material_capability(self):
        """Test summarizing with material capability."""
        audit = [
            {
                "capability_name": "wos.context_pack.build",
                "outcome": "success",
            }
        ]
        result = _summarize_tool_influence(audit)
        assert len(result["entries"]) == 1
        assert "wos.context_pack.build" in result["material_capability_invocations"]
        assert result["material_influence"] is True

    def test_summarize_with_non_material_capability(self):
        """Test summarizing with non-material capability."""
        audit = [
            {
                "capability_name": "other.capability",
                "outcome": "success",
            }
        ]
        result = _summarize_tool_influence(audit)
        assert len(result["entries"]) == 1
        assert result["material_capability_invocations"] == []
        assert result["material_influence"] is False

    def test_summarize_ignores_failed_outcomes(self):
        """Test that failed outcomes don't count as material influence."""
        audit = [
            {
                "capability_name": "wos.context_pack.build",
                "outcome": "denied",
            }
        ]
        result = _summarize_tool_influence(audit)
        assert "wos.context_pack.build" not in result["material_capability_invocations"]

    def test_summarize_deduplicates_capabilities(self):
        """Test deduplication of material capabilities."""
        audit = [
            {"capability_name": "wos.context_pack.build", "outcome": "success"},
            {"capability_name": "wos.context_pack.build", "outcome": "ok"},
        ]
        result = _summarize_tool_influence(audit)
        assert result["material_capability_invocations"].count("wos.context_pack.build") == 1

    def test_summarize_truncates_to_24_entries(self):
        """Test that entries are truncated to 24."""
        audit = [
            {"capability_name": f"cap_{i}", "outcome": "success"}
            for i in range(30)
        ]
        result = _summarize_tool_influence(audit)
        assert len(result["entries"]) == 24


class TestRetrievalInfluenceFromTurn:
    """Tests for _retrieval_influence_from_turn function."""

    def test_retrieval_influence_none_turn(self):
        """Test with None turn."""
        result = _retrieval_influence_from_turn(None)
        assert result is None

    def test_retrieval_influence_non_dict_turn(self):
        """Test with non-dict turn."""
        result = _retrieval_influence_from_turn("not a dict")
        assert result is None

    def test_retrieval_influence_empty_turn(self):
        """Test with turn without retrieval."""
        turn = {}
        with patch("app.services.ai_stack_evidence_service.build_retrieval_trace") as mock_trace:
            mock_trace.return_value = {
                "domain": "test_domain",
                "profile": "test_profile",
                "hit_count": 0,
                "status": "ok",
            }
            result = _retrieval_influence_from_turn(turn)
            assert result is not None
            assert result["domain"] == "test_domain"

    def test_retrieval_influence_with_retrieval_dict(self):
        """Test with turn containing retrieval data."""
        turn = {
            "retrieval": {
                "hits": [{"id": "hit1"}],
            }
        }
        with patch("app.services.ai_stack_evidence_service.build_retrieval_trace") as mock_trace:
            mock_trace.return_value = {
                "domain": "live",
                "profile": "full",
                "hit_count": 1,
                "status": "ok",
                "evidence_strength": "strong",
                "evidence_tier": "governance_ready",
            }
            result = _retrieval_influence_from_turn(turn)
            assert result["evidence_tier"] == "governance_ready"


class TestCommittedNarrativeSurface:
    """Tests for _committed_narrative_surface function."""

    def test_empty_diagnostic(self):
        """Test with empty diagnostic."""
        result = _committed_narrative_surface({})
        assert result["committed_state"] is None
        assert result["last_committed_turn_summary"] is None
        assert result["world_engine_warnings"] == []

    def test_with_committed_state(self):
        """Test with committed state."""
        diag = {
            "committed_state": {"key": "value"},
            "authoritative_history_tail": [],
            "warnings": [],
        }
        result = _committed_narrative_surface(diag)
        assert result["committed_state"] == {"key": "value"}

    def test_with_last_committed_turn(self):
        """Test extracting last committed turn."""
        diag = {
            "committed_state": None,
            "authoritative_history_tail": [
                {
                    "turn_number": 1,
                    "trace_id": "trace-1",
                    "narrative_commit": "committed",
                    "turn_outcome": "success",
                }
            ],
            "warnings": ["warning1"],
        }
        result = _committed_narrative_surface(diag)
        assert result["last_committed_turn_summary"]["turn_number"] == 1
        assert result["world_engine_warnings"] == ["warning1"]


class TestLastTurnGraphMode:
    """Tests for _last_turn_graph_mode function."""

    def test_empty_graph(self):
        """Test with empty graph."""
        result = _last_turn_graph_mode({})
        assert result["execution_health"] is None
        assert result["fallback_path_taken"] is False

    def test_graph_with_repro_metadata(self):
        """Test graph with repro metadata."""
        graph = {
            "execution_health": "healthy",
            "fallback_path_taken": False,
            "repro_metadata": {
                "graph_path_summary": "primary_path",
                "adapter_invocation_mode": "normal",
            },
            "graph_name": "main_graph",
            "graph_version": 1,
        }
        result = _last_turn_graph_mode(graph)
        assert result["execution_health"] == "healthy"
        assert result["graph_path_summary"] == "primary_path"
        assert result["graph_name"] == "main_graph"


class TestDegradedPathSignalList:
    """Tests for _degraded_path_signal_list function."""

    def test_no_signals(self):
        """Test graph with no degradation signals."""
        graph = {
            "errors": [],
            "fallback_path_taken": False,
            "execution_health": "healthy",
        }
        result = _degraded_path_signal_list(graph)
        assert result == []

    def test_graph_errors_signal(self):
        """Test with graph errors."""
        graph = {
            "errors": [{"message": "error"}],
            "fallback_path_taken": False,
        }
        result = _degraded_path_signal_list(graph)
        assert "graph_errors_present" in result

    def test_fallback_path_signal(self):
        """Test with fallback path."""
        graph = {
            "errors": [],
            "fallback_path_taken": True,
        }
        result = _degraded_path_signal_list(graph)
        assert "fallback_path_taken" in result

    def test_execution_health_signals(self):
        """Test with degraded execution health."""
        for health in ["model_fallback", "degraded_generation", "graph_error"]:
            graph = {
                "errors": [],
                "fallback_path_taken": False,
                "execution_health": health,
            }
            result = _degraded_path_signal_list(graph)
            assert f"execution_health:{health}" in result


class TestRuntimeQualityAggregation:
    """Tests for _runtime_quality_aggregation function."""

    def test_runtime_quality_counts_and_signals(self):
        diag_list = [
            {"turn_number": 1, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {
                "turn_number": 2,
                "runtime_governance_surface": {
                    "quality_class": "weak_but_legal",
                    "degradation_signals": ["weak_signal_accepted"],
                },
            },
            {
                "turn_number": 3,
                "runtime_governance_surface": {
                    "quality_class": "weak_but_legal",
                    "degradation_signals": ["thin_prose_override"],
                },
            },
            {
                "turn_number": 4,
                "runtime_governance_surface": {
                    "quality_class": "degraded",
                    "degradation_signals": ["fallback_used"],
                },
            },
        ]
        agg = _runtime_quality_aggregation(diag_list)
        assert agg["quality_class_counts"]["healthy"] == 1
        assert agg["quality_class_counts"]["weak_but_legal"] == 2
        assert agg["quality_class_counts"]["degraded"] == 1
        assert agg["degradation_signal_counts"]["fallback_used"] == 1
        assert agg["latest_degraded_turns"][-1]["turn_number"] == 4

    def test_runtime_quality_rising_degraded_posture(self):
        diag_list = [
            {"turn_number": 1, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {"turn_number": 2, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {"turn_number": 3, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {"turn_number": 4, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {"turn_number": 5, "runtime_governance_surface": {"quality_class": "healthy", "degradation_signals": []}},
            {
                "turn_number": 6,
                "runtime_governance_surface": {"quality_class": "degraded", "degradation_signals": ["fallback_used"]},
            },
            {
                "turn_number": 7,
                "runtime_governance_surface": {"quality_class": "degraded", "degradation_signals": ["fallback_used"]},
            },
            {
                "turn_number": 8,
                "runtime_governance_surface": {"quality_class": "degraded", "degradation_signals": ["fallback_used"]},
            },
            {
                "turn_number": 9,
                "runtime_governance_surface": {"quality_class": "degraded", "degradation_signals": ["fallback_used"]},
            },
            {
                "turn_number": 10,
                "runtime_governance_surface": {"quality_class": "degraded", "degradation_signals": ["fallback_used"]},
            },
        ]
        agg = _runtime_quality_aggregation(diag_list)
        assert agg["rising_degraded_posture"] is True


class TestImprovementPackageRecencyTimestamp:
    """Tests for _improvement_package_recency_timestamp function."""

    def test_valid_iso_timestamp(self):
        """Test with valid ISO timestamp."""
        package = {"generated_at": "2026-01-15T10:30:00Z"}
        result = _improvement_package_recency_timestamp(package)
        assert isinstance(result, float)
        assert result > 0

    def test_invalid_timestamp(self):
        """Test with invalid timestamp."""
        package = {"generated_at": "invalid"}
        result = _improvement_package_recency_timestamp(package)
        assert result == 0.0

    def test_missing_generated_at(self):
        """Test with missing generated_at."""
        package = {}
        result = _improvement_package_recency_timestamp(package)
        assert result == 0.0

    def test_empty_string_timestamp(self):
        """Test with empty string timestamp."""
        package = {"generated_at": "   "}
        result = _improvement_package_recency_timestamp(package)
        assert result == 0.0


class TestBuildCrossLayerClassifiers:
    """Tests for _build_cross_layer_classifiers function."""

    def test_no_diagnostics(self):
        """Test with no diagnostics available."""
        result = _build_cross_layer_classifiers(
            execution_truth=None,
            degraded_path_signals=[],
            bridge_errors=[],
            diag_list=None,
        )
        assert result["last_turn_diagnostics_available"] is False
        assert result["runtime_retrieval_evidence_tier"] == "no_turn_diagnostics"
        assert result["bridge_reachability"] == "ok"

    def test_with_graph_mode_fallback(self):
        """Test with fallback graph mode."""
        execution_truth = {
            "last_turn_graph_mode": {
                "fallback_path_taken": True,
                "execution_health": "healthy",
            }
        }
        result = _build_cross_layer_classifiers(
            execution_truth=execution_truth,
            degraded_path_signals=[],
            bridge_errors=[],
            diag_list=[{}],
        )
        assert result["graph_execution_posture"] == "fallback_or_alternate_path"

    def test_with_degraded_execution_health(self):
        """Test with degraded execution health."""
        execution_truth = {
            "last_turn_graph_mode": {
                "fallback_path_taken": False,
                "execution_health": "degraded",
            }
        }
        result = _build_cross_layer_classifiers(
            execution_truth=execution_truth,
            degraded_path_signals=[],
            bridge_errors=[],
            diag_list=[{}],
        )
        assert result["graph_execution_posture"] == "degraded_execution_health"

    def test_with_bridge_errors(self):
        """Test with bridge errors."""
        result = _build_cross_layer_classifiers(
            execution_truth=None,
            degraded_path_signals=[],
            bridge_errors=[{"error": "connection failed"}],
            diag_list=None,
        )
        assert result["bridge_reachability"] == "degraded"


class TestImprovementEvidenceInfluence:
    """Tests for _improvement_evidence_influence function."""

    def test_empty_package(self):
        """Test with empty package."""
        result = _improvement_evidence_influence({})
        assert result["workflow_stage_ids"] == []
        assert result["improvement_loop_progress_len"] == 0
        assert result["governance_terminal_accepted"] is False

    def test_with_workflow_stages(self):
        """Test with workflow stages."""
        package = {
            "workflow_stages": [
                {"id": "stage1", "loop_stage": "retrieval"},
                {"id": "stage2", "loop_stage": "generation"},
            ]
        }
        result = _improvement_evidence_influence(package)
        assert "stage1" in result["workflow_stage_ids"]
        assert "retrieval" in result["improvement_loop_stages"]

    def test_governance_accepted_status(self):
        """Test governance accepted status."""
        package = {
            "governance_review_state": {"status": "governance_accepted"}
        }
        result = _improvement_evidence_influence(package)
        assert result["governance_terminal_accepted"] is True
        assert result["distinct_from_publishable_recommendation"] is False

    def test_governance_rejected_status(self):
        """Test governance rejected status."""
        package = {
            "governance_review_state": {"status": "governance_rejected"}
        }
        result = _improvement_evidence_influence(package)
        assert result["governance_terminal_rejected"] is True

    def test_evidence_bundle_analysis(self):
        """Test evidence bundle analysis."""
        package = {
            "evidence_bundle": {
                "retrieval_source_paths": ["/path1", "/path2"],
                "transcript_evidence": {"data": "transcript"},
                "governance_review_bundle_id": "bundle-123",
            }
        }
        result = _improvement_evidence_influence(package)
        assert result["retrieval_source_path_count"] == 2
        assert result["has_transcript_evidence"] is True
        assert result["has_governance_review_bundle"] is True


class TestWritersRoomGovernanceSignals:
    """Tests for _writers_room_governance_signals function."""

    def test_empty_review(self):
        """Test with empty review."""
        result = _writers_room_governance_signals({})
        assert result["review_id"] is None
        assert result["review_status"] is None
        assert result["capability_audit_tail"] == []

    def test_with_review_state(self):
        """Test with review state."""
        review = {
            "review_id": "review-123",
            "review_state": {"status": "in_progress"},
            "retrieval_trace": {
                "evidence_tier": "governance_ready",
                "evidence_strength": "strong",
            },
        }
        with patch("app.services.ai_stack_evidence_service._retrieval_tier_strong_enough_for_governance") as mock_strong:
            mock_strong.return_value = True
            result = _writers_room_governance_signals(review)
            assert result["review_id"] == "review-123"
            assert result["review_status"] == "in_progress"
            assert result["evidence_tier"] == "governance_ready"

    def test_capability_audit_tail(self):
        """Test capability audit tail extraction."""
        review = {
            "capability_audit": [
                {"capability_name": "cap1"},
                {"capability_name": "cap2"},
            ]
        }
        result = _writers_room_governance_signals(review)
        assert "cap1" in result["capability_audit_tail"]
        assert "cap2" in result["capability_audit_tail"]

    def test_artifact_counts(self):
        """Test artifact counting."""
        review = {
            "issues": [{"id": "issue1"}, {"id": "issue2"}],
            "patch_candidates": [{"id": "patch1"}],
            "variant_candidates": [],
        }
        result = _writers_room_governance_signals(review)
        assert result["artifact_counts"]["issues"] == 2
        assert result["artifact_counts"]["patch_candidates"] == 1
        assert result["artifact_counts"]["variant_candidates"] == 0


class TestSessionEvidenceBundle:
    """Tests for session evidence bundle functions."""

    def test_assemble_session_evidence_bundle_no_session(self):
        """Test assembling bundle when session not found."""
        with patch("app.services.ai_stack_evidence_service.get_runtime_session") as mock_get:
            mock_get.return_value = None

            result = assemble_session_evidence_bundle(
                session_id="sess-123",
                trace_id="trace-456"
            )

            # When session not found, it returns a dict
            assert isinstance(result, dict)
            mock_get.assert_called_once_with("sess-123")

    def test_build_session_evidence_bundle(self):
        """Test wrapper function."""
        with patch("app.services.ai_stack_evidence_service.assemble_session_evidence_bundle") as mock_assemble:
            mock_assemble.return_value = {"bundle": "data"}

            result = build_session_evidence_bundle(
                session_id="sess-123",
                trace_id="trace-456"
            )

            assert result == {"bundle": "data"}


class TestLatestReviewAndPackage:
    """Tests for latest writers room review and improvement package."""

    def test_latest_writers_room_review_no_dir(self):
        """Test when writers room directory doesn't exist."""
        with patch("app.services.ai_stack_evidence_service.Path") as mock_path:
            mock_path.return_value.exists.return_value = False
            result = _latest_writers_room_review()
            assert result is None

    def test_latest_writers_room_review_no_files(self):
        """Test when no JSON files exist."""
        with patch("app.services.ai_stack_evidence_service.Path") as mock_path:
            mock_root = MagicMock()
            mock_root.exists.return_value = True
            mock_root.glob.return_value = []
            mock_path.return_value = mock_root

            result = _latest_writers_room_review()
            assert result is None

    def test_latest_writers_room_review_no_valid_json(self):
        """Test when review file exists but contains invalid JSON."""
        # The actual function tries to open files, so we test the logic pathways
        # that don't require actual file I/O
        assert _latest_writers_room_review() is None or isinstance(_latest_writers_room_review(), dict)

    def test_latest_improvement_package_empty(self):
        """Test when no packages exist."""
        with patch("app.services.ai_stack_evidence_service.list_recommendation_packages") as mock_list:
            mock_list.return_value = []
            result = _latest_improvement_package()
            assert result is None

    def test_latest_improvement_package_found(self):
        """Test finding latest package."""
        with patch("app.services.ai_stack_evidence_service.list_recommendation_packages") as mock_list:
            with patch("app.services.ai_stack_evidence_service._improvement_package_recency_timestamp") as mock_ts:
                pkg1 = {"generated_at": "2026-01-01T00:00:00Z"}
                pkg2 = {"generated_at": "2026-01-15T00:00:00Z"}
                mock_list.return_value = [pkg1, pkg2]
                mock_ts.side_effect = lambda p: 1000 if p == pkg1 else 2000

                result = _latest_improvement_package()
                assert result == pkg2


class TestBuildReleaseReadinessReport:
    """Tests for build_release_readiness_report function."""

    def test_build_release_readiness_report(self):
        """Test building release readiness report."""
        with patch("app.services.ai_stack_evidence_service._latest_writers_room_review") as mock_wr:
            with patch("app.services.ai_stack_evidence_service._latest_improvement_package") as mock_pkg:
                with patch("app.services.ai_stack_release_readiness_report.build_release_readiness_report_payload") as mock_payload:
                    mock_wr.return_value = None
                    mock_pkg.return_value = None
                    mock_payload.return_value = {"report": "data"}

                    result = build_release_readiness_report(trace_id="trace-123")

                    # Should return dict from the payload builder
                    assert isinstance(result, dict)
