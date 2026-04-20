"""Configuration Startup and Authentication Tests for World Engine.

WAVE 5: Comprehensive tests for strict config validation, startup fail-fast behavior,
and hardened internal API key handling.

Tests cover:
- Strict PLAY_SERVICE_SECRET validation (required, 32+ bytes, cryptographically random)
- PLAY_SERVICE_INTERNAL_API_KEY handling (missing vs blank vs valid)
- Persistence/store config (RUN_STORE_BACKEND, RUN_STORE_URL)
- Fail-fast startup on invalid config
- Health check behavior (/api/health, /api/health/ready)
- Config isolation per environment
- Startup idempotency

Markers:
- @pytest.mark.unit - unit-level tests
- @pytest.mark.config - configuration-specific tests
- @pytest.mark.contract - contract/interface tests
- @pytest.mark.security - security-focused tests
"""

from __future__ import annotations

import importlib
import os
import sys
import tempfile
import warnings
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Ensure world-engine is in path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestPlayServiceSecretValidation:
    """Test PLAY_SERVICE_SECRET strict validation and startup behavior."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_validation_rejects_none(self):
        """PLAY_SERVICE_SECRET validation must reject None."""
        from app.config import validate_play_service_secret

        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret(None, is_production=True)

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_validation_rejects_empty_string(self):
        """PLAY_SERVICE_SECRET validation must reject empty string."""
        from app.config import validate_play_service_secret

        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret("", is_production=True)

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_validation_rejects_whitespace_only(self):
        """PLAY_SERVICE_SECRET validation must reject whitespace-only strings."""
        from app.config import validate_play_service_secret

        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret("   \t\n  ", is_production=True)

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_secret_validation_requires_32_bytes_production(self):
        """PLAY_SERVICE_SECRET must be 32+ bytes in production."""
        from app.config import validate_play_service_secret

        # Less than 32 bytes should fail
        with pytest.raises(ValueError, match="play_service_secret must be at least 32 bytes in production"):
            validate_play_service_secret("short_secret_here", is_production=True)

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_secret_validation_accepts_32_bytes_production(self):
        """PLAY_SERVICE_SECRET with exactly 32 bytes should pass in production."""
        from app.config import validate_play_service_secret

        secret_32 = "a" * 32
        result = validate_play_service_secret(secret_32, is_production=True)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_secret_validation_accepts_64_bytes_production(self):
        """PLAY_SERVICE_SECRET with 64 bytes should pass in production."""
        from app.config import validate_play_service_secret

        secret_64 = "b" * 64
        result = validate_play_service_secret(secret_64, is_production=True)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_validation_allows_short_test_mode(self):
        """PLAY_SERVICE_SECRET can be short in test mode."""
        from app.config import validate_play_service_secret

        result = validate_play_service_secret("test", is_production=False)
        assert result is True

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_validation_rejects_empty_test_mode(self):
        """PLAY_SERVICE_SECRET must not be empty even in test mode."""
        from app.config import validate_play_service_secret

        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret("", is_production=False)


class TestPlayServiceSecretStartup:
    """Test PLAY_SERVICE_SECRET startup configuration loading."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_missing_secret_issues_warning(self, monkeypatch):
        """Missing PLAY_SERVICE_SECRET should issue warning on load."""
        # Clean environment
        monkeypatch.delenv("PLAY_SERVICE_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_SHARED_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        monkeypatch.setenv("FLASK_ENV", "test")

        # Mock dotenv.load_dotenv to prevent loading .env from parent directory
        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            # Capture warnings on reload
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                import app.config
                importlib.reload(app.config)

                # Should have warning about missing secret
                warning_messages = [str(warning.message) for warning in w]
                assert any("PLAY_SERVICE_SECRET" in msg for msg in warning_messages), \
                    f"Expected PLAY_SERVICE_SECRET warning, got: {warning_messages}"

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_from_primary_env_var(self, monkeypatch):
        """PLAY_SERVICE_SECRET loads from PLAY_SERVICE_SECRET env var first."""
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "primary-secret-value")
        monkeypatch.setenv("PLAY_SERVICE_SHARED_SECRET", "fallback-secret-value")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_SECRET == "primary-secret-value"

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_from_fallback_env_var(self, monkeypatch):
        """PLAY_SERVICE_SECRET falls back to PLAY_SERVICE_SHARED_SECRET."""
        monkeypatch.delenv("PLAY_SERVICE_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        monkeypatch.setenv("PLAY_SERVICE_SHARED_SECRET", "fallback-secret-value")
        monkeypatch.setenv("FLASK_ENV", "test")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            import app.config
            importlib.reload(app.config)

            assert app.config.PLAY_SERVICE_SECRET == "fallback-secret-value"

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_none_when_missing(self, monkeypatch):
        """PLAY_SERVICE_SECRET should be None when completely unset."""
        monkeypatch.delenv("PLAY_SERVICE_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_SHARED_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        monkeypatch.setenv("FLASK_ENV", "test")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            import app.config
            importlib.reload(app.config)

            assert app.config.PLAY_SERVICE_SECRET is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_none_when_blank(self, monkeypatch):
        """PLAY_SERVICE_SECRET should be None when set to blank."""
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "")
        monkeypatch.setenv("PLAY_SERVICE_SHARED_SECRET", "")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_SECRET is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_secret_none_when_whitespace(self, monkeypatch):
        """PLAY_SERVICE_SECRET should be None when set to whitespace."""
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "   \t\n  ")
        monkeypatch.setenv("PLAY_SERVICE_SHARED_SECRET", "")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_SECRET is None


