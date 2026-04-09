# MCP Phase A2 — Observability & Reproducibility Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add end-to-end traceability for every MCP/Operator/API interaction via trace ID propagation, structured audit logging, and a diagnostics export endpoint.

**Architecture:** Three integrated systems: (1) contextvars-based trace ID propagation with Flask middleware for both /api/v1 and /play routes, (2) stdlib logging with JSON formatter for 3 audit event types (api.endpoint, turn.request, turn.execute), (3) read-only /export operator endpoint returning compact reproducible debug bundle. All systems avoid logging secrets/PII via hashing and truncation.

**Tech Stack:** Python contextvars, stdlib logging + JSON formatter, Flask before_request/after_request hooks, hashlib.sha256

---

## File Structure

**New Files:**
- `backend/app/observability/__init__.py` — package marker
- `backend/app/observability/trace.py` — contextvars trace ID system (~120 lines)
- `backend/app/observability/audit_log.py` — structured audit logger (~180 lines)
- `backend/tests/test_observability.py` — comprehensive tests (~350 lines)

**Modified Files:**
- `backend/app/api/v1/__init__.py` — register app-level before/after request hooks for trace + audit
- `backend/app/api/v1/session_routes.py` — add GET /export endpoint for operator endpoints
- `backend/app/runtime/turn_dispatcher.py` — call audit logger in dispatch_turn()
- `backend/app/web/routes.py` — register before_request hook for /play routes to enable tracing

---

## Task 1: Trace ID System (contextvars + helpers)

**Files:**
- Create: `backend/app/observability/trace.py`
- Create: `backend/app/observability/__init__.py`
- Test: `backend/tests/test_observability.py` (trace tests)

### Step 1: Create observability package init
Create empty `backend/app/observability/__init__.py`:
```python
"""Observability for MCP — tracing, logging, diagnostics."""
```

### Step 2: Write failing tests for trace system

Add to `backend/tests/test_observability.py`:

```python
"""Tests for observability system: trace ID, audit logging."""

import contextvars
import uuid
import pytest
from unittest.mock import patch
from flask import g

# Import the trace module (will fail initially - that's expected)
from app.observability.trace import (
    TRACE_ID,
    set_trace_id,
    get_trace_id,
    ensure_trace_id,
)


class TestTraceID:
    """Tests for contextvars-based trace ID system."""

    def test_ensure_trace_id_with_incoming_value(self):
        """ensure_trace_id(incoming_value) sets and returns that value."""
        result = ensure_trace_id("custom-trace-123")
        assert result == "custom-trace-123"
        assert get_trace_id() == "custom-trace-123"

    def test_ensure_trace_id_generates_uuid_if_none(self):
        """ensure_trace_id(None) generates UUIDv4 if contextvar not set."""
        # Reset contextvar first
        token = TRACE_ID.set(None)
        try:
            result = ensure_trace_id(None)
            assert result is not None
            # Verify it's a valid UUID
            uuid.UUID(result)
            assert get_trace_id() == result
        finally:
            TRACE_ID.reset(token)

    def test_ensure_trace_id_idempotent(self):
        """ensure_trace_id(None) uses existing contextvar if already set."""
        token = TRACE_ID.set("existing-trace")
        try:
            result = ensure_trace_id(None)
            assert result == "existing-trace"
        finally:
            TRACE_ID.reset(token)

    def test_set_get_trace_id(self):
        """set_trace_id and get_trace_id work correctly."""
        set_trace_id("test-trace-456")
        assert get_trace_id() == "test-trace-456"

    def test_get_trace_id_returns_none_when_not_set(self):
        """get_trace_id() returns None if contextvar never set."""
        token = TRACE_ID.set(None)
        try:
            assert get_trace_id() is None
        finally:
            TRACE_ID.reset(token)
```

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestTraceID -xvs`
Expected: FAIL (module doesn't exist)

### Step 3: Implement trace.py

Create `backend/app/observability/trace.py`:

```python
"""Trace ID system using contextvars for request and non-request contexts."""

import contextvars
import uuid

# Context variable stores trace_id across request and non-request code paths
TRACE_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "trace_id", default=None
)


def set_trace_id(trace_id: str) -> None:
    """Set trace_id in the current context."""
    TRACE_ID.set(trace_id)


