"""Writers Room generation stage — preflight routing and bounded adapter probe."""

from __future__ import annotations

from typing import Any

from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    LatencyBudget,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.model_routing_evidence import attach_stage_routing_evidence


def run_writers_room_generation_preflight(
    *,
    adapters: dict[str, Any],
    specs: list[AdapterModelSpec],
    module_id: str,
    retrieval_text: str,
    evidence_tag: str,
    lf_trace: Any = None,
) -> dict[str, Any]:
    """Route cheap preflight; optionally call selected adapter; attach routing evidence."""
    from app.observability.langfuse_adapter import get_langfuse_adapter

    lf_adapter = get_langfuse_adapter()

    preflight_req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.cheap_preflight,
        requires_structured_output=False,
        latency_budget=LatencyBudget.strict,
    )
    pre_decision = route_model(preflight_req, specs=specs)
    preflight_trace: dict[str, Any] = {
        "stage": "preflight",
        "workflow_phase": WorkflowPhase.preflight.value,
        "task_kind": TaskKind.cheap_preflight.value,
        "decision": pre_decision.model_dump(mode="json"),
    }
    pre_adapter = (
        adapters.get(pre_decision.selected_adapter_name)
        if pre_decision.selected_adapter_name
        else None
    )
    if pre_adapter and pre_decision.selected_adapter_name:
        pre_prompt = (
            f"Writers-Room retrieval preflight for module={module_id}. "
            f"In one or two sentences, is retrieved context likely sufficient for a canon review? "
            f"(yes/no + brief reason). evidence_tier={evidence_tag}.\n"
            f"Context excerpt:\n{(retrieval_text or '')[:1800]}"
        )
        try:
            pre_call = pre_adapter.generate(
                pre_prompt, timeout_seconds=5.0, retrieval_context=retrieval_text or None
            )
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_success"] = pre_call.success
            preflight_trace["content_excerpt"] = (pre_call.content or "").strip()[:500]

            # Record generation if Langfuse tracing is enabled
            if lf_trace:
                try:
                    lf_adapter.record_generation(
                        name="writers_room_preflight",
                        model=pre_decision.selected_adapter_name,
                        provider=pre_decision.selected_adapter_name,
                        prompt=pre_prompt[:2000],
                        completion=(pre_call.content or "")[:2000],
                        metadata={"evidence_tag": evidence_tag, "module_id": module_id},
                        trace=lf_trace,
                    )
                except Exception:
                    pass  # Langfuse errors never break the main flow
        except Exception as exc:  # noqa: BLE001 — bounded diagnostic; workflow continues
            preflight_trace["bounded_model_call"] = True
            preflight_trace["adapter_key"] = pre_decision.selected_adapter_name
            preflight_trace["call_error"] = str(exc)
    else:
        preflight_trace["bounded_model_call"] = False
        preflight_trace["skip_reason"] = "no_eligible_adapter_or_missing_provider_adapter"

    attach_stage_routing_evidence(preflight_trace, preflight_req)
    return preflight_trace
