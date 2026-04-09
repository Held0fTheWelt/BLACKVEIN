# MCP A1.3: Bridge Operator Endpoints Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement 4 read-only JSON endpoints that expose in-memory session data with service token authentication, replacing existing 501 stubs.

**Architecture:** Create a small auth module with @require_mcp_service_token decorator for env-var-based token validation. Replace 4 stub endpoints in session_routes.py with minimal JSON builders that fetch from session_store and format responses. All endpoints return 200/401/404/503 (never 501).

**Tech Stack:** Flask blueprints, Pydantic SessionState models, session_store in-memory registry, hmac for constant-time token compare.

---

## File Structure

| File | Responsibility |
|------|-----------------|
| `backend/app/api/v1/auth.py` (NEW) | Service token validation decorator; env var reading; constant-time comparison |
| `backend/app/api/v1/session_routes.py` (MODIFY) | Replace 4 existing 501 stub handlers with real implementations |
| `backend/tests/test_session_routes.py` (CREATE/EXTEND) | 10+ tests covering auth + happy path + error cases |

---

## Task 1: Implement Service Token Auth Decorator

**Files:**
- Create: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_api_auth.py`

- [ ] **Step 1: Write failing test for missing MCP_SERVICE_TOKEN env var**

```python
# backend/tests/test_api_auth.py
import os
import pytest
from flask import Flask
from backend.app.api.v1.auth import require_mcp_service_token

def test_require_mcp_service_token_missing_env_returns_503():
    """When MCP_SERVICE_TOKEN not set, decorator should return 503."""
    # Ensure env var is not set
    if "MCP_SERVICE_TOKEN" in os.environ:
        del os.environ["MCP_SERVICE_TOKEN"]

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer sometoken"})
        assert response.status_code == 503
        data = response.get_json()
        assert data["error"]["code"] == "MISCONFIGURED"
        assert "MCP_SERVICE_TOKEN" in data["error"]["message"]
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend && PYTHONPATH=. pytest tests/test_api_auth.py::test_require_mcp_service_token_missing_env_returns_503 -v
```

Expected: FAIL (module doesn't exist yet)

- [ ] **Step 3: Write auth.py with decorator skeleton**

```python
# backend/app/api/v1/auth.py
"""Service token authentication for MCP operator endpoints.

Provides the @require_mcp_service_token decorator for protecting
read-only operator endpoints with environment-based token validation.
"""

import os
import hmac
import hashlib
from functools import wraps
from flask import request, jsonify


def require_mcp_service_token(f):
    """Decorator: validate MCP_SERVICE_TOKEN from Authorization header.

    - Reads MCP_SERVICE_TOKEN from environment (required, no fallback).
    - If missing/empty: return 503 JSON (misconfiguration).
    - Expects header: Authorization: Bearer <token>
    - If missing/invalid token: return 401 JSON (unauthorized).
    - Uses constant-time comparison to prevent timing attacks.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if MCP_SERVICE_TOKEN is configured
        token = os.getenv("MCP_SERVICE_TOKEN", "").strip()
        if not token:
            return jsonify({
                "error": {
                    "code": "MISCONFIGURED",
                    "message": "MCP_SERVICE_TOKEN not configured"
                }
            }), 503

        # Extract Authorization header
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return jsonify({
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Missing or invalid Authorization header"
                }
            }), 401

        provided_token = auth_header[7:]  # Strip "Bearer " prefix

        # Constant-time comparison
        if not hmac.compare_digest(provided_token, token):
            return jsonify({
                "error": {
                    "code": "UNAUTHORIZED",
                    "message": "Invalid token"
                }
            }), 401

        return f(*args, **kwargs)
    return decorated_function
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. pytest tests/test_api_auth.py::test_require_mcp_service_token_missing_env_returns_503 -v
```

Expected: PASS

- [ ] **Step 5: Add test for valid token**

```python
def test_require_mcp_service_token_valid_token_allows_request(monkeypatch):
    """When token is valid, request proceeds to handler."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer secret-token-123"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == "ok"
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. pytest tests/test_api_auth.py::test_require_mcp_service_token_valid_token_allows_request -v
```

Expected: PASS

- [ ] **Step 7: Add test for missing Authorization header**

```python
def test_require_mcp_service_token_missing_header_returns_401(monkeypatch):
    """When Authorization header missing, return 401."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test")  # No Authorization header
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"
```

- [ ] **Step 8: Add test for invalid token**

```python
def test_require_mcp_service_token_invalid_token_returns_401(monkeypatch):
    """When token doesn't match, return 401."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"
