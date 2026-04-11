"""Adapter generation with retry policy (extracted from ai_turn_executor)."""

from __future__ import annotations

from collections.abc import Callable

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter, generate_with_timeout
from app.runtime.ai_failure_recovery import AIFailureClass, RetryPolicy


def run_adapter_generation_with_retry(
    *,
    execution_adapter: StoryAIAdapter,
    retry_policy: RetryPolicy,
    adapter_generate_timeout_ms: int,
    build_request: Callable[[int], AdapterRequest],
    enrich_request: Callable[[AdapterRequest], None],
    mark_reduced_context: Callable[[], None],
    starting_attempt: int = 1,
) -> tuple[AdapterResponse, int]:
    """Run generate_with_timeout in a retry loop matching legacy ai_turn_executor semantics."""
    response: AdapterResponse | None = None
    current_attempt = starting_attempt
    request = build_request(current_attempt)
    enrich_request(request)

    while current_attempt <= retry_policy.MAX_RETRIES:
        if current_attempt > 1:
            mark_reduced_context()
            request = build_request(current_attempt)
            enrich_request(request)

        response = generate_with_timeout(
            adapter=execution_adapter,
            request=request,
            timeout_ms=adapter_generate_timeout_ms,
        )
        has_error = response.error is not None
        is_empty = not response.raw_output or not response.raw_output.strip()
        if has_error or is_empty:
            failure_class = AIFailureClass.ADAPTER_ERROR
            if has_error and isinstance(response.error, str) and response.error.startswith(
                "adapter_generate_timeout:"
            ):
                failure_class = AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE
            if (
                retry_policy.is_retryable_failure(failure_class)
                and current_attempt < retry_policy.MAX_RETRIES
            ):
                current_attempt += 1
                continue
        break

    assert response is not None
    return response, current_attempt
