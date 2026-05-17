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
from urllib.parse import urlparse

# Langfuse environment slug (no spaces); aligns with dashboard naming conventions.
WOS_LANGFUSE_ENV_AI_TESTING = "ai-testing"
WOS_LANGFUSE_ENV_TESTS = "tests"
LOCAL_LANGFUSE_EVIDENCE_SCOPE = "local_langfuse"
LOCAL_LANGFUSE_PROOF_LEVEL = "local_only"

_MAX_ENV_LEN = 40
_TRUTHY = {"1", "true", "yes", "on"}
_FALSEY = {"0", "false", "no", "off"}
_LOCALHOST_LANGFUSE_HOSTS = frozenset({"localhost", "127.0.0.1", "0.0.0.0"})
_DOCKER_LANGFUSE_HOSTS = frozenset({"langfuse-web", "langfuse"})
_LOCAL_LANGFUSE_ENVIRONMENTS = frozenset({"local"})
_DEFAULT_LANGFUSE_BASE_URL = "https://cloud.langfuse.com"


def _truthy_env(name: str) -> bool:
    value = (os.environ.get(name) or "").strip().lower()
    return bool(value and value not in _FALSEY)


def _inside_container() -> bool:
    return (
        os.path.exists("/.dockerenv")
        or _truthy_env("WOS_RUNNING_IN_DOCKER")
        or _truthy_env("WOS_BACKEND_RUNNING_IN_DOCKER")
        or _truthy_env("WOS_WORLD_ENGINE_RUNNING_IN_DOCKER")
    )


def _normalize_base_url(value: str | None) -> str:
    return str(value or "").strip().rstrip("/")


def _base_url_host(value: str | None) -> str:
    try:
        return (urlparse(_normalize_base_url(value)).hostname or "").lower()
    except Exception:
        return ""


def _runtime_env_langfuse_base_url() -> str:
    explicit = _normalize_base_url(os.environ.get("WOS_LANGFUSE_RUNTIME_BASE_URL"))
    if explicit:
        return explicit
    return _normalize_base_url(os.environ.get("LANGFUSE_BASE_URL")) or _normalize_base_url(
        os.environ.get("LANGFUSE_HOST")
    )


def resolve_runtime_langfuse_base_url(
    configured_base_url: str | None,
    *,
    running_in_container: bool | None = None,
) -> tuple[str, str]:
    """Return the Langfuse base URL a backend/runtime process should call.

    Operators often use ``http://localhost:3000`` in the admin UI because that is
    the host-browser URL. Inside Docker, however, ``localhost`` is the runtime
    container itself, so local self-hosted Langfuse must be addressed by Compose
    service DNS (``http://langfuse-web:3000``).

    The helper only remaps local-host URLs while running inside a container and
    only when runtime env points to the Langfuse Compose service. Cloud or other
    explicit remote URLs remain untouched.
    """
    configured = _normalize_base_url(configured_base_url) or _DEFAULT_LANGFUSE_BASE_URL
    explicit_runtime = _normalize_base_url(os.environ.get("WOS_LANGFUSE_RUNTIME_BASE_URL"))
    if explicit_runtime:
        return explicit_runtime, "runtime_override_env"

    env_base_url = _runtime_env_langfuse_base_url()
    if not env_base_url:
        return configured, "configured"

    in_container = _inside_container() if running_in_container is None else running_in_container
    configured_host = _base_url_host(configured)
    env_host = _base_url_host(env_base_url)
    if (
        in_container
        and configured_host in _LOCALHOST_LANGFUSE_HOSTS
        and env_host in _DOCKER_LANGFUSE_HOSTS
    ):
        return env_base_url, "docker_service_env_for_localhost"

    return configured, "configured"


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


def is_local_langfuse_evidence_context(base_url: str | None = None) -> bool:
    """Return whether the current Langfuse target is local diagnostic evidence."""
    explicit_local = (
        (os.environ.get("WOS_LANGFUSE_LOCAL_EVIDENCE") or "").strip().lower() in _TRUTHY
        or (os.environ.get("WOS_LANGFUSE_EVIDENCE_SCOPE") or "").strip() == LOCAL_LANGFUSE_EVIDENCE_SCOPE
        or (os.environ.get("WOS_LANGFUSE_PROOF_LEVEL") or "").strip() == LOCAL_LANGFUSE_PROOF_LEVEL
    )
    if explicit_local:
        return True

    environment_values = (
        os.environ.get("WOS_LANGFUSE_EVIDENCE_ENVIRONMENT"),
        os.environ.get("LANGFUSE_ENVIRONMENT"),
        os.environ.get("WOS_LANGFUSE_TRACING_ENVIRONMENT"),
    )
    if any(str(value or "").strip().lower() in _LOCAL_LANGFUSE_ENVIRONMENTS for value in environment_values):
        return True

    candidate_urls = (
        base_url,
        os.environ.get("WOS_LANGFUSE_RUNTIME_BASE_URL"),
        os.environ.get("LANGFUSE_BASE_URL"),
        os.environ.get("LANGFUSE_HOST"),
    )
    local_hosts = _LOCALHOST_LANGFUSE_HOSTS | _DOCKER_LANGFUSE_HOSTS
    return any(_base_url_host(value) in local_hosts for value in candidate_urls if value)


def local_langfuse_evidence_metadata(base_url: str | None = None) -> dict[str, object]:
    """Return mandatory local-only metadata for local Langfuse evidence.

    The helper accepts explicit env markers, local Langfuse environments, and local
    self-hosted base URLs. This keeps local traces diagnostic even if an operator
    enters the browser URL (``http://localhost:3000``) in backend settings.
    """
    if not is_local_langfuse_evidence_context(base_url):
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
        "local_only": True,
        "live_or_staging_evidence": False,
    }
