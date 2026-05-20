"""Finalizer-Pfad und Budget-Zusammenfassung für Supervisor-Merge (Feinsplit von merge_finalize_sections)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.supervisor.supervisor_merge_finalize_finalizer_budget_paths import (
    commit_supervisor_finalizer_exception_fallback,
    commit_supervisor_finalizer_success,
)
from app.runtime.supervisor.supervisor_orchestrate_working_state import SupervisorOrchestrateWorkingState


def supervisor_invoke_finalizer_or_deterministic_fallback(
    orchestrator: Any,
    *,
    policy: Any,
    base_request: AdapterRequest,
    adapter: StoryAIAdapter,
    started: float,
    state: SupervisorOrchestrateWorkingState,
    merge_record: Any,
    merged_decision: Any,
) -> tuple[AdapterResponse, str | None]:
    """Merge bereits erfolgt; Finalizer ausführen oder deterministischen Fallback. Mutiert ``state`` und ``merge_record``."""

    finalizer_error: str | None = None
    try:
        finalizer_agent = orchestrator.registry.require_enabled("finalizer")
        elapsed_ms = int((perf_counter() - started) * 1000)
        finalizer_block_reason = orchestrator._get_budget_block_reason(
            policy=policy,
            consumed_agent_calls=state.consumed_agent_calls,
            consumed_tool_calls=state.consumed_tool_calls,
            consumed_total_tokens=state.consumed_total_tokens,
            elapsed_ms=elapsed_ms,
        )
        if finalizer_block_reason:
            state.failover_events.append(
                {
                    "reason": "turn_budget_exhausted",
                    "agent_id": "finalizer",
                    "detail": finalizer_block_reason,
                }
            )
            raise RuntimeError(finalizer_block_reason)
        finalizer_sequence = len(state.invocations) + 1
        (
            finalizer_invocation,
            finalizer_result,
            final_response,
            finalizer_fallback_used,
            finalizer_fallback_reason,
        ) = orchestrator.finalize_with_agent(
            finalizer_agent=finalizer_agent,
            sequence_index=finalizer_sequence,
            base_request=base_request,
            adapter=adapter,
            merged_decision=merged_decision,
            all_results=state.results,
            allow_fallback=policy.allow_finalizer_fallback,
        )
        commit_supervisor_finalizer_success(
            state=state,
            merge_record=merge_record,
            finalizer_agent=finalizer_agent,
            finalizer_invocation=finalizer_invocation,
            finalizer_result=finalizer_result,
            final_response=final_response,
            finalizer_fallback_used=finalizer_fallback_used,
            finalizer_fallback_reason=finalizer_fallback_reason,
        )
    except Exception as exc:  # pragma: no cover - defensive path
        finalizer_error = f"finalizer_unavailable_or_invalid: {exc}"
        final_response = commit_supervisor_finalizer_exception_fallback(
            orchestrator,
            adapter=adapter,
            state=state,
            merge_record=merge_record,
            merged_decision=merged_decision,
            base_request=base_request,
            finalizer_error=finalizer_error,
        )

    return final_response, finalizer_error


def supervisor_build_budget_summary(
    orchestrator: Any,
    *,
    policy: Any,
    started: float,
    state: SupervisorOrchestrateWorkingState,
) -> dict[str, Any]:
    elapsed_total_ms = int((perf_counter() - started) * 1000)
    return {
        "configured": {
            "max_turn_duration_ms": policy.max_turn_duration_ms,
            "max_total_agent_calls": policy.max_total_agent_calls,
            "max_total_tool_calls": policy.max_total_tool_calls,
            "max_total_tokens": policy.max_total_tokens,
            "max_failed_agent_calls": policy.max_failed_agent_calls,
            "max_degraded_steps": policy.max_degraded_steps,
        },
        "consumed": {
            "turn_duration_ms": elapsed_total_ms,
            "total_agent_calls": state.consumed_agent_calls,
            "total_tool_calls": state.consumed_tool_calls,
            "token_proxy_units": state.consumed_token_proxy,
            "consumed_total_tokens": state.consumed_total_tokens,
            "token_usage_mode": orchestrator._aggregate_usage_mode(
                exact_usage_count=state.exact_usage_count,
                proxy_fallback_count=state.proxy_fallback_count,
            ),
            "proxy_fallback_count": state.proxy_fallback_count,
            "failed_agent_calls": state.failed_agent_calls,
            "degraded_steps": state.degraded_steps,
        },
        "limit_hit": bool(state.failover_events),
    }