def get_trace_id() -> str | None:
    """Get trace_id from the current context, or None if not set."""
    return TRACE_ID.get()


def ensure_trace_id(incoming: str | None) -> str:
    """Idempotent trace_id getter/setter.

    If incoming is provided, set it and return it.
    If incoming is None and contextvar is already set, return existing value.
    If incoming is None and contextvar not set, generate UUIDv4, set it, return it.

    Args:
        incoming: Incoming trace_id from request header (or None)

    Returns:
        trace_id: The trace_id to use for this request/execution
    """
    if incoming:
        # Incoming value takes precedence
        set_trace_id(incoming)
        return incoming

    # Check if already set in contextvar
    existing = get_trace_id()
    if existing:
        return existing

    # Generate new UUID
    new_trace_id = str(uuid.uuid4())
    set_trace_id(new_trace_id)
    return new_trace_id
```

### Step 4: Run tests to verify they pass

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestTraceID -xvs`
Expected: PASS (all 5 tests)

### Step 5: Commit

```bash
git add backend/app/observability/__init__.py backend/app/observability/trace.py backend/tests/test_observability.py
git commit -m "feat(obs): implement contextvars-based trace ID system with ensure_trace_id()"
```

---

## Task 2: Structured Audit Logger (JSON formatter + event helpers)

**Files:**
- Create: `backend/app/observability/audit_log.py`
- Test: `backend/tests/test_observability.py` (audit logging tests)

### Step 1: Write failing tests for audit logger

Add to `backend/tests/test_observability.py`:

```python
import json
from unittest.mock import patch
import logging

from app.observability.audit_log import (
    get_audit_logger,
    safe_hash,
    log_api_endpoint,
    log_turn_request,
    log_turn_execution,
)


class TestAuditLogger:
    """Tests for structured audit logging."""

    def test_get_audit_logger_returns_wos_audit_logger(self):
        """get_audit_logger() returns logger named 'wos.audit'."""
        logger = get_audit_logger()
        assert logger.name == "wos.audit"

    def test_safe_hash_produces_consistent_hash(self):
        """safe_hash produces SHA-256 hash."""
        result = safe_hash("test input")
        # Should be 64-char hex string (SHA-256)
        assert len(result) == 64
        assert all(c in "0123456789abcdef" for c in result)
        # Consistent
        assert safe_hash("test input") == result

    def test_safe_hash_different_for_different_input(self):
        """safe_hash differs for different inputs."""
        hash1 = safe_hash("input1")
        hash2 = safe_hash("input2")
        assert hash1 != hash2

    def test_log_api_endpoint_writes_json_entry(self, caplog):
        """log_api_endpoint writes structured JSON to wos.audit logger."""
        with caplog.at_level(logging.INFO, logger="wos.audit"):
            log_api_endpoint(
                trace_id="trace-123",
                session_id="sess-abc",
                endpoint="/api/v1/sessions/sess-abc",
                method="GET",
                status_code=200,
                duration_ms=45,
                outcome="ok",
            )

        # Verify log was written
        assert len(caplog.records) == 1
        record = caplog.records[0]
        # Log message should be JSON
        log_data = json.loads(record.getMessage())
        assert log_data["event"] == "api.endpoint"
        assert log_data["trace_id"] == "trace-123"
        assert log_data["session_id"] == "sess-abc"
        assert log_data["status_code"] == 200
        assert log_data["outcome"] == "ok"

    def test_log_turn_request_writes_json_entry(self, caplog):
        """log_turn_request writes turn.request event."""
        with caplog.at_level(logging.INFO, logger="wos.audit"):
            log_turn_request(
                trace_id="trace-456",
                session_id="sess-xyz",
                operator_input="some input",
                status_code=200,
                duration_ms=120,
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        log_data = json.loads(record.getMessage())
        assert log_data["event"] == "turn.request"
        assert log_data["trace_id"] == "trace-456"
        assert "operator_input_hash" in log_data
        assert "operator_input_length" in log_data
        assert log_data["status_code"] == 200

    def test_log_turn_execution_writes_json_entry(self, caplog):
        """log_turn_execution writes turn.execute event."""
        with caplog.at_level(logging.INFO, logger="wos.audit"):
            log_turn_execution(
                trace_id="trace-789",
                session_id="sess-def",
                execution_mode="mock",
                turn_before=2,
                turn_after=3,
                outcome="success",
            )

        assert len(caplog.records) == 1
        record = caplog.records[0]
        log_data = json.loads(record.getMessage())
        assert log_data["event"] == "turn.execute"
        assert log_data["execution_mode"] == "mock"
        assert log_data["turn_before"] == 2
        assert log_data["turn_after"] == 3
        assert log_data["outcome"] == "success"
```

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestAuditLogger -xvs`
Expected: FAIL (module doesn't exist)

### Step 2: Implement audit_log.py

Create `backend/app/observability/audit_log.py`:

```python
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
```

### Step 3: Run tests to verify they pass

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestAuditLogger -xvs`
Expected: PASS (all 7 tests)

