"""Erfolgs- und Fallback-Pfade für Supervisor-Finalizer nach Merge (DS-014)."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.runtime_models import (
    AgentInvocationRecord,
    AgentResultRecord,
    TokenUsageRecord,
)
from app.runtime.supervisor.supervisor_orchestrate_working_state import SupervisorOrchestrateWorkingState


def commit_supervisor_finalizer_success(
    *,
    state: SupervisorOrchestrateWorkingState,
    merge_record: Any,
    finalizer_agent: Any,
    finalizer_invocation: AgentInvocationRecord,
    finalizer_result: AgentResultRecord,
    final_response: AdapterResponse,
    finalizer_fallback_used: bool,
    finalizer_fallback_reason: str | None,
) -> None:
    state.invocations.append(finalizer_invocation)
    state.results.append(finalizer_result)
    state.consumed_agent_calls += 1
    state.consumed_token_proxy += int(
        finalizer_invocation.budget_consumed.get("token_proxy_units", 0)
    )
    state.consumed_total_tokens += int(
        finalizer_invocation.budget_consumed.get("consumed_total_tokens", 0)
    )
    if finalizer_invocation.budget_consumed.get("token_usage_mode") == "exact":
        state.exact_usage_count += 1
    else:
        state.proxy_fallback_count += 1
    merge_record.finalizer_agent_id = finalizer_agent.agent_id
    merge_record.finalizer_status = "fallback" if finalizer_fallback_used else "success"
    merge_record.fallback_used = finalizer_fallback_used
    merge_record.fallback_reason = finalizer_fallback_reason
    merge_record.final_output_source = (
        "deterministic_merge_fallback"
        if finalizer_fallback_used
        else finalizer_result.agent_id
    )


def commit_supervisor_finalizer_exception_fallback(
    orchestrator: Any,
    *,
    adapter: StoryAIAdapter,
    state: SupervisorOrchestrateWorkingState,
    merge_record: Any,
    merged_decision: Any,
    base_request: AdapterRequest,
    finalizer_error: str,
) -> AdapterResponse:
    merged_payload = orchestrator._build_merged_payload(merged_decision)
    final_response = AdapterResponse(
        raw_output="[supervisor finalizer unavailable fallback] using deterministic merged payload",
        structured_payload=merged_payload,
        backend_metadata={
            "adapter": adapter.adapter_name,
            "supervisor_finalizer_fallback": True,
            "supervisor_finalizer_fallback_reason": finalizer_error,
        },
        error=None,
    )
    state.invocations.append(
        AgentInvocationRecord(
            agent_id="finalizer",
            role="finalizer",
            invocation_sequence=len(state.invocations) + 1,
            input_summary=(base_request.operator_input or "")[:200],
            tool_policy_snapshot={
                "allowed_tools": [],
                "max_tool_calls": 0,
                "per_tool_timeout_ms": 0,
            },
            model_profile="default",
            adapter_name=adapter.adapter_name,
            execution_status="error",
            duration_ms=0,
            budget_consumed={
                "tool_calls": 0,
                "token_proxy_units": 0,
                "consumed_total_tokens": 0,
                "token_usage_mode": "proxy",
            },
            token_usage=TokenUsageRecord(total_tokens=0, usage_mode="proxy"),
            error_summary=finalizer_error,
            tool_call_transcript=[],
            policy_violations=[],
        )
    )
    state.results.append(
        AgentResultRecord(
            agent_id="finalizer",
            payload=merged_payload,
            confidence="low",
            bounded_summary="Deterministic merge payload used because finalizer could not run.",
            result_shape="finalizer_fallback_payload",
        )
    )
    merge_record.finalizer_agent_id = "finalizer"
    merge_record.finalizer_status = "fallback"
    merge_record.fallback_used = True
    merge_record.fallback_reason = finalizer_error
    merge_record.final_output_source = "deterministic_merge_fallback"
    state.failover_events.append(
        {
            "reason": "finalizer_failed_deterministic_merge_fallback",
            "agent_id": "finalizer",
            "detail": finalizer_error,
        }
    )
    return final_response
