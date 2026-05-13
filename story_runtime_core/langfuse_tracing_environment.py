"""Resolve Langfuse SDK ``environment`` per trace (backend + world-engine).

Langfuse stores one environment per trace via the client used to emit observations.

**Canonical rule:** the Langfuse project ``environment`` string must match **backend
observability settings** (passed as ``default`` from credential ``environment``). We do
**not** invent a separate ``live`` Langfuse environment for UI play; ``trace_origin`` /
``execution_tier`` remain WoS metadata on the trace.

Resolution order:

- ``WOS_LANGFUSE_TRACING_ENVIRONMENT`` — if non-empty, returned as-is (truncated to 40 chars).
- ``PYTEST_CURRENT_TEST`` set — ``tests`` or ``ai-testing`` (plain pytest vs agent-assisted).
- ``live_ui`` + ``execution_tier=live`` — returns ``default`` (backend observability env).
- Otherwise — ``default`` (backend observability env).

``tests`` groups automated test traces in Langfuse separately from operator ``development``
sessions and from ``ai-testing`` (``WOS_AI_AGENT_TESTING=1``).
"""

from __future__ import annotations

import os

# Langfuse environment slug (no spaces); aligns with dashboard naming conventions.
WOS_LANGFUSE_ENV_AI_TESTING = "ai-testing"
WOS_LANGFUSE_ENV_TESTS = "tests"

_MAX_ENV_LEN = 40


def resolve_langfuse_environment(
    trace_origin: str | None,
    execution_tier: str | None,
    *,
    default: str = "development",
) -> str:
    """Return the Langfuse client environment string for this trace."""
    explicit = (os.environ.get("WOS_LANGFUSE_TRACING_ENVIRONMENT") or "").strip()
    if explicit:
        return explicit[:_MAX_ENV_LEN]

    pytest_active = bool((os.environ.get("PYTEST_CURRENT_TEST") or "").strip())
    agent_testing = (os.environ.get("WOS_AI_AGENT_TESTING") or "").strip() == "1"
    if pytest_active:
        return WOS_LANGFUSE_ENV_AI_TESTING if agent_testing else WOS_LANGFUSE_ENV_TESTS

    origin = (trace_origin or "").strip().lower()
    tier = (execution_tier or "").strip().lower()

    if origin == "live_ui" and tier == "live":
        fallback = (default or "development").strip() or "development"
        return fallback[:_MAX_ENV_LEN]

    fallback = (default or "development").strip() or "development"
    return fallback[:_MAX_ENV_LEN]
