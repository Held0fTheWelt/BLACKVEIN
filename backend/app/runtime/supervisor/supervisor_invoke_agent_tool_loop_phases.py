"""Phased helpers for ``run_supervisor_agent_tool_loop`` (DS-027 — budget / cache / execute)."""

from __future__ import annotations

from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.cache.orchestration_cache import OrchestrationTurnCache
from app.runtime.turn.tool_loop import (
    HostToolContext,
    ToolCallTranscriptEntry,
    ToolCallStatus,
    ToolLoopPolicy,
    ToolRequest,
    execute_tool_request,
)


def build_supervisor_tool_loop_policy_and_context(
    *,
    agent: AgentConfig,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]],
) -> tuple[ToolLoopPolicy, HostToolContext]:
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
    return tool_policy, tool_context


def resolve_supervisor_tool_call_entry_and_result(
    orchestrator: Any,
    *,
    tool_request: ToolRequest,
    tool_policy: ToolLoopPolicy,
    tool_context: HostToolContext,
    tool_registry: dict[str, Any] | None,
    turn_cache: OrchestrationTurnCache,
) -> tuple[ToolCallTranscriptEntry, dict[str, Any]]:
    """Run one tool call (cacheable path or live execution with optional cache store)."""
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
            return entry, tool_result
        entry, tool_result = execute_tool_request(
            tool_request,
            policy=tool_policy,
            context=tool_context,
            registry=tool_registry,
        )
        if entry.status == ToolCallStatus.SUCCESS and isinstance(tool_result.get("result"), dict):
            turn_cache.put(cache_key, {"result": tool_result.get("result")})
        return entry, tool_result
    turn_cache.mark_bypass()
    return execute_tool_request(
        tool_request,
        policy=tool_policy,
        context=tool_context,
        registry=tool_registry,
    )
