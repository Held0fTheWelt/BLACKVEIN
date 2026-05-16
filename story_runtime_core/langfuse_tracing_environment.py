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
LOCAL_LANGFUSE_EVIDENCE_SCOPE = "local_langfuse"
LOCAL_LANGFUSE_PROOF_LEVEL = "local_only"

_MAX_ENV_LEN = 40
_TRUTHY = {"1", "true", "yes", "on"}


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


def local_langfuse_evidence_metadata() -> dict[str, object]:
    """Return mandatory local-only metadata when local Langfuse evidence is enabled.

    This helper is intentionally opt-in via env. It marks local observability as
    diagnostic evidence only and prevents local Langfuse traces/scores from being
    confused with live or staging proof.
    """
    explicit_local = (
        (os.environ.get("WOS_LANGFUSE_LOCAL_EVIDENCE") or "").strip().lower() in _TRUTHY
        or (os.environ.get("WOS_LANGFUSE_EVIDENCE_SCOPE") or "").strip() == LOCAL_LANGFUSE_EVIDENCE_SCOPE
        or (os.environ.get("WOS_LANGFUSE_PROOF_LEVEL") or "").strip() == LOCAL_LANGFUSE_PROOF_LEVEL
    )
    if not explicit_local:
        return {}

    environment = (
        os.environ.get("WOS_LANGFUSE_EVIDENCE_ENVIRONMENT")
        or os.environ.get("LANGFUSE_ENVIRONMENT")
        or os.environ.get("WOS_LANGFUSE_TRACING_ENVIRONMENT")
        or "local"
    )
    return {
        "environment": str(environment or "local").strip() or "local",
        "evidence_scope": LOCAL_LANGFUSE_EVIDENCE_SCOPE,
        "proof_level": LOCAL_LANGFUSE_PROOF_LEVEL,
        "live_or_staging_evidence": False,
    }
