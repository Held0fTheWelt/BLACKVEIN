"""Helfer für execute_supervisor_orchestration — DS-014."""

from __future__ import annotations

from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.runtime_models import AgentInvocationRecord, AgentResultRecord
from app.runtime.supervisor_execution_types import SupervisorExecutionResult
from app.runtime.supervisor_invoke_agent import invoke_supervisor_agent
from app.runtime.supervisor_orchestration_audit import append_tool_audit_rows_for_invocation


@dataclass
class SupervisorOrchestrateWorkingState:
    invocations: list[AgentInvocationRecord] = field(default_factory=list)
    results: list[AgentResultRecord] = field(default_factory=list)
    tool_transcript: list[dict[str, Any]] = field(default_factory=list)
    policy_violations: list[str] = field(default_factory=list)
    parsed_decisions: dict[str, Any] = field(default_factory=dict)
    failover_events: list[dict[str, Any]] = field(default_factory=list)
    tool_audit: list[dict[str, Any]] = field(default_factory=list)
    consumed_agent_calls: int = 0
    consumed_tool_calls: int = 0
    failed_agent_calls: int = 0
    degraded_steps: int = 0
    consumed_token_proxy: int = 0
    consumed_total_tokens: int = 0
    exact_usage_count: int = 0
    proxy_fallback_count: int = 0
    shared_preview_feedback: list[dict[str, Any]] = field(default_factory=list)


def orchestrate_run_non_finalizer_agents(
    orchestrator: Any,
    *,
    plan: Any,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    tool_registry: dict[str, Any] | None,
    turn_cache: OrchestrationTurnCache,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> None:
    """Plant und führt alle Agenten bis finalizer aus (ohne Merge/Finalizer)."""
    for agent_id in plan.execution_order:
        if agent_id == "finalizer":
            continue
        agent = orchestrator.registry.require_enabled(agent_id)
        sequence_index = len(state.invocations) + 1
        elapsed_ms = int((perf_counter() - started) * 1000)
        budget_block_reason = orchestrator._get_budget_block_reason(
            policy=policy,
            consumed_agent_calls=state.consumed_agent_calls,
            consumed_tool_calls=state.consumed_tool_calls,
            consumed_total_tokens=state.consumed_total_tokens,
            elapsed_ms=elapsed_ms,
        )
        if budget_block_reason:
            if agent.participation == "optional" and policy.skip_optional_agents_under_pressure:
                state.degraded_steps += 1
                state.failover_events.append(
                    {
                        "reason": "optional_agent_skipped_budget",
                        "agent_id": agent.agent_id,
                        "detail": budget_block_reason,
                    }
                )
                state.invocations.append(
                    orchestrator._build_skipped_invocation(
                        agent=agent,
                        sequence_index=sequence_index,
                        base_request=base_request,
                        reason="optional_agent_skipped_budget",
                    )
                )
                continue
            state.failover_events.append(
                {
                    "reason": "turn_budget_exhausted",
                    "agent_id": agent.agent_id,
                    "detail": budget_block_reason,
                }
            )
            break

        invocation, result, parsed = invoke_supervisor_agent(
            orchestrator,
            agent=agent,
            sequence_index=sequence_index,
            base_request=base_request,
            adapter=adapter,
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events or [],
            tool_registry=tool_registry,
            turn_cache=turn_cache,
            shared_preview_feedback=state.shared_preview_feedback,
        )
        state.invocations.append(invocation)
        state.results.append(result)
        state.tool_transcript.extend(invocation.tool_call_transcript)
        state.policy_violations.extend(invocation.policy_violations)
        state.consumed_agent_calls += 1
        audit_rows, counted_tool_calls, preview_rows = append_tool_audit_rows_for_invocation(
            agent=agent,
            tool_transcript=invocation.tool_call_transcript,
            consume_budget_on_failed_tool_call=policy.consume_budget_on_failed_tool_call,
        )
        state.tool_audit.extend(audit_rows)
        state.shared_preview_feedback.extend(preview_rows)
        state.consumed_tool_calls += counted_tool_calls
        state.consumed_token_proxy += int(invocation.budget_consumed.get("token_proxy_units", 0))
        state.consumed_total_tokens += int(invocation.budget_consumed.get("consumed_total_tokens", 0))
        if invocation.budget_consumed.get("token_usage_mode") == "exact":
            state.exact_usage_count += 1
        else:
            state.proxy_fallback_count += 1
        failed = invocation.execution_status != "success"
        if failed:
            state.failed_agent_calls += 1
        if parsed is not None:
            state.parsed_decisions[agent.agent_id] = parsed
        if failed:
            if agent.participation == "optional" and policy.continue_after_optional_failure:
                state.degraded_steps += 1
                state.failover_events.append(
                    {
                        "reason": "optional_agent_failed_continue",
                        "agent_id": agent.agent_id,
                        "detail": invocation.error_summary or "agent_execution_failed",
                    }
                )
                continue
            state.failover_events.append(
                {
                    "reason": "required_agent_failed_abort",
                    "agent_id": agent.agent_id,
                    "detail": invocation.error_summary or "agent_execution_failed",
                }
            )
            break
        if state.failed_agent_calls > policy.max_failed_agent_calls:
            state.failover_events.append(
                {
                    "reason": "failed_agent_call_budget_exhausted",
                    "agent_id": agent.agent_id,
                    "detail": f"failed_agent_calls={state.failed_agent_calls}",
                }
            )
            break
        if state.degraded_steps > policy.max_degraded_steps:
            state.failover_events.append(
                {
                    "reason": "degraded_steps_exhausted",
                    "agent_id": agent.agent_id,
                    "detail": f"degraded_steps={state.degraded_steps}",
                }
            )
            break


def orchestrate_merge_finalize_and_package(
    orchestrator: Any,
    *,
    plan: Any,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    turn_cache: OrchestrationTurnCache,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> SupervisorExecutionResult:
    """Merge, Finalizer (inkl. Fallback), Budget-Summary und Ergebnisobjekt."""
    from app.runtime.supervisor_orchestrate_merge_finalize_sections import (
        package_supervisor_execution_result,
        supervisor_merge_finalize_response_and_budget,
    )

    final_response, budget_summary, merge_record = supervisor_merge_finalize_response_and_budget(
        orchestrator,
        plan=plan,
        policy=policy,
        base_request=base_request,
        adapter=adapter,
        turn_cache=turn_cache,
        started=started,
        state=state,
    )
    return package_supervisor_execution_result(
        final_response=final_response,
        plan=plan,
        state=state,
        merge_record=merge_record,
        budget_summary=budget_summary,
        turn_cache=turn_cache,
    )
