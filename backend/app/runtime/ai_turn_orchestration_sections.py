from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_turn_generation import run_adapter_generation_with_retry
from app.runtime.ai_turn_orchestration_branch import (
    build_operator_audit_for_turn,
    resolve_execution_adapter_and_traces,
)
from app.runtime.ai_turn_shared_types import (
    _FirstAdapterResponseOutcome,
    _RoutingAndGenerationBundle,
    _SupervisorOrchestrationBranchOutcome,
)
from app.runtime.runtime_models import DegradedMarker, SessionState
from app.runtime.supervisor_orchestrator import SupervisorOrchestrator
from app.runtime.tool_loop import ToolLoopPolicy


def run_supervisor_orchestration_branch(
    *,
    execution_adapter: StoryAIAdapter,
    session: SessionState,
    module: ContentModule,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    build_request: Callable[[int], AdapterRequest],
    enrich_request: Callable[[AdapterRequest], None],
    execution_controls: dict[str, Any],
    tool_call_transcript: list[dict[str, Any]],
    preview_records: list[dict[str, Any]],
) -> _SupervisorOrchestrationBranchOutcome:
    base_request = build_request(attempt=1)
    enrich_request(base_request)
    orchestrator = SupervisorOrchestrator()
    orchestrated = orchestrator.orchestrate(
        base_request=base_request,
        adapter=execution_adapter,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events or [],
        tool_registry=None,
    )
    supervisor_tool_transcript = orchestrated.agent_tool_transcript
    if supervisor_tool_transcript:
        tool_call_transcript.extend(supervisor_tool_transcript)
        for entry in supervisor_tool_transcript:
            if entry.get("tool_name") != "wos.guard.preview_delta":
                continue
            preview_result = entry.get("preview_result_summary")
            if not isinstance(preview_result, dict):
                continue
            preview_records.append(
                {
                    "sequence_index": entry.get("sequence_index"),
                    "request_id": entry.get("preview_request_id"),
                    "requesting_agent_id": entry.get("agent_id"),
                    "request_summary": entry.get("sanitized_arguments") or {},
                    "result": preview_result,
                }
            )
    tool_loop_summary = {
        "enabled": False,
        "total_calls": 0,
        "stop_reason": "orchestration_enabled",
        "limit_hit": False,
        "finalized_after_tool_use": False,
        "execution_controls": execution_controls,
    }
    return _SupervisorOrchestrationBranchOutcome(
        response=orchestrated.final_response,
        current_attempt=1,
        supervisor_plan=orchestrated.plan,
        subagent_invocations=orchestrated.invocations,
        subagent_results=orchestrated.results,
        merge_finalization=orchestrated.merge_finalization,
        orchestration_budget_summary=orchestrated.budget_summary,
        orchestration_failover=orchestrated.failover_events,
        orchestration_cache=orchestrated.cache_summary,
        tool_audit=orchestrated.tool_audit,
        tool_loop_summary=tool_loop_summary,
    )


def make_adapter_request_pipeline(
    *,
    session: SessionState,
    module: ContentModule,
    current_turn: int,
    operator_input: str,
    recent_events: list[dict[str, Any]] | None,
    tool_loop_enabled: bool,
    tool_loop_policy: ToolLoopPolicy,
    tool_results: list[dict[str, Any]],
    tool_call_count_supplier: Callable[[], int],
    interpretation_logged: list[bool],
    build_adapter_request_fn: Callable[..., AdapterRequest],
) -> tuple[
    Callable[[int], AdapterRequest],
    Callable[[AdapterRequest], None],
    Callable[[], None],
]:
    mcp_enrichment_enabled = session.metadata.get("mcp_enrichment_enabled", False)

    def build_request(attempt: int) -> AdapterRequest:
        request = build_adapter_request_fn(
            session,
            module,
            operator_input=operator_input,
            recent_events=recent_events,
            attempt=attempt,
        )
        if not interpretation_logged[0] and request.input_interpretation is not None:
            interpretation_logged[0] = True
            log_key = "operator_input_interpretation_log"
            if log_key not in session.metadata:
                session.metadata[log_key] = []
            session.metadata[log_key].append(
                {
                    "turn_number": current_turn,
                    "envelope": request.input_interpretation.model_dump(mode="json"),
                }
            )
        if tool_loop_enabled:
            request.metadata["tool_loop"] = {
                "enabled": True,
                "sequence_index": tool_call_count_supplier() + 1,
                "max_tool_calls_per_turn": tool_loop_policy.max_tool_calls_per_turn,
                "tool_results": tool_results[-tool_loop_policy.max_tool_calls_per_turn :],
            }
        return request

    def enrich_request_with_mcp(request: AdapterRequest) -> None:
        if not mcp_enrichment_enabled:
            return
        from app.mcp_client.enrichment import build_mcp_enrichment
        from app.mcp_client.client import OperatorEndpointClient
        from app.observability.trace import get_trace_id

        _trace_id = get_trace_id()
        _client = session.metadata.get("_mcp_client_override") or OperatorEndpointClient()
        enrichment = build_mcp_enrichment(session.session_id, _trace_id, _client)
        request.metadata["mcp_context_enrichment"] = enrichment

    def mark_reduced_context_if_needed() -> None:
        if DegradedMarker.REDUCED_CONTEXT_ACTIVE not in session.degraded_state.active_markers:
            session.degraded_state.active_markers.add(DegradedMarker.REDUCED_CONTEXT_ACTIVE)
            session.degraded_state.marker_timestamps[DegradedMarker.REDUCED_CONTEXT_ACTIVE] = (
                datetime.now(timezone.utc)
            )
            if not session.degraded_state.is_degraded:
                session.degraded_state.is_degraded = True
                session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = (
                    datetime.now(timezone.utc)
                )

    return build_request, enrich_request_with_mcp, mark_reduced_context_if_needed


