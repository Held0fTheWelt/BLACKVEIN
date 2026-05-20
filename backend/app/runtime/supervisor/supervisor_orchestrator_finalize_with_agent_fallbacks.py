"""Parse- und Token-Budget-Fallbacks für den Supervisor-Finalizer (DS-014 optional split)."""

from __future__ import annotations

from typing import Any

from app.runtime.agent_registry import AgentConfig
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.ai.ai_decision import process_adapter_response


def finalizer_apply_parse_failure_fallback(
    *,
    merged_payload: dict[str, Any],
    adapter: StoryAIAdapter,
    parse_result: Any,
    final_response: AdapterResponse,
    allow_fallback: bool,
) -> tuple[AdapterResponse, Any, bool, str | None]:
    """Bei Parse-Fehler optional deterministischen Payload setzen."""
    finalizer_fallback_used = False
    finalizer_fallback_reason: str | None = None
    if parse_result.success:
        return final_response, parse_result, finalizer_fallback_used, finalizer_fallback_reason
    if not allow_fallback:
        raise RuntimeError("finalizer_failed_no_fallback")
    finalizer_fallback_used = True
    reason = "; ".join(parse_result.errors) if parse_result.errors else "finalizer_parse_failed"
    finalizer_fallback_reason = f"finalizer_unavailable_or_invalid: {reason}"
    fallback_raw = "[supervisor finalizer fallback] using deterministic merged payload"
    final_response = AdapterResponse(
        raw_output=fallback_raw,
        structured_payload=merged_payload,
        backend_metadata={
            "adapter": adapter.adapter_name,
            "supervisor_finalizer_fallback": True,
            "supervisor_finalizer_fallback_reason": finalizer_fallback_reason,
        },
        error=None,
    )
    parse_result = process_adapter_response(final_response)
    return final_response, parse_result, finalizer_fallback_used, finalizer_fallback_reason


def finalizer_apply_token_budget_fallback_if_needed(
    orchestrator: Any,
    *,
    merged_payload: dict[str, Any],
    adapter: StoryAIAdapter,
    finalizer_agent: AgentConfig,
    final_response: AdapterResponse,
    parse_result: Any,
    token_consumed: dict[str, Any],
    token_usage: Any,
    allow_fallback: bool,
    finalizer_fallback_used: bool,
    finalizer_fallback_reason: str | None,
) -> tuple[AdapterResponse, Any, dict[str, Any], Any, bool, str | None]:
    max_agent_tokens = max(finalizer_agent.budget_profile.max_agent_tokens, 0)
    if max_agent_tokens <= 0 or int(token_consumed.get("consumed_total_tokens", 0)) <= max_agent_tokens:
        return (
            final_response,
            parse_result,
            token_consumed,
            token_usage,
            finalizer_fallback_used,
            finalizer_fallback_reason,
        )
    reason = (
        "agent_token_budget_exhausted:"
        f"{int(token_consumed.get('consumed_total_tokens', 0))}>{max_agent_tokens}"
    )
    if not allow_fallback:
        raise RuntimeError(reason)
    finalizer_fallback_used = True
    finalizer_fallback_reason = f"finalizer_unavailable_or_invalid: {reason}"
    final_response = AdapterResponse(
        raw_output="[supervisor finalizer fallback] using deterministic merged payload",
        structured_payload=merged_payload,
        backend_metadata={
            "adapter": adapter.adapter_name,
            "supervisor_finalizer_fallback": True,
            "supervisor_finalizer_fallback_reason": finalizer_fallback_reason,
        },
        error=None,
    )
    parse_result = process_adapter_response(final_response)
    token_consumed, token_usage = orchestrator._build_token_consumption(final_response)
    return (
        final_response,
        parse_result,
        token_consumed,
        token_usage,
        finalizer_fallback_used,
        finalizer_fallback_reason,
    )
