"""Runtime drift resistance for audit and routing-evidence shapes (G-DRIFT-01)."""

from __future__ import annotations

from app.runtime.model_routing_contracts import (
    Complexity,
    LatencyBudget,
    RouteReasonCode,
    RoutingDecision,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import build_routing_evidence
from app.runtime.operator_audit import AUDIT_SCHEMA_VERSION, build_runtime_operator_audit


def test_audit_schema_version_is_stable_string():
    assert AUDIT_SCHEMA_VERSION == "1"


ROUTING_EVIDENCE_STABLE_KEYS = frozenset(
    {
        "route_reason_code",
        "requested_workflow_phase",
        "requested_task_kind",
        "routing_overview",
        "diagnostics_overview",
        "diagnostics_flags",
        "diagnostics_causes",
        "policy_execution_aligned",
        "execution_deviation",
        "no_eligible_spec_selection",
    }
)


def test_build_routing_evidence_emits_stable_key_superset_for_role_matrix_primary():
    req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        complexity=Complexity.medium,
        latency_budget=LatencyBudget.normal,
    )
    dec = RoutingDecision(
        selected_adapter_name="mock",
        selected_provider="mock",
        selected_model="m",
        phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        route_reason_code=RouteReasonCode.role_matrix_primary,
    )
    ev = build_routing_evidence(routing_request=req, routing_decision=dec, executed_adapter_name="mock")
    missing = ROUTING_EVIDENCE_STABLE_KEYS - set(ev.keys())
    assert not missing, f"Unexpected routing_evidence drift: missing {missing}"


def test_runtime_operator_audit_empty_traces_still_emits_stable_top_level_keys():
    rollup = {"routing_evidence": {}}
    audit = build_runtime_operator_audit(
        runtime_stage_traces=[],
        runtime_orchestration_summary=None,
        model_routing_trace=rollup,
    )
    assert audit["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    assert frozenset(audit.keys()) >= {
        "audit_schema_version",
        "audit_summary",
        "audit_timeline",
        "audit_deviations",
        "audit_flags",
        "audit_review_fingerprint",
    }
