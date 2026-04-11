"""Task 3: operator audit layer — deterministic builders from existing evidence only."""

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
from app.runtime.operator_audit import (
    AUDIT_SCHEMA_VERSION,
    build_audit_timeline_entry,
    build_bounded_surface_operator_audit,
    build_runtime_operator_audit,
    runtime_additive_orchestration_fields,
)


def _minimal_req_dec(adapter: str = "a1") -> tuple[RoutingRequest, RoutingDecision]:
    req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        complexity=Complexity.medium,
        latency_budget=LatencyBudget.normal,
    )
    dec = RoutingDecision(
        selected_adapter_name=adapter,
        selected_provider="p",
        selected_model="m",
        phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        route_reason_code=RouteReasonCode.role_matrix_primary,
    )
    return req, dec


def test_runtime_additive_fields_separate_packaging_from_no_adapter_skip():
    traces = [
        {
            "stage_id": "preflight",
            "stage_kind": "routed_model_stage",
            "bounded_model_call": False,
            "skip_reason": "no_eligible_adapter_for_preflight_stage",
            "routing_evidence": {},
        },
        {
            "stage_id": "packaging",
            "stage_kind": "packaging",
            "bounded_model_call": False,
            "skip_reason": None,
            "routing_evidence": {},
        },
    ]
    add = runtime_additive_orchestration_fields(traces)
    assert add["stages_skipped_no_eligible_adapter"] == ["preflight"]
    assert add["stages_without_bounded_model_call_by_design"] == ["packaging"]


def test_runtime_operator_audit_timeline_order_is_stable():
    req, dec = _minimal_req_dec()
    ev = build_routing_evidence(routing_request=req, routing_decision=dec, executed_adapter_name="a1")
    traces = [
        {
            "stage_id": "preflight",
            "stage_kind": "routed_model_stage",
            "bounded_model_call": True,
            "skip_reason": None,
            "routing_evidence": ev,
            "errors": [],
        },
        {
            "stage_id": "packaging",
            "stage_kind": "packaging",
            "bounded_model_call": False,
            "skip_reason": None,
            "routing_evidence": {},
            "errors": [],
        },
    ]
    summary = {
        "final_path": "slm_only",
        "synthesis_skipped": True,
        "synthesis_skip_reason": "slm_sufficient",
        "synthesis_gate_reason": "slm_sufficient",
    }
    rollup = {"routing_evidence": ev}
    audit = build_runtime_operator_audit(
        runtime_stage_traces=traces,
        runtime_orchestration_summary=summary,
        model_routing_trace=rollup,
    )
    assert audit["audit_schema_version"] == AUDIT_SCHEMA_VERSION
    assert len(audit["audit_timeline"]) == 2
    assert audit["audit_timeline"][0]["ordinal"] == 0
    assert audit["audit_timeline"][1]["stage_key"] == "packaging"
    assert audit["audit_timeline"][1]["stage_kind"] == "packaging"
    assert audit["audit_summary"]["synthesis_gate_reason"] == "slm_sufficient"


def test_bounded_surface_audit_adds_stage_id_alias():
    req, dec = _minimal_req_dec("slm")
    ev = build_routing_evidence(routing_request=req, routing_decision=dec, executed_adapter_name="slm")
    routing = {
        "preflight": {
            "stage": "preflight",
            "bounded_model_call": True,
            "routing_evidence": ev,
            "decision": dec.model_dump(mode="json"),
        },
        "synthesis": {
            "stage": "synthesis",
            "bounded_model_call": False,
            "skip_reason": "no_eligible_adapter_or_missing_provider_adapter",
            "routing_evidence": build_routing_evidence(
                routing_request=RoutingRequest(
                    workflow_phase=WorkflowPhase.generation,
                    task_kind=TaskKind.narrative_formulation,
                    complexity=Complexity.medium,
                    latency_budget=LatencyBudget.normal,
                ),
                routing_decision=RoutingDecision(
                    selected_adapter_name="",
                    selected_provider="",
                    selected_model="",
                    phase=WorkflowPhase.generation,
                    task_kind=TaskKind.narrative_formulation,
                    route_reason_code=RouteReasonCode.no_eligible_adapter,
                ),
                bounded_model_call=False,
                skip_reason="no_eligible_adapter_or_missing_provider_adapter",
            ),
            "decision": {},
        },
    }
    audit = build_bounded_surface_operator_audit(surface="improvement", task_2a_routing=routing)
    assert routing["preflight"].get("stage_id") == "preflight"
    assert audit["audit_summary"]["surface"] == "improvement"
    assert len(audit["audit_timeline"]) == 2


def test_build_audit_timeline_entry_legacy_shape():
    entry = build_audit_timeline_entry(
        0,
        {
            "stage_id": "legacy_single_route",
            "stage_kind": "legacy_single_route",
            "routing_evidence": {},
            "errors": [],
        },
    )
    assert entry["ordinal"] == 0
    assert entry["stage_key"] == "legacy_single_route"
