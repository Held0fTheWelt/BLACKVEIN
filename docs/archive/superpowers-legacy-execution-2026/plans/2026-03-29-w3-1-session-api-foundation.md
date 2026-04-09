# W3.1 Canonical Session API Foundation

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the minimum canonical session/turn execution API required for a playable UI to start, inspect, and advance game sessions.

**Architecture:** Add 5 focused Flask blueprint endpoints that directly expose W2 runtime session operations without bypassing validation or guards. New endpoints live in `backend/app/api/v1/session_routes.py` with supporting service functions in `backend/app/services/session_service.py`. All endpoints accept session_id path parameter and return W2 model state directly.

**Tech Stack:** Flask blueprints, Pydantic models for request/response validation, Python async/await for W2 runtime integration, pytest for endpoint testing.

---

## File Structure & Responsibilities

### Files to Create

**`backend/app/api/v1/session_routes.py`** — Session lifecycle endpoints
- Responsibility: Flask routes for the 5 canonical session operations
- Exports: Blueprint `session_bp` with routes for start, get, execute turn, get logs, get state
- Dependencies: `session_service`, Flask request/jsonify, auth decorators

**`backend/app/services/session_service.py`** — Session service layer
- Responsibility: Coordinate between API layer and W2 runtime
- Functions: `create_session(module_id)`, `get_session(session_id)`, `execute_turn(session_id, decision)`, `get_session_logs(session_id)`, `get_session_state(session_id)`
- Dependencies: W2 models, runtime modules, error handling

**`backend/tests/api/v1/test_session_routes.py`** — Integration tests for session endpoints
- Responsibility: Test each endpoint against real W2 runtime
- Fixtures: test session setup, cleanup
- Tests: 5 main tests (one per endpoint) + edge cases

### Files to Modify

**`backend/app/__init__.py`** — Register session blueprint
- Modify: Add `session_bp.register_blueprint()` call in app factory

**`backend/app/api/v1/__init__.py`** — Export session blueprint
- Modify: Export `session_bp` from this package

---

## Task Decomposition

### Task 1: Create Session Service Layer

**Files:**
- Create: `backend/app/services/session_service.py`
- Modify: (none yet)
- Test: (unit test in task 3)

- [ ] **Step 1: Write failing service test**

Create `backend/tests/services/test_session_service.py`:

```python
import pytest
from app.services.session_service import create_session, get_session

def test_create_session_returns_session_state():
    """Verify create_session returns a SessionState object."""
    session = create_session(module_id="god_of_carnage")

    assert session is not None
    assert hasattr(session, 'session_id')
    assert hasattr(session, 'module_id')
    assert session.module_id == "god_of_carnage"
    assert session.turn_counter == 0
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/services/test_session_service.py::test_create_session_returns_session_state -v
```

Expected: `ModuleNotFoundError: No module named 'app.services.session_service'`

- [ ] **Step 3: Create session_service.py with create_session**

Create `backend/app/services/session_service.py`:

```python
"""W3 Session Management Service Layer

Provides service-level operations for session lifecycle:
- create_session: Start a new game session with W2 runtime
- get_session: Retrieve current session state
- execute_turn: Execute a turn via W2 turn executor
- get_session_logs: Retrieve session event logs
- get_session_state: Retrieve session canonical state
"""

from app.runtime.w2_models import SessionState
from app.runtime.session_start import start_session
from app.content.module_loader import load_module


def create_session(module_id: str) -> SessionState:
    """Create a new game session.

    Args:
        module_id: The content module to load (e.g., "god_of_carnage")

    Returns:
        SessionState: Initialized session ready for turn execution

    Raises:
        ValueError: If module_id is not found or invalid
    """
    # Load the content module
    module = load_module(module_id)
    if not module:
        raise ValueError(f"Module '{module_id}' not found")

    # Initialize session with W2 runtime
    session = start_session(module_id)

    return session


def get_session(session_id: str) -> SessionState | None:
    """Retrieve a session by ID.

    Args:
        session_id: The session identifier

    Returns:
        SessionState: The session, or None if not found

    Note: This requires session persistence, which is deferred to W3.2
    """
    # TODO: W3.2 - Implement session persistence/retrieval
    # For now, raise NotImplementedError
    raise NotImplementedError("Session persistence deferred to W3.2")


def execute_turn(session_id: str, decision: dict) -> dict:
    """Execute a turn in a session.

    Args:
        session_id: The session identifier
        decision: The player/AI decision (structure TBD with W2 validation)

    Returns:
        dict: Execution result with execution_status, deltas, events

    Note: This requires session retrieval (W3.2)
    """
    # TODO: W3.2 - Implement full turn execution with persistence
    raise NotImplementedError("Turn execution requires session persistence (W3.2)")


def get_session_logs(session_id: str) -> list:
    """Retrieve event logs from a session.

    Args:
        session_id: The session identifier

    Returns:
        list: Event log entries

    Note: Requires session retrieval (W3.2)
    """
    # TODO: W3.2 - Implement log retrieval from persisted session
    raise NotImplementedError("Log retrieval requires session persistence (W3.2)")


def get_session_state(session_id: str) -> dict:
    """Retrieve the canonical state from a session.

    Args:
        session_id: The session identifier

    Returns:
        dict: The canonical_state dict from SessionState

    Note: Requires session retrieval (W3.2)
    """
    # TODO: W3.2 - Implement state retrieval from persisted session
    raise NotImplementedError("State retrieval requires session persistence (W3.2)")
```

