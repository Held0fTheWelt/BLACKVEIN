"""Helfer für invoke_supervisor_agent (Tool-Loop und Record-Bau) — DS-021."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter, generate_with_timeout
from app.runtime.ai_decision import ParsedAIDecision, process_adapter_response
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord
from app.runtime.supervisor_orchestration_audit import enrich_preview_delta_transcript_entry
from app.runtime.tool_loop import (
    HostToolContext,
    ToolCallTranscriptEntry,
    ToolCallStatus,
    ToolLoopPolicy,
    detect_tool_request_payload,
    execute_tool_request,
)


def run_supervisor_agent_tool_loop(
    orchestrator: Any,
    *,
    agent: AgentConfig,
    sequence_index: int,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]],
    tool_registry: dict[str, Any] | None,
    turn_cache: OrchestrationTurnCache,
    shared_preview_feedback: list[dict[str, Any]],
    request: AdapterRequest,
    initial_response: AdapterResponse,
) -> tuple[AdapterRequest, AdapterResponse, list[dict[str, Any]], list[str]]:
    """Führt Tool-Aufrufe bis Stopp aus; liefert letzte Request/Response und Transkript."""
    tool_call_transcript: list[dict[str, Any]] = []
    policy_violations: list[str] = []
    tool_results: list[dict[str, Any]] = []
    max_tool_calls = max(agent.budget_profile.max_tool_calls, 0)
    tool_context = HostToolContext(
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
    )
    tool_policy = ToolLoopPolicy(
        enabled=max_tool_calls > 0,
        allowed_tools=list(agent.allowed_tools),
        max_tool_calls_per_turn=max_tool_calls,
        per_tool_timeout_ms=agent.budget_profile.per_tool_timeout_ms,
        max_retries_per_tool_call=agent.budget_profile.max_retries_per_tool_call,
    )
    response = initial_response
    tool_calls = 0
    while tool_policy.enabled and tool_calls < tool_policy.max_tool_calls_per_turn:
        tool_request = detect_tool_request_payload(
            response.structured_payload,
            sequence_index=tool_calls + 1,
        )
        if tool_request is None:
            break
        cache_key: str | None = None
        if orchestrator._is_cacheable_tool(tool_request.tool_name):
            cache_key = OrchestrationTurnCache.make_tool_key(
                tool_request.tool_name,
                tool_request.arguments,
            )
            cached = turn_cache.get(cache_key)
            if cached is not None:
                entry = ToolCallTranscriptEntry(
                    sequence_index=tool_request.sequence_index,
                    tool_name=tool_request.tool_name,
                    sanitized_arguments={},
                    status=ToolCallStatus.SUCCESS,
                    attempts=1,
                    duration_ms=0,
                    result_summary="cache_hit",
                )
                tool_result = {
                    "request_id": tool_request.request_id,
                    "sequence_index": tool_request.sequence_index,
                    "tool_name": tool_request.tool_name,
                    "status": ToolCallStatus.SUCCESS,
                    "result": cached.get("result"),
                    "cache_hit": True,
                }
            else:
                entry, tool_result = execute_tool_request(
                    tool_request,
                    policy=tool_policy,
                    context=tool_context,
                    registry=tool_registry,
                )
                if (
                    entry.status == ToolCallStatus.SUCCESS
                    and isinstance(tool_result.get("result"), dict)
                ):
                    turn_cache.put(cache_key, {"result": tool_result.get("result")})
        else:
            turn_cache.mark_bypass()
            entry, tool_result = execute_tool_request(
                tool_request,
                policy=tool_policy,
                context=tool_context,
                registry=tool_registry,
            )
        entry_dict = entry.model_dump()
        entry_dict["agent_id"] = agent.agent_id
        if tool_result.get("cache_hit"):
            entry_dict["cache_hit"] = True
        if tool_request.tool_name == "wos.guard.preview_delta":
            enrich_preview_delta_transcript_entry(entry_dict, tool_result)
        tool_call_transcript.append(entry_dict)
        tool_results.append(tool_result)
        if entry.status == ToolCallStatus.REJECTED:
            policy_violations.append(
                f"{agent.agent_id}:{tool_result.get('error', 'tool_rejected')}"
            )
            break
        if entry.status != ToolCallStatus.SUCCESS:
            break
        tool_calls += 1
        request = orchestrator._build_agent_request(
            base_request=base_request,
            agent=agent,
            sequence_index=sequence_index,
            tool_results=tool_results,
            cross_agent_preview_feedback=shared_preview_feedback,
        )
        response = generate_with_timeout(
            adapter=adapter,
            request=request,
            timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
        )
    return request, response, tool_call_transcript, policy_violations


def build_supervisor_agent_invocation_result(
    orchestrator: Any,
    *,
    agent: AgentConfig,
    sequence_index: int,
    adapter: StoryAIAdapter,
    request: AdapterRequest,
    response: AdapterResponse,
    tool_call_transcript: list[dict[str, Any]],
    policy_violations: list[str],
    started: float,
) -> tuple[AgentInvocationRecord, AgentResultRecord, ParsedAIDecision | None]:
    """Parse-Retries, Budget-Checks und fertige AgentInvocation/Result-Records."""
    duration_ms = int((perf_counter() - started) * 1000)
    retry_count = 0
    parse_result = process_adapter_response(response)
    while (
        not parse_result.success
        and retry_count < max(agent.budget_profile.max_attempts - 1, 0)
    ):
        retry_count += 1
        response = generate_with_timeout(
            adapter=adapter,
            request=request,
            timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
        )
        parse_result = process_adapter_response(response)
    status = "success" if parse_result.success else "error"
    error_summary = "; ".join(parse_result.errors) if parse_result.errors else None
    result_payload = response.structured_payload if isinstance(response.structured_payload, dict) else {}
    token_consumed, token_usage = orchestrator._build_token_consumption(response)
    if duration_ms > agent.budget_profile.max_agent_duration_ms:
        status = "error"
        extra = (
            f"agent_duration_budget_exhausted:{duration_ms}>{agent.budget_profile.max_agent_duration_ms}"
        )
        error_summary = f"{error_summary}; {extra}" if error_summary else extra
    max_agent_tokens = max(agent.budget_profile.max_agent_tokens, 0)
    if max_agent_tokens > 0 and int(token_consumed.get("consumed_total_tokens", 0)) > max_agent_tokens:
        status = "error"
        extra = (
            "agent_token_budget_exhausted:"
            f"{int(token_consumed.get('consumed_total_tokens', 0))}>{max_agent_tokens}"
        )
        error_summary = f"{error_summary}; {extra}" if error_summary else extra
        policy_violations.append(f"{agent.agent_id}:{extra}")
    bounded_summary = (
        parse_result.decision.scene_interpretation[:200]
        if parse_result.success and parse_result.decision
        else (response.raw_output or "")[:200]
    )
    invocation = AgentInvocationRecord(
        agent_id=agent.agent_id,
        role=agent.role,
        invocation_sequence=sequence_index,
        input_summary=(request.operator_input or "")[:200],
        tool_policy_snapshot={
            "allowed_tools": list(agent.allowed_tools),
            "max_tool_calls": agent.budget_profile.max_tool_calls,
            "per_tool_timeout_ms": agent.budget_profile.per_tool_timeout_ms,
        },
        model_profile=agent.model_selection.model_profile,
        adapter_name=(agent.model_selection.adapter_name or adapter.adapter_name),
        execution_status=status,
        duration_ms=duration_ms,
        retry_count=retry_count,
        budget_snapshot={
            "max_attempts": agent.budget_profile.max_attempts,
            "max_tool_calls": agent.budget_profile.max_tool_calls,
            "max_agent_duration_ms": agent.budget_profile.max_agent_duration_ms,
            "max_agent_tokens": agent.budget_profile.max_agent_tokens,
        },
        budget_consumed={
            "tool_calls": len(tool_call_transcript),
            **token_consumed,
        },
        token_usage=token_usage,
        error_summary=error_summary,
        tool_call_transcript=tool_call_transcript,
        policy_violations=policy_violations,
    )
    result = AgentResultRecord(
        agent_id=agent.agent_id,
        payload=result_payload,
        confidence="high" if parse_result.success else "low",
        bounded_summary=bounded_summary,
        result_shape="parsed_decision" if parse_result.success else "unparsed_payload",
    )
    return invocation, result, parse_result.decision if parse_result.success else None
