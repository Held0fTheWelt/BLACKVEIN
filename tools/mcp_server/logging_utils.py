"""Structured logging helpers and optional backend telemetry ingest."""

import json
import os
import sys
import time
from contextvars import ContextVar, Token
from uuid import uuid4
from typing import Any

_telemetry_buffer: ContextVar[list[dict] | None] = ContextVar("mcp_telemetry_buffer", default=None)
_telemetry_suite: ContextVar[str] = ContextVar("mcp_telemetry_suite", default="all")


def generate_trace_id() -> str:
    """Generate UUID v4 trace ID."""
    return str(uuid4())


def begin_telemetry_capture(wos_mcp_suite_label: str) -> Token:
    """Start capturing stderr-shaped records for optional HTTP ingest (per JSON-RPC dispatch)."""
    _telemetry_suite.set(wos_mcp_suite_label)
    return _telemetry_buffer.set([])


def end_telemetry_capture(buffer_token: Token) -> list[dict]:
    """Stop capture and return accumulated records (detaches buffer from context)."""
    buf = _telemetry_buffer.get()
    _telemetry_buffer.reset(buffer_token)
    return list(buf or [])


def _enqueue_telemetry(entry: dict) -> None:
    buf = _telemetry_buffer.get()
    if buf is None:
        return
    rec = dict(entry)
    rec["wos_mcp_suite"] = _telemetry_suite.get()
    buf.append(rec)


def flush_telemetry_to_backend(records: list[dict]) -> None:
    """POST ``records`` to ``WOS_MCP_TELEMETRY_INGEST_URL`` with ``MCP_SERVICE_TOKEN`` (best-effort)."""
    url = (os.environ.get("WOS_MCP_TELEMETRY_INGEST_URL") or "").strip()
    if not url or not records:
        return
    token = (os.environ.get("MCP_SERVICE_TOKEN") or "").strip()
    if not token:
        return
    try:
        import requests

        requests.post(
            url,
            json={"records": records},
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            },
            timeout=3,
        )
    except Exception as exc:  # noqa: BLE001 — never break MCP on telemetry failure
        err = {"type": "telemetry_ingest_error", "message": str(exc)[:200]}
        print(json.dumps(err), file=sys.stderr)


def log_request(trace_id: str, method: str, params: dict) -> None:
    """Log incoming JSON-RPC request."""
    entry = {
        "type": "request",
        "trace_id": trace_id,
        "timestamp": time.time(),
        "method": method,
        "params_keys": list(params.keys()) if params else [],
    }
    print(json.dumps(entry), file=sys.stderr)
    _enqueue_telemetry(entry)


def log_response(
    trace_id: str, method: str, status: str, duration_ms: float, error_code: str | None = None
) -> None:
    """Log outgoing JSON-RPC response."""
    entry: dict[str, Any] = {
        "type": "response",
        "trace_id": trace_id,
        "timestamp": time.time(),
        "method": method,
        "status": status,
        "duration_ms": round(duration_ms, 2),
    }
    if error_code:
        entry["error_code"] = error_code
    print(json.dumps(entry), file=sys.stderr)
    _enqueue_telemetry(entry)


def log_tool_call(
    trace_id: str,
    tool_name: str,
    duration_ms: float,
    status: str,
    error_code: str | None = None,
    *,
    tool_class: str | None = None,
    authority_source: str | None = None,
    operating_profile: str | None = None,
) -> None:
    """Log tool execution (M1: canonical audit fields)."""
    entry: dict[str, Any] = {
        "type": "tool_call",
        "trace_id": trace_id,
        "timestamp": time.time(),
        "tool_name": tool_name,
        "duration_ms": round(duration_ms, 2),
        "status": status,
    }
    if error_code:
        entry["error_code"] = error_code
    if tool_class:
        entry["tool_class"] = tool_class
    if authority_source:
        entry["authority_source"] = authority_source
    if operating_profile:
        entry["operating_profile"] = operating_profile
    print(json.dumps(entry), file=sys.stderr)
    _enqueue_telemetry(entry)
