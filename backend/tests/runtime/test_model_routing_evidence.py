"""Task 2C-2 / Task 2D / Task 2F: shared routing_evidence helper."""

from app.runtime.model_routing_contracts import (
    RouteReasonCode,
    RoutingDecision,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import build_routing_evidence, routing_overview_for_reason_code


def _assert_task2f_diagnostics_shape(ev: dict) -> None:
    assert "diagnostics_overview" in ev
    do = ev["diagnostics_overview"]
    for k in ("title", "summary", "severity", "operator_hint", "short_explanation"):
        assert k in do
    assert "diagnostics_flags" in ev
    df = ev["diagnostics_flags"]
    for k in (
        "escalation_applied",
        "degradation_applied",
        "no_eligible_spec_selection",
        "policy_execution_aligned",
        "fallback_to_passed_adapter",
        "bounded_model_call",
        "has_execution_deviation",
    ):
        assert k in df
    assert "diagnostics_causes" in ev
    assert isinstance(ev["diagnostics_causes"], list)


def test_build_routing_evidence_marks_no_eligible_when_code_says_so():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    dec = RoutingDecision(
        selected_adapter_name="",
        selected_provider="",
        selected_model="",
        phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        route_reason_code=RouteReasonCode.no_eligible_adapter,
    )
    ev = build_routing_evidence(
        routing_request=req,
        routing_decision=dec,
        executed_adapter_name="passed_only",
        passed_adapter_name="passed_only",
        resolved_via_get_adapter=False,
        fallback_to_passed_adapter=True,
        bounded_model_call=None,
        skip_reason=None,
    )
    assert ev["no_eligible_spec_selection"] is True
    assert ev["fallback_to_passed_adapter"] is True
    assert ev["route_reason_code"] == "no_eligible_adapter"
    ro = ev["routing_overview"]
    assert ro["title"] == "No eligible spec"
    assert ro["severity"] == "failed_selection"
    assert ev["policy_execution_aligned"] is None
    assert ev["execution_deviation"] is None
    _assert_task2f_diagnostics_shape(ev)
    do = ev["diagnostics_overview"]
    assert do["summary"] == "No eligible spec"
    assert do["severity"] == "failed_selection"
    assert do["operator_hint"] == "Review model registration"
    assert do["short_explanation"] == ro["summary"]
    assert ev["diagnostics_flags"]["has_execution_deviation"] is False
    assert any(c.get("code") == "no_eligible_spec" for c in ev["diagnostics_causes"])


def test_policy_execution_aligned_true_when_registry_resolved():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    dec = RoutingDecision(
        selected_adapter_name="routed",
        selected_provider="p",
        selected_model="m",
        phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        route_reason_code=RouteReasonCode.role_matrix_primary,
    )
    ev = build_routing_evidence(
        routing_request=req,
        routing_decision=dec,
        executed_adapter_name="routed",
        resolved_via_get_adapter=True,
        fallback_to_passed_adapter=False,
    )
    assert ev["policy_execution_aligned"] is True
    assert ev["execution_deviation"] is None
    assert ev["routing_overview"]["title"] == "Primary role match"
    assert ev["routing_overview"]["severity"] == "normal"
    _assert_task2f_diagnostics_shape(ev)
    assert ev["diagnostics_overview"]["summary"] == "Primary route"
    assert ev["diagnostics_overview"]["operator_hint"] == ""
    assert ev["diagnostics_flags"]["policy_execution_aligned"] is True
    assert ev["diagnostics_flags"]["has_execution_deviation"] is False


def test_routing_overview_matches_escalation_reason_codes():
    for code, title, severity in (
        ("escalation_due_to_structured_output_gap", "Escalated for structure", "elevated"),
        ("escalation_due_to_explicit_hint", "Escalated for risk", "elevated"),
        ("escalation_due_to_high_stakes_task", "Escalated for risk", "elevated"),
        ("escalation_due_to_complexity", "Escalated for quality", "elevated"),
        ("fallback_only", "Fallback route", "degraded"),
        ("latency_constraint", "Constrained by latency", "normal"),
        ("cost_constraint", "Constrained by cost", "normal"),
    ):
        ov = routing_overview_for_reason_code(code, no_eligible_spec_selection=False)
        assert ov["title"] == title, code
        assert ov["severity"] == severity, code


def test_diagnostics_overview_summary_vocabulary_matches_route_codes():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    for code, expected_summary in (
        (RouteReasonCode.role_matrix_primary, "Primary route"),
        (RouteReasonCode.fallback_only, "Fallback route"),
        (RouteReasonCode.escalation_due_to_explicit_hint, "Escalated route"),
    ):
        dec = RoutingDecision(
            selected_adapter_name="a",
            selected_provider="p",
            selected_model="m",
            phase=WorkflowPhase.generation,
            task_kind=TaskKind.narrative_formulation,
            route_reason_code=code,
        )
        ev = build_routing_evidence(routing_request=req, routing_decision=dec, executed_adapter_name="a")
        assert ev["diagnostics_overview"]["summary"] == expected_summary


def test_diagnostics_deterministic_twice():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    dec = RoutingDecision(
        selected_adapter_name="x",
        selected_provider="p",
        selected_model="m",
        phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        route_reason_code=RouteReasonCode.cost_constraint,
    )
    kw = dict(
        routing_request=req,
        routing_decision=dec,
        executed_adapter_name="x",
    )
    ev1 = build_routing_evidence(**kw)
    ev2 = build_routing_evidence(**kw)
    assert ev1["diagnostics_overview"] == ev2["diagnostics_overview"]
    assert ev1["diagnostics_flags"] == ev2["diagnostics_flags"]
    assert ev1["diagnostics_causes"] == ev2["diagnostics_causes"]


def test_bounded_skip_adds_cause_and_registration_hint():
    req = RoutingRequest(workflow_phase=WorkflowPhase.preflight, task_kind=TaskKind.cheap_preflight)
    dec = RoutingDecision(
        selected_adapter_name="a",
        selected_provider="p",
        selected_model="m",
        phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        route_reason_code=RouteReasonCode.role_matrix_primary,
    )
    ev = build_routing_evidence(
        routing_request=req,
        routing_decision=dec,
        bounded_model_call=False,
        skip_reason="no_eligible_adapter_or_missing_provider_adapter",
    )
    assert ev["diagnostics_overview"]["operator_hint"] == "Review model registration"
    assert any(c.get("code") == "bounded_call_skipped" for c in ev["diagnostics_causes"])


def test_degraded_primary_route_summary_and_widening_hint():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    dec = RoutingDecision(
        selected_adapter_name="a",
        selected_provider="p",
        selected_model="m",
        phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        route_reason_code=RouteReasonCode.role_matrix_primary,
        decision_factors={"preferred_pool_widened": True},
        degradation_applied=True,
    )
    ev = build_routing_evidence(routing_request=req, routing_decision=dec, executed_adapter_name="a")
    assert ev["diagnostics_overview"]["summary"] == "Degraded route"
    assert ev["diagnostics_overview"]["operator_hint"] == "Selection degraded due to fallback widening"
    assert any(c.get("code") == "preferred_pool_widened" for c in ev["diagnostics_causes"])


def test_execution_deviation_when_selected_differs_from_executed():
    req = RoutingRequest(workflow_phase=WorkflowPhase.generation, task_kind=TaskKind.narrative_formulation)
    dec = RoutingDecision(
        selected_adapter_name="openai",
        selected_provider="openai",
        selected_model="gpt",
        phase=WorkflowPhase.generation,
        task_kind=TaskKind.narrative_formulation,
        route_reason_code=RouteReasonCode.fallback_only,
    )
    ev = build_routing_evidence(
        routing_request=req,
        routing_decision=dec,
        executed_adapter_name="mock",
        execution_deviation_note="primary_failed_or_unavailable",
    )
    assert ev["policy_execution_aligned"] is False
    assert ev["routing_overview"]["title"] == "Fallback route"
    dev = ev["execution_deviation"]
    assert dev is not None
    assert dev["selected_adapter_name"] == "openai"
    assert dev["executed_adapter_name"] == "mock"
    assert dev["note"] == "primary_failed_or_unavailable"
    _assert_task2f_diagnostics_shape(ev)
    do = ev["diagnostics_overview"]
    assert do["summary"] == "Execution deviation"
    assert do["title"] == "Execution differed from policy selection"
    assert do["severity"] == "degraded"
    assert "openai" in do["short_explanation"] and "mock" in do["short_explanation"]
    assert ev["diagnostics_flags"]["has_execution_deviation"] is True
    assert any(c.get("code") == "execution_deviation" for c in ev["diagnostics_causes"])


def test_stage_like_alignment_by_name_match():
    req = RoutingRequest(workflow_phase=WorkflowPhase.preflight, task_kind=TaskKind.cheap_preflight)
    dec = RoutingDecision(
        selected_adapter_name="MockLLM",
        selected_provider="mock",
        selected_model="m",
        phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        route_reason_code=RouteReasonCode.role_matrix_primary,
    )
    ev = build_routing_evidence(
        routing_request=req,
        routing_decision=dec,
        executed_adapter_name="mockllm",
    )
    assert ev["policy_execution_aligned"] is True

