"""Routing / staged orchestration / operator-audit enrichment for ``execute_turn_with_ai``."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from app.runtime.adapter_registry import get_adapter, iter_model_specs
from app.runtime.ai_adapter import AdapterRequest, StoryAIAdapter
from app.runtime.ai_turn_routing_builders import (
    build_model_routing_trace_dict,
    build_runtime_routing_request,
)
from app.runtime.area2_operator_truth import (
    enrich_operator_audit_with_area2_truth,
    resolve_routing_bootstrap_enabled,
)
from app.runtime.area2_routing_authority import AUTHORITY_SOURCE_RUNTIME
from app.runtime.model_routing import route_model
from app.runtime.operator_audit import build_runtime_operator_audit
from app.runtime.runtime_ai_stages import StagedGenerationResult, run_runtime_staged_generation
from app.runtime.runtime_models import SessionState


@dataclass
class ExecutionAdapterResolution:
    """State after Phase 4a (adapter + traces + optional staged holder)."""

    execution_adapter: StoryAIAdapter
    model_routing_trace: dict[str, Any]
    runtime_stage_traces_for_log: list[dict[str, Any]] | None
    runtime_orchestration_summary_for_log: dict[str, Any] | None
    staged_result_holder: StagedGenerationResult | None


def resolve_execution_adapter_and_traces(
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    orchestration_enabled: bool,
    staged_enabled: bool,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    mark_retry_context_fn: Callable[[], None] | None,
) -> ExecutionAdapterResolution:
    if orchestration_enabled:
        routing_request = build_runtime_routing_request(session)
        routing_decision = route_model(routing_request)
        resolved_from_registry = None
        if routing_decision.selected_adapter_name:
            resolved_from_registry = get_adapter(routing_decision.selected_adapter_name)
        execution_adapter = resolved_from_registry if resolved_from_registry is not None else passed_adapter
        model_routing_trace = build_model_routing_trace_dict(
            routing_request=routing_request,
            routing_decision=routing_decision,
            passed_adapter=passed_adapter,
            execution_adapter=execution_adapter,
            resolved_via_get_adapter=resolved_from_registry is not None,
        )
        if isinstance(session.metadata, dict):
            session.metadata["last_model_routing_trace"] = model_routing_trace
        return ExecutionAdapterResolution(
            execution_adapter=execution_adapter,
            model_routing_trace=model_routing_trace,
            runtime_stage_traces_for_log=[],
            runtime_orchestration_summary_for_log={
                "staged_pipeline_preempted": "agent_orchestration",
                "reason": "supervisor_orchestrator_handles_full_turn_no_runtime_stages",
            },
            staged_result_holder=None,
        )
    if staged_enabled:
        staged_result_holder = run_runtime_staged_generation(
            session=session,
            passed_adapter=passed_adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=build_adapter_request_fn,
            enrich_request_fn=enrich_request_fn,
            mark_retry_context_fn=mark_retry_context_fn,
        )
        model_routing_trace = staged_result_holder.model_routing_trace
        runtime_stage_traces_for_log = staged_result_holder.runtime_stage_traces
        runtime_orchestration_summary_for_log = staged_result_holder.runtime_orchestration_summary
        execution_adapter = staged_result_holder.final_execution_adapter or passed_adapter
        if isinstance(session.metadata, dict):
            session.metadata["last_model_routing_trace"] = model_routing_trace
        return ExecutionAdapterResolution(
            execution_adapter=execution_adapter,
            model_routing_trace=model_routing_trace,
            runtime_stage_traces_for_log=runtime_stage_traces_for_log,
            runtime_orchestration_summary_for_log=runtime_orchestration_summary_for_log,
            staged_result_holder=staged_result_holder,
        )
    routing_request = build_runtime_routing_request(session)
    routing_decision = route_model(routing_request)
    resolved_from_registry = None
    if routing_decision.selected_adapter_name:
        resolved_from_registry = get_adapter(routing_decision.selected_adapter_name)
    execution_adapter = resolved_from_registry if resolved_from_registry is not None else passed_adapter
    model_routing_trace = build_model_routing_trace_dict(
        routing_request=routing_request,
        routing_decision=routing_decision,
        passed_adapter=passed_adapter,
        execution_adapter=execution_adapter,
        resolved_via_get_adapter=resolved_from_registry is not None,
    )
    if isinstance(session.metadata, dict):
        session.metadata["last_model_routing_trace"] = model_routing_trace
    return ExecutionAdapterResolution(
        execution_adapter=execution_adapter,
        model_routing_trace=model_routing_trace,
        runtime_stage_traces_for_log=None,
        runtime_orchestration_summary_for_log=None,
        staged_result_holder=None,
    )


def build_operator_audit_for_turn(
    *,
    resolution: ExecutionAdapterResolution,
) -> dict[str, Any] | None:
    holder = resolution.staged_result_holder
    if holder is not None and holder.operator_audit:
        operator_audit_for_log = holder.operator_audit
    else:
        operator_audit_for_log = build_runtime_operator_audit(
            runtime_stage_traces=resolution.runtime_stage_traces_for_log,
            runtime_orchestration_summary=resolution.runtime_orchestration_summary_for_log,
            model_routing_trace=resolution.model_routing_trace,
        )
    if isinstance(operator_audit_for_log, dict):
        _specs_rt = list(iter_model_specs())
        enrich_operator_audit_with_area2_truth(
            operator_audit_for_log,
            surface="runtime",
            authority_source=AUTHORITY_SOURCE_RUNTIME,
            bootstrap_enabled=resolve_routing_bootstrap_enabled(),
            registry_model_spec_count=len(_specs_rt),
            specs_for_coverage=_specs_rt,
            runtime_stage_traces=resolution.runtime_stage_traces_for_log,
            model_routing_trace=resolution.model_routing_trace,
            runtime_orchestration_summary=resolution.runtime_orchestration_summary_for_log,
        )
    return operator_audit_for_log
