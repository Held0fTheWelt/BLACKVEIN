"""Merge + finalizer + budget assembly for supervisor orchestration (DS-039)."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor_execution_types import SupervisorExecutionResult
from app.runtime.supervisor_merge_finalize_finalizer_budget import (
    supervisor_build_budget_summary,
    supervisor_invoke_finalizer_or_deterministic_fallback,
)
from app.runtime.supervisor_orchestrate_execute_sections import SupervisorOrchestrateWorkingState


def supervisor_merge_finalize_response_and_budget(
    orchestrator: Any,
    *,
    plan: Any,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    turn_cache: OrchestrationTurnCache,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> tuple[AdapterResponse, dict[str, Any], Any]:
    """Merge agent outputs, run finalizer (or fallback), build budget_summary; mutates ``state``.

    Returns ``(final_response, budget_summary, merge_record)``.
    """
    merged_decision, merge_record = orchestrator.merge_agent_results(state.parsed_decisions)
    final_response, finalizer_error = supervisor_invoke_finalizer_or_deterministic_fallback(
        orchestrator,
        policy=policy,
        base_request=base_request,
        adapter=adapter,
        started=started,
        state=state,
        merge_record=merge_record,
        merged_decision=merged_decision,
    )

    if merge_record.fallback_used and not merge_record.fallback_reason and finalizer_error:
        merge_record.fallback_reason = finalizer_error
    merge_record.policy_violations = state.policy_violations
    budget_summary = supervisor_build_budget_summary(
        orchestrator, policy=policy, started=started, state=state
    )
    return final_response, budget_summary, merge_record


def package_supervisor_execution_result(
    *,
    final_response: AdapterResponse,
    plan: Any,
    state: SupervisorOrchestrateWorkingState,
    merge_record: Any,
    budget_summary: dict[str, Any],
    turn_cache: OrchestrationTurnCache,
) -> SupervisorExecutionResult:
    return SupervisorExecutionResult(
        final_response=final_response,
        plan=plan,
        invocations=state.invocations,
        results=state.results,
        merge_finalization=merge_record,
        agent_tool_transcript=state.tool_transcript,
        policy_violations=state.policy_violations,
        budget_summary=budget_summary,
        failover_events=state.failover_events,
        cache_summary=turn_cache.summary(),
        tool_audit=state.tool_audit,
    )