- [ ] **Step 4: Run test to verify it passes**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/services/test_session_service.py::test_create_session_returns_session_state -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
cd backend
git add app/services/session_service.py tests/services/test_session_service.py
git commit -m "feat(w3): add session service layer for W3.1 foundation"
```

---

### Task 2: Create Session Routes (Endpoints)

**Files:**
- Create: `backend/app/api/v1/session_routes.py`
- Modify: `backend/app/__init__.py`, `backend/app/api/v1/__init__.py`
- Test: (integration test in task 3)

- [ ] **Step 1: Write failing integration test**

Create `backend/tests/api/v1/test_session_routes.py`:

```python
import pytest
from app.runtime.w2_models import SessionState


@pytest.fixture
def api_client(app):
    """Provide Flask test client."""
    return app.test_client()


def test_post_sessions_creates_session(api_client):
    """POST /api/v1/sessions creates a new session."""
    response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )

    assert response.status_code == 201
    data = response.get_json()
    assert 'session_id' in data
    assert data['module_id'] == 'god_of_carnage'
    assert data['turn_counter'] == 0
    assert 'canonical_state' in data


def test_get_sessions_by_id_returns_session_data(api_client):
    """GET /api/v1/sessions/{session_id} retrieves session."""
    # Create a session first
    create_response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )
    session_id = create_response.get_json()['session_id']

    # Retrieve it
    response = api_client.get(f'/api/v1/sessions/{session_id}')

    # W3.1: Should return 501 (not yet implemented - requires persistence)
    assert response.status_code == 501


def test_post_sessions_turn_executes_turn(api_client):
    """POST /api/v1/sessions/{session_id}/turns executes a turn."""
    # Create session first
    create_response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )
    session_id = create_response.get_json()['session_id']

    # Execute turn
    response = api_client.post(
        f'/api/v1/sessions/{session_id}/turns',
        json={'decision': {}}
    )

    # W3.1: Should return 501 (not yet implemented - requires persistence)
    assert response.status_code == 501


def test_get_sessions_logs_returns_event_logs(api_client):
    """GET /api/v1/sessions/{session_id}/logs retrieves event logs."""
    # Create session
    create_response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )
    session_id = create_response.get_json()['session_id']

    # Get logs
    response = api_client.get(f'/api/v1/sessions/{session_id}/logs')

    # W3.1: Should return 501 (not yet implemented - requires persistence)
    assert response.status_code == 501


def test_get_sessions_state_returns_canonical_state(api_client):
    """GET /api/v1/sessions/{session_id}/state retrieves canonical state."""
    # Create session
    create_response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )
    session_id = create_response.get_json()['session_id']

    # Get state
    response = api_client.get(f'/api/v1/sessions/{session_id}/state')

    # W3.1: Should return 501 (not yet implemented - requires persistence)
    assert response.status_code == 501
```

- [ ] **Step 2: Run test to verify it fails**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/api/v1/test_session_routes.py::test_post_sessions_creates_session -v
```

