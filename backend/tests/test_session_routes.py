"""W3.1 — Integration tests for session API routes (in-process W2 bridge, not World Engine).

Endpoints are volatile and explicitly warned in JSON; live runs use the play service.
"""

import pytest

from app.runtime.session_start import SessionStartError


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
        assert "warnings" in data
        assert "backend_in_process_session_not_authoritative_live_runtime" in data["warnings"]
        assert "authoritative_runs_execute_in_world_engine_play_service" in data["warnings"]

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

    def test_create_session_module_not_found_returns_404(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.api.v1.session_routes.create_session",
            lambda module_id: (_ for _ in ()).throw(
                SessionStartError("module_not_found", module_id, "missing")
            ),
        )
        response = client.post("/api/v1/sessions", json={"module_id": "missing_module"})
        assert response.status_code == 404
        data = response.get_json()
        assert "error" in data
        assert "module_not_found" in data["error"]

    def test_create_session_module_invalid_returns_422(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.api.v1.session_routes.create_session",
            lambda module_id: (_ for _ in ()).throw(
                SessionStartError("module_invalid", module_id, "invalid")
            ),
        )
        response = client.post("/api/v1/sessions", json={"module_id": "broken_module"})
        assert response.status_code == 422
        data = response.get_json()
        assert "error" in data
        assert "module_invalid" in data["error"]

    def test_create_session_no_start_scene_returns_422(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.api.v1.session_routes.create_session",
            lambda module_id: (_ for _ in ()).throw(
                SessionStartError("no_start_scene", module_id, "missing initial scene")
            ),
        )
        response = client.post("/api/v1/sessions", json={"module_id": "broken_module"})
        assert response.status_code == 422

    def test_create_session_invalid_json_returns_400(self, client):
        response = client.post(
            "/api/v1/sessions",
            data="{bad-json",
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "error" in response.get_json()


class TestGetSessionEndpoint:
    """Tests for GET /api/v1/sessions/<session_id> (A1.3 snapshot endpoint)."""

    def test_get_session_without_auth_header_returns_401(self, client, monkeypatch):
        """GET /sessions/<id> without auth header returns 401."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get("/api/v1/sessions/some-session-id")

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"
        assert "Authorization" in data["error"]["message"]

    def test_get_session_with_invalid_token_returns_401(self, client, monkeypatch):
        """GET /sessions/<id> with invalid token returns 401."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "correct-token")
        response = client.get(
            "/api/v1/sessions/some-session-id",
            headers={"Authorization": "Bearer wrong-token"}
        )

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_get_session_without_env_var_returns_503(self, client, monkeypatch):
        """GET /sessions/<id> without MCP_SERVICE_TOKEN env var returns 503."""
        monkeypatch.delenv("MCP_SERVICE_TOKEN", raising=False)
        response = client.get(
            "/api/v1/sessions/some-session-id",
            headers={"Authorization": "Bearer any-token"}
        )

        assert response.status_code == 503
        data = response.get_json()
        assert data["error"]["code"] == "MISCONFIGURED"

    def test_get_session_nonexistent_returns_404(self, client, monkeypatch):
        """GET /sessions/<id> for non-existent session returns 404."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get(
            "/api/v1/sessions/nonexistent-session-id",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_session_with_valid_token_returns_200(self, client, monkeypatch):
        """GET /sessions/<id> with valid token and existing session returns 200."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Now get the session
        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["session_id"] == session_id
        assert data["module_id"] == "god_of_carnage"
        assert "canonical_state" in data
        assert "warnings" in data
        assert "in_memory_session_state_is_volatile" in data["warnings"]

    def test_get_session_prefers_world_engine_authoritative_snapshot_when_bound(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        from app.runtime.session_store import get_session as get_runtime_session

        runtime_session = get_runtime_session(session_id)
        runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we_story_snapshot"

        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_state",
            lambda *_a, **_k: {"turn_counter": 3, "current_scene_id": "scene_2", "committed_state": {}},
        )

        response = client.get(
            f"/api/v1/sessions/{session_id}",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we_story_snapshot"
        assert data["turn_counter"] == 3
        assert data["current_scene_id"] == "scene_2"
        assert "authoritative_state" in data
        assert "world_engine_story_runtime_authoritative_snapshot" in data["warnings"]


class TestExecuteTurnEndpoint:
    """Tests for POST /api/v1/sessions/<session_id>/turns."""

    def test_execute_turn_requires_existing_session(self, client):
        response = client.post(
            "/api/v1/sessions/some-session-id/turns",
            json={"player_input": "look around"},
        )
        assert response.status_code == 404

    def test_execute_turn_proxies_to_world_engine(self, client, monkeypatch):
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        monkeypatch.setattr(
            "app.api.v1.session_routes.create_story_session",
            lambda **_: {"session_id": "we_story_1"},
        )
        monkeypatch.setattr(
            "app.api.v1.session_routes.compile_module",
            lambda *_args, **_kwargs: type(
                "Compiled",
                (),
                {
                    "runtime_projection": type(
                        "Projection",
                        (),
                        {"model_dump": staticmethod(lambda **_: {"start_scene_id": "scene_1"})},
                    )()
                },
            )(),
        )
        monkeypatch.setattr(
            "app.api.v1.session_routes.execute_story_turn_in_engine",
            lambda **_: {"turn": {"turn_number": 1, "raw_input": "hello"}},
        )
        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_state",
            lambda *_, **__: {"turn_counter": 1, "current_scene_id": "scene_1"},
        )
        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_diagnostics",
            lambda *_, **__: {"diagnostics": [{"interpreted_input": {"kind": "speech"}}]},
        )

        response = client.post(
            f"/api/v1/sessions/{session_id}/turns",
            json={"player_input": "hello"},
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we_story_1"
        assert data["turn"]["turn_number"] == 1


class TestGetLogsEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/logs (A1.3 event history endpoint)."""

    def test_get_logs_without_auth_header_returns_401(self, client, monkeypatch):
        """GET /sessions/<id>/logs without auth header returns 401."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get("/api/v1/sessions/some-session-id/logs")

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_get_logs_nonexistent_returns_404(self, client, monkeypatch):
        """GET /sessions/<id>/logs for non-existent session returns 404."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get(
            "/api/v1/sessions/nonexistent-session-id/logs",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_logs_returns_empty_events_with_warnings(self, client, monkeypatch):
        """GET /sessions/<id>/logs returns empty events + warnings."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Get logs
        response = client.get(
            f"/api/v1/sessions/{session_id}/logs",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["session_id"] == session_id
        assert "events" in data
        assert isinstance(data["events"], list)
        assert len(data["events"]) == 0  # Empty in A1.3
        assert "total" in data
        assert data["total"] == 0
        assert "warnings" in data
        assert "in_memory_session_state_is_volatile" in data["warnings"]
        assert "history_not_available_in_current_runtime" in data["warnings"]


class TestGetStateEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/state (A1.3 state-only endpoint)."""

    def test_get_state_without_auth_header_returns_401(self, client, monkeypatch):
        """GET /sessions/<id>/state without auth header returns 401."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get("/api/v1/sessions/some-session-id/state")

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_get_state_nonexistent_returns_404(self, client, monkeypatch):
        """GET /sessions/<id>/state for non-existent session returns 404."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get(
            "/api/v1/sessions/nonexistent-session-id/state",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_state_returns_canonical_state_with_warnings(self, client, monkeypatch):
        """GET /sessions/<id>/state returns state + warnings."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Get state
        response = client.get(
            f"/api/v1/sessions/{session_id}/state",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["session_id"] == session_id
        assert "current_scene_id" in data
        assert "canonical_state" in data
        assert "canonical_state_truncated" in data
        assert "warnings" in data
        assert "in_memory_session_state_is_volatile" in data["warnings"]

    def test_get_state_prefers_world_engine_authoritative_state_when_bound(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        from app.runtime.session_store import get_session as get_runtime_session

        runtime_session = get_runtime_session(session_id)
        runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we_story_3"

        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_state",
            lambda *_a, **_k: {
                "turn_counter": 5,
                "current_scene_id": "scene_3",
                "committed_state": {
                    "current_scene_id": "scene_3",
                    "last_narrative_commit": {"allowed": True, "commit_reason_code": "legal_transition_committed"},
                },
                "runtime_projection": {"start_scene_id": "scene_1"},
            },
        )

        response = client.get(
            f"/api/v1/sessions/{session_id}/state",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we_story_3"
        assert data["turn_counter"] == 5
        assert data["current_scene_id"] == "scene_3"
        assert data["committed_state"]["current_scene_id"] == "scene_3"
        assert data["runtime_projection"]["start_scene_id"] == "scene_1"
        assert "world_engine_story_runtime_authoritative_state" in data["warnings"]


class TestGetDiagnosticsEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/diagnostics (A1.3 debug bundle)."""

    def test_get_diagnostics_without_auth_header_returns_401(self, client, monkeypatch):
        """GET /sessions/<id>/diagnostics without auth header returns 401."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get("/api/v1/sessions/some-session-id/diagnostics")

        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"

    def test_get_diagnostics_nonexistent_returns_404(self, client, monkeypatch):
        """GET /sessions/<id>/diagnostics for non-existent session returns 404."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.get(
            "/api/v1/sessions/nonexistent-session-id/diagnostics",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 404
        data = response.get_json()
        assert data["error"]["code"] == "NOT_FOUND"

    def test_get_diagnostics_returns_envelope_structure(self, client, monkeypatch):
        """GET /sessions/<id>/diagnostics returns diagnostics envelope."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")

        # Create a session first
        create_resp = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"}
        )
        session_id = create_resp.get_json()["session_id"]

        # Get diagnostics
        response = client.get(
            f"/api/v1/sessions/{session_id}/diagnostics",
            headers={"Authorization": "Bearer test-token"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["session_id"] == session_id
        assert "turn_counter" in data
        assert "current_scene_id" in data
        assert "capabilities" in data
        assert "guard" in data
        assert "trace" in data
        assert "warnings" in data
        # Check capabilities structure
        assert "has_turn_history" in data["capabilities"]
        assert "has_guard_outcome" in data["capabilities"]
        assert "has_trace_ids" in data["capabilities"]
        # Check guard structure
        assert "outcome" in data["guard"]
        assert "rejected_reasons" in data["guard"]
        assert "last_error" in data["guard"]
        # Check trace structure
        assert "trace_ids" in data["trace"]
        # Check warnings include expected entries
        assert "in_memory_session_state_is_volatile" in data["warnings"]
        assert "backend_diagnostics_not_world_engine_run" in data["warnings"]

    def test_get_diagnostics_prefers_world_engine_authoritative_payload(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        from app.runtime.session_store import get_session as get_runtime_session

        runtime_session = get_runtime_session(session_id)
        runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we_story_2"

        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_diagnostics",
            lambda *_a, **_k: {
                "turn_counter": 4,
                "committed_state": {"current_scene_id": "scene_2", "turn_counter": 4},
                "diagnostics": [{"narrative_commit": {"allowed": True, "committed_scene_id": "scene_2"}}],
            },
        )

        response = client.get(
            f"/api/v1/sessions/{session_id}/diagnostics",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we_story_2"
        assert data["turn_counter"] == 4
        assert data["current_scene_id"] == "scene_2"
        assert data["committed_state"]["current_scene_id"] == "scene_2"
        assert data["diagnostics"][0]["narrative_commit"]["allowed"] is True
        assert "world_engine_story_runtime_authoritative_diagnostics" in data["warnings"]


class TestSessionEndpointStatusCodes:
    """Contract tests for endpoint status codes."""

    def test_create_returns_201(self, client):
        """POST /sessions returns 201 Created on success."""
        response = client.post(
            "/api/v1/sessions",
            json={"module_id": "god_of_carnage"},
        )
        assert response.status_code == 201

    def test_turns_returns_404_when_session_missing(self, client, monkeypatch):
        """POST /sessions/<id>/turns returns 404 for missing session."""
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        response = client.post(
            "/api/v1/sessions/any-id/turns",
            json={"player_input": "look around"},
        )
        assert response.status_code == 404


class TestCapabilityAuditEndpoint:
    """Tests for GET /api/v1/sessions/<session_id>/capability-audit."""

    def test_capability_audit_returns_empty_before_story_session_exists(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        response = client.get(
            f"/api/v1/sessions/{session_id}/capability-audit",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["total"] == 0
        assert "capability_audit_not_available_before_first_turn" in data["warnings"]

    def test_capability_audit_returns_world_engine_rows(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]

        from app.runtime.session_store import get_session as get_runtime_session

        runtime_session = get_runtime_session(session_id)
        runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we_story_1"

        monkeypatch.setattr(
            "app.api.v1.session_routes.get_story_diagnostics",
            lambda *_a, **_k: {
                "diagnostics": [
                    {
                        "graph": {
                            "capability_audit": [
                                {
                                    "capability_name": "wos.context_pack.build",
                                    "outcome": "allowed",
                                    "trace_id": "trace_1",
                                }
                            ]
                        }
                    }
                ]
            },
        )

        response = client.get(
            f"/api/v1/sessions/{session_id}/capability-audit",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we_story_1"
        assert data["total"] == 1
        assert data["audit"][0]["capability_name"] == "wos.context_pack.build"
