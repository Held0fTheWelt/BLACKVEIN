"""Budget-Gate, Invoke und Zähler für Non-Finalizer-Schritte (DS-014 optional split)."""

from __future__ import annotations

from time import perf_counter
from typing import Any, Literal

from app.runtime.ai_adapter import AdapterRequest, StoryAIAdapter
from app.runtime.cache.orchestration_cache import OrchestrationTurnCache
from app.runtime.supervisor.supervisor_invoke_agent import invoke_supervisor_agent
from app.runtime.supervisor.supervisor_orchestration_audit import append_tool_audit_rows_for_invocation
from app.runtime.supervisor.supervisor_orchestrate_working_state import SupervisorOrchestrateWorkingState

BudgetGate = Literal["invoke", "skip_iteration", "break_loop"]


def non_finalizer_resolve_budget_gate(
    orchestrator: Any,
    *,
    agent: Any,
    policy: Any,
    base_request: AdapterRequest,
    sequence_index: int,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> BudgetGate:
    elapsed_ms = int((perf_counter() - started) * 1000)
    budget_block_reason = orchestrator._get_budget_block_reason(
        policy=policy,
        consumed_agent_calls=state.consumed_agent_calls,
        consumed_tool_calls=state.consumed_tool_calls,
        consumed_total_tokens=state.consumed_total_tokens,
        elapsed_ms=elapsed_ms,
    )
    if not budget_block_reason:
        return "invoke"
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
        return "skip_iteration"
    state.failover_events.append(
        {
            "reason": "turn_budget_exhausted",
            "agent_id": agent.agent_id,
            "detail": budget_block_reason,
        }
    )
    return "break_loop"


def non_finalizer_invoke_and_accumulate_counters(
    orchestrator: Any,
    *,
    agent: Any,
    sequence_index: int,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    session: Any,
    module: Any,
    current_turn: int,
    recent_events: list[dict[str, Any]] | None,
    tool_registry: dict[str, Any] | None,
    turn_cache: OrchestrationTurnCache,
    policy: Any,
    state: SupervisorOrchestrateWorkingState,
) -> tuple[Any, Any, Any]:
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
    return invocation, result, parsed


def non_finalizer_should_break_after_invocation(
    *,
    agent: Any,
    policy: Any,
    invocation: Any,
    state: SupervisorOrchestrateWorkingState,
) -> bool:
    failed = invocation.execution_status != "success"
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
            return False
        state.failover_events.append(
            {
                "reason": "required_agent_failed_abort",
                "agent_id": agent.agent_id,
                "detail": invocation.error_summary or "agent_execution_failed",
            }
        )
        return True
    if state.failed_agent_calls > policy.max_failed_agent_calls:
        state.failover_events.append(
            {
                "reason": "failed_agent_call_budget_exhausted",
                "agent_id": agent.agent_id,
                "detail": f"failed_agent_calls={state.failed_agent_calls}",
            }
        )
        return True
    if state.degraded_steps > policy.max_degraded_steps:
        state.failover_events.append(
            {
                "reason": "degraded_steps_exhausted",
                "agent_id": agent.agent_id,
                "detail": f"degraded_steps={state.degraded_steps}",
            }
        )
        return True
    return False
