"""Configuration startup and contract tests for World Engine.

WAVE 5: Startup/Auth/Config fail-fast and explicit behavior.
Tests define required behavior for configuration loading and validation.

Mark: @pytest.mark.contract - defines configuration contract
"""

from __future__ import annotations

import os
import warnings
from pathlib import Path
from unittest.mock import patch

import pytest

from app.config import (
    validate_play_service_secret,
    validate_play_service_internal_api_key,
    validate_database_url,
    validate_redis_url,
    validate_cors_origins,
    PLAY_SERVICE_SECRET,
    PLAY_SERVICE_INTERNAL_API_KEY,
    RUN_STORE_DIR,
)


class TestPlayServiceSecretStartupContract:
    """Test PLAY_SERVICE_SECRET startup behavior and requirements."""

    @pytest.mark.contract
    def test_missing_play_service_secret_issues_warning_in_test_mode(self, monkeypatch):
        """Missing PLAY_SERVICE_SECRET in explicit test mode should issue warning."""
        monkeypatch.delenv("PLAY_SERVICE_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_SHARED_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        monkeypatch.setenv("FLASK_ENV", "test")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                import importlib
                import app.config
                importlib.reload(app.config)
                warning_messages = [str(warning.message) for warning in w]
                assert any("PLAY_SERVICE_SECRET" in msg for msg in warning_messages), \
                    f"Expected PLAY_SERVICE_SECRET warning, got: {warning_messages}"

    @pytest.mark.contract
    def test_missing_play_service_secret_fails_in_production_mode(self, monkeypatch):
        """Missing PLAY_SERVICE_SECRET should raise error in production mode."""
        monkeypatch.delenv("PLAY_SERVICE_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_SHARED_SECRET", raising=False)
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        monkeypatch.setenv("FLASK_ENV", "production")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            with pytest.raises(ValueError, match="PLAY_SERVICE_SECRET is required"):
                import importlib
                import app.config
                importlib.reload(app.config)

    @pytest.mark.contract
    def test_blank_play_service_secret_fails_in_production_mode(self, monkeypatch):
        """Blank PLAY_SERVICE_SECRET should raise error in production mode."""
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "")
        monkeypatch.setenv("FLASK_ENV", "production")

        with pytest.raises(ValueError, match="PLAY_SERVICE_SECRET is required"):
            import importlib
            import app.config
            importlib.reload(app.config)

    @pytest.mark.contract
    def test_blank_play_service_secret_rejected_in_validation(self):
        """Blank PLAY_SERVICE_SECRET should be explicitly rejected in validation."""
        # Empty string should raise
        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret("")

        # Whitespace-only should raise
        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret("   \t\n  ")

        # None should raise
        with pytest.raises(ValueError, match="play_service_secret cannot be empty"):
            validate_play_service_secret(None)

    @pytest.mark.contract
    @pytest.mark.parametrize("is_production", [True, False])
    def test_play_service_secret_length_requirements(self, is_production):
        """PLAY_SERVICE_SECRET length requirements differ by environment."""
        # In production: must be at least 32 bytes
        if is_production:
            with pytest.raises(ValueError, match="play_service_secret must be at least 32 bytes in production"):
                validate_play_service_secret("short", is_production=True)

            # Exactly 32 bytes should pass
            result = validate_play_service_secret("a" * 32, is_production=True)
            assert result is True

        # In test: short secrets acceptable
        result = validate_play_service_secret("short", is_production=False)
        assert result is True

    @pytest.mark.contract
    def test_play_service_secret_from_env_or_fallback(self, monkeypatch):
        """PLAY_SERVICE_SECRET loads from PLAY_SERVICE_SECRET or PLAY_SERVICE_SHARED_SECRET."""
        # Primary env var takes precedence
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "primary-secret")
        monkeypatch.setenv("PLAY_SERVICE_SHARED_SECRET", "fallback-secret")

        import importlib
        import app.config
        importlib.reload(app.config)
        # After reload, PLAY_SERVICE_SECRET should be the primary value
        from app.config import PLAY_SERVICE_SECRET as pss
        assert pss == "primary-secret"

    @pytest.mark.contract
    def test_validate_play_service_secret_function_exists(self):
        """validate_play_service_secret function must exist and be callable."""
        assert callable(validate_play_service_secret)
        assert validate_play_service_secret("valid_secret_32_chars_long_ok", is_production=False) is True


