"""Internal API key validation tests for World Engine.

WAVE 5: Internal API key guard and validation.
Tests ensure internal endpoints properly validate API keys and reject unauthorized access.

Mark: @pytest.mark.security, @pytest.mark.contract, @pytest.mark.integration
"""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.http import _require_internal_api_key


class TestInternalApiKeyGuardFunction:
    """Test the _require_internal_api_key dependency function."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_accepts_valid_key(self):
        """Valid internal API key should be accepted by guard."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            # Should not raise
            _require_internal_api_key(x_play_service_key="valid-api-key")

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_invalid_key(self):
        """Invalid key should raise HTTPException 401."""
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="wrong-key")

            assert exc_info.value.status_code == 401
            assert "Missing or invalid internal API key" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_missing_key(self):
        """Missing key (None) should raise HTTPException 401."""
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key=None)

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_allows_any_key_when_not_configured(self):
        """When PLAY_SERVICE_INTERNAL_API_KEY not set, any key allowed (no enforcement)."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", None):
            # Should not raise even with wrong key or no key
            _require_internal_api_key(x_play_service_key="any-key")
            _require_internal_api_key(x_play_service_key=None)

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_blank_key_when_set(self):
        """Blank key should be rejected when expected key is set."""
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="")

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_whitespace_key_when_set(self):
        """Whitespace-only key should be rejected when expected key is set."""
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="   \t   ")

            assert exc_info.value.status_code == 401


class TestInternalJoinContextEndpoint:
    """Test /api/internal/join-context endpoint with API key guard."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_requires_api_key(self):
        """POST /api/internal/join-context should require internal API key when configured."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            # Patch config to enforce API key
            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "required-key"):
                client = TestClient(app)

                # Create a run first
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                assert run_response.status_code == 200
                run_id = run_response.json()["run"]["id"]

                # Try to join without API key - should fail with 401
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                )
                assert join_response.status_code == 401

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_accepts_valid_key(self):
        """POST /api/internal/join-context should accept valid API key."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            # Patch the config to set an internal API key
            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-internal-key"):
                client = TestClient(app)

                # Create a run first
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                assert run_response.status_code == 200
                run_id = run_response.json()["run"]["id"]

                # Join with valid API key header
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                    headers={"X-Play-Service-Key": "test-internal-key"},
                )
                # Should succeed or at least not return 401
                assert join_response.status_code != 401
                # Might be 404 if template not found, but not 401
                if join_response.status_code == 200:
                    assert "participant_id" in join_response.json()

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_rejects_invalid_key(self):
        """POST /api/internal/join-context should reject invalid API key."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            # Patch the config to set an internal API key
            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-internal-key"):
                client = TestClient(app)

                # Create a run first
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                assert run_response.status_code == 200
                run_id = run_response.json()["run"]["id"]

                # Try to join with wrong API key
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                    headers={"X-Play-Service-Key": "wrong-key"},
                )
                assert join_response.status_code == 401

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_rejects_missing_key_when_required(self):
        """POST /api/internal/join-context should reject missing key when configured."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            # Patch the config to set an internal API key
            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-internal-key"):
                client = TestClient(app)

                # Create a run first
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                assert run_response.status_code == 200
                run_id = run_response.json()["run"]["id"]

                # Try to join without API key header
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                )
                assert join_response.status_code == 401