```

- [ ] **Step 9: Run all auth tests**

```bash
cd backend && PYTHONPATH=. pytest tests/test_api_auth.py -v
```

Expected: All tests PASS (4 tests)

- [ ] **Step 10: Commit auth module**

```bash
git add backend/app/api/v1/auth.py backend/tests/test_api_auth.py
git commit -m "feat(auth): add MCP service token validation decorator"
```

---

## Task 2: Replace Snapshot Endpoint (GET /api/v1/sessions/<session_id>)

**Files:**
- Modify: `backend/app/api/v1/session_routes.py`
- Test: `backend/tests/test_session_routes.py`

- [ ] **Step 1: Write failing test for snapshot endpoint**

```python
# backend/tests/test_session_routes.py
import os
import pytest
from flask import Flask
from backend.app import create_app
from backend.app.runtime.session_store import create_session, get_session
from backend.app.runtime.w2_models import SessionState

@pytest.fixture
def app():
    """Create test app with MCP_SERVICE_TOKEN set."""
    os.environ["MCP_SERVICE_TOKEN"] = "test-token"
    app = create_app()
    app.config["TESTING"] = True
    return app

@pytest.fixture
def client(app):
    return app.test_client()

def test_get_session_snapshot_with_valid_token(client):
    """GET /api/v1/sessions/<id> returns snapshot with valid token."""
    # Create a test session (assume POST /api/v1/sessions works)
    # For now, mock the session in the store
    session_state = SessionState(
        session_id="test-session-1",
        module_id="god_of_carnage",
        module_version="1.0.0",
        current_scene_id="act-1",
        status="active",
        turn_counter=3,
        canonical_state={"world": "state"},
        execution_mode="mock",
        adapter_name="mock_adapter"
    )

    # Mock: create session directly in store (skipping full POST flow for unit test)
    from backend.app.runtime.session_store import _runtime_sessions
    from backend.app.content.module_loader import load_module

    module = load_module("god_of_carnage")
    runtime_session = create_session("test-session-1", session_state, module)

    # Test GET endpoint with valid token
    response = client.get(
        "/api/v1/sessions/test-session-1",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["session_id"] == "test-session-1"
    assert data["module_id"] == "god_of_carnage"
    assert data["turn_counter"] == 3
    assert "warnings" in data
    assert "in_memory_session_state_is_volatile" in data["warnings"]
```

- [ ] **Step 2: Run test to verify it fails (endpoint returns 501)**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_snapshot_with_valid_token -v
```

Expected: FAIL (endpoint currently returns 501)

- [ ] **Step 3: Replace snapshot endpoint in session_routes.py**

```python
# In backend/app/api/v1/session_routes.py, replace the stub:

@api_v1_bp.route("/sessions/<session_id>", methods=["GET"])
@require_mcp_service_token
def get_session_by_id(session_id):
    """Return session snapshot: metadata + current state.

    Auth: Requires valid MCP_SERVICE_TOKEN via Authorization header.

    Returns:
        200: Session snapshot with full metadata and canonical state
        401: Invalid or missing Authorization header
        404: Session not found
        503: MCP_SERVICE_TOKEN misconfigured
    """
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    state = runtime_session.current_runtime_state

    # Determine canonical_state handling
    canonical_state = state.canonical_state
    canonical_state_truncated = False
    canonical_state_summary = None

    # Simple size check: if canonical_state JSON > 50KB, truncate
    import json
    try:
        state_json = json.dumps(canonical_state)
        if len(state_json) > 50 * 1024:  # 50KB
            canonical_state_summary = {
                "keys": sorted(canonical_state.keys()) if isinstance(canonical_state, dict) else [],
                "total_fields": len(canonical_state) if isinstance(canonical_state, dict) else 0
            }
            canonical_state = None
            canonical_state_truncated = True
    except (TypeError, AttributeError):
        # If canonical_state can't be serialized, treat as small
        pass

    response = {
        "session_id": state.session_id,
        "module_id": state.module_id,
        "module_version": state.module_version,
        "current_scene_id": state.current_scene_id,
        "status": state.status,
        "turn_counter": state.turn_counter,
        "execution_mode": state.execution_mode,
        "adapter_name": state.adapter_name,
        "canonical_state": canonical_state,
        "canonical_state_truncated": canonical_state_truncated,
        "warnings": ["in_memory_session_state_is_volatile"]
    }

    if canonical_state_summary:
        response["canonical_state_summary"] = canonical_state_summary

    return jsonify(response), 200
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_snapshot_with_valid_token -v
```

Expected: PASS

- [ ] **Step 5: Add test for 404 (session not found)**

```python
def test_get_session_snapshot_session_not_found(client):
    """GET /api/v1/sessions/<id> returns 404 if session doesn't exist."""
    response = client.get(
        "/api/v1/sessions/nonexistent-session",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 404
    data = response.get_json()
    assert data["error"]["code"] == "NOT_FOUND"
```

- [ ] **Step 6: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_snapshot_session_not_found -v
```

Expected: PASS

- [ ] **Step 7: Commit snapshot endpoint**

```bash
git add backend/app/api/v1/session_routes.py backend/tests/test_session_routes.py
git commit -m "feat(api): implement GET /api/v1/sessions/<id> snapshot endpoint"
```

---

## Task 3: Replace State Endpoint (GET /api/v1/sessions/<session_id>/state)

**Files:**
- Modify: `backend/app/api/v1/session_routes.py`
- Test: `backend/tests/test_session_routes.py`

- [ ] **Step 1: Write failing test for state endpoint**

```python
def test_get_session_state_with_valid_token(client):
    """GET /api/v1/sessions/<id>/state returns canonical state."""
    # Use the same test session from Task 2
    from backend.app.runtime.session_store import create_session
    from backend.app.content.module_loader import load_module
    from backend.app.runtime.w2_models import SessionState

    session_state = SessionState(
        session_id="test-session-2",
        module_id="god_of_carnage",
        module_version="1.0.0",
        current_scene_id="act-2",
        status="active",
        turn_counter=5,
        canonical_state={"world": "state-2"},
        execution_mode="mock",
        adapter_name="mock_adapter"
    )

    module = load_module("god_of_carnage")
    create_session("test-session-2", session_state, module)

    response = client.get(
        "/api/v1/sessions/test-session-2/state",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["session_id"] == "test-session-2"
    assert data["current_scene_id"] == "act-2"
    assert data["canonical_state"] == {"world": "state-2"}
    assert "warnings" in data
    assert "in_memory_session_state_is_volatile" in data["warnings"]
```

- [ ] **Step 2: Run test to verify it fails (endpoint returns 501)**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_state_with_valid_token -v
```

Expected: FAIL (endpoint currently returns 501)

- [ ] **Step 3: Replace state endpoint in session_routes.py**

```python
# In backend/app/api/v1/session_routes.py, replace the stub:

@api_v1_bp.route("/sessions/<session_id>/state", methods=["GET"])
@require_mcp_service_token
def get_session_canonical_state(session_id):
    """Return canonical world state for the session.

    Auth: Requires valid MCP_SERVICE_TOKEN via Authorization header.

    Returns:
        200: Canonical state snapshot with scene and metadata
        401: Invalid or missing Authorization header
        404: Session not found
        503: MCP_SERVICE_TOKEN misconfigured
    """
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    state = runtime_session.current_runtime_state

    # Same truncation logic as snapshot
    canonical_state = state.canonical_state
    canonical_state_truncated = False
    canonical_state_summary = None

    import json
    try:
        state_json = json.dumps(canonical_state)
        if len(state_json) > 50 * 1024:
            canonical_state_summary = {
                "keys": sorted(canonical_state.keys()) if isinstance(canonical_state, dict) else [],
                "total_fields": len(canonical_state) if isinstance(canonical_state, dict) else 0
            }
            canonical_state = None
            canonical_state_truncated = True
    except (TypeError, AttributeError):
        pass

    response = {
        "session_id": state.session_id,
        "current_scene_id": state.current_scene_id,
        "canonical_state": canonical_state,
        "canonical_state_truncated": canonical_state_truncated,
        "warnings": ["in_memory_session_state_is_volatile"]
    }

    if canonical_state_summary:
        response["canonical_state_summary"] = canonical_state_summary

    return jsonify(response), 200
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_state_with_valid_token -v
```

Expected: PASS

- [ ] **Step 5: Commit state endpoint**

```bash
git add backend/app/api/v1/session_routes.py
git commit -m "feat(api): implement GET /api/v1/sessions/<id>/state endpoint"
```

---

## Task 4: Replace Logs and Diagnostics Endpoints

**Files:**
- Modify: `backend/app/api/v1/session_routes.py`
- Test: `backend/tests/test_session_routes.py`

- [ ] **Step 1: Write failing test for logs endpoint**

```python
def test_get_session_logs_returns_empty_with_warnings(client):
    """GET /api/v1/sessions/<id>/logs returns empty events + warnings."""
    from backend.app.runtime.session_store import create_session
    from backend.app.content.module_loader import load_module
    from backend.app.runtime.w2_models import SessionState

    session_state = SessionState(
        session_id="test-session-3",
        module_id="god_of_carnage",
        module_version="1.0.0",
        current_scene_id="act-3",
        status="active",
        turn_counter=0,
        canonical_state={},
        execution_mode="mock",
        adapter_name="mock_adapter"
    )

    module = load_module("god_of_carnage")
    create_session("test-session-3", session_state, module)

    response = client.get(
        "/api/v1/sessions/test-session-3/logs",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["session_id"] == "test-session-3"
    assert data["events"] == []
    assert data["total"] == 0
    assert "history_not_available_in_current_runtime" in data["warnings"]
    assert "in_memory_session_state_is_volatile" in data["warnings"]
```

- [ ] **Step 2: Write failing test for diagnostics endpoint**

```python
def test_get_session_diagnostics_returns_envelope(client):
    """GET /api/v1/sessions/<id>/diagnostics returns future-proof envelope."""
    # Use same session from logs test
    response = client.get(
        "/api/v1/sessions/test-session-3/diagnostics",
        headers={"Authorization": "Bearer test-token"}
    )

    assert response.status_code == 200
    data = response.get_json()
    assert data["session_id"] == "test-session-3"
    assert data["turn_counter"] == 0
    assert data["current_scene_id"] == "act-3"

    # Check envelope structure
    assert "capabilities" in data
    assert data["capabilities"]["has_turn_history"] is False
    assert data["capabilities"]["has_guard_outcome"] is False
    assert data["capabilities"]["has_trace_ids"] is False

    assert "guard" in data
    assert data["guard"]["outcome"] is None
    assert data["guard"]["rejected_reasons"] == []

    assert "trace" in data
    assert data["trace"]["trace_ids"] == []

    # Check warnings
    assert "in_memory_session_state_is_volatile" in data["warnings"]
    assert "diagnostics_limited_to_current_runtime" in data["warnings"]
    assert "guard_and_trace_not_recorded_yet" in data["warnings"]
```

- [ ] **Step 3: Run tests to verify they fail**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_logs_returns_empty_with_warnings tests/test_session_routes.py::test_get_session_diagnostics_returns_envelope -v
```

Expected: FAIL (endpoints return 501)

- [ ] **Step 4: Replace logs and diagnostics endpoints in session_routes.py**

```python
# In backend/app/api/v1/session_routes.py, replace the stubs:

@api_v1_bp.route("/sessions/<session_id>/logs", methods=["GET"])
@require_mcp_service_token
def get_session_event_logs(session_id):
    """Return event logs for a session (empty in A1.3).

    Auth: Requires valid MCP_SERVICE_TOKEN via Authorization header.

    Returns:
        200: Event list (empty) with warnings about unavailability
        401: Invalid or missing Authorization header
        404: Session not found
        503: MCP_SERVICE_TOKEN misconfigured

    Note: A1.3 does not implement logging infrastructure. History
    will be populated in W3.2 when persistence layer is added.
    """
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    return jsonify({
        "session_id": session_id,
        "events": [],
        "total": 0,
        "warnings": [
            "history_not_available_in_current_runtime",
            "in_memory_session_state_is_volatile"
        ]
    }), 200


@api_v1_bp.route("/sessions/<session_id>/diagnostics", methods=["GET"])
@require_mcp_service_token
def get_session_diagnostics(session_id):
    """Return diagnostics envelope for a session.

    Auth: Requires valid MCP_SERVICE_TOKEN via Authorization header.

    Returns:
        200: Diagnostics envelope with capabilities and guard/trace info
        401: Invalid or missing Authorization header
        404: Session not found
        503: MCP_SERVICE_TOKEN misconfigured

    Note: The envelope is future-proof (ready for W3.2 additions).
    Fields like guard_outcome, trace_ids, etc. are null/empty until
    the runtime infrastructure records them.
    """
    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    if not runtime_session:
        return jsonify({
            "error": {
                "code": "NOT_FOUND",
                "message": f"Session {session_id} not found"
            }
        }), 404

    state = runtime_session.current_runtime_state

    return jsonify({
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
    }), 200
```

- [ ] **Step 5: Run tests to verify they pass**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py::test_get_session_logs_returns_empty_with_warnings tests/test_session_routes.py::test_get_session_diagnostics_returns_envelope -v
```

Expected: PASS

- [ ] **Step 6: Add test for 404 on logs and diagnostics**

```python
def test_get_session_logs_404_not_found(client):
    """GET /api/v1/sessions/<id>/logs returns 404 if session missing."""
    response = client.get(
        "/api/v1/sessions/nonexistent/logs",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 404

def test_get_session_diagnostics_404_not_found(client):
    """GET /api/v1/sessions/<id>/diagnostics returns 404 if session missing."""
    response = client.get(
        "/api/v1/sessions/nonexistent/diagnostics",
        headers={"Authorization": "Bearer test-token"}
    )
    assert response.status_code == 404
```

- [ ] **Step 7: Run all new tests**

```bash
cd backend && PYTHONPATH=. pytest tests/test_session_routes.py -v
```

Expected: All tests PASS (10+ tests total)

- [ ] **Step 8: Commit logs and diagnostics endpoints**

```bash
git add backend/app/api/v1/session_routes.py backend/tests/test_session_routes.py
git commit -m "feat(api): implement GET /api/v1/sessions/<id>/logs and /diagnostics endpoints"
```

---

## Task 5: Final Verification & Cleanup

**Files:**
- Verify: `backend/app/api/v1/session_routes.py`
- Verify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_session_routes.py` and `backend/tests/test_api_auth.py`

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend && PYTHONPATH=. pytest tests/ -q
```

Expected: All tests passing, including the 10+ new tests for A1.3 endpoints

- [ ] **Step 2: Verify no 501 responses for the 4 endpoints**

```bash
cd backend && grep -n "501" backend/app/api/v1/session_routes.py
```

Expected: No results (all stubs replaced)

- [ ] **Step 3: Verify auth decorator is applied to all 4 endpoints**

```bash
cd backend && grep -B 1 "@require_mcp_service_token" backend/app/api/v1/session_routes.py | grep -E "(snapshot|state|logs|diagnostics)"
```

Expected: All 4 endpoints have the decorator

- [ ] **Step 4: Add import for auth decorator to session_routes.py**

At the top of `backend/app/api/v1/session_routes.py`, add:

```python
from app.api.v1.auth import require_mcp_service_token
```

- [ ] **Step 5: Verify no circular imports**

```bash
cd backend && PYTHONPATH=. python -c "from app.api.v1 import session_routes; print('OK')"
```

Expected: No import errors

- [ ] **Step 6: Final commit**

```bash
git add backend/app/api/v1/session_routes.py
git commit -m "feat(api): add auth import to session routes"
```

- [ ] **Step 7: Show implementation summary**

```bash
git log --oneline -5
echo "---"
git diff HEAD~4...HEAD --stat
```

---

## Summary

**Total tasks:** 5
**Total steps:** ~40
**Files created:** 2 (auth.py, test_api_auth.py)
**Files modified:** 2 (session_routes.py, test_session_routes.py)
**Tests added:** 10+
**Endpoints implemented:** 4 (all returning 200/401/404/503, no 501)

**Key outcomes:**
- ✅ 4 read-only JSON endpoints with service token auth
- ✅ No 501 stubs remain
- ✅ No new logging/guard/trace infrastructure added
- ✅ Deterministic canonical_state truncation (if needed)
- ✅ All responses include volatility warnings
- ✅ Constant-time token comparison
- ✅ Env-var-only MCP_SERVICE_TOKEN (503 if missing)
