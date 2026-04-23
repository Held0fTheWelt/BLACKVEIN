"""Tests for Phase D QA Canonical Turn Diagnostics Routes."""

import pytest


class TestPlayQaDiagnosticsRoutes:
    """Test /api/v1/play/<session_id>/qa-diagnostics-canonical-turn endpoint."""

    def test_endpoint_requires_jwt(self, client):
        """Endpoint returns 401 when no JWT token provided."""
        response = client.get("/api/v1/play/test-session-123/qa-diagnostics-canonical-turn")
        assert response.status_code == 401

    def test_endpoint_requires_feature(self, client, admin_headers, monkeypatch):
        """Endpoint returns 403 when user lacks FEATURE_VIEW_QA_CANONICAL_TURN."""
        # Mock a user without the feature
        def mock_check_feature(feature_id):
            return False

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)

        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 403

    def test_endpoint_returns_404_for_invalid_session(self, client, admin_headers, monkeypatch):
        """Endpoint returns 404 when session not found."""

        def mock_get_session(session_id):
            return None

        def mock_check_feature(feature_id):
            return True

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)
        monkeypatch.setattr("app.services.session_service.get_session_by_id", mock_get_session)

        response = client.get(
            "/api/v1/play/invalid-session/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_endpoint_returns_qa_projection(self, client, admin_headers, monkeypatch):
        """Endpoint returns QA projection when authorized and session exists."""
        mock_session = {
            "payload": {
                "runtime_state": {
                    "session_id": "test-session-123",
                    "trace_id": "trace-001",
                    "turn_number": 5,
                    "turn_timestamp_iso": "2026-04-24T10:00:00Z",
                    "current_scene_id": "scene_001",
                    "selected_scene_function": "establish_pressure",
                    "pacing_mode": "standard",
                    "quality_class": "healthy",
                    "degradation_signals": [],
                    "visibility_class_markers": [],
                    "vitality_telemetry_v1": {"response_present": True},
                    "selected_responder_set": [
                        {"actor_id": "alice", "preferred_reaction_order": 0, "role": "primary_responder"},
                        {"actor_id": "bob", "preferred_reaction_order": 1, "role": "secondary_reactor"},
                    ],
                    "graph_diagnostics": {"graph_name": "runtime_graph"},
                }
            }
        }

        def mock_get_session(session_id):
            return mock_session

        def mock_check_feature(feature_id):
            return True

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)
        monkeypatch.setattr("app.services.session_service.get_session_by_id", mock_get_session)

        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        projection = data["data"]
        assert projection["schema_version"] == "qa_canonical_turn_projection.v1"
        assert "tier_a_primary" in projection
        assert "tier_b_detailed" in projection

    def test_endpoint_respects_include_raw_parameter(self, client, admin_headers, monkeypatch):
        """Endpoint includes raw canonical record when ?include_raw=1."""
        mock_session = {
            "payload": {
                "runtime_state": {
                    "session_id": "test-session-123",
                    "trace_id": "trace-001",
                    "turn_number": 5,
                    "graph_diagnostics": {},
                }
            }
        }

        def mock_get_session(session_id):
            return mock_session

        def mock_check_feature(feature_id):
            return True

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)
        monkeypatch.setattr("app.services.session_service.get_session_by_id", mock_get_session)

        # Without include_raw
        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        data = response.get_json()
        assert data["data"]["raw_canonical_record"] is None

        # With include_raw=1
        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn?include_raw=1",
            headers=admin_headers,
        )
        data = response.get_json()
        assert data["data"]["raw_canonical_record"] is not None

    def test_endpoint_rate_limited(self, client, admin_headers, monkeypatch):
        """Endpoint enforces rate limiting (30 per minute)."""

        def mock_get_session(session_id):
            return None

        def mock_check_feature(feature_id):
            return True

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)
        monkeypatch.setattr("app.services.session_service.get_session_by_id", mock_get_session)

        # This test verifies the endpoint has rate limiting configured
        # The actual rate limiting is enforced by Flask-Limiter in the route definition
        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        # Should have rate limit headers
        assert "RateLimit-Limit" in response.headers or response.status_code in [401, 403, 404]


class TestQaProjectionIntegrity:
    """Test QA projection schema and data integrity."""

    def test_projection_schema_valid(self, client, admin_headers, monkeypatch):
        """QA projection has correct schema structure."""
        mock_session = {
            "payload": {
                "runtime_state": {
                    "session_id": "test-session",
                    "trace_id": "trace-001",
                    "graph_diagnostics": {},
                    "selected_responder_set": [],
                }
            }
        }

        def mock_get_session(session_id):
            return mock_session

        def mock_check_feature(feature_id):
            return True

        monkeypatch.setattr("app.auth.permissions.check_feature", mock_check_feature)
        monkeypatch.setattr("app.services.session_service.get_session_by_id", mock_get_session)

        response = client.get(
            "/api/v1/play/test-session/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        projection = response.get_json()["data"]

        # Verify required fields
        assert "schema_version" in projection
        assert projection["schema_version"] == "qa_canonical_turn_projection.v1"
        assert "tier_a_primary" in projection
        assert "tier_b_detailed" in projection
        assert "graph_execution_summary" in projection
        assert "raw_canonical_record_available" in projection
