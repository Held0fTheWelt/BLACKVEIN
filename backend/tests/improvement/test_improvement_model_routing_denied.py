"""Task 4: honest failure paths for Improvement bounded routing (G-NEG-02)."""

from __future__ import annotations

from app.runtime.model_routing_contracts import LatencyBudget, RoutingRequest, TaskKind, WorkflowPhase
from app.services.improvement_task2a_routing import _run_routed_bounded_call
from app.services.writers_room_model_routing import build_writers_room_model_route_specs


def test_run_routed_bounded_call_missing_provider_adapter_skips_with_skip_reason():
    """Route selects a name not present in adapters dict → bounded call skipped, evidence attached."""
    specs = build_writers_room_model_route_specs()
    req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
        latency_budget=LatencyBudget.strict,
    )
    trace, excerpt = _run_routed_bounded_call(
        stage="preflight",
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        routing_request=req,
        specs=specs,
        adapters={},
        prompt="test prompt",
        context_text="ctx",
        timeout_seconds=1.0,
    )
    assert trace.get("bounded_model_call") is False
    assert trace.get("skip_reason") == "no_eligible_adapter_or_missing_provider_adapter"
    assert excerpt == ""
    rev = trace.get("routing_evidence") or {}
    assert rev.get("route_reason_code")
    assert "no_eligible_spec_selection" in rev