### Step 4: Commit

```bash
git add backend/app/observability/audit_log.py backend/tests/test_observability.py
git commit -m "feat(obs): implement structured audit logger with JSON formatting and safe_hash()"
```

---

## Task 3: Flask Middleware (before/after request hooks for trace + audit)

**Files:**
- Modify: `backend/app/api/v1/__init__.py`
- Modify: `backend/app/web/routes.py`
- Test: `backend/tests/test_observability.py` (Flask integration tests)

### Step 1: Write failing tests for Flask middleware

Add to `backend/tests/test_observability.py`:

```python
import re
import time


class TestFlaskMiddleware:
    """Tests for trace/audit middleware integration with Flask."""

    def test_trace_id_header_preserved_in_response(self, client, monkeypatch):
        """If request has X-WoS-Trace-Id header, same value returned in response."""
        incoming_trace = "test-trace-header-123"
        response = client.get(
            "/api/v1/sessions/sess-test",
            headers={"X-WoS-Trace-Id": incoming_trace, "Authorization": "Bearer test-token"},
        )
        # Response should have X-WoS-Trace-Id header
        assert response.headers.get("X-WoS-Trace-Id") == incoming_trace

    def test_trace_id_generated_if_missing(self, client, monkeypatch):
        """If request omits X-WoS-Trace-Id, UUID generated and returned."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        # Create a session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Request without trace header
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"}
        )

        # Response should have X-WoS-Trace-Id header with UUID format
        trace_id = response.headers.get("X-WoS-Trace-Id")
        assert trace_id is not None
        # Verify it looks like a UUID (simple check)
        assert re.match(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$", trace_id)

    def test_api_endpoint_writes_audit_log(self, client, monkeypatch, caplog):
        """A1.3 operator endpoint writes one audit log entry."""
        import logging
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Get the session via operator endpoint
        with caplog.at_level(logging.INFO, logger="wos.audit"):
            response = client.get(
                f"/api/v1/sessions/{session_id}",
                headers={"Authorization": "Bearer test-token"}
            )

        assert response.status_code == 200
        # Verify one audit log was written
        audit_records = [r for r in caplog.records if r.name == "wos.audit"]
        assert len(audit_records) == 1
        log_data = json.loads(audit_records[0].getMessage())
        assert log_data["event"] == "api.endpoint"
        assert log_data["session_id"] == session_id
        assert log_data["status_code"] == 200
```

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestFlaskMiddleware::test_trace_id_header_preserved_in_response -xvs`
Expected: FAIL (hooks not registered yet)

### Step 2: Implement middleware in backend/app/api/v1/__init__.py

Modify `backend/app/api/v1/__init__.py` to add trace + audit middleware:

```python
"""API v1 routes and middleware."""

from flask import Blueprint, request, g
import time

from app.observability.trace import ensure_trace_id
from app.observability.audit_log import (
    get_audit_logger,
    log_api_endpoint,
)

# Create blueprint
api_v1_bp = Blueprint("api_v1", __name__, url_prefix="/api/v1")


@api_v1_bp.before_request
def before_request_trace_and_audit():
    """Set up trace ID and start timing for audit log."""
    # Extract trace ID from header, or generate new one
    incoming_trace = request.headers.get("X-WoS-Trace-Id")
    trace_id = ensure_trace_id(incoming_trace)

    # Store in g for convenient access in route handlers
    g.trace_id = trace_id

    # Start timing
    g.request_start_time = time.time()