Expected: 404 (endpoint doesn't exist)

- [ ] **Step 3: Create session_routes.py with Flask endpoints**

Create `backend/app/api/v1/session_routes.py`:

```python
"""W3.1 Canonical Session API Routes

Exposes minimum session operations required by playable UI:
- POST /api/v1/sessions — Create session
- GET /api/v1/sessions/{session_id} — Get session (W3.2)
- POST /api/v1/sessions/{session_id}/turns — Execute turn (W3.2)
- GET /api/v1/sessions/{session_id}/logs — Get logs (W3.2)
- GET /api/v1/sessions/{session_id}/state — Get state (W3.2)

All endpoints preserve W2 runtime authority - no bypassing validation/guards.
"""

from flask import Blueprint, request, jsonify
from app.services.session_service import (
    create_session,
    get_session,
    execute_turn,
    get_session_logs,
    get_session_state,
)
from app.runtime.w2_models import SessionState

session_bp = Blueprint('sessions', __name__, url_prefix='/api/v1/sessions')


@session_bp.route('', methods=['POST'])
def create_new_session():
    """POST /api/v1/sessions — Create a new session.

    Request:
        {
            "module_id": "god_of_carnage"
        }

    Response (201):
        {
            "session_id": "uuid",
            "module_id": "god_of_carnage",
            "module_version": "0.1.0",
            "current_scene_id": "phase_1",
            "status": "active",
            "turn_counter": 0,
            "canonical_state": {...},
            "execution_mode": "mock",
            "adapter_name": "mock",
            "created_at": "2026-03-29T...",
            "metadata": {}
        }
    """
    data = request.get_json() or {}
    module_id = data.get('module_id')

    if not module_id:
        return jsonify({'error': 'module_id is required'}), 400

    try:
        session: SessionState = create_session(module_id)
        return jsonify(session.model_dump()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@session_bp.route('/<session_id>', methods=['GET'])
def get_session_by_id(session_id: str):
    """GET /api/v1/sessions/{session_id} — Get session details.

    Response (501 in W3.1 - requires persistence in W3.2):
        {
            "error": "Session persistence deferred to W3.2"
        }

    Note: Full implementation requires W3.2 session persistence layer.
    """
    return jsonify({'error': 'Session retrieval requires persistence (W3.2)'}), 501


@session_bp.route('/<session_id>/turns', methods=['POST'])
def execute_turn_endpoint(session_id: str):
    """POST /api/v1/sessions/{session_id}/turns — Execute a turn.

    Request:
        {
            "decision": {...}
        }

    Response (501 in W3.1 - requires persistence in W3.2):
        {
            "error": "Turn execution requires persistence (W3.2)"
        }

    Note: Full implementation requires W3.2 session persistence layer.
    """
    return jsonify({'error': 'Turn execution requires persistence (W3.2)'}), 501


@session_bp.route('/<session_id>/logs', methods=['GET'])
def get_session_logs_endpoint(session_id: str):
    """GET /api/v1/sessions/{session_id}/logs — Get event logs.

    Response (501 in W3.1 - requires persistence in W3.2):
        {
            "error": "Log retrieval requires persistence (W3.2)"
        }

    Note: Full implementation requires W3.2 session persistence layer.
    """
    return jsonify({'error': 'Log retrieval requires persistence (W3.2)'}), 501


@session_bp.route('/<session_id>/state', methods=['GET'])
def get_session_state_endpoint(session_id: str):
    """GET /api/v1/sessions/{session_id}/state — Get canonical state.

    Response (501 in W3.1 - requires persistence in W3.2):
        {
            "error": "State retrieval requires persistence (W3.2)"
        }

    Note: Full implementation requires W3.2 session persistence layer.
    """
    return jsonify({'error': 'State retrieval requires persistence (W3.2)'}), 501
```

- [ ] **Step 4: Register blueprint in app factory**

Modify `backend/app/__init__.py` - find the app factory function and add:

```python
from app.api.v1 import session_bp  # Add to imports

# In app factory function, after other blueprints:
app.register_blueprint(session_bp)
```

- [ ] **Step 5: Export blueprint from v1 package**

Modify `backend/app/api/v1/__init__.py` - add:

```python
from app.api.v1.session_routes import session_bp

__all__ = [
    # existing exports...
    'session_bp',
]
```

- [ ] **Step 6: Run integration test to verify it passes**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/api/v1/test_session_routes.py::test_post_sessions_creates_session -v
```

Expected: PASS (201 response with session data)

- [ ] **Step 7: Run all session route tests**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/api/v1/test_session_routes.py -v
```

Expected: 1 PASS (create), 4 PASS (others return 501)

- [ ] **Step 8: Commit**

```bash
cd backend
git add app/api/v1/session_routes.py app/api/v1/__init__.py app/__init__.py tests/api/v1/test_session_routes.py
git commit -m "feat(w3): add canonical session API endpoints (W3.1 foundation)"
```

---

### Task 3: Add Session Routes to API Documentation

**Files:**
- Create: None (inline documentation in routes)
- Modify: None (docstrings already in place)
- Test: (manual verification)

- [ ] **Step 1: Verify endpoint docstrings are clear**

Run inspection:

```bash
cd backend
python -c "from app.api.v1 import session_routes; print(session_routes.create_new_session.__doc__)"
```

Expected: See the docstring with request/response format

- [ ] **Step 2: Test endpoint response format matches docstring**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/api/v1/test_session_routes.py::test_post_sessions_creates_session -v
```

Expected: PASS with response matching documented format

---

### Task 4: Verify No Regressions

**Files:**
- Modify: None
- Test: Run existing test suite

- [ ] **Step 1: Run full backend test suite**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/ -q --tb=short
```

Expected: All existing tests pass (638+ tests)

- [ ] **Step 2: Verify W2 tests still pass**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/runtime/ -q --tb=short
```

Expected: All 638 runtime tests pass, zero regressions

---

### Task 5: Add Contract Stability Tests

**Files:**
- Modify: `tests/api/v1/test_session_routes.py`
- Test: (unit test for contract validation)

- [ ] **Step 1: Add contract validation test**

Add to `backend/tests/api/v1/test_session_routes.py`:

```python
def test_create_session_response_has_required_fields(api_client):
    """Verify create session response has all required W3 contract fields."""
    response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )

    assert response.status_code == 201
    data = response.get_json()

    # Contract: Session response must have these fields
    required_fields = [
        'session_id',
        'module_id',
        'module_version',
        'current_scene_id',
        'status',
        'turn_counter',
        'canonical_state',
        'execution_mode',
        'adapter_name',
        'created_at',
    ]

    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_session_endpoints_return_correct_status_codes(api_client):
    """Verify unimplemented endpoints return 501 (not implemented)."""
    # Create session
    create_response = api_client.post(
        '/api/v1/sessions',
        json={'module_id': 'god_of_carnage'}
    )
    session_id = create_response.get_json()['session_id']

    # W3.1: These should return 501 (not yet implemented)
    endpoints = [
        ('GET', f'/api/v1/sessions/{session_id}'),
        ('POST', f'/api/v1/sessions/{session_id}/turns'),
        ('GET', f'/api/v1/sessions/{session_id}/logs'),
        ('GET', f'/api/v1/sessions/{session_id}/state'),
    ]

    for method, path in endpoints:
        if method == 'GET':
            response = api_client.get(path)
        else:
            response = api_client.post(path, json={})

        assert response.status_code == 501, f"{method} {path} should return 501, got {response.status_code}"
