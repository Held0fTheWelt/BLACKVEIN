"""W3.1 — Integration tests for session API routes.

Tests the session management endpoints:
- POST /api/v1/sessions - Create a new session
- GET /api/v1/sessions/<session_id> - Retrieve session (W3.2 deferred)
- POST /api/v1/sessions/<session_id>/turns - Execute turn (W3.2 deferred)
- GET /api/v1/sessions/<session_id>/logs - Get event logs (W3.2 deferred)
- GET /api/v1/sessions/<session_id>/state - Get world state (W3.2 deferred)
"""

import pytest


class TestCreateSessionEndpoint:
    """Tests for POST /api/v1/sessions."""

    def test_create_session_with_valid_module_creates_session(self, client):
        """POST /sessions with module_id creates a session and returns 201."""
        response = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"},
        )

        assert response.status_code == 201
        data = response.get_json()
        assert data["module_id"] == "god_of_carnage"
        assert "session_id" in data
        assert data["turn_counter"] == 0
        assert data["status"] == "active"

    def test_create_session_missing_module_id_returns_400(self, client):
        """POST /sessions without module_id returns 400."""
        response = client.post("/api/v1/sessions", json={})

        assert response.status_code == 400
        data = response.get_json()
        assert "error" in data
        assert "module_id" in data["error"].lower()

    def test_create_session_response_contains_required_fields(self, client):
        """POST /sessions response contains all required SessionState fields."""
        response = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"},
        )

        assert response.status_code == 201
        data = response.get_json()

        # Required fields
        assert "session_id" in data
        assert "module_id" in data
        assert "module_version" in data
        assert "current_scene_id" in data
        assert "status" in data
        assert "turn_counter" in data
        assert "canonical_state" in data
        assert "execution_mode" in data
        assert "adapter_name" in data
        assert "created_at" in data
        assert "updated_at" in data
        assert "metadata" in data
        assert "context_layers" in data
        assert "degraded_state" in data

    def test_create_session_returns_serializable_response(self, client):
        """POST /sessions response is JSON-serializable and valid."""
        response = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"},
        )

        assert response.status_code == 201
        data = response.get_json()

        # Verify fields are reasonable values
        assert isinstance(data["session_id"], str)
        assert len(data["session_id"]) == 32  # uuid4().hex is 32 chars
        assert isinstance(data["module_id"], str)
        assert isinstance(data["module_version"], str)
        assert isinstance(data["turn_counter"], int)
        assert data["turn_counter"] == 0


class TestGetSessionEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>."""

    def test_get_session_returns_501_not_implemented(self, client):
        """GET /sessions/<id> returns 501 (W3.2 deferred)."""
        response = client.get("/api/v1/sessions/some-session-id")

        assert response.status_code == 501
        data = response.get_json()
        assert "error" in data
        assert "W3.2" in data["error"] or "persistence" in data["error"]


class TestExecuteTurnEndpoint:
    """Tests for POST /api/v1/sessions/<session_id>/turns."""

    def test_execute_turn_returns_501_not_implemented(self, client):
        """POST /sessions/<id>/turns returns 501 (W3.2 deferred)."""
        response = client.post(
            "/api/v1/sessions/some-session-id/turns",
            json={"decision": {}},
        )

        assert response.status_code == 501
        data = response.get_json()
        assert "error" in data
        assert "W3.2" in data["error"] or "persistence" in data["error"]


class TestGetLogsEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/logs."""

    def test_get_logs_returns_501_not_implemented(self, client):
        """GET /sessions/<id>/logs returns 501 (W3.2 deferred)."""
        response = client.get("/api/v1/sessions/some-session-id/logs")

        assert response.status_code == 501
        data = response.get_json()
        assert "error" in data
        assert "W3.2" in data["error"] or "persistence" in data["error"]


class TestGetStateEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/state."""

    def test_get_state_returns_501_not_implemented(self, client):
        """GET /sessions/<id>/state returns 501 (W3.2 deferred)."""
        response = client.get("/api/v1/sessions/some-session-id/state")

        assert response.status_code == 501
        data = response.get_json()
        assert "error" in data
        assert "W3.2" in data["error"] or "persistence" in data["error"]


class TestSessionEndpointStatusCodes:
    """Contract tests for endpoint status codes."""

    def test_create_returns_201(self, client):
        """POST /sessions returns 201 Created on success."""
        response = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"},
        )
        assert response.status_code == 201

    def test_get_returns_501(self, client):
        """GET /sessions/<id> returns 501 Not Implemented."""
        response = client.get("/api/v1/sessions/any-id")
        assert response.status_code == 501

    def test_turns_returns_501(self, client):
        """POST /sessions/<id>/turns returns 501 Not Implemented."""
        response = client.post(
            "/api/v1/sessions/any-id/turns",
            json={"decision": {}},
        )
        assert response.status_code == 501

    def test_logs_returns_501(self, client):
        """GET /sessions/<id>/logs returns 501 Not Implemented."""
        response = client.get("/api/v1/sessions/any-id/logs")
        assert response.status_code == 501

    def test_state_returns_501(self, client):
        """GET /sessions/<id>/state returns 501 Not Implemented."""
        response = client.get("/api/v1/sessions/any-id/state")
        assert response.status_code == 501
