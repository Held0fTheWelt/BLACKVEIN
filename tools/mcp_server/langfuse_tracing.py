"""Langfuse MCP tracing — best-effort span emission for MCP tool calls.

Credentials are fetched from the backend via the internal observability endpoint
(same mechanism as world-engine).  No LANGFUSE_PUBLIC_KEY / SECRET_KEY in env
required; just set:

    LANGFUSE_MCP_ENABLED=1
    BACKEND_BASE_URL=http://localhost:8000          # already used by MCP server
    INTERNAL_RUNTIME_CONFIG_TOKEN=<token>           # same as world-engine

Direct env vars (LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY) override / serve as
fallback when the backend is unreachable.

Linked mode: caller injects  "_meta": {"langfuse_trace_id": "<id>"}  (or W3C
traceparent) into params → span is attached to an upstream story runtime trace.
Standalone mode: new Langfuse trace per MCP tool call.

Never raises from public methods — all tracing failures are suppressed so the
MCP dispatch path is never affected.
"""
from __future__ import annotations

import os
from typing import Any

_REDACTED_KEYS = frozenset({"password", "token", "secret", "key", "api_key", "bearer", "credential"})
_MAX_VALUE_LEN = 500
_MAX_RESULT_LEN = 2000


def _sanitize_arguments(arguments: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in arguments.items():
        lower_k = str(k).lower()
        if any(r in lower_k for r in _REDACTED_KEYS):
            out[k] = "[redacted]"
        elif isinstance(v, str) and len(v) > _MAX_VALUE_LEN:
            out[k] = v[:_MAX_VALUE_LEN] + "…"
        else:
            out[k] = v
    return out


def _sanitize_result(result: dict[str, Any] | None) -> dict[str, Any] | str | None:
    if result is None:
        return None
    try:
        import json
        raw = json.dumps(result)
    except Exception:
        return str(result)[:_MAX_RESULT_LEN]
    if len(raw) > _MAX_RESULT_LEN:
        return raw[:_MAX_RESULT_LEN] + "…"
    return result


def _extract_parent_trace_id(meta: dict[str, Any] | None) -> str | None:
    """Read Langfuse trace ID from _meta.langfuse_trace_id or W3C traceparent."""
    if not meta or not isinstance(meta, dict):
        return None
    lf_id = meta.get("langfuse_trace_id")
    if isinstance(lf_id, str) and lf_id.strip():
        return lf_id.strip()
    tp = meta.get("traceparent", "")
    parts = str(tp).split("-")
    if len(parts) == 4 and parts[0] == "00" and len(parts[1]) == 32:
        return parts[1]
    return None


class McpLangfuseTracer:
    """Best-effort Langfuse tracing for MCP tool calls.

    Credentials are resolved in this order:
    1. LANGFUSE_PUBLIC_KEY / LANGFUSE_SECRET_KEY env vars (direct override)
    2. Backend internal endpoint (INTERNAL_RUNTIME_CONFIG_TOKEN required)

    The Langfuse client is initialised lazily on the first tool call so the
    backend fetch does not block server startup.
    """

    _instance: McpLangfuseTracer | None = None

    def __init__(self) -> None:
        self._enabled_flag = os.environ.get("LANGFUSE_MCP_ENABLED", "").strip() == "1"
        # Direct env vars (override / offline fallback)
        self._public_key = os.environ.get("LANGFUSE_PUBLIC_KEY", "").strip()
        self._secret_key = os.environ.get("LANGFUSE_SECRET_KEY", "").strip()
        self._base_url = (
            os.environ.get("LANGFUSE_BASE_URL", "").strip()
            or os.environ.get("LANGFUSE_HOST", "").strip()
            or "https://cloud.langfuse.com"
        )
        # Backend credential source (mirrors world-engine adapter + MCP runtime variants)
        self._backend_url = (
            os.environ.get("BACKEND_RUNTIME_CONFIG_URL", "").strip()
            or os.environ.get("BACKEND_INTERNAL_URL", "").strip()
            or os.environ.get("BACKEND_BASE_URL", "").strip()
            or "http://localhost:8000"
        ).rstrip("/")
        self._internal_token = (
            os.environ.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "").strip()
            or os.environ.get("BACKEND_INTERNAL_RUNTIME_CONFIG_TOKEN", "").strip()
            or os.environ.get("RUNTIME_CONFIG_TOKEN", "").strip()
        )
        self._credentials_fetched = False
        self._lf: Any = None

    @classmethod
    def get_instance(cls) -> McpLangfuseTracer:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def is_enabled(self) -> bool:
        return self._enabled_flag

    def _fetch_credentials_from_backend(self) -> None:
        """Fetch Langfuse credentials from backend internal endpoint (best-effort)."""
        backend_url = (
            os.environ.get("BACKEND_RUNTIME_CONFIG_URL", "").strip()
            or os.environ.get("BACKEND_INTERNAL_URL", "").strip()
            or os.environ.get("BACKEND_BASE_URL", "").strip()
            or self._backend_url
            or "http://localhost:8000"
        ).rstrip("/")
        runtime_token = (
            os.environ.get("INTERNAL_RUNTIME_CONFIG_TOKEN", "").strip()
            or os.environ.get("BACKEND_INTERNAL_RUNTIME_CONFIG_TOKEN", "").strip()
            or os.environ.get("RUNTIME_CONFIG_TOKEN", "").strip()
            or self._internal_token
        )
        bearer_token = os.environ.get("BACKEND_BEARER_TOKEN", "").strip()
        if not runtime_token and not bearer_token:
            return
        try:
            import httpx  # type: ignore[import]
            endpoint = f"{backend_url}/api/v1/internal/observability/langfuse-credentials"
            header_attempts: list[dict[str, str]] = []
            if runtime_token:
                header_attempts.append({"X-Internal-Config-Token": runtime_token})
            if bearer_token:
                # Optional runtime deployment fallback: some setups terminate auth upstream.
                header_attempts.append({"Authorization": f"Bearer {bearer_token}"})
            with httpx.Client(timeout=5.0) as client:
                for headers in header_attempts:
                    resp = client.get(endpoint, headers=headers)
                    if resp.status_code != 200:
                        continue
                    data = resp.json().get("data", {})
                    if not data.get("enabled"):
                        return
                    pk = str(data.get("public_key") or "").strip()
                    sk = str(data.get("secret_key") or "").strip()
                    if pk and sk:
                        self._public_key = pk
                        self._secret_key = sk
                        self._base_url = str(data.get("base_url") or self._base_url)
                        self._backend_url = backend_url
                        if runtime_token:
                            self._internal_token = runtime_token
                        return
        except Exception:
            pass

    def _get_client(self) -> Any:
        if self._lf is not None:
            return self._lf
        if not self._enabled_flag:
            return None
        if not self._credentials_fetched:
            self._credentials_fetched = True
            if not (self._public_key and self._secret_key):
                self._fetch_credentials_from_backend()
        if not (self._public_key and self._secret_key):
            return None
        try:
            from langfuse import Langfuse  # type: ignore[import]
            self._lf = Langfuse(
                public_key=self._public_key,
                secret_key=self._secret_key,
                base_url=self._base_url,
            )
        except Exception:
            pass
        return self._lf

    def trace_tool_call(
        self,
        *,
        wos_trace_id: str,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any] | None,
        duration_ms: float,
        status: str,
        error: str | None = None,
        suite: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        """Emit a Langfuse span for an MCP tool call. Never raises."""
        if not self._enabled_flag:
            return
        try:
            lf = self._get_client()
            if lf is None:
                return
            parent_trace_id = _extract_parent_trace_id(meta)
            safe_args = _sanitize_arguments(arguments)
            safe_result = _sanitize_result(result)
            span_metadata: dict[str, Any] = {
                "wos_trace_id": wos_trace_id,
                "suite": suite or "unknown",
                "duration_ms": round(duration_ms, 1),
                "status": status,
                "span_origin": "mcp_tool",
                "trace_origin": "mcp",
                "execution_tier": "diagnostic",
                "canonical_player_flow": False,
                "tool_name": tool_name,
            }
            if error:
                span_metadata["error"] = error
            if parent_trace_id:
                trace = lf.trace(id=parent_trace_id)
            else:
                trace = lf.trace(
                    name=f"mcp.{tool_name}",
                    metadata={
                        "wos_trace_id": wos_trace_id,
                        "suite": suite or "unknown",
                        "trace_origin": "mcp",
                        "execution_tier": "diagnostic",
                        "canonical_player_flow": False,
                        "tool_name": tool_name,
                    },
                )
            span = trace.span(
                name=f"mcp.tool.{tool_name}",
                input=safe_args,
                metadata=span_metadata,
            )
            span.end(
                output=safe_result,
                level="ERROR" if status == "error" else "DEFAULT",
            )
            lf.flush()
        except Exception:
            pass