class TestPlayServiceInternalApiKeyStartupContract:
    """Test PLAY_SERVICE_INTERNAL_API_KEY startup behavior and requirements."""

    @pytest.mark.contract
    def test_internal_api_key_optional(self, monkeypatch):
        """PLAY_SERVICE_INTERNAL_API_KEY is optional but when set should not be blank."""
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)
        # Ensure PLAY_SERVICE_SECRET is set so config doesn't fail
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "test-secret-for-config-test")
        monkeypatch.setenv("FLASK_ENV", "test")

        from unittest.mock import patch
        with patch("dotenv.load_dotenv"):
            import importlib
            import app.config
            importlib.reload(app.config)
            from app.config import PLAY_SERVICE_INTERNAL_API_KEY as piak
            # Should be None when not set
            assert piak is None

    @pytest.mark.contract
    def test_internal_api_key_blank_becomes_none(self, monkeypatch):
        """Blank PLAY_SERVICE_INTERNAL_API_KEY should be treated as None."""
        monkeypatch.setenv("PLAY_SERVICE_INTERNAL_API_KEY", "   ")

        import importlib
        import app.config
        importlib.reload(app.config)
        from app.config import PLAY_SERVICE_INTERNAL_API_KEY as piak
        # Should be None when set to whitespace
        assert piak is None

    @pytest.mark.contract
    def test_internal_api_key_when_set(self, monkeypatch):
        """When PLAY_SERVICE_INTERNAL_API_KEY is set, it should be preserved."""
        monkeypatch.setenv("PLAY_SERVICE_INTERNAL_API_KEY", "valid-api-key")

        import importlib
        import app.config
        importlib.reload(app.config)
        from app.config import PLAY_SERVICE_INTERNAL_API_KEY as piak
        assert piak == "valid-api-key"

    @pytest.mark.contract
    def test_validate_internal_api_key_function_exists(self):
        """validate_play_service_internal_api_key function must exist and be callable."""
        assert callable(validate_play_service_internal_api_key)

    @pytest.mark.contract
    def test_internal_api_key_validation_accepts_valid_key(self):
        """Valid internal API key should pass validation."""
        result = validate_play_service_internal_api_key("valid-key-123", is_required=False)
        assert result is True

    @pytest.mark.contract
    def test_internal_api_key_validation_rejects_blank_when_required(self):
        """Blank key should be rejected when required."""
        with pytest.raises(ValueError, match="play_service_internal_api_key cannot be empty when required"):
            validate_play_service_internal_api_key("", is_required=True)

        with pytest.raises(ValueError, match="play_service_internal_api_key cannot be empty when required"):
            validate_play_service_internal_api_key(None, is_required=True)

    @pytest.mark.contract
    def test_internal_api_key_validation_rejects_whitespace_when_set(self):
        """Whitespace-only key should be rejected when already set."""
        with pytest.raises(ValueError, match="play_service_internal_api_key cannot be blank"):
            validate_play_service_internal_api_key("   ", is_required=False)


class TestRunStoreDirStartupContract:
    """Test RUN_STORE_DIR startup behavior and requirements."""

    @pytest.mark.contract
    def test_run_store_dir_configured(self):
        """RUN_STORE_DIR must be configured and must be a Path."""
        assert RUN_STORE_DIR is not None
        assert isinstance(RUN_STORE_DIR, Path)

    @pytest.mark.contract
    def test_run_store_dir_has_valid_structure(self):
        """RUN_STORE_DIR should follow expected directory structure."""
        # RUN_STORE_DIR should be under DATA_DIR/runs pattern
        assert "runs" in str(RUN_STORE_DIR)
        # Should be an absolute path or relative to app root
        assert RUN_STORE_DIR.is_absolute() or str(RUN_STORE_DIR).startswith(".")


