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

    def test_create_session_bootstraps_world_engine_story_session_id_when_bridge_available(self, client, monkeypatch):
        monkeypatch.setattr(
            "app.api.v1.session_routes.compile_module",
            lambda *_a, **_k: type("Compiled", (), {"runtime_projection": type("Projection", (), {"model_dump": staticmethod(lambda **_: {"start_scene_id": "scene_1"})})()})(),
        )
        monkeypatch.setattr("app.api.v1.session_routes.create_story_session", lambda **_: {"session_id": "we-bootstrapped-1"})

        response = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        assert response.status_code == 201
        data = response.get_json()
        assert data["world_engine_story_session_id"] == "we-bootstrapped-1"
        assert data["canonical_state"] == {"compatibility_state_scope": "minimal_after_authoritative_binding"}
        assert data["metadata"]["compatibility_state_minimized"] is True
        assert "world_engine_story_session_bootstrapped_for_bridge_first_compatibility" in data["warnings"]
        assert "backend_local_compatibility_state_minimized_after_authoritative_binding" in data["warnings"]

    def test_create_session_still_succeeds_when_world_engine_story_bootstrap_fails(self, client, monkeypatch):
        gse = __import__("app.services.game_service", fromlist=["GameServiceError"]).GameServiceError
        monkeypatch.setattr(
            "app.api.v1.session_routes.compile_module",
            lambda *_a, **_k: type("Compiled", (), {"runtime_projection": type("Projection", (), {"model_dump": staticmethod(lambda **_: {"start_scene_id": "scene_1"})})()})(),
        )
        monkeypatch.setattr("app.api.v1.session_routes.create_story_session", lambda **_: (_ for _ in ()).throw(gse("play down", status_code=503)))

        response = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        assert response.status_code == 201
        data = response.get_json()
        assert "world_engine_story_session_id" not in data
        assert "world_engine_story_session_bootstrap_failed:503" in data["warnings"]

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
            "app.api.v1.session_routes.create_local_bootstrap_session",
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
            "app.api.v1.session_routes.create_local_bootstrap_session",
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
            "app.api.v1.session_routes.create_local_bootstrap_session",
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

        assert response.status_code == 409
        data = response.get_json()
        assert data["session_id"] == session_id
        assert data["error"]["code"] == "AUTHORITATIVE_STORY_SESSION_ID_OR_EXPLICIT_LOCAL_FALLBACK_REQUIRED"

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
            lambda **_: {"turn": {"turn_number": 1, "raw_input": "hello", "shell_readout_projection": {"response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"}, "visible_output_bundle_addressed": {"gm_narration": ["Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply."]}}},
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
        assert data["turn"]["shell_readout_projection"]["response_line_prefix_now"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"
        assert data["turn"]["visible_output_bundle_addressed"]["gm_narration"][0].startswith("Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway — A sharp reply.")


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

        assert response.status_code == 409
        data = response.get_json()
        assert data["session_id"] == session_id
        assert data["error"]["code"] == "AUTHORITATIVE_STORY_SESSION_ID_OR_EXPLICIT_LOCAL_FALLBACK_REQUIRED"

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

        assert response.status_code == 409
        data = response.get_json()
        assert data["session_id"] == session_id
        assert data["error"]["code"] == "AUTHORITATIVE_STORY_SESSION_ID_OR_EXPLICIT_LOCAL_FALLBACK_REQUIRED"

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


class TestExplicitUnboundLocalFallback:
    def test_get_session_can_still_use_explicit_local_fallback_when_unbound(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]
        response = client.get(f"/api/v1/sessions/{session_id}?allow_backend_local_fallback=1", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        assert "backend_local_fallback_explicitly_requested" in response.get_json()["warnings"]

    def test_get_state_can_still_use_explicit_local_fallback_when_unbound(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]
        response = client.get(f"/api/v1/sessions/{session_id}/state?allow_backend_local_fallback=1", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        assert "backend_local_fallback_explicitly_requested" in response.get_json()["warnings"]

    def test_get_diagnostics_can_still_use_explicit_local_fallback_when_unbound(self, client, monkeypatch):
        monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
        create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
        session_id = create_resp.get_json()["session_id"]
        response = client.get(f"/api/v1/sessions/{session_id}/diagnostics?allow_backend_local_fallback=1", headers={"Authorization": "Bearer test-token"})
        assert response.status_code == 200
        assert "backend_local_fallback_explicitly_requested" in response.get_json()["warnings"]



def test_get_state_returns_shell_readout_projection_when_authoritative_state_has_it(client, monkeypatch):
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    create_resp = client.post("/api/v1/sessions", json={"module_id": "god_of_carnage"})
    session_id = create_resp.get_json()["session_id"]

    from app.runtime.session_store import get_session as get_runtime_session

    runtime_session = get_runtime_session(session_id)
    runtime_session.current_runtime_state.metadata["world_engine_story_session_id"] = "we_story_shell"

    monkeypatch.setattr(
        "app.api.v1.session_routes.get_story_state",
        lambda *_, **__: {
            "turn_counter": 5,
            "current_scene_id": "hallway_threshold",
            "committed_state": {
                "current_scene_id": "hallway_threshold",
                "shell_readout_projection": {
                    "social_weather_now": "Exit pressure is dominating the room; even practical movement is reading as failed repair.",
                    "live_surface_now": "The doorway is the hot surface right now; hovering there reads as departure pressure, not neutral movement.",
                    "carryover_now": "Departure shame is still active; the room has not spent the earlier failed-exit pressure.",
                    "social_geometry_now": "Pressure is sitting with the host side and spouse axis rather than the guests.",
                    "situational_freedom_now": "Distance shifts, hovering, and trying not to leave cleanly will all be socially legible here.",
                    "address_pressure_now": "Veronique is effectively pressing you through failed departure pressure; the doorway is acting like an accusation, not a neutral exit.",
                    "social_moment_now": "This is a failed-exit moment under brittle civility.",
                    "response_pressure_now": "The room is pressing for repair, explanation, or a refusal to leave cleanly.",
                    "response_address_source_now": "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction.",
                    "response_exchange_now": "Your act drew a failed repair answer because your move turned departure into repair pressure.",
                    "response_exchange_label_now": "failed repair",
                    "response_line_prefix_now": "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway",
                    "who_answers_now": "Veronique is the one answering now; the host side is speaking through spouse embarrassment, with civility hardening into correction.",
                    "why_this_reply_now": "The room read the act as failed repair, so the host side answered through spouse embarrassment at the doorway and let the reply pull the moment back under principle instead of letting the exit close it, in a principle-first rebuke that uses civility as correction.",
                    "observation_foothold_now": "You are inside a failed-exit exchange now; the host side is answering through departure pressure and restraint still reads as part of the exchange.",
                    "room_pressure_now": "The room feels exit-loaded; the doorway still reads as a social trap.",
                    "salient_object_now": "The threshold itself is acting like a pressure object.",
                    "dominant_social_reading_now": "It is landing as failed repair and renewed departure pressure rather than a clean practical move.",
                    "social_axis_now": "The host side and spouse axis are carrying the weight; Veronique is taking the room's boundary reading.",
                    "host_guest_pressure_now": "Host-side pressure is carrying more of the room; the guests have more room to watch than absorb.",
                    "spouse_axis_now": "One partner is carrying social cost for the other's act; the spouse axis is not settled.",
                    "cross_couple_now": "Cross-couple strain is live, though it is not fully taking over the room.",
                    "pressure_redistribution_now": "Pressure has shifted from practical movement into spouse embarrassment and departure shame.",
                },
            },
            "runtime_projection": {"start_scene_id": "scene_1"},
        },
    )

    response = client.get(f"/api/v1/sessions/{session_id}/state", headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = response.get_json()
    assert data["committed_state"]["shell_readout_projection"]["social_weather_now"].startswith("Exit pressure is dominating the room")
    assert data["committed_state"]["shell_readout_projection"]["live_surface_now"].startswith("The doorway is the hot surface right now")
    assert data["committed_state"]["shell_readout_projection"]["carryover_now"].startswith("Departure shame is still active")
    assert data["committed_state"]["shell_readout_projection"]["social_geometry_now"].startswith("Pressure is sitting with the host side and spouse axis")
    assert data["committed_state"]["shell_readout_projection"]["situational_freedom_now"].startswith("Distance shifts, hovering")
    assert data["committed_state"]["shell_readout_projection"]["address_pressure_now"].startswith("Veronique is effectively pressing you through failed departure pressure")
    assert data["committed_state"]["shell_readout_projection"]["social_moment_now"].startswith("This is a failed-exit moment under brittle civility")
    assert data["committed_state"]["shell_readout_projection"]["response_pressure_now"].startswith("The room is pressing for repair, explanation")
    assert data["committed_state"]["shell_readout_projection"]["response_address_source_now"] == "Veronique answers from the host side through the spouse axis in failed repair, with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction."
    assert data["committed_state"]["shell_readout_projection"]["response_exchange_now"].startswith("Your act drew a failed repair answer")
    assert data["committed_state"]["shell_readout_projection"]["response_exchange_label_now"] == "failed repair"
    assert data["committed_state"]["shell_readout_projection"]["response_line_prefix_now"] == "Veronique, from the host side through the spouse axis, answers in failed repair with host-side spouse embarrassment at the doorway, in a principle-first rebuke that uses civility as correction, the earlier failed exit still sitting at the doorway"
    assert data["committed_state"]["shell_readout_projection"]["who_answers_now"].startswith("Veronique is the one answering now")
    assert data["committed_state"]["shell_readout_projection"]["why_this_reply_now"].startswith("The room read the act as failed repair")
    assert data["committed_state"]["shell_readout_projection"]["observation_foothold_now"].startswith("You are inside a failed-exit exchange now")
    assert data["committed_state"]["shell_readout_projection"]["room_pressure_now"].startswith("The room feels exit-loaded")
    assert data["committed_state"]["shell_readout_projection"]["dominant_social_reading_now"].startswith("It is landing as failed repair")
    assert data["committed_state"]["shell_readout_projection"]["host_guest_pressure_now"].startswith("Host-side pressure is carrying more of the room")
    assert data["committed_state"]["shell_readout_projection"]["spouse_axis_now"].startswith("One partner is carrying social cost")