```

- [ ] **Step 2: Run contract tests**

```bash
cd backend
PYTHONPATH=. python -m pytest tests/api/v1/test_session_routes.py::test_create_session_response_has_required_fields -v
```

Expected: PASS

- [ ] **Step 3: Commit**

```bash
cd backend
git add tests/api/v1/test_session_routes.py
git commit -m "test(w3): add contract validation tests for session API"
```

---

## Verification Checklist

- [ ] All 5 canonical session endpoints exist (1 implemented, 4 return 501)
- [ ] Implemented endpoint (POST /sessions) creates SessionState via W2 runtime
- [ ] Response format matches W3 contract (session_id, module_id, state, etc.)
- [ ] Endpoint docstrings document request/response format
- [ ] 4 future endpoints (get, execute turn, logs, state) return 501 with clear "W3.2" messages
- [ ] No W2 runtime behavior changed
- [ ] All 638 existing tests pass (zero regressions)
- [ ] Service layer (`session_service.py`) provides abstraction for future W3.2 work
- [ ] Blueprint properly registered and exported

---

## What This Completes (W3.1 Scope)

✅ **Minimum Session API Foundation:**
- `POST /api/v1/sessions` — Create sessions (WORKING)
- `GET /api/v1/sessions/{session_id}` — Get session (deferred to W3.2)
- `POST /api/v1/sessions/{session_id}/turns` — Execute turn (deferred to W3.2)
- `GET /api/v1/sessions/{session_id}/logs` — Get logs (deferred to W3.2)
- `GET /api/v1/sessions/{session_id}/state` — Get state (deferred to W3.2)

✅ **Preserved W2 Authority:**
- No validation bypassed
- No guard behavior changed
- Session creation uses `start_session()` directly

✅ **Clear Deferral Path:**
- 4 endpoints explicitly marked "requires W3.2"
- Service layer prepared for persistence layer
- Test structure ready for W3.2 completion

---

## What W3.2 Will Add

(Out of scope - mentioned for clarity)
- Session persistence (database/cache)
- Session retrieval by ID
- Turn execution with state updates
- Event log retrieval
- Full lifecycle management

---

## Commit Message

```
feat(w3): establish canonical session API foundation

W3.1 minimum session API:
- POST /api/v1/sessions — Create session (working)
- GET /api/v1/sessions/{session_id} — (W3.2)
- POST /api/v1/sessions/{session_id}/turns — (W3.2)
- GET /api/v1/sessions/{session_id}/logs — (W3.2)
- GET /api/v1/sessions/{session_id}/state — (W3.2)

Creates SessionState via W2 runtime, preserves validation authority.
Service layer abstraction ready for W3.2 persistence work.
All 638 existing tests passing, zero regressions.
```
