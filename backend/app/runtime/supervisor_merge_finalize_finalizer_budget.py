"""Finalizer-Pfad und Budget-Zusammenfassung für Supervisor-Merge (Feinsplit von merge_finalize_sections)."""

from __future__ import annotations

from time import perf_counter
from typing import Any

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.runtime_models import (
    AgentInvocationRecord,
    AgentResultRecord,
    TokenUsageRecord,
)
from app.runtime.supervisor_orchestrate_execute_sections import SupervisorOrchestrateWorkingState


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
    except Exception as exc:  # pragma: no cover - defensive path
        finalizer_error = f"finalizer_unavailable_or_invalid: {exc}"
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