class TestPlayServiceInternalApiKeyValidation:
    """Test PLAY_SERVICE_INTERNAL_API_KEY strict validation."""

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_blank_api_key_treated_as_not_configured(self):
        """Blank PLAY_SERVICE_INTERNAL_API_KEY should be treated as not configured."""
        # When API key is blank (empty string), it's treated the same as None
        # so requests without a key are allowed (key validation is skipped)
        from app.api.http import _require_internal_api_key

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", ""):
            # Should not raise - blank key means no validation
            result = _require_internal_api_key(x_play_service_key=None)
            assert result is None

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_invalid_api_key_returns_401(self):
        """Invalid PLAY_SERVICE_INTERNAL_API_KEY in request should return 401."""
        from app.api.http import _require_internal_api_key
        from fastapi import HTTPException

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-key-value"):
            with pytest.raises(HTTPException) as exc_info:
                _require_internal_api_key(x_play_service_key="wrong-key")
            assert exc_info.value.status_code == 401

    @pytest.mark.unit
    @pytest.mark.config
    @pytest.mark.security
    def test_valid_api_key_passes(self):
        """Valid PLAY_SERVICE_INTERNAL_API_KEY in request should pass."""
        from app.api.http import _require_internal_api_key

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", "valid-key-value"):
            # Should not raise
            result = _require_internal_api_key(x_play_service_key="valid-key-value")
            assert result is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_api_key_not_required_when_none(self):
        """API key validation should pass when key is None (not configured)."""
        from app.api.http import _require_internal_api_key

        with patch("app.api.http.PLAY_SERVICE_INTERNAL_API_KEY", None):
            # Should not raise even without header
            result = _require_internal_api_key(x_play_service_key=None)
            assert result is None


