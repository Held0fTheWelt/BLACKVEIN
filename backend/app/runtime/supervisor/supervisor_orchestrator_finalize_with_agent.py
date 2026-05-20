"""Finalizer-Subagent: Generierung, Parse-Fallback, Token-Budget, Invocations (DS-014)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.ai_adapter import (
    AdapterRequest,
    StoryAIAdapter,
    generate_with_timeout,
)
from app.runtime.ai.ai_decision import ParsedAIDecision, process_adapter_response
from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord
from app.runtime.supervisor.supervisor_orchestrator_finalize_with_agent_fallbacks import (
    finalizer_apply_parse_failure_fallback,
    finalizer_apply_token_budget_fallback_if_needed,
)
from app.runtime.supervisor.supervisor_orchestrator_finalize_with_agent_records import (
    build_finalizer_invocation_and_agent_result,
)


def run_finalize_with_agent(
    orchestrator: Any,
    *,
    finalizer_agent: AgentConfig,
    sequence_index: int,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    merged_decision: ParsedAIDecision,
    all_results: list[AgentResultRecord],
    allow_fallback: bool,
) -> tuple[AgentInvocationRecord, AgentResultRecord, AdapterResponse, bool, str | None]:
    merged_payload = orchestrator._build_merged_payload(merged_decision)
    finalizer_request = orchestrator._build_agent_request(
        base_request=base_request,
        agent=finalizer_agent,
        sequence_index=sequence_index,
        tool_results=[],
    )
    finalizer_request.metadata["supervisor_merge_payload"] = merged_payload
    finalizer_request.metadata["supervisor_subagent_result_summaries"] = [
        {"agent_id": item.agent_id, "summary": item.bounded_summary}
        for item in all_results
    ]

    started = perf_counter()
    final_response = generate_with_timeout(
        adapter=adapter,
        request=finalizer_request,
        timeout_ms=max(finalizer_agent.budget_profile.max_agent_duration_ms, 1),
    )
    parse_result = process_adapter_response(final_response)
    duration_ms = int((perf_counter() - started) * 1000)
    finalizer_fallback_used = False
    finalizer_fallback_reason: str | None = None
    final_response, parse_result, finalizer_fallback_used, finalizer_fallback_reason = (
        finalizer_apply_parse_failure_fallback(
            merged_payload=merged_payload,
            adapter=adapter,
            parse_result=parse_result,
            final_response=final_response,
            allow_fallback=allow_fallback,
        )
    )

    token_consumed, token_usage = orchestrator._build_token_consumption(final_response)
    (
        final_response,
        parse_result,
        token_consumed,
        token_usage,
        finalizer_fallback_used,
        finalizer_fallback_reason,
    ) = finalizer_apply_token_budget_fallback_if_needed(
        orchestrator,
        merged_payload=merged_payload,
        adapter=adapter,
        finalizer_agent=finalizer_agent,
        final_response=final_response,
        parse_result=parse_result,
        token_consumed=token_consumed,
        token_usage=token_usage,
        allow_fallback=allow_fallback,
        finalizer_fallback_used=finalizer_fallback_used,
        finalizer_fallback_reason=finalizer_fallback_reason,
    )
    invocation, result = build_finalizer_invocation_and_agent_result(
        finalizer_agent=finalizer_agent,
        sequence_index=sequence_index,
        finalizer_request=finalizer_request,
        adapter=adapter,
        parse_result=parse_result,
        final_response=final_response,
        duration_ms=duration_ms,
        token_consumed=token_consumed,
        token_usage=token_usage,
        finalizer_fallback_used=finalizer_fallback_used,
        finalizer_fallback_reason=finalizer_fallback_reason,
    )
    return (
        invocation,
        result,
        final_response,
        finalizer_fallback_used,
        finalizer_fallback_reason,
    )
