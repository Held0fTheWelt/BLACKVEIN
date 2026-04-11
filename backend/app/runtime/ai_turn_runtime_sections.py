from __future__ import annotations

from typing import Any, Callable

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_turn_primary_tool_loop import run_primary_tool_loop
from app.runtime.ai_turn_shared_types import (
    _AiTurnOrchestrationLogBundle,
    _FirstAdapterResponseOutcome,
    _RoutingAndGenerationBundle,
    _ToolLoopSectionOutcome,
)
from app.runtime.runtime_models import SessionState
from app.runtime.tool_loop import HostToolContext, ToolLoopPolicy, ToolLoopStopReason


def run_primary_tool_loop_section(
    *,
    tool_loop_enabled: bool,
    response: AdapterResponse,
    tool_loop_policy: ToolLoopPolicy,
    session: SessionState,
    module: ContentModule,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    generate_pair: Callable[[], tuple[AdapterResponse, int]],
    execution_controls: dict[str, Any],
    tool_call_transcript: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    tool_call_count: int,
    tool_loop_stop_reason: ToolLoopStopReason,
    tool_limit_hit: bool,
    finalized_after_tool_use: bool,
    last_successful_tool_sequence: int | None,
    preview_records: list[dict[str, Any]],
    tool_loop_summary_existing: dict[str, Any] | None,
) -> _ToolLoopSectionOutcome:
    if tool_loop_enabled and response and not response.error and response.raw_output.strip():
        tl_out = run_primary_tool_loop(
            initial_response=response,
            tool_loop_policy=tool_loop_policy,
            tool_context=HostToolContext(
                session=session,
                module=module,
                current_turn=current_turn,
                recent_events=recent_events or [],
            ),
            generate_pair=generate_pair,
        )
        response = tl_out.response
        tool_call_transcript = tl_out.tool_call_transcript
        tool_results = tl_out.tool_results
        tool_call_count = tl_out.tool_call_count
        tool_loop_stop_reason = tl_out.tool_loop_stop_reason
        tool_limit_hit = tl_out.tool_limit_hit
        finalized_after_tool_use = tl_out.finalized_after_tool_use
        last_successful_tool_sequence = tl_out.last_successful_tool_sequence
        preview_records.extend(tl_out.preview_records)

    tool_loop_summary = tool_loop_summary_existing
    if tool_loop_enabled:
        tool_loop_summary = {
            "enabled": True,
            "total_calls": tool_call_count,
            "stop_reason": tool_loop_stop_reason,
            "limit_hit": tool_limit_hit,
            "finalized_after_tool_use": finalized_after_tool_use,
            "execution_controls": execution_controls,
        }

    return _ToolLoopSectionOutcome(
        response=response,
        tool_call_transcript=tool_call_transcript,
        tool_results=tool_results,
        tool_call_count=tool_call_count,
        tool_loop_stop_reason=tool_loop_stop_reason,
        tool_limit_hit=tool_limit_hit,
        finalized_after_tool_use=finalized_after_tool_use,
        last_successful_tool_sequence=last_successful_tool_sequence,
        tool_loop_summary=tool_loop_summary,
    )


def build_orchestration_log_bundle(
    *,
    routing: _RoutingAndGenerationBundle,
    fa: _FirstAdapterResponseOutcome,
    tool_call_transcript: list[dict[str, Any]],
    last_successful_tool_sequence: int | None,
    tool_loop_summary: dict[str, Any] | None,
    preview_diagnostics: dict[str, Any] | None,
) -> _AiTurnOrchestrationLogBundle:
    return _AiTurnOrchestrationLogBundle(
        tool_loop_summary=tool_loop_summary,
        tool_call_transcript=tool_call_transcript,
        last_successful_tool_sequence=last_successful_tool_sequence,
        preview_diagnostics=preview_diagnostics,
        supervisor_plan=fa.supervisor_plan,
        subagent_invocations=fa.subagent_invocations,
        subagent_results=fa.subagent_results,
        merge_finalization=fa.merge_finalization,
        orchestration_budget_summary=fa.orchestration_budget_summary,
        orchestration_failover=fa.orchestration_failover,
        orchestration_cache=fa.orchestration_cache,
        tool_audit=fa.tool_audit,
        model_routing_trace=routing.model_routing_trace,
        runtime_stage_traces_for_log=routing.runtime_stage_traces_for_log,
        runtime_orchestration_summary_for_log=routing.runtime_orchestration_summary_for_log,
        operator_audit_for_log=routing.operator_audit_for_log,
    )
