"""Tests for ai_turn_routing_builders.py."""
from unittest.mock import MagicMock, patch

import pytest

from app.runtime.ai_turn.ai_turn_routing_builders import (
    build_model_routing_trace_dict,
    build_runtime_routing_request,
)
from app.runtime.model_routing_contracts import (
    CostSensitivity,
    EscalationHint,
    LatencyBudget,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.runtime_models import DegradedMarker


class TestBuildRuntimeRoutingRequest:
    """Tests for build_runtime_routing_request function."""

    def test_build_routing_request_minimal(self):
        """Test building routing request with minimal session data."""
        session = MagicMock(
            metadata={},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request is not None
        assert request.workflow_phase == WorkflowPhase.generation
        assert request.task_kind == TaskKind.narrative_formulation
        assert request.requires_structured_output is True
        assert request.latency_budget == LatencyBudget.normal
        assert request.cost_sensitivity == CostSensitivity.medium
        assert request.escalation_hints == []

    def test_build_routing_request_with_task_kind(self):
        """Test that task_kind is parsed from metadata."""
        session = MagicMock(
            metadata={"routing_task_kind": "narrative_formulation"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request.task_kind == TaskKind.narrative_formulation

    def test_build_routing_request_invalid_task_kind_fallback(self):
        """Test that invalid task_kind falls back to default."""
        session = MagicMock(
            metadata={"routing_task_kind": "invalid_task"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        # Should fall back to narrative_formulation
        assert request.task_kind == TaskKind.narrative_formulation

    def test_build_routing_request_with_latency_budget(self):
        """Test that latency_budget is parsed from metadata."""
        session = MagicMock(
            metadata={"routing_latency_budget": "strict"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request.latency_budget == LatencyBudget.strict

    def test_build_routing_request_invalid_latency_budget_fallback(self):
        """Test that invalid latency_budget falls back to default."""
        session = MagicMock(
            metadata={"routing_latency_budget": "invalid_latency"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request.latency_budget == LatencyBudget.normal

    def test_build_routing_request_with_cost_sensitivity(self):
        """Test that cost_sensitivity is parsed from metadata."""
        session = MagicMock(
            metadata={"routing_cost_sensitivity": "high"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request.cost_sensitivity == CostSensitivity.high

    def test_build_routing_request_invalid_cost_sensitivity_fallback(self):
        """Test that invalid cost_sensitivity falls back to default."""
        session = MagicMock(
            metadata={"routing_cost_sensitivity": "invalid_cost"},
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        assert request.cost_sensitivity == CostSensitivity.medium

    def test_build_routing_request_with_fallback_marker(self):
        """Test escalation hint added for FALLBACK_ACTIVE marker."""
        session = MagicMock(
            metadata={},
            degraded_state=MagicMock(
                active_markers=[DegradedMarker.FALLBACK_ACTIVE]
            ),
        )

        request = build_runtime_routing_request(session)

        assert EscalationHint.continuity_risk in request.escalation_hints

    def test_build_routing_request_with_retry_exhausted_marker(self):
        """Test escalation hint added for RETRY_EXHAUSTED marker."""
        session = MagicMock(
            metadata={},
            degraded_state=MagicMock(
                active_markers=[DegradedMarker.RETRY_EXHAUSTED]
            ),
        )

        request = build_runtime_routing_request(session)

        assert EscalationHint.continuity_risk in request.escalation_hints

    def test_build_routing_request_with_multiple_markers(self):
        """Test escalation hint with multiple degradation markers."""
        session = MagicMock(
            metadata={},
            degraded_state=MagicMock(
                active_markers=[
                    DegradedMarker.FALLBACK_ACTIVE,
                    DegradedMarker.RETRY_EXHAUSTED,
                ]
            ),
        )

        request = build_runtime_routing_request(session)

        # Should have continuity_risk hint
        assert EscalationHint.continuity_risk in request.escalation_hints

    def test_build_routing_request_non_dict_metadata(self):
        """Test handling when metadata is not a dict."""
        session = MagicMock(
            metadata="not a dict",
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        # Should use defaults
        assert request.task_kind == TaskKind.narrative_formulation
        assert request.latency_budget == LatencyBudget.normal
        assert request.cost_sensitivity == CostSensitivity.medium

    def test_build_routing_request_non_string_metadata_values(self):
        """Test handling when metadata values are not strings."""
        session = MagicMock(
            metadata={
                "routing_task_kind": 123,  # Not a string
                "routing_latency_budget": {"key": "value"},  # Not a string
                "routing_cost_sensitivity": None,  # Not a string
            },
            degraded_state=MagicMock(active_markers=[]),
        )

        request = build_runtime_routing_request(session)

        # Should use defaults for all
        assert request.task_kind == TaskKind.narrative_formulation
        assert request.latency_budget == LatencyBudget.normal
        assert request.cost_sensitivity == CostSensitivity.medium

    def test_build_routing_request_all_metadata_options(self):
        """Test building request with all metadata options configured."""
        session = MagicMock(
            metadata={
                "routing_task_kind": "narrative_formulation",
                "routing_latency_budget": "relaxed",
                "routing_cost_sensitivity": "low",
            },
            degraded_state=MagicMock(
                active_markers=[DegradedMarker.FALLBACK_ACTIVE]
            ),
        )

        request = build_runtime_routing_request(session)

        assert request.task_kind == TaskKind.narrative_formulation
        assert request.latency_budget == LatencyBudget.relaxed
        assert request.cost_sensitivity == CostSensitivity.low
        assert EscalationHint.continuity_risk in request.escalation_hints


class TestBuildModelRoutingTraceDict:
    """Tests for build_model_routing_trace_dict function."""

    @pytest.fixture
    def mock_components(self):
        """Create mock routing components."""
        return {
            "routing_request": MagicMock(
                model_dump=MagicMock(return_value={"request": "data"})
            ),
            "routing_decision": MagicMock(
                selected_adapter_name="adapter_a",
                selected_model="gpt-4",
                escalation_applied=False,
                degradation_applied=False,
                model_dump=MagicMock(return_value={"decision": "data"}),
            ),
            "passed_adapter": MagicMock(adapter_name="passed_adapter"),
            "execution_adapter": MagicMock(adapter_name="execution_adapter"),
        }

    def test_build_trace_dict_resolved_via_get_adapter(self, mock_components):
        """Test trace dict when resolved via get_adapter."""
        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            trace = build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            assert trace["routing_invoked"] is True
            assert trace["resolved_via_get_adapter"] is True
            assert trace["fallback_to_passed_adapter"] is False
            assert trace["passed_adapter_name"] == "passed_adapter"
            assert trace["executed_adapter_name"] == "execution_adapter"
            assert trace["selected_adapter_name"] == "adapter_a"
            assert trace["selected_model"] == "gpt-4"

    def test_build_trace_dict_fallback_to_passed_adapter(self, mock_components):
        """Test trace dict when falling back to passed adapter."""
        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            trace = build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=False,
            )

            assert trace["resolved_via_get_adapter"] is False
            assert trace["fallback_to_passed_adapter"] is True

    def test_build_trace_dict_with_escalation(self, mock_components):
        """Test trace dict when escalation was applied."""
        mock_components["routing_decision"].escalation_applied = True

        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            trace = build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            assert trace["escalation_applied"] is True

    def test_build_trace_dict_with_degradation(self, mock_components):
        """Test trace dict when degradation was applied."""
        mock_components["routing_decision"].degradation_applied = True

        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            trace = build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            assert trace["degradation_applied"] is True

    def test_build_trace_dict_model_dump_called(self, mock_components):
        """Test that model_dump is called with json mode."""
        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {}

            build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            mock_components["routing_request"].model_dump.assert_called_once_with(
                mode="json"
            )
            mock_components["routing_decision"].model_dump.assert_called_once_with(
                mode="json"
            )

    def test_build_trace_dict_evidence_building(self, mock_components):
        """Test that routing evidence is built with correct parameters."""
        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            # Verify build_routing_evidence was called with correct arguments
            mock_evidence.assert_called_once()
            call_kwargs = mock_evidence.call_args[1]
            assert call_kwargs["routing_request"] == mock_components["routing_request"]
            assert (
                call_kwargs["routing_decision"]
                == mock_components["routing_decision"]
            )
            assert call_kwargs["executed_adapter_name"] == "execution_adapter"
            assert call_kwargs["passed_adapter_name"] == "passed_adapter"
            assert call_kwargs["resolved_via_get_adapter"] is True
            assert call_kwargs["fallback_to_passed_adapter"] is False

    def test_build_trace_dict_contains_all_keys(self, mock_components):
        """Test that trace dict contains all required keys."""
        with patch(
            "app.runtime.routing.model_routing_evidence.build_routing_evidence"
        ) as mock_evidence:
            mock_evidence.return_value = {"evidence": "data"}

            trace = build_model_routing_trace_dict(
                routing_request=mock_components["routing_request"],
                routing_decision=mock_components["routing_decision"],
                passed_adapter=mock_components["passed_adapter"],
                execution_adapter=mock_components["execution_adapter"],
                resolved_via_get_adapter=True,
            )

            required_keys = {
                "routing_invoked",
                "request",
                "decision",
                "passed_adapter_name",
                "executed_adapter_name",
                "selected_adapter_name",
                "selected_model",
                "resolved_via_get_adapter",
                "fallback_to_passed_adapter",
                "escalation_applied",
                "degradation_applied",
                "routing_evidence",
            }
            assert all(key in trace for key in required_keys)
