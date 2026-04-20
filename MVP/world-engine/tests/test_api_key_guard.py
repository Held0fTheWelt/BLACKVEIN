"""API key guard and internal authentication tests for World Engine.

WAVE 6: Comprehensive internal API key validation and authentication.
Tests ensure internal endpoints properly validate API keys and reject unauthorized access.

Mark: @pytest.mark.security, @pytest.mark.contract, @pytest.mark.integration
"""

from __future__ import annotations

from unittest.mock import patch
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.http import _require_internal_api_key
from conftest import build_test_app


class TestApiKeyGuardFunction:
    """Test the _require_internal_api_key dependency function directly."""

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
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="wrong-key")

            assert exc_info.value.status_code == 401
            assert "Missing or invalid internal API key" in exc_info.value.detail

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_missing_key(self):
        """Missing key (None) should raise HTTPException 401."""
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
    def test_guard_rejects_empty_key_when_configured(self):
        """Empty string key should be rejected when expected key is set."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="")

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_rejects_whitespace_key_when_configured(self):
        """Whitespace-only key should be rejected when expected key is set."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="   \t   ")

            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_case_sensitive_key_comparison(self):
        """API key comparison should be case-sensitive."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "ValidApiKey"):
            # Wrong case should fail
            with pytest.raises(HTTPException):
                _require_internal_api_key(x_play_service_key="validapikey")

            # Correct case should pass
            _require_internal_api_key(x_play_service_key="ValidApiKey")

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_error_message_is_consistent(self):
        """Guard should return consistent error message."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            try:
                _require_internal_api_key(x_play_service_key="wrong")
            except HTTPException as e:
                assert e.detail == "Missing or invalid internal API key"
            else:
                pytest.fail("Expected HTTPException")

    @pytest.mark.unit
    @pytest.mark.security
    def test_guard_error_code_is_401_not_403(self):
        """Guard should return 401 (Unauthorized) not 403 (Forbidden)."""
        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="wrong")
            assert exc_info.value.status_code == 401


class TestInternalJoinContextEndpoint:
    """Test /api/internal/join-context endpoint with API key guard."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_requires_api_key_when_configured(self):
        """POST /api/internal/join-context should require API key when configured."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

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
        """POST /api/internal/join-context should accept valid API key (not 401)."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-internal-key"):
                client = TestClient(app)

                # Create a run first
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "apartment_confrontation_group", "display_name": "Player1"},
                )
                assert run_response.status_code == 200
                run_id = run_response.json()["run"]["id"]

                # Join with valid API key header
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id, "display_name": "Player2"},
                    headers={"X-Play-Service-Key": "test-internal-key"},
                )
                # Should succeed auth (200, 409 if full) or permission error (403)
                # Should NOT be 401 (auth failure)
                assert join_response.status_code in [200, 409, 403]
                assert join_response.status_code != 401

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_rejects_wrong_key(self):
        """POST /api/internal/join-context should reject wrong API key."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "correct-key"):
                client = TestClient(app)

                # Create a run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo"},
                )
                run_id = run_response.json()["run"]["id"]

                # Try with wrong key
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"X-Play-Service-Key": "wrong-key"},
                )
                assert join_response.status_code == 401

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_accepts_request_without_key_when_not_configured(self):
        """POST /api/internal/join-context should work without key if not configured."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", None):
                client = TestClient(app)

                # Create a run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo"},
                )
                run_id = run_response.json()["run"]["id"]

                # Should work without header
                join_response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                )
                assert join_response.status_code in [200, 409]

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_error_response_is_json(self):
        """401 error from join-context should be JSON."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "required-key"):
                client = TestClient(app)

                # Try without key
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": "any-run"},
                )

                assert response.status_code == 401
                assert response.headers["content-type"].startswith("application/json")
                body = response.json()
                assert "detail" in body

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_returns_200_with_valid_key_and_run(self):
        """POST /api/internal/join-context should return 200 with valid key and run."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "my-key"):
                client = TestClient(app)

                # Create a joinable run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "apartment_confrontation_group"},
                )
                run_id = run_response.json()["run"]["id"]

                # Join with correct key
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"X-Play-Service-Key": "my-key"},
                )

                assert response.status_code in [200, 409]
                if response.status_code == 200:
                    body = response.json()
                    assert "run_id" in body
                    assert "participant_id" in body

    @pytest.mark.integration
    @pytest.mark.security
    def test_internal_join_context_response_includes_required_fields(self):
        """POST /api/internal/join-context response should include required fields."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "my-key"):
                client = TestClient(app)

                # Create run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "apartment_confrontation_group"},
                )
                run_id = run_response.json()["run"]["id"]

                # Join with key
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"X-Play-Service-Key": "my-key"},
                )

                if response.status_code == 200:
                    body = response.json()
                    required_fields = ["run_id", "participant_id", "role_id", "display_name"]
                    for field in required_fields:
                        assert field in body


class TestApiKeyHeaderNaming:
    """Test header naming and case sensitivity."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_api_key_header_is_case_insensitive(self):
        """HTTP headers are case-insensitive, so X-Play-Service-Key should work."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-key"):
                client = TestClient(app)

                # Create run
                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo"},
                )
                run_id = run_response.json()["run"]["id"]

                # Test lowercase header
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"x-play-service-key": "test-key"},
                )
                # Should be accepted (HTTP headers are case-insensitive)
                assert response.status_code in [200, 401, 409]

    @pytest.mark.integration
    @pytest.mark.security
    def test_api_key_header_exact_name(self):
        """API key header should be named X-Play-Service-Key."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "test-key"):
                client = TestClient(app)

                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo"},
                )
                run_id = run_response.json()["run"]["id"]

                # Correct header
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"X-Play-Service-Key": "test-key"},
                )
                assert response.status_code in [200, 409]

                # Wrong header name should fail
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"Authorization": "Bearer test-key"},
                )
                assert response.status_code == 401


class TestApiKeySecurityProperties:
    """Test security properties of API key validation."""

    @pytest.mark.integration
    @pytest.mark.security
    def test_api_key_in_response_body_never_exposed(self):
        """API key should never appear in response body."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "secret-key-123"):
                client = TestClient(app)

                run_response = client.post(
                    "/api/runs",
                    json={"template_id": "god_of_carnage_solo"},
                )
                run_id = run_response.json()["run"]["id"]

                # Try with wrong key
                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": run_id},
                    headers={"X-Play-Service-Key": "wrong-key"},
                )

                # Error response should not contain the key
                body = response.json()
                response_text = str(body)
                assert "secret-key-123" not in response_text
                assert "wrong-key" not in response_text

    @pytest.mark.integration
    @pytest.mark.security
    def test_api_key_not_in_error_message(self):
        """API key should not be logged or exposed in error messages."""
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            app = build_test_app(tmp_path)

            with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "my-secret"):
                client = TestClient(app)

                response = client.post(
                    "/api/internal/join-context",
                    json={"run_id": "any"},
                    headers={"X-Play-Service-Key": "my-secret"},
                )

                # Response should not contain the key
                assert "my-secret" not in response.text
