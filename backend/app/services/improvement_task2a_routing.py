"""Phase 2C-1: Task 2A routing trace + bounded model excerpts for improvement packages."""

from __future__ import annotations

from typing import Any

from story_runtime_core.adapters import BaseModelAdapter, build_default_model_adapters

from app.runtime import model_routing
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    LatencyBudget,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import attach_stage_routing_evidence
from app.runtime.area2_operator_truth import (
    bounded_traces_from_task_2a_routing,
    enrich_operator_audit_with_area2_truth,
    resolve_routing_bootstrap_enabled,
)
from app.runtime.area2_routing_authority import AUTHORITY_SOURCE_IMPROVEMENT
from app.runtime.operator_audit import build_bounded_surface_operator_audit
from app.services.writers_room_model_routing import build_writers_room_model_route_specs

_MODEL_ASSISTED_DISCLAIMER = (
    "Advisory prose only: model-assisted text supplements the package and does not replace "
    "deterministic sandbox metrics, threshold-based recommendation labels, or human governance."
)


def _run_routed_bounded_call(
    *,
    stage: str,
    workflow_phase: WorkflowPhase,
    task_kind: TaskKind,
    routing_request: RoutingRequest,
    specs: list[AdapterModelSpec],
    adapters: dict[str, BaseModelAdapter],
    prompt: str,
    context_text: str,
    timeout_seconds: float,
) -> tuple[dict[str, Any], str]:
    """Return trace entry and content excerpt (non-empty only on successful model output)."""
    decision = model_routing.route_model(routing_request, specs=specs)
    trace: dict[str, Any] = {
        "stage": stage,
        "workflow_phase": workflow_phase.value,
        "task_kind": task_kind.value,
        "decision": decision.model_dump(mode="json"),
    }
    name = decision.selected_adapter_name or ""
    adapter = adapters.get(name) if name else None
    if not adapter or not name:
        trace["bounded_model_call"] = False
        trace["skip_reason"] = "no_eligible_adapter_or_missing_provider_adapter"
        attach_stage_routing_evidence(trace, routing_request)
        return trace, ""

    trace["bounded_model_call"] = True
    trace["adapter_key"] = name
    trace["executed_adapter_name"] = name
    excerpt = ""
    try:
        call = adapter.generate(
            prompt,
            timeout_seconds=timeout_seconds,
            retrieval_context=context_text or None,
        )
        trace["call_success"] = call.success
        if call.success and (call.content or "").strip():
            excerpt = (call.content or "").strip()[:500]
    except Exception as exc:  # noqa: BLE001 — bounded diagnostic; package still persists
        trace["call_error"] = str(exc)
    attach_stage_routing_evidence(trace, routing_request)
    return trace, excerpt


def enrich_improvement_package_with_task2a_routing(
    package_response: dict[str, Any],
    *,
    context_text: str,
    baseline_id: str,
    variant_id: str,
    adapters: dict[str, BaseModelAdapter] | None = None,
    specs: list[AdapterModelSpec] | None = None,
) -> None:
    """Mutate ``package_response`` with ``task_2a_routing`` and ``model_assisted_interpretation``.

    Does not read or write ``evaluation``.
    """
    ad = adapters if adapters is not None else build_default_model_adapters()
    sp = specs if specs is not None else build_writers_room_model_route_specs()

    base_for_synthesis = package_response.get("deterministic_recommendation_base")
    if base_for_synthesis is None or str(base_for_synthesis).strip() == "":
        base_for_synthesis = str(package_response.get("recommendation_summary") or "")

    preflight_req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
        latency_budget=LatencyBudget.strict,
    )
    pre_prompt = (
        f"Improvement evaluation preflight for baseline={baseline_id} variant={variant_id}. "
        "In one or two sentences, is the retrieved context likely sufficient to interpret "
        "this sandbox evaluation? (yes/no + brief reason).\n"
        f"Context excerpt:\n{(context_text or '')[:1800]}"
    )
    pre_trace, pre_excerpt = _run_routed_bounded_call(
        stage="preflight",
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        routing_request=preflight_req,
        specs=sp,
        adapters=ad,
        prompt=pre_prompt,
        context_text=context_text,
        timeout_seconds=5.0,
    )

    synthesis_req = RoutingRequest(
        workflow_phase=WorkflowPhase.revision,
        task_kind=TaskKind.revision_synthesis,
        requires_structured_output=False,
    )
    syn_prompt = (
        f"Improvement recommendation interpretation. Deterministic suggestion: {base_for_synthesis}. "
        "In 2–3 sentences, summarize what a human reviewer should focus on given the context excerpt.\n"
        f"Context excerpt:\n{(context_text or '')[:1800]}"
    )
    syn_trace, syn_excerpt = _run_routed_bounded_call(
        stage="synthesis",
        workflow_phase=WorkflowPhase.revision,
        task_kind=TaskKind.revision_synthesis,
        routing_request=synthesis_req,
        specs=sp,
        adapters=ad,
        prompt=syn_prompt,
        context_text=context_text,
        timeout_seconds=12.0,
    )

    package_response["task_2a_routing"] = {
        "preflight": pre_trace,
        "synthesis": syn_trace,
    }
    package_response["model_assisted_interpretation"] = {
        "disclaimer": _MODEL_ASSISTED_DISCLAIMER,
        "preflight_excerpt": pre_excerpt,
        "synthesis_excerpt": syn_excerpt,
    }
    det_base = package_response.get("deterministic_recommendation_base")
    package_response["operator_audit"] = build_bounded_surface_operator_audit(
        surface="improvement",
        task_2a_routing=package_response["task_2a_routing"],
        execution_hints={
            "deterministic_recommendation_base_present": bool(
                det_base is not None and str(det_base).strip() != ""
            ),
            "preflight_excerpt_nonempty": bool(pre_excerpt.strip()),
            "synthesis_excerpt_nonempty": bool(syn_excerpt.strip()),
        },
    )
    enrich_operator_audit_with_area2_truth(
        package_response["operator_audit"],
        surface="improvement",
        authority_source=AUTHORITY_SOURCE_IMPROVEMENT,
        bootstrap_enabled=resolve_routing_bootstrap_enabled(),
        registry_model_spec_count=len(sp),
        specs_for_coverage=list(sp),
        bounded_traces=bounded_traces_from_task_2a_routing(package_response["task_2a_routing"]),
    )
