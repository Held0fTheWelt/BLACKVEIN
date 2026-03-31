"""Structured audit logging with JSON formatting and secret masking."""

import logging
import json
import hashlib
from datetime import datetime, timezone

from app.observability.trace import get_trace_id


# Custom JSON formatter for audit logs
class JSONFormatter(logging.Formatter):
    """Format log records as JSON lines."""

    def format(self, record: logging.LogRecord) -> str:
        """Format record as JSON."""
        # record.msg should be a dict already (set by our logging functions)
        if isinstance(record.msg, dict):
            return json.dumps(record.msg)
        # Fallback for non-dict messages
        return json.dumps({"message": str(record.msg)})


def _get_or_create_audit_logger() -> logging.Logger:
    """Get or create the wos.audit logger with JSON formatter."""
    logger = logging.getLogger("wos.audit")

    # Only configure if not already configured (avoid duplicate handlers)
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    return logger


def get_audit_logger() -> logging.Logger:
    """Get the audit logger."""
    return _get_or_create_audit_logger()


def safe_hash(text: str) -> str:
    """Hash text for safe logging (SHA-256 hex)."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def log_api_endpoint(
    trace_id: str | None,
    session_id: str | None,
    endpoint: str,
    method: str,
    status_code: int,
    duration_ms: int,
    outcome: str,
    error_code: str | None = None,
) -> None:
    """Log API endpoint access (A1.3 operator endpoints, /export, etc)."""
    logger = get_audit_logger()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event": "api.endpoint",
        "endpoint": endpoint,
        "method": method,
        "session_id": session_id,
        "status_code": status_code,
        "duration_ms": duration_ms,
        "outcome": outcome,
    }
    if error_code:
        entry["error_code"] = error_code

    logger.info(entry)


def log_turn_request(
    trace_id: str | None,
    session_id: str | None,
    operator_input: str,
    status_code: int,
    duration_ms: int,
    error_code: str | None = None,
) -> None:
    """Log turn request (web boundary event)."""
    logger = get_audit_logger()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event": "turn.request",
        "session_id": session_id,
        "operator_input_hash": safe_hash(operator_input),
        "operator_input_length": len(operator_input),
        "status_code": status_code,
        "duration_ms": duration_ms,
        "outcome": "ok" if status_code == 200 else "error",
    }
    if error_code:
        entry["error_code"] = error_code

    logger.info(entry)


def log_turn_execution(
    trace_id: str | None,
    session_id: str | None,
    execution_mode: str,
    turn_before: int,
    turn_after: int,
    outcome: str,
    error_code: str | None = None,
) -> None:
    """Log turn execution (runtime boundary event)."""
    logger = get_audit_logger()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event": "turn.execute",
        "session_id": session_id,
        "execution_mode": execution_mode,
        "turn_before": turn_before,
        "turn_after": turn_after,
        "outcome": outcome,
    }
    if error_code:
        entry["error_code"] = error_code

    logger.info(entry)


def log_mcp_tool_call(
    trace_id: str | None,
    session_id: str | None,
    tool_name: str,
    duration_ms: int,
    success: bool,
    error: str | None = None,
) -> None:
    """Log MCP tool call (preflight enrichment event)."""
    logger = get_audit_logger()

    entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "trace_id": trace_id,
        "event": "mcp.tool_call",
        "session_id": session_id,
        "tool_name": tool_name,
        "duration_ms": duration_ms,
        "success": success,
    }
    if error:
        entry["error"] = error

    logger.info(entry)
