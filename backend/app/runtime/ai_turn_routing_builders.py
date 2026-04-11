"""Build routing requests and model-routing trace payloads for AI turns."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import StoryAIAdapter
from app.runtime.model_routing_contracts import (
    CostSensitivity,
    EscalationHint,
    LatencyBudget,
    RoutingDecision,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.runtime_models import DegradedMarker, SessionState


def build_runtime_routing_request(session: SessionState) -> RoutingRequest:
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    task_kind = TaskKind.narrative_formulation
    raw_tk = meta.get("routing_task_kind")
    if isinstance(raw_tk, str):
        try:
            task_kind = TaskKind(raw_tk)
        except ValueError:
            pass
    hints: list[EscalationHint] = []
    markers = session.degraded_state.active_markers
    if DegradedMarker.FALLBACK_ACTIVE in markers or DegradedMarker.RETRY_EXHAUSTED in markers:
        hints.append(EscalationHint.continuity_risk)
    latency_budget = LatencyBudget.normal
    cost_sensitivity = CostSensitivity.medium
    lb = meta.get("routing_latency_budget")
    if isinstance(lb, str):
        try:
            latency_budget = LatencyBudget(lb)
        except ValueError:
            pass
    cs = meta.get("routing_cost_sensitivity")
    if isinstance(cs, str):
        try:
            cost_sensitivity = CostSensitivity(cs)
        except ValueError:
            pass
    return RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=task_kind,
        requires_structured_output=True,
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        escalation_hints=hints,
    )


def build_model_routing_trace_dict(
    *,
    routing_request: RoutingRequest,
    routing_decision: RoutingDecision,
    passed_adapter: StoryAIAdapter,
    execution_adapter: StoryAIAdapter,
    resolved_via_get_adapter: bool,
) -> dict[str, Any]:
    from app.runtime.model_routing_evidence import build_routing_evidence

    return {
        "routing_invoked": True,
        "request": routing_request.model_dump(mode="json"),
        "decision": routing_decision.model_dump(mode="json"),
        "passed_adapter_name": passed_adapter.adapter_name,
        "executed_adapter_name": execution_adapter.adapter_name,
        "selected_adapter_name": routing_decision.selected_adapter_name,
        "selected_model": routing_decision.selected_model,
        "resolved_via_get_adapter": resolved_via_get_adapter,
        "fallback_to_passed_adapter": not resolved_via_get_adapter,
        "escalation_applied": routing_decision.escalation_applied,
        "degradation_applied": routing_decision.degradation_applied,
        "routing_evidence": build_routing_evidence(
            routing_request=routing_request,
            routing_decision=routing_decision,
            executed_adapter_name=execution_adapter.adapter_name,
            passed_adapter_name=passed_adapter.adapter_name,
            resolved_via_get_adapter=resolved_via_get_adapter,
            fallback_to_passed_adapter=not resolved_via_get_adapter,
            bounded_model_call=None,
            skip_reason=None,
        ),
    }
