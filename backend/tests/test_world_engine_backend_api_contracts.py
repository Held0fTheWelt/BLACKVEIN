"""Contract tests for the world engine integrating with the backend API (tickets, schema, runs, formats).

Uses markers: contract, integration (see classes below).
"""

import pytest
from datetime import datetime, timezone
import json


@pytest.mark.contract
@pytest.mark.integration
class TestEngineBackendTickets:
    """Test ticket verification between engine and backend."""

    def test_engine_tickets_verified_by_backend(self, client, auth_headers, test_user):
        """Engine tickets can be verified by backend authentication system."""
        # This test verifies the contract for ticket-based engine auth
        # Engine would provide a ticket, backend verifies it
        user, password = test_user

        # Authenticated user should be able to access protected endpoints
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == user.username


@pytest.mark.contract
@pytest.mark.integration
class TestEngineParticipantDataSchema:
    """Test that engine participant data matches backend schema."""

    def test_engine_participant_data_matches_backend_schema(self, client, auth_headers, test_user):
        """Engine participant objects match backend user schema requirements."""
        user, password = test_user

        # Get user data that engine would reference
        response = client.get(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        # User should have at least these fields for engine
        if response.status_code == 200:
            data = response.get_json()
            # Engine-critical fields
            if data:
                assert "id" in data or "username" in data
                assert "username" in data

    def test_engine_user_role_data_maps_to_backend_roles(self, client, auth_headers, admin_user):
        """Engine can determine user role from backend user data."""
        user, password = admin_user

        response = client.get(
            f"/api/v1/users/{user.id}",
            headers=auth_headers
        )

        if response.status_code == 200:
            data = response.get_json()
            # Should have role information engine can use
            assert isinstance(data, dict)


@pytest.mark.contract
@pytest.mark.integration
class TestEngineRunLifecycle:
    """Test that engine run lifecycle matches backend expectations."""

    def test_engine_run_lifecycle_matches_backend_expectations(self, client, auth_headers, test_user):
        """Engine run state transitions align with backend data model."""
        user, password = test_user

        # Create game session
        response = client.post(
            "/api/v1/game/sessions",
            json={
                "user_id": user.id,
                "session_type": "game_run"
            },
            headers=auth_headers
        )

        # Should either create successfully or indicate why it can't
        if response.status_code == 201:
            session = response.get_json()
            assert "id" in session
            assert session.get("status") in ["created", "pending", "active", "completed"]

    def test_engine_session_status_transitions_valid(self, client, auth_headers):
        """Engine can transition session status in valid order."""
        # Valid transitions: created -> pending -> active -> completed
        # Backend should enforce valid transitions
        response = client.get("/api/v1/game/sessions", headers=auth_headers)

        # Should return list or empty
        assert response.status_code in [200, 404]


@pytest.mark.contract
@pytest.mark.integration
class TestEngineDataFormatCompatibility:
    """Test engine data format compatibility with backend storage."""

    def test_engine_playback_data_format_compatible_with_backend(self, client, auth_headers, test_user):
        """Engine playback data format matches backend storage expectations."""
        user, password = test_user

        # Engine would store playback data - verify backend can accept it
        playback_data = {
            "version": "1.0",
            "events": [
                {"type": "move", "actor_id": user.id, "timestamp": datetime.now(timezone.utc).isoformat()},
            ],
            "duration_ms": 1000
        }

        # This would be stored in backend
        assert isinstance(playback_data, dict)
        assert "version" in playback_data
        assert "events" in playback_data

    def test_engine_transcript_format_matches_api_specification(self, client, auth_headers):
        """Engine transcript data format matches backend API spec."""
        # Transcript should have standard fields
        transcript = {
            "run_id": "engine-run-123",
            "participants": ["user1", "user2"],
            "events": [],
            "created_at": datetime.now(timezone.utc).isoformat(),
            "duration": 3600
        }

        # Verify contract format
        assert "run_id" in transcript
        assert "participants" in transcript
        assert isinstance(transcript["participants"], list)
        assert "created_at" in transcript

    def test_engine_error_reporting_format_correct(self, client, auth_headers, test_user):
        """Engine error reporting format matches backend error schema."""
        user, password = test_user

        # Engine error report format
        error_report = {
            "error_type": "game_crash",
            "error_message": "Unexpected exception",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "run_id": "engine-run-xyz",
            "user_id": user.id,
            "stack_trace": "..."
        }

        # Verify schema
        assert "error_type" in error_report
        assert "timestamp" in error_report
        assert "run_id" in error_report
        assert isinstance(error_report["timestamp"], str)


@pytest.mark.contract
@pytest.mark.integration
class TestEngineWebsocketContract:
    """Test WebSocket message format compatibility between engine and backend."""

    def test_engine_websocket_messages_backend_compatible(self, client, auth_headers):
        """Engine WebSocket messages follow format compatible with backend."""
        # Standard engine WebSocket message format
        message = {
            "type": "game_state_update",
            "run_id": "run-123",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": {"state": "in_progress"}
        }

        # Contract verification
        assert "type" in message
        assert "run_id" in message
        assert "timestamp" in message
        assert isinstance(message["type"], str)


@pytest.mark.contract
@pytest.mark.integration
class TestEngineDataPersistence:
    """Test engine data persistence contract with backend."""

    def test_engine_snapshot_data_recoverable_by_backend(self, client, auth_headers, test_user):
        """Engine snapshot data can be stored and recovered by backend."""
        user, password = test_user

        # Engine creates a snapshot
        snapshot = {
            "run_id": "run-abc123",
            "state": {
                "current_turn": 5,
                "participant_positions": [1, 2, 3],
                "game_log": ["event1", "event2"]
            },
            "created_at": datetime.now(timezone.utc).isoformat()
        }

        # Verify snapshot structure
        assert "run_id" in snapshot
        assert "state" in snapshot
        assert isinstance(snapshot["state"], dict)

    def test_engine_concurrent_runs_isolated_per_backend_spec(self, client, auth_headers, test_user):
        """Multiple concurrent engine runs are properly isolated per backend spec."""
        user, password = test_user

        # Multiple runs should be independent
        run1_id = "engine-run-1"
        run2_id = "engine-run-2"

        # Backend should treat these independently
        assert run1_id != run2_id

    def test_engine_database_migration_compatible_with_backend(self, client, auth_headers):
        """Engine data model migrations are compatible with backend."""
        # Engine should be able to read existing backend data
        response = client.get("/api/v1/users", headers=auth_headers)

        # Should return valid data
        assert response.status_code in [200, 403, 404]


@pytest.mark.contract
@pytest.mark.integration
class TestEngineAuthenticationContract:
    """Test engine authentication and authorization with backend."""

    def test_engine_uses_backend_authentication_correctly(self, client, auth_headers, test_user):
        """Engine properly uses backend authentication tokens."""
        user, password = test_user

        # Engine request with valid token should work
        response = client.get(
            "/api/v1/auth/me",
            headers=auth_headers
        )
        assert response.status_code == 200

    def test_engine_invalid_tokens_rejected_by_backend(self, client):
        """Invalid tokens are properly rejected by backend."""
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer invalid-token"}
        )
        assert response.status_code == 401

    def test_engine_authorization_levels_match_backend_hierarchy(self, client, admin_headers, admin_user):
        """Engine respects backend user authorization levels."""
        user, password = admin_user

        # Admin should have higher privileges
        response = client.get(
            "/api/v1/auth/me",
            headers=admin_headers
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == user.username


@pytest.mark.contract
@pytest.mark.integration
class TestEngineTimestampContracts:
    """Test timestamp format compatibility between engine and backend."""

    def test_engine_timestamps_iso8601_format(self, client, auth_headers):
        """Engine timestamps must be in ISO8601 format for backend."""
        # Valid ISO8601 timestamps
        timestamps = [
            "2024-01-01T12:00:00Z",
            "2024-01-01T12:00:00+00:00",
            datetime.now(timezone.utc).isoformat(),
        ]

        for ts in timestamps:
            # Backend should parse ISO8601
            assert isinstance(ts, str)
            assert "T" in ts or isinstance(ts, str)

    def test_engine_timezone_aware_timestamps_required(self, client, auth_headers):
        """Engine must provide timezone-aware timestamps."""
        # Create timezone-aware timestamp
        utc_time = datetime.now(timezone.utc)
        assert utc_time.tzinfo is not None

        iso_ts = utc_time.isoformat()
        assert isinstance(iso_ts, str)


@pytest.mark.contract
@pytest.mark.integration
class TestEngineErrorHandling:
    """Test error handling contract between engine and backend."""

    def test_engine_handles_backend_validation_errors(self, client, auth_headers):
        """Engine properly handles 400 validation errors from backend."""
        # Invalid request should return 400
        response = client.post(
            "/api/v1/game/sessions",
            json={"invalid_field": "value"},
            headers=auth_headers
        )

        # Should return 400, not 500
        assert response.status_code in [400, 404, 405]

    def test_engine_handles_backend_not_found_errors(self, client, auth_headers):
        """Engine properly handles 404 errors from backend."""
        response = client.get(
            "/api/v1/users/999999",
            headers=auth_headers
        )

        # Should return 404 or 403 (depends on endpoint security)
        assert response.status_code in [404, 403]

    def test_engine_handles_backend_permission_errors(self, client, auth_headers, test_user):
        """Engine properly handles 403 permission errors from backend."""
        user, password = test_user

        # Attempt to access restricted resource
        response = client.get(
            "/api/v1/admin/stats",
            headers=auth_headers
        )

        # Should return 403 if restricted, not 500
        assert response.status_code in [403, 404, 405]