class TestDatabaseUrlValidationContract:
    """Test database URL validation contract."""

    @pytest.mark.contract
    def test_validate_database_url_function_exists(self):
        """validate_database_url function must exist and be callable."""
        assert callable(validate_database_url)

    @pytest.mark.contract
    @pytest.mark.parametrize("valid_url", [
        "postgresql://localhost/test",
        "postgres://localhost/test",
        "mysql://localhost/test",
        "sqlite:///test.db",
        "mysql+pymysql://user:pass@host/db",
        "postgresql+psycopg2://user:pass@host/db",
    ])
    def test_valid_database_urls_accepted(self, valid_url):
        """Valid database URLs should be accepted."""
        result = validate_database_url(valid_url)
        assert result is True

    @pytest.mark.contract
    @pytest.mark.parametrize("invalid_url", [
        "http://localhost/test",
        "ftp://localhost/test",
        "invalid-scheme://localhost/test",
        "",  # Empty when required
        None,  # None when required
    ])
    def test_invalid_database_urls_rejected(self, invalid_url):
        """Invalid database URLs should be rejected when required."""
        with pytest.raises(ValueError, match="database_url"):
            validate_database_url(invalid_url, required=True)

    @pytest.mark.contract
    def test_database_url_optional(self):
        """When required=False, None and empty strings should pass."""
        result = validate_database_url(None, required=False)
        assert result is True

        result = validate_database_url("", required=False)
        assert result is True


class TestRedisUrlValidationContract:
    """Test Redis URL validation contract."""

    @pytest.mark.contract
    def test_validate_redis_url_function_exists(self):
        """validate_redis_url function must exist and be callable."""
        assert callable(validate_redis_url)

    @pytest.mark.contract
    @pytest.mark.parametrize("valid_url", [
        "redis://localhost:6379",
        "redis://localhost:6379/0",
        "redis://:password@localhost:6379",
        "rediss://localhost:6379",  # TLS variant
    ])
    def test_valid_redis_urls_accepted(self, valid_url):
        """Valid Redis URLs should be accepted."""
        result = validate_redis_url(valid_url)
        assert result is True

    @pytest.mark.contract
    @pytest.mark.parametrize("invalid_url", [
        "http://localhost:6379",
        "ftp://localhost:6379",
        "postgresql://localhost:6379",
    ])
    def test_invalid_redis_urls_rejected_when_required(self, invalid_url):
        """Invalid Redis URLs should be rejected when required."""
        with pytest.raises(ValueError, match="redis_url"):
            validate_redis_url(invalid_url, required=True)

    @pytest.mark.contract
    def test_redis_url_optional_by_default(self):
        """Redis is optional by default."""
        result = validate_redis_url(None, required=False)
        assert result is True

        result = validate_redis_url("", required=False)
        assert result is True

        result = validate_redis_url("   ", required=False)
        assert result is True


class TestCorsOriginsValidationContract:
    """Test CORS origins validation contract."""

    @pytest.mark.contract
    def test_validate_cors_origins_function_exists(self):
        """validate_cors_origins function must exist and be callable."""
        assert callable(validate_cors_origins)

    @pytest.mark.contract
    @pytest.mark.parametrize("valid_origins", [
        ["https://example.com"],
        ["https://example.com", "https://app.example.com"],
        [],  # Empty list is valid
    ])
    def test_valid_cors_origins_accepted(self, valid_origins):
        """Valid CORS origins should be accepted."""
        result = validate_cors_origins(valid_origins, is_production=True)
        assert result is True

    @pytest.mark.contract
    @pytest.mark.parametrize("invalid_origin", [
        ["*"],  # Wildcards not allowed
        ["https://*"],  # Wildcards not allowed
        ["example.com"],  # Missing scheme
        ["http://example.com"],  # HTTP in production
    ])
    def test_invalid_cors_origins_rejected_in_production(self, invalid_origin):
        """Invalid CORS origins should be rejected in production."""
        with pytest.raises(ValueError, match="cors_origins"):
            validate_cors_origins(invalid_origin, is_production=True)

    @pytest.mark.contract
    def test_cors_origins_http_allowed_in_dev(self):
        """HTTP origins allowed in development mode."""
        result = validate_cors_origins(["http://localhost:3000"], is_production=False)
        assert result is True