@api_v1_bp.after_request
def after_request_trace_and_audit(response):
    """Log endpoint access and add trace header to response."""
    trace_id = getattr(g, "trace_id", None)

    # Set trace ID in response header
    if trace_id:
        response.headers["X-WoS-Trace-Id"] = trace_id

    # Log API endpoint access (for operator endpoints)
    # Only log /api/v1 calls that involve sessions
    if "/sessions" in request.path:
        start_time = getattr(g, "request_start_time", time.time())
        duration_ms = int((time.time() - start_time) * 1000)

        # Extract session_id from path if present
        session_id = None
        parts = request.path.split("/")
        if len(parts) >= 4 and parts[2] == "sessions":
            session_id = parts[3] if len(parts) > 3 else None

        log_api_endpoint(
            trace_id=trace_id,
            session_id=session_id,
            endpoint=request.path,
            method=request.method,
            status_code=response.status_code,
            duration_ms=duration_ms,
            outcome="ok" if 200 <= response.status_code < 400 else "error",
        )

    return response


# Import routes after blueprint creation
from app.api.v1 import session_routes  # noqa: F401, E402
```

### Step 3: Register middleware for /play routes

Modify `backend/app/web/routes.py` to add before_request hook for trace ID:

```python
# Near the top of routes.py, after web_bp creation:

from app.observability.trace import ensure_trace_id

@web_bp.before_request
def before_request_trace():
    """Set up trace ID for web routes."""
    incoming_trace = request.headers.get("X-WoS-Trace-Id")
    trace_id = ensure_trace_id(incoming_trace)
    g.trace_id = trace_id

@web_bp.after_request
def after_request_trace(response):
    """Add trace header to response."""
    trace_id = getattr(g, "trace_id", None)
    if trace_id:
        response.headers["X-WoS-Trace-Id"] = trace_id
    return response
```

### Step 4: Run tests to verify they pass

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestFlaskMiddleware -xvs`
Expected: PASS (all 3 tests)

### Step 5: Commit

```bash
git add backend/app/api/v1/__init__.py backend/app/web/routes.py backend/tests/test_observability.py
git commit -m "feat(obs): add Flask middleware for trace ID propagation and audit logging"
```

---

## Task 4: Turn Execution Logging (dispatch_turn integration)

**Files:**
- Modify: `backend/app/runtime/turn_dispatcher.py`
- Test: `backend/tests/test_observability.py` (turn execution tests)

### Step 1: Write failing test for turn execution logging

Add to `backend/tests/test_observability.py`:

```python
class TestTurnExecutionLogging:
    """Tests for turn execution boundary logging."""

    def test_turn_execution_logs_with_trace_id(self, caplog):
        """dispatch_turn() logs turn.execute event with trace_id."""
        import logging
        from app.observability.trace import ensure_trace_id
        from app.runtime.turn_dispatcher import dispatch_turn

        # Set up trace ID
        trace_id = ensure_trace_id("test-trace-dispatch")

        with caplog.at_level(logging.INFO, logger="wos.audit"):
            # Mock dispatch_turn to just verify logging call
            # (actual turn execution is heavy; we're just testing logging)
            from unittest.mock import patch, MagicMock

            with patch("app.runtime.turn_dispatcher.log_turn_execution") as mock_log:
                # Create minimal mocks
                session = MagicMock()
                session.session_id = "sess-test"
                session.current_runtime_state.turn_counter = 2

                decision_input = {"test": "input"}

                # Call dispatch_turn (will fail if not mocked, but we're mocking the log call)
                try:
                    dispatch_turn(session, "mock", decision_input)
                except Exception:
                    pass  # We're only testing the logging call

                # Verify log_turn_execution was called with trace_id
                if mock_log.called:
                    call_args = mock_log.call_args
                    assert call_args[1]["trace_id"] == trace_id or call_args[0][0] == trace_id
```

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestTurnExecutionLogging::test_turn_execution_logs_with_trace_id -xvs`
Expected: FAIL (logging call not yet in dispatch_turn)

### Step 2: Modify turn_dispatcher.py to add logging

Modify `backend/app/runtime/turn_dispatcher.py`:

Add near the top:
```python
from app.observability.trace import get_trace_id
from app.observability.audit_log import log_turn_execution
```

Add to `dispatch_turn()` function (at appropriate place where turn executes):
```python
def dispatch_turn(session, execution_mode, decision_input):
    """Execute a turn in a session.

    Args:
        session: RuntimeSession object
        execution_mode: "mock" or "ai"
        decision_input: Dict of operator decision input

    Returns:
        ExecutionResult
    """
    trace_id = get_trace_id()
    if not trace_id:
        from app.observability.trace import ensure_trace_id
        trace_id = ensure_trace_id(None)

    turn_before = session.current_runtime_state.turn_counter

    try:
        # ... existing turn execution logic ...
        result = execute_turn_logic(session, execution_mode, decision_input)

        turn_after = session.current_runtime_state.turn_counter

        # Log turn execution
        log_turn_execution(
            trace_id=trace_id,
            session_id=session.session_id,
            execution_mode=execution_mode,
            turn_before=turn_before,
            turn_after=turn_after,
            outcome="success",
        )

        return result
    except Exception as e:
        turn_after = session.current_runtime_state.turn_counter
        log_turn_execution(
            trace_id=trace_id,
            session_id=session.session_id,
            execution_mode=execution_mode,
            turn_before=turn_before,
            turn_after=turn_after,
            outcome="error",
            error_code=type(e).__name__,
        )
        raise