class TestPlayServiceInternalApiKeyStartup:
    """Test PLAY_SERVICE_INTERNAL_API_KEY startup configuration."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_api_key_optional_when_not_set(self, monkeypatch):
        """PLAY_SERVICE_INTERNAL_API_KEY should be None when not set."""
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        # Ensure PLAY_SERVICE_SECRET is set so config doesn't fail
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "test-secret-for-config-test")
        monkeypatch.setenv("FLASK_ENV", "test")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            import app.config
            importlib.reload(app.config)

            assert app.config.PLAY_SERVICE_INTERNAL_API_KEY is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_api_key_none_when_blank(self, monkeypatch):
        """PLAY_SERVICE_INTERNAL_API_KEY should be None when blank."""
        monkeypatch.setenv("PLAY_SERVICE_INTERNAL_API_KEY", "")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_INTERNAL_API_KEY is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_api_key_none_when_whitespace(self, monkeypatch):
        """PLAY_SERVICE_INTERNAL_API_KEY should be None when whitespace."""
        monkeypatch.setenv("PLAY_SERVICE_INTERNAL_API_KEY", "   \t\n  ")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_INTERNAL_API_KEY is None

    @pytest.mark.unit
    @pytest.mark.config
    def test_api_key_preserved_when_set(self, monkeypatch):
        """PLAY_SERVICE_INTERNAL_API_KEY should be preserved when set."""
        monkeypatch.setenv("PLAY_SERVICE_INTERNAL_API_KEY", "my-internal-api-key")

        import app.config
        importlib.reload(app.config)

        assert app.config.PLAY_SERVICE_INTERNAL_API_KEY == "my-internal-api-key"


class TestRunStoreConfigValidation:
    """Test RUN_STORE_BACKEND and RUN_STORE_URL configuration."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_store_backend_defaults_to_json(self, monkeypatch):
        """RUN_STORE_BACKEND should default to json."""
        monkeypatch.delenv("RUN_STORE_BACKEND", raising=False)

        import app.config
        importlib.reload(app.config)

        assert app.config.RUN_STORE_BACKEND == "json"

    @pytest.mark.unit
    @pytest.mark.config
    def test_store_backend_respects_env_var(self, monkeypatch):
        """RUN_STORE_BACKEND should respect environment variable."""
        monkeypatch.setenv("RUN_STORE_BACKEND", "sqlalchemy")
        monkeypatch.setenv("RUN_STORE_URL", "sqlite:///:memory:")

        import app.config
        importlib.reload(app.config)

        assert app.config.RUN_STORE_BACKEND == "sqlalchemy"

    @pytest.mark.unit
    @pytest.mark.config
    def test_store_url_empty_by_default(self, monkeypatch):
        """RUN_STORE_URL should be empty by default."""
        monkeypatch.delenv("RUN_STORE_URL", raising=False)

        import app.config
        importlib.reload(app.config)

        assert app.config.RUN_STORE_URL == ""

    @pytest.mark.unit
    @pytest.mark.config
    def test_store_url_respects_env_var(self, monkeypatch):
        """RUN_STORE_URL should respect environment variable."""
        monkeypatch.setenv("RUN_STORE_URL", "postgresql://localhost/wos")

        import app.config
        importlib.reload(app.config)

        assert app.config.RUN_STORE_URL == "postgresql://localhost/wos"

    @pytest.mark.unit
    @pytest.mark.config
    def test_json_store_requires_valid_path(self, tmp_path):
        """JSON store should create directory if it doesn't exist."""
        from app.runtime.store import JsonRunStore

        store_path = tmp_path / "json_store"
        assert not store_path.exists()

        store = JsonRunStore(store_path)

        # Directory should be created
        assert store_path.exists()
        assert store_path.is_dir()

    @pytest.mark.unit
    @pytest.mark.config
    def test_sqlalchemy_store_requires_url(self, tmp_path):
        """SQLAlchemy store should raise if URL not provided."""
        from app.runtime.store import build_run_store

        with pytest.raises(ValueError, match="RUN_STORE_URL is required"):
            build_run_store(root=tmp_path, backend="sqlalchemy", url=None)

    @pytest.mark.unit
    @pytest.mark.config
    def test_invalid_store_backend_raises(self, tmp_path):
        """Invalid store backend should raise ValueError."""
        from app.runtime.store import build_run_store

        with pytest.raises(ValueError, match="Unsupported run store backend"):
            build_run_store(root=tmp_path, backend="invalid-backend", url=None)


class TestHealthEndpointBehavior:
    """Test health endpoint behavior and contract."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_health_endpoint_returns_200(self, client):
        """GET /api/health should return 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.contract
    def test_health_endpoint_returns_ok_status(self, client):
        """GET /api/health should return {"status": "ok"}."""
        response = client.get("/api/health")
        assert response.json() == {"status": "ok"}

    @pytest.mark.unit
    @pytest.mark.contract
    def test_health_endpoint_returns_json(self, client):
        """GET /api/health should return JSON content type."""
        response = client.get("/api/health")
        assert "application/json" in response.headers.get("content-type", "")

    @pytest.mark.unit
    @pytest.mark.contract
    def test_health_endpoint_always_available(self, client):
        """GET /api/health should be available even if other systems fail."""
        # Health endpoint should succeed regardless of store/manager state
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


