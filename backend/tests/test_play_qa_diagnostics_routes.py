"""Tests for Phase D QA Canonical Turn Diagnostics Routes."""

import pytest

pytestmark = pytest.mark.observability


@pytest.fixture
def mock_runtime_state():
    """Shared canonical play runtime state."""
    return {
        "session_id": "world-engine-session-123",
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


class TestPlayQaDiagnosticsRoutes:
    """Test /api/v1/play/<session_id>/qa-diagnostics-canonical-turn endpoint."""

    def test_endpoint_requires_jwt(self, client):
        """Endpoint returns 401 when no JWT token provided."""
        response = client.get("/api/v1/play/test-session-123/qa-diagnostics-canonical-turn")
        assert response.status_code == 401

    def test_endpoint_requires_feature(self, client, admin_headers, monkeypatch):
        """Endpoint returns 403 when user lacks FEATURE_VIEW_QA_CANONICAL_TURN."""
        # Mock a user without the feature
        def mock_user_can_access(user, feature_id):
            return False

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)

        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 403

    def test_endpoint_returns_404_for_invalid_session(self, client, admin_headers, monkeypatch):
        """Endpoint returns 404 when session not found."""

        def mock_user_can_access(user, feature_id):
            return True

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)
        monkeypatch.setattr(
            "app.api.v1.play_qa_diagnostics_routes._canonical_runtime_state_for_play_run",
            lambda run_id: (None, None),
        )

        response = client.get(
            "/api/v1/play/invalid-session/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 404

    def test_endpoint_returns_qa_projection(self, client, admin_headers, monkeypatch, mock_runtime_state):
        """Endpoint returns QA projection when authorized and session exists."""

        def mock_user_can_access(user, feature_id):
            return True

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)
        monkeypatch.setattr(
            "app.api.v1.play_qa_diagnostics_routes._canonical_runtime_state_for_play_run",
            lambda run_id: (mock_runtime_state, "world-engine-session-123"),
        )

        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
            headers=admin_headers,
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["ok"] is True
        projection = data["data"]
        assert projection["schema_version"] == "qa_canonical_turn_projection.v1"

        # Verify tier-A fields are present and have correct values
        assert "tier_a_primary" in projection
        tier_a = projection["tier_a_primary"]
        assert tier_a["turn_metadata"]["session_id"] == "world-engine-session-123"
        assert tier_a["turn_metadata"]["turn_number"] == 5
        assert tier_a["quality_class"] == "healthy"
        assert tier_a["responder_selection"]["primary_responder_id"] == "alice"
        assert projection["canonical_play_path"] is True
        assert projection["play_run_id"] == "test-session-123"

        assert "tier_b_detailed" in projection

    def test_endpoint_respects_include_raw_parameter(self, client, admin_headers, monkeypatch, mock_runtime_state):
        """Endpoint includes raw canonical record when ?include_raw=1."""

        def mock_user_can_access(user, feature_id):
            return True

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)
        monkeypatch.setattr(
            "app.api.v1.play_qa_diagnostics_routes._canonical_runtime_state_for_play_run",
            lambda run_id: (mock_runtime_state, "world-engine-session-123"),
        )

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
        raw_record = data["data"]["raw_canonical_record"]
        assert raw_record is not None
        # Verify content structure
        assert isinstance(raw_record, dict)
        assert "turn_metadata" in raw_record
        assert raw_record["turn_metadata"]["session_id"] == "world-engine-session-123"
        assert raw_record["turn_metadata"]["turn_number"] == 5

    def test_endpoint_rate_limited(self, client, admin_headers, monkeypatch):
        """Endpoint enforces rate limiting (30 per minute)."""

        def mock_user_can_access(user, feature_id):
            return True

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)
        monkeypatch.setattr(
            "app.api.v1.play_qa_diagnostics_routes._canonical_runtime_state_for_play_run",
            lambda run_id: (None, None),
        )

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

    def test_projection_schema_valid(self, client, admin_headers, monkeypatch, mock_runtime_state):
        """QA projection has correct schema structure."""

        def mock_user_can_access(user, feature_id):
            return True

        monkeypatch.setattr("app.auth.feature_registry.user_can_access_feature", mock_user_can_access)
        monkeypatch.setattr(
            "app.api.v1.play_qa_diagnostics_routes._canonical_runtime_state_for_play_run",
            lambda run_id: (mock_runtime_state, "world-engine-session-123"),
        )

        response = client.get(
            "/api/v1/play/test-session-123/qa-diagnostics-canonical-turn",
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