class TestStartupReadinessDeterministic:
    """Test that startup and readiness behavior is deterministic."""

    @pytest.mark.contract
    @pytest.mark.integration
    def test_app_creates_ticket_manager_with_secret(self, client):
        """App startup must create TicketManager with configured secret."""
        from app.auth.tickets import TicketManager
        # Client is created via conftest fixture which builds the app with test-secret
        # The app.state.ticket_manager should be a TicketManager instance
        assert hasattr(client.app, "state")
        assert hasattr(client.app.state, "ticket_manager")
        assert isinstance(client.app.state.ticket_manager, TicketManager)

    @pytest.mark.contract
    @pytest.mark.integration
    def test_app_creates_runtime_manager_on_startup(self, client):
        """App startup must create RuntimeManager."""
        from app.runtime.manager import RuntimeManager
        assert hasattr(client.app, "state")
        assert hasattr(client.app.state, "manager")
        assert isinstance(client.app.state.manager, RuntimeManager)

    @pytest.mark.contract
    def test_config_loading_repeatable(self, monkeypatch):
        """Config loading should be repeatable without side effects."""
        import importlib
        import app.config as config_mod

        # Ensure environment is clean and consistent for this test
        monkeypatch.setenv("PLAY_SERVICE_SECRET", "test-secret-for-repeatability")
        monkeypatch.delenv("PLAY_SERVICE_INTERNAL_API_KEY", raising=False)

        # Reload to set consistent initial state
        config_mod = importlib.reload(config_mod)

        # Get values after first reload
        initial_secret = config_mod.PLAY_SERVICE_SECRET
        initial_api_key = config_mod.PLAY_SERVICE_INTERNAL_API_KEY
        initial_run_store = config_mod.RUN_STORE_DIR

        # Reload again - environment hasn't changed
        config_mod = importlib.reload(config_mod)

        # Values should be the same after reload
        assert config_mod.PLAY_SERVICE_SECRET == initial_secret
        assert config_mod.PLAY_SERVICE_INTERNAL_API_KEY == initial_api_key
        assert config_mod.RUN_STORE_DIR == initial_run_store


class TestTicketManagerSecretValidation:
    """Test TicketManager secret validation contract."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_manager_rejects_missing_secret(self):
        """TicketManager should reject missing secret explicitly."""
        from app.auth.tickets import TicketManager, TicketError

        with pytest.raises(TicketError, match="PLAY_SERVICE_SECRET is required"):
            # Pass None with no global secret available
            from unittest.mock import patch
            with patch("app.auth.tickets.PLAY_SERVICE_SECRET", None):
                TicketManager(None)

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_manager_rejects_blank_secret(self):
        """TicketManager should reject blank secret explicitly."""
        from app.auth.tickets import TicketManager, TicketError

        # Empty string should fail
        with pytest.raises(TicketError, match="Secret cannot be None or blank"):
            TicketManager("")

        # Whitespace-only should fail
        with pytest.raises(TicketError, match="Secret cannot be None or blank"):
            TicketManager("   ")

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_manager_accepts_valid_explicit_secret(self):
        """TicketManager should accept valid explicit secret."""
        from app.auth.tickets import TicketManager

        manager = TicketManager("valid-secret-32-chars-long-okya")
        assert manager.secret == b"valid-secret-32-chars-long-okya"

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_manager_accepts_valid_global_secret(self):
        """TicketManager should accept valid global secret when None passed."""
        from app.auth.tickets import TicketManager
        from unittest.mock import patch

        with patch("app.auth.tickets.PLAY_SERVICE_SECRET", "global-valid-secret-ok"):
            manager = TicketManager(None)
            assert manager.secret == b"global-valid-secret-ok"

    @pytest.mark.contract
    @pytest.mark.security
    def test_ticket_manager_fails_fast_on_initialization(self):
        """TicketManager should fail fast during __init__, not during use."""
        from app.auth.tickets import TicketManager, TicketError

        # Should raise immediately in __init__, not later
        with pytest.raises(TicketError):
            TicketManager("")

        # No .issue() or .verify() call should be needed to trigger error