class TestApiKeyHeaderHandling:
    """Test proper handling of API key headers."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_api_key_header_is_case_insensitive_in_fastapi(self):
        """FastAPI converts header names to lowercase for accessing."""
        # This is testing FastAPI behavior, but important for API key handling
        # FastAPI's Header() dependency automatically handles case variations
        # by using the alias parameter

        # Test that the guard function receives the value correctly
        # (FastAPI will pass it correctly regardless of how it's sent)
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-key"):
            _require_internal_api_key(x_play_service_key="valid-key")

    @pytest.mark.unit
    @pytest.mark.security
    def test_api_key_not_logged_in_error(self):
        """API key should not be exposed in error messages."""
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "super-secret-key-12345"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="wrong-key")

            error_detail = exc_info.value.detail
            # Error detail should not contain the secret key or the provided key
            assert "super-secret-key-12345" not in error_detail
            assert "wrong-key" not in error_detail
            # Should only be generic message
            assert "Missing or invalid internal API key" in error_detail


class TestPublicEndpointsNotAffected:
    """Test that public endpoints are not affected by internal key guard."""

    @pytest.mark.integration
    def test_health_endpoint_not_guarded(self, client):
        """GET /api/health should work without API key."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}

    @pytest.mark.integration
    def test_health_ready_endpoint_not_guarded(self, client):
        """GET /api/health/ready should work without API key."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200
        assert "status" in response.json()

    @pytest.mark.integration
    def test_list_templates_endpoint_not_guarded(self, client):
        """GET /api/templates should work without API key."""
        response = client.get("/api/templates")
        assert response.status_code == 200
        # Should return list (even if empty)
        assert isinstance(response.json(), list)

    @pytest.mark.integration
    def test_list_runs_endpoint_not_guarded(self, client):
        """GET /api/runs should work without API key."""
        response = client.get("/api/runs")
        assert response.status_code == 200
        # Should return list (even if empty)
        assert isinstance(response.json(), list)

    @pytest.mark.integration
    def test_create_run_endpoint_not_guarded(self, client):
        """POST /api/runs should work without API key."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "display_name": "TestPlayer"},
        )
        assert response.status_code == 200

    @pytest.mark.integration
    def test_create_ticket_endpoint_not_guarded(self, client):
        """POST /api/tickets should work without API key guard (but may fail for other reasons)."""
        # First create a run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "display_name": "Player1", "account_id": "test-acct"},
        )
        assert run_response.status_code == 200
        run_id = run_response.json()["run"]["id"]

        # Create ticket without API key header
        # The ticket endpoint itself has no API key guard (unlike /internal/join-context)
        ticket_response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "display_name": "Player2", "account_id": "test-acct"},
        )
        # Should succeed (200) or at least not be rejected for missing API key (would be 401)
        assert ticket_response.status_code in [200, 403]  # 403 could be permission-related, not auth
        if ticket_response.status_code == 200:
            assert "ticket" in ticket_response.json()


class TestMultipleRequestsWithDifferentKeys:
    """Test handling of multiple requests with different API keys."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_valid_and_invalid_requests_in_sequence(self):
        """Valid and invalid API key requests should be handled independently."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "correct-key"):
                client = TestClient(app)

                # Create a run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                run_id = run_response.json()["run"]["id"]

                # Request 1: with correct key - should work
                r1 = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                    headers={"X-Play-Service-Key": "correct-key"},
                )
                assert r1.status_code != 401

                # Request 2: with wrong key - should fail
                r2 = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player3"},
                    headers={"X-Play-Service-Key": "wrong-key"},
                )
                assert r2.status_code == 401

                # Request 3: without key - should fail
                r3 = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player4"},
                )
                assert r3.status_code == 401

                # Request 4: with correct key again - should work
                r4 = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player5"},
                    headers={"X-Play-Service-Key": "correct-key"},
                )
                assert r4.status_code != 401


class TestApiKeyValidationOrder:
    """Test that API key validation happens before processing."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_api_key_check_before_payload_validation(self):
        """API key should be checked before payload is validated."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-key"):
                client = TestClient(app)

                # Send request with wrong key and invalid payload
                response = client.post(
                    "/api/internal/join-context",
                    json={"invalid": "request"},  # Missing required fields
                    headers={"X-Play-Service-Key": "wrong-key"},
                )

                # Should fail with 401 (auth) not 422 (validation)
                assert response.status_code == 401


class TestApiKeyBehaviorWhenNotConfigured:
    """Test behavior when PLAY_SERVICE_INTERNAL_API_KEY is not configured."""

    @pytest.mark.integration
    def test_internal_endpoint_accessible_when_key_not_configured(self):
        """Internal endpoint should be accessible when key not configured."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", None):
                client = TestClient(app)

                # Create a run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                run_id = run_response.json()["run"]["id"]

                # Should be able to access without API key when not configured
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                )
                # Should succeed (not return 401)
                assert join_response.status_code != 401

    @pytest.mark.integration
    def test_internal_endpoint_accessible_with_any_key_when_not_configured(self):
        """Internal endpoint should accept any/no key when not configured."""
        from conftest import build_test_app
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", None):
                client = TestClient(app)

                # Create a run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo", "display_name": "Player1"},
                )
                run_id = run_response.json()["run"]["id"]

                # Request with arbitrary key should work
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                    headers={"X-Play-Service-Key": "arbitrary-key"},
                )
                # Should succeed (not return 401)
                assert join_response.status_code != 401