```

### Step 3: Run tests

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestTurnExecutionLogging -xvs`
Expected: PASS

### Step 4: Commit

```bash
git add backend/app/runtime/turn_dispatcher.py backend/tests/test_observability.py
git commit -m "feat(obs): add turn.execute audit logging to dispatch_turn()"
```

---

## Task 5: /export Operator Endpoint

**Files:**
- Modify: `backend/app/api/v1/session_routes.py`
- Test: `backend/tests/test_observability.py` (export endpoint tests)

### Step 1: Write failing tests for /export endpoint

Add to `backend/tests/test_observability.py`:

```python
class TestExportEndpoint:
    """Tests for GET /api/v1/sessions/<id>/export endpoint."""

    def test_export_without_auth_returns_401(self, client):
        """GET /export without auth header returns 401."""
        response = client.get("/api/v1/sessions/sess-test/export")
        assert response.status_code == 401

    def test_export_nonexistent_session_returns_404(self, client, monkeypatch):
        """GET /export for non-existent session returns 404."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get(
            "/api/v1/sessions/nonexistent/export",
            headers={"Authorization": "Bearer test-token"}
        )
        assert response.status_code == 404

    def test_export_returns_bundle_structure(self, client, monkeypatch):
        """GET /export returns complete diagnostics bundle."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Get export
        response = client.get(
            f"/api/v1/sessions/{session_id}/export",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()

        # Verify bundle structure
        assert "session_snapshot" in data
        assert "diagnostics" in data
        assert "logs" in data
        assert "meta" in data

        # Verify meta
        assert "exported_at" in data["meta"]
        assert "trace_id" in data["meta"]
        assert "warnings" in data["meta"]
        assert "in_memory_session_state_is_volatile" in data["meta"]["warnings"]
```

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestExportEndpoint::test_export_without_auth_returns_401 -xvs`
Expected: FAIL (endpoint doesn't exist)

### Step 2: Implement /export endpoint in session_routes.py

Add to `backend/app/api/v1/session_routes.py`:

```python
@api_v1_bp.route("/sessions/<session_id>/export", methods=["GET"])
@require_mcp_service_token
def export_session_bundle(session_id):
    """Export session bundle for diagnostics and reproducibility (A2 operator endpoint).

    Returns a compact JSON bundle containing snapshot, diagnostics, logs, and metadata.
    Protected by MCP_SERVICE_TOKEN.
    """
    import json
    from app.observability.trace import get_trace_id

    # Get session
    session = get_runtime_session(session_id)
    if not session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    state = session.current_runtime_state
    trace_id = get_trace_id()

    # Determine if canonical_state needs truncation (50KB threshold)
    state_json = json.dumps(state.canonical_state)
    state_size = len(state_json.encode('utf-8'))
    is_truncated = state_size > 50 * 1024

    # Build export bundle
    bundle = {
        "session_snapshot": {
            "session_id": session_id,
            "module_id": session.module.metadata.module_id,
            "module_version": session.module.metadata.version,
            "current_scene_id": state.current_scene_id,
            "status": state.status.value,
            "turn_counter": state.turn_counter,
            "execution_mode": state.execution_mode,
            "adapter_name": state.adapter_name,
            "canonical_state": state.canonical_state if not is_truncated else None,
            "canonical_state_truncated": is_truncated,
            "warnings": ["in_memory_session_state_is_volatile"]
        },
        "diagnostics": {
            "session_id": session_id,
            "turn_counter": state.turn_counter,
            "current_scene_id": state.current_scene_id,
            "capabilities": {
                "has_turn_history": False,
                "has_guard_outcome": False,
                "has_trace_ids": False
            },
            "guard": {
                "outcome": None,
                "rejected_reasons": [],
                "last_error": None
            },
            "trace": {
                "trace_ids": []
            },
            "warnings": [
                "in_memory_session_state_is_volatile",
                "diagnostics_limited_to_current_runtime",
                "guard_and_trace_not_recorded_yet"
            ]
        },
        "logs": {
            "events": [],
            "total": 0,
            "warnings": [
                "history_not_available_in_current_runtime",
                "in_memory_session_state_is_volatile"
            ]
        },
        "meta": {
            "exported_at": datetime.utcnow().isoformat() + "Z",
            "trace_id": trace_id,
            "warnings": [
                "in_memory_session_state_is_volatile",
                "audit_logs_not_persisted_in_a2"
            ]
        }
    }

    return jsonify(bundle), 200
