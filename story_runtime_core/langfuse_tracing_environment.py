"""Resolve Langfuse SDK ``environment`` per trace (backend + world-engine).

Langfuse stores one environment per trace via the client used to emit observations.
We map:

- ``live`` — canonical live UI / live runtime (``trace_origin=live_ui`` + ``execution_tier=live``).
- ``development`` — pytest and other automated tests (``PYTEST_CURRENT_TEST`` set) unless
  agent-assisted testing is flagged.
- ``ai-testing`` — same process as tests, but runs triggered with ``WOS_AI_AGENT_TESTING=1``
  (e.g. Cursor MCP / agent shell) so traces separate from plain CI/pytest.

Override (escape hatch): ``WOS_LANGFUSE_TRACING_ENVIRONMENT`` — if non-empty, returned as-is
(truncated to 40 chars for Langfuse slug limits).

Display note: product wording "AI testing" is represented as slug ``ai-testing`` (Langfuse
environment names are lowercase alphanumeric + hyphens).
"""

from __future__ import annotations

import os

# Langfuse environment slug (no spaces); aligns with dashboard naming conventions.
WOS_LANGFUSE_ENV_AI_TESTING = "ai-testing"

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

    origin = (trace_origin or "").strip().lower()
    tier = (execution_tier or "").strip().lower()

    if origin == "live_ui" and tier == "live":
        return "live"

    pytest_active = bool((os.environ.get("PYTEST_CURRENT_TEST") or "").strip())
    agent_testing = (os.environ.get("WOS_AI_AGENT_TESTING") or "").strip() == "1"

    if pytest_active:
        return WOS_LANGFUSE_ENV_AI_TESTING if agent_testing else "development"

    fallback = (default or "development").strip() or "development"
    return fallback[:_MAX_ENV_LEN]