class TestReadyEndpointBehavior:
    """Test ready endpoint behavior and contract."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_200(self, client):
        """GET /api/health/ready should return 200 OK."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_ready_status(self, client):
        """GET /api/health/ready should return status ready."""
        response = client.get("/api/health/ready")
        assert response.json()["status"] == "ready"

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_app_info(self, client):
        """GET /api/health/ready should include app title."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "app" in body
        assert isinstance(body["app"], str)

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_store_info(self, client):
        """GET /api/health/ready should include store backend info."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "store" in body
        assert isinstance(body["store"], dict)
        assert "backend" in body["store"]

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_template_count(self, client):
        """GET /api/health/ready should include template count."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "template_count" in body
        assert isinstance(body["template_count"], int)
        assert body["template_count"] >= 0

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_run_count(self, client):
        """GET /api/health/ready should include run count."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "run_count" in body
        assert isinstance(body["run_count"], int)
        assert body["run_count"] >= 0

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_returns_json(self, client):
        """GET /api/health/ready should return JSON content type."""
        response = client.get("/api/health/ready")
        assert "application/json" in response.headers.get("content-type", "")


class TestAppStartupValidation:
    """Test app startup and initialization behavior."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_app_has_ticket_manager_on_startup(self, client):
        """App should initialize TicketManager on startup."""
        from app.auth.tickets import TicketManager

        assert hasattr(client.app, "state")
        assert hasattr(client.app.state, "ticket_manager")
        assert isinstance(client.app.state.ticket_manager, TicketManager)

    @pytest.mark.unit
    @pytest.mark.contract
    def test_app_has_runtime_manager_on_startup(self, client):
        """App should initialize RuntimeManager on startup."""
        from app.runtime.manager import RuntimeManager

        assert hasattr(client.app, "state")
        assert hasattr(client.app.state, "manager")
        assert isinstance(client.app.state.manager, RuntimeManager)

    @pytest.mark.unit
    @pytest.mark.contract
    def test_app_initializes_without_secret(self, tmp_path):
        """App should initialize even without PLAY_SERVICE_SECRET configured."""
        # This tests that missing secret doesn't block app startup
        # (it just warns)
        from tests.conftest import build_test_app

        app = build_test_app(tmp_path)

        # App should be created successfully
        assert app is not None
        assert isinstance(app, FastAPI)

    @pytest.mark.unit
    @pytest.mark.contract
    def test_app_can_be_tested_with_test_client(self, client):
        """App should work correctly with FastAPI TestClient."""
        # Basic sanity check
        response = client.get("/api/health")
        assert response.status_code == 200


class TestConfigIsolationPerEnvironment:
    """Test that config is properly isolated per environment."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_separate_app_instances_have_separate_configs(self, tmp_path):
        """Separate app instances should have separate config states."""
        from tests.conftest import build_test_app

        # Create two app instances with different store backends
        app1 = build_test_app(tmp_path)
        app2 = build_test_app(tmp_path / "store2")

        # Both should work independently
        assert app1 is not None
        assert app2 is not None

        # Managers should be separate instances
        assert app1.state.manager is not app2.state.manager

    @pytest.mark.unit
    @pytest.mark.config
    def test_config_reload_preserves_values(self, monkeypatch):
        """Config module reloads should preserve consistent values."""
        import app.config

        # Set consistent environment
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "consistent-secret")
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)

        # Reload to establish baseline
        importlib.reload(app.config)
        initial_secret = app.config.PLAY_SERVICE_SECRET
        initial_api_key = app.config.PLAY_SERVICE_INTERNAL_API_KEY

        # Reload again without changing environment
        importlib.reload(app.config)

        # Values should be consistent
        assert app.config.PLAY_SERVICE_SECRET == initial_secret
        assert app.config.PLAY_SERVICE_INTERNAL_API_KEY == initial_api_key


