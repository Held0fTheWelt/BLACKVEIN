"""Bounded subagent invocation with tool loop (extracted from SupervisorOrchestrator)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.ai_adapter import AdapterRequest, StoryAIAdapter, generate_with_timeout
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor_invoke_agent_sections import (
    build_supervisor_agent_invocation_result,
    run_supervisor_agent_tool_loop,
)
from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord


def invoke_supervisor_agent(
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
) -> tuple[AgentInvocationRecord, AgentResultRecord, ParsedAIDecision | None]:
    request = orchestrator._build_agent_request(
        base_request=base_request,
        agent=agent,
        sequence_index=sequence_index,
        tool_results=[],
        cross_agent_preview_feedback=shared_preview_feedback,
    )
    started = perf_counter()
    response = generate_with_timeout(
        adapter=adapter,
        request=request,
        timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
    )
    request, response, tool_call_transcript, policy_violations = run_supervisor_agent_tool_loop(
        orchestrator,
        agent=agent,
        sequence_index=sequence_index,
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
        tool_registry=tool_registry,
        turn_cache=turn_cache,
        shared_preview_feedback=shared_preview_feedback,
        request=request,
        initial_response=response,
    )
    return build_supervisor_agent_invocation_result(
        orchestrator,
        agent=agent,
        sequence_index=sequence_index,
        adapter=adapter,
        request=request,
        response=response,
        tool_call_transcript=tool_call_transcript,
        policy_violations=policy_violations,
        started=started,
    )
