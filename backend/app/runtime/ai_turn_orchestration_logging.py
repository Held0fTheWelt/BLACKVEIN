from __future__ import annotations

from typing import Any

from app.runtime.ai_decision_logging import pack_ai_turn_orchestration_attachments
from app.runtime.ai_turn_shared_types import _AiTurnOrchestrationLogBundle


def build_turn_orchestration_attachments(
    *,
    tool_loop_summary: dict[str, Any] | None,
    tool_call_transcript: list[dict[str, Any]],
    last_successful_tool_sequence: int | None,
    preview_diagnostics: dict[str, Any] | None,
    supervisor_plan: Any,
    subagent_invocations: Any,
    subagent_results: Any,
    merge_finalization: Any,
    orchestration_budget_summary: Any,
    orchestration_failover: Any,
    orchestration_cache: Any,
    tool_audit: Any,
    model_routing_trace: dict[str, Any] | None,
    runtime_stage_traces_for_log: list[dict[str, Any]] | None,
    runtime_orchestration_summary_for_log: dict[str, Any] | None,
    operator_audit_for_log: dict[str, Any] | None,
) -> dict[str, Any]:
    return pack_ai_turn_orchestration_attachments(
        tool_loop_summary=tool_loop_summary,
        tool_call_transcript=tool_call_transcript,
        last_successful_tool_sequence=last_successful_tool_sequence,
        preview_diagnostics=preview_diagnostics,
        supervisor_plan=supervisor_plan,
        subagent_invocations=subagent_invocations,
        subagent_results=subagent_results,
        merge_finalization=merge_finalization,
        orchestration_budget_summary=orchestration_budget_summary,
        orchestration_failover=orchestration_failover,
        orchestration_cache=orchestration_cache,
        tool_audit=tool_audit,
        model_routing_trace=model_routing_trace,
        runtime_stage_traces=runtime_stage_traces_for_log,
        runtime_orchestration_summary=runtime_orchestration_summary_for_log,
        operator_audit=operator_audit_for_log,
    )


def attachments_from_orchestration_bundle(
    bundle: _AiTurnOrchestrationLogBundle,
) -> dict[str, Any]:
    return build_turn_orchestration_attachments(
        tool_loop_summary=bundle.tool_loop_summary,
        tool_call_transcript=bundle.tool_call_transcript,
        last_successful_tool_sequence=bundle.last_successful_tool_sequence,
        preview_diagnostics=bundle.preview_diagnostics,
        supervisor_plan=bundle.supervisor_plan,
        subagent_invocations=bundle.subagent_invocations,
        subagent_results=bundle.subagent_results,
        merge_finalization=bundle.merge_finalization,
        orchestration_budget_summary=bundle.orchestration_budget_summary,
        orchestration_failover=bundle.orchestration_failover,
        orchestration_cache=bundle.orchestration_cache,
        tool_audit=bundle.tool_audit,
        model_routing_trace=bundle.model_routing_trace,
        runtime_stage_traces_for_log=bundle.runtime_stage_traces_for_log,
        runtime_orchestration_summary_for_log=bundle.runtime_orchestration_summary_for_log,
        operator_audit_for_log=bundle.operator_audit_for_log,
    )