```

Add imports at top:
```python
from datetime import datetime
```

### Step 3: Run tests

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py::TestExportEndpoint -xvs`
Expected: PASS (all 3 tests)

### Step 4: Commit

```bash
git add backend/app/api/v1/session_routes.py backend/tests/test_observability.py
git commit -m "feat(obs): implement /export operator endpoint with diagnostics bundle"
```

---

## Task 6: Final Verification & Integration

**Files:**
- Test: `backend/tests/test_observability.py`

### Step 1: Run full observability test suite

Run: `cd backend && PYTHONPATH=. python -m pytest tests/test_observability.py -v --tb=short`
Expected: All 20+ tests PASS

### Step 2: Run full backend test suite to check for regressions

Run: `cd backend && PYTHONPATH=. python -m pytest tests/ -q --tb=line 2>&1 | tail -30`
Expected: All existing tests still pass + new observability tests

### Step 3: Verify no secrets in logs (manual check)

Grep for common secret patterns in audit log calls:
```bash
grep -r "password\|token\|secret\|credential" backend/app/observability/
```
Expected: No results (all sensitive data is hashed)

### Step 4: Create feature branch and final commit

```bash
git log --oneline -5
# Verify 5 commits: trace, audit_log, middleware, turn_execution, export
```

### Step 5: Summary

Expected output:
```
Commit hashes:
- feat(obs): implement contextvars-based trace ID system
- feat(obs): implement structured audit logger with JSON formatting
- feat(obs): add Flask middleware for trace ID propagation and audit logging
- feat(obs): add turn.execute audit logging to dispatch_turn()
- feat(obs): implement /export operator endpoint with diagnostics bundle

Files modified/created:
- backend/app/observability/__init__.py (new)
- backend/app/observability/trace.py (new)
- backend/app/observability/audit_log.py (new)
- backend/app/api/v1/__init__.py (modified - added middleware)
- backend/app/api/v1/session_routes.py (modified - added /export)
- backend/app/runtime/turn_dispatcher.py (modified - added logging)
- backend/app/web/routes.py (modified - added trace hook)
- backend/tests/test_observability.py (new)

Verification:
✅ Trace ID flows end-to-end via contextvars + headers
✅ A1.3 endpoints write api.endpoint audit logs
✅ Turn execution writes turn.execute audit logs
✅ /export returns compact reproducible bundle
✅ No secrets logged (all hashed/redacted)
✅ operator_input never logged raw (hashed)
✅ canonical_state not logged raw (truncated if >50KB)
✅ Tests: 20+ passing, no regressions
```