def build_routing_and_generation_bundle(
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    orchestration_enabled: bool,
    staged_enabled: bool,
    adapter_generate_timeout_ms: int,
    retry_policy: Any,
    build_request: Callable[[int], AdapterRequest],
    enrich_request: Callable[[AdapterRequest], None],
    mark_retry_context: Callable[[], None],
) -> _RoutingAndGenerationBundle:
    routing_res = resolve_execution_adapter_and_traces(
        session=session,
        passed_adapter=passed_adapter,
        orchestration_enabled=orchestration_enabled,
        staged_enabled=staged_enabled,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_request,
        enrich_request_fn=enrich_request,
        mark_retry_context_fn=mark_retry_context,
    )

    def generate_with_runtime_policy(
        *,
        starting_attempt: int = 1,
    ) -> tuple[AdapterResponse, int]:
        return run_adapter_generation_with_retry(
            execution_adapter=routing_res.execution_adapter,
            retry_policy=retry_policy,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_request=build_request,
            enrich_request=enrich_request,
            mark_reduced_context=mark_retry_context,
            starting_attempt=starting_attempt,
        )

    operator_audit_for_log = build_operator_audit_for_turn(resolution=routing_res)
    return _RoutingAndGenerationBundle(
        execution_adapter=routing_res.execution_adapter,
        model_routing_trace=routing_res.model_routing_trace,
        runtime_stage_traces_for_log=routing_res.runtime_stage_traces_for_log,
        runtime_orchestration_summary_for_log=routing_res.runtime_orchestration_summary_for_log,
        staged_result_holder=routing_res.staged_result_holder,
        operator_audit_for_log=operator_audit_for_log,
        generate_with_runtime_policy=generate_with_runtime_policy,
    )


def resolve_first_adapter_response(
    *,
    orchestration_enabled: bool,
    staged_enabled: bool,
    staged_result_holder: Any,
    execution_adapter: StoryAIAdapter,
    session: SessionState,
    module: ContentModule,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    build_request: Callable[[int], AdapterRequest],
    enrich_request: Callable[[AdapterRequest], None],
    execution_controls: dict[str, Any],
    tool_call_transcript: list[dict[str, Any]],
    preview_records: list[dict[str, Any]],
    generate_wp: Callable[..., tuple[AdapterResponse, int]],
) -> _FirstAdapterResponseOutcome:
    if orchestration_enabled:
        ob = run_supervisor_orchestration_branch(
            execution_adapter=execution_adapter,
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events,
            build_request=build_request,
            enrich_request=enrich_request,
            execution_controls=execution_controls,
            tool_call_transcript=tool_call_transcript,
            preview_records=preview_records,
        )
        return _FirstAdapterResponseOutcome(
            response=ob.response,
            current_attempt=ob.current_attempt,
            supervisor_plan=ob.supervisor_plan,
            subagent_invocations=ob.subagent_invocations,
            subagent_results=ob.subagent_results,
            merge_finalization=ob.merge_finalization,
            orchestration_budget_summary=ob.orchestration_budget_summary,
            orchestration_failover=ob.orchestration_failover,
            orchestration_cache=ob.orchestration_cache,
            tool_audit=ob.tool_audit,
            tool_loop_summary=ob.tool_loop_summary,
        )
    if staged_enabled and staged_result_holder is not None:
        response = staged_result_holder.response
        if staged_result_holder.synthesis_skipped:
            current_attempt = 1
        else:
            current_attempt = max(1, staged_result_holder.synthesis_attempt_count)
        return _FirstAdapterResponseOutcome(
            response=response,
            current_attempt=current_attempt,
            supervisor_plan=None,
            subagent_invocations=None,
            subagent_results=None,
            merge_finalization=None,
            orchestration_budget_summary=None,
            orchestration_failover=None,
            orchestration_cache=None,
            tool_audit=None,
            tool_loop_summary=None,
        )
    response, current_attempt = generate_wp(starting_attempt=1)
    return _FirstAdapterResponseOutcome(
        response=response,
        current_attempt=current_attempt,
        supervisor_plan=None,
        subagent_invocations=None,
        subagent_results=None,
        merge_finalization=None,
        orchestration_budget_summary=None,
        orchestration_failover=None,
        orchestration_cache=None,
        tool_audit=None,
        tool_loop_summary=None,
    )
