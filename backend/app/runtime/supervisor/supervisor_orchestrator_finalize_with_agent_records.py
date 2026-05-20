"""Invocation- und Result-Records für den Supervisor-Finalizer (DS-014 optional split)."""

from __future__ import annotations

from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord


def build_finalizer_invocation_and_agent_result(
    *,
    finalizer_agent: AgentConfig,
    sequence_index: int,
    finalizer_request: AdapterRequest,
    adapter: StoryAIAdapter,
    parse_result: Any,
    final_response: AdapterResponse,
    duration_ms: int,
    token_consumed: dict[str, Any],
    token_usage: Any,
    finalizer_fallback_used: bool,
    finalizer_fallback_reason: str | None,
) -> tuple[AgentInvocationRecord, AgentResultRecord]:
    invocation = AgentInvocationRecord(
        agent_id=finalizer_agent.agent_id,
        role=finalizer_agent.role,
        invocation_sequence=sequence_index,
        input_summary=(finalizer_request.operator_input or "")[:200],
        tool_policy_snapshot={
            "allowed_tools": [],
            "max_tool_calls": 0,
            "per_tool_timeout_ms": finalizer_agent.budget_profile.per_tool_timeout_ms,
        },
        model_profile=finalizer_agent.model_selection.model_profile,
        adapter_name=(finalizer_agent.model_selection.adapter_name or adapter.adapter_name),
        execution_status="success" if parse_result.success else "error",
        duration_ms=duration_ms,
        retry_count=0,
        budget_snapshot={
            "max_attempts": finalizer_agent.budget_profile.max_attempts,
            "max_tool_calls": 0,
            "max_agent_duration_ms": finalizer_agent.budget_profile.max_agent_duration_ms,
            "max_agent_tokens": finalizer_agent.budget_profile.max_agent_tokens,
        },
        budget_consumed={"tool_calls": 0, **token_consumed},
        token_usage=token_usage,
        error_summary="; ".join(parse_result.errors) if parse_result.errors else None,
        tool_call_transcript=[],
        policy_violations=[],
    )
    if finalizer_fallback_reason:
        invocation.error_summary = finalizer_fallback_reason
    result = AgentResultRecord(
        agent_id=finalizer_agent.agent_id,
        payload=final_response.structured_payload or {},
        confidence="low" if finalizer_fallback_used else ("high" if parse_result.success else "low"),
        bounded_summary=(
            "Deterministic merge payload used because finalizer produced no valid decision."
            if finalizer_fallback_used
            else (
                parse_result.decision.rationale[:220]
                if parse_result.success and parse_result.decision
                else final_response.raw_output[:220]
            )
        ),
        result_shape=(
            "finalizer_fallback_payload"
            if finalizer_fallback_used
            else "finalized_decision"
        ),
    )
    return invocation, result