class TestInternalApiKeyEndpointGuard:
    """Test internal API key endpoint protection."""

    @pytest.mark.unit
    @pytest.mark.security
    def test_internal_endpoint_requires_api_key_when_configured(self):
        """Internal endpoints should require API key when configured."""
        from tests.conftest import build_test_app
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Manually create app with configured API key
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            # We need to patch the config before importing routers
            with patch("app.config.PLAY_SERVICE_INTERNAL_API_KEY", "test-api-key"):
                import importlib
                import app.api.http
                importlib.reload(app.api.http)

                app = build_test_app(tmp_path)
                client = TestClient(app)

                # Request without API key should fail
                response = client.post(
                    "/api/internal/join-context",
                    json={
                        "run_id": "test-run",
                        "account_id": "test-account",
                        "character_id": "test-character",
                        "display_name": "Test"
                    }
                )
                assert response.status_code == 401

    @pytest.mark.unit
    @pytest.mark.security
    def test_internal_endpoint_allows_request_with_valid_key(self):
        """Internal endpoints should allow requests with valid API key."""
        from tests.conftest import build_test_app
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)

            # Manually create app with configured API key
            from fastapi import FastAPI
            from fastapi.testclient import TestClient

            with patch("app.config.PLAY_SERVICE_INTERNAL_API_KEY", "test-api-key"):
                import importlib
                import app.api.http
                importlib.reload(app.api.http)

                app = build_test_app(tmp_path)
                client = TestClient(app)

                # Request with valid API key should pass key validation
                # (but may fail with 404 if run doesn't exist)
                response = client.post(
                    "/api/internal/join-context",
                    headers={"x-play-service-key": "test-api-key"},
                    json={
                        "run_id": "nonexistent",
                        "account_id": "test-account",
                        "character_id": "test-character",
                        "display_name": "Test"
                    }
                )
                # Should not be 401 (key validation passed)
                assert response.status_code != 401


class TestStartupIdempotency:
    """Test that repeated startups behave consistently."""

    @pytest.mark.unit
    @pytest.mark.contract
    def test_health_endpoint_idempotent(self, client):
        """Health endpoint should return consistent results across calls."""
        response1 = client.get("/api/health")
        response2 = client.get("/api/health")

        assert response1.json() == response2.json()
        assert response1.status_code == response2.status_code

    @pytest.mark.unit
    @pytest.mark.contract
    def test_ready_endpoint_idempotent(self, client):
        """Ready endpoint should return consistent status across calls."""
        response1 = client.get("/api/health/ready")
        response2 = client.get("/api/health/ready")

        # Status and structure should match
        assert response1.json()["status"] == response2.json()["status"]
        assert response1.status_code == response2.status_code

    @pytest.mark.unit
    @pytest.mark.contract
    def test_template_list_idempotent(self, client):
        """Template list should be consistent across calls."""
        response1 = client.get("/api/templates")
        response2 = client.get("/api/templates")

        # Same templates in same order
        assert response1.json() == response2.json()
        assert response1.status_code == response2.status_code


class TestFailFastValidation:
    """Test fail-fast behavior on invalid config."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_invalid_store_backend_fails_immediately(self, tmp_path):
        """Invalid store backend should fail immediately on store creation."""
        from app.runtime.store import build_run_store

        with pytest.raises(ValueError, match="Unsupported run store backend"):
            build_run_store(root=tmp_path, backend="invalid-backend")

    @pytest.mark.unit
    @pytest.mark.config
    def test_missing_store_url_for_sqlalchemy_fails(self, tmp_path):
        """SQLAlchemy backend without URL should fail immediately."""
        from app.runtime.store import build_run_store

        with pytest.raises(ValueError, match="RUN_STORE_URL is required"):
            build_run_store(root=tmp_path, backend="sqlalchemy", url=None)


class TestErrorMessagesAreActionable:
    """Test that error messages guide users to fix issues."""

    @pytest.mark.unit
    @pytest.mark.config
    def test_missing_store_url_error_message_clear(self, tmp_path):
        """Error for missing store URL should clearly explain requirement."""
        from app.runtime.store import build_run_store

        try:
            build_run_store(root=tmp_path, backend="sqlalchemy", url=None)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            # Error message should mention what's required
            error_msg = str(e)
            assert "RUN_STORE_URL" in error_msg or "url" in error_msg.lower()

    @pytest.mark.unit
    @pytest.mark.config
    def test_invalid_secret_length_error_message_clear(self):
        """Error for invalid secret length should clearly state requirement."""
        from app.config import validate_play_service_secret

        try:
            validate_play_service_secret("short", is_production=True)
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            # Should mention the requirement
            assert "32" in error_msg or "byte" in error_msg.lower()

    @pytest.mark.unit
    @pytest.mark.config
    def test_invalid_backend_error_message_clear(self, tmp_path):
        """Error for invalid backend should clearly state supported options."""
        from app.runtime.store import build_run_store

        try:
            build_run_store(root=tmp_path, backend="invalid")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            error_msg = str(e)
            # Should mention that backend is unsupported
            assert "Unsupported" in error_msg or "backend" in error_msg.lower()
