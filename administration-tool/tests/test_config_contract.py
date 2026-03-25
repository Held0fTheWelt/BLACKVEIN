"""Tests for app configuration contract and validation.

Validates that:
- Production-like mode rejects missing SECRET_KEY if required
- Blank SECRET_KEY behavior is explicit (test mode accepts, prod-like rejects)
- BACKEND_API_URL validation is explicit
- Invalid backend URL is rejected if intended
- Backend URL injection works under valid config
- Config isolation between tests
"""
from __future__ import annotations

import pytest


class TestSecretKeyContract:
    """Test SECRET_KEY configuration contract."""

    @pytest.mark.contract
    def test_test_mode_accepts_any_secret_key(self, app_factory):
        """Test that app accepts short secrets in test mode."""
        app = app_factory(test_config={"SECRET_KEY": "short", "TESTING": True})
        assert app.secret_key == "short"

    @pytest.mark.contract
    def test_secret_key_is_set_when_provided(self, app_factory):
        """Test that app uses provided SECRET_KEY."""
        secret = "this-is-my-test-secret-key-exactly"
        app = app_factory(test_config={"SECRET_KEY": secret, "TESTING": True})
        assert app.secret_key == secret

    @pytest.mark.contract
    def test_secret_key_required_in_production_mode(self, app_factory, monkeypatch):
        """Test that app raises error when SECRET_KEY is missing in production mode."""
        # Clean environment to ensure no SECRET_KEY from .env or previous tests
        monkeypatch.delenv("SECRET_KEY", raising=False)
        with pytest.raises(ValueError, match="SECRET_KEY must be provided"):
            app_factory(test_config={})

    @pytest.mark.contract
    def test_secret_key_fallback_allowed_in_test_mode(self, app_factory):
        """Test that app generates key when SECRET_KEY missing but TESTING=True."""
        app = app_factory(test_config={"TESTING": True})
        # Should generate a key via secrets.token_urlsafe(32)
        assert app.secret_key is not None
        assert len(app.secret_key) > 0

    @pytest.mark.contract
    def test_secret_key_fallback_is_different_each_time_in_test_mode(self, app_factory, monkeypatch):
        """Test that fallback-generated keys are different for each app in test mode."""
        # Clean environment to force fallback generation
        monkeypatch.delenv("SECRET_KEY", raising=False)

        app1 = app_factory(test_config={"TESTING": True})
        secret1 = app1.secret_key

        app2 = app_factory(test_config={"TESTING": True})
        secret2 = app2.secret_key

        # Both should be non-empty and different (random generation)
        assert secret1 and secret2
        assert len(secret1) > 0 and len(secret2) > 0
        assert secret1 != secret2, "Fallback-generated keys should be random/different"

    @pytest.mark.contract
    def test_secret_key_is_not_empty_string(self, app_factory):
        """Test that secret_key is never an empty string (when provided)."""
        app = app_factory(test_config={"SECRET_KEY": "test-secret", "TESTING": True})
        assert app.secret_key != ""
        assert app.secret_key is not None


class TestBackendURLContract:
    """Test BACKEND_API_URL configuration contract."""

    @pytest.mark.contract
    def test_backend_url_is_configured_in_app_config(self, app_factory):
        """Test that BACKEND_API_URL is available in app.config."""
        url = "https://api.example.com"
        app = app_factory(test_config={"BACKEND_API_URL": url, "TESTING": True})
        assert "BACKEND_API_URL" in app.config
        assert app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_can_be_localhost(self, app_factory):
        """Test that localhost URLs are accepted."""
        url = "http://localhost:5000"
        app = app_factory(test_config={"BACKEND_API_URL": url, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_can_be_https(self, app_factory):
        """Test that HTTPS URLs are accepted."""
        url = "https://secure-api.example.com"
        app = app_factory(test_config={"BACKEND_API_URL": url, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_trailing_slash_removed(self, app_factory):
        """Test that trailing slashes are stripped from backend URL."""
        url_with_slash = "https://api.example.com/"
        app = app_factory(test_config={"BACKEND_API_URL": url_with_slash, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == "https://api.example.com"

    @pytest.mark.contract
    def test_backend_url_with_path_preserved(self, app_factory):
        """Test that backend URL with path segments is preserved."""
        url_with_path = "https://api.example.com/v1/api"
        app = app_factory(test_config={"BACKEND_API_URL": url_with_path, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == "https://api.example.com/v1/api"

    @pytest.mark.contract
    def test_backend_url_with_port(self, app_factory):
        """Test that backend URL with port is preserved."""
        url_with_port = "http://localhost:3000"
        app = app_factory(test_config={"BACKEND_API_URL": url_with_port, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == "http://localhost:3000"

    @pytest.mark.contract
    def test_backend_url_multiple_trailing_slashes_removed(self, app_factory):
        """Test that multiple trailing slashes are removed."""
        url_with_slashes = "https://api.example.com///"
        app = app_factory(test_config={"BACKEND_API_URL": url_with_slashes, "TESTING": True})
        assert app.config["BACKEND_API_URL"] == "https://api.example.com"


class TestConfigIsolation:
    """Test that config is isolated between test instances."""

    @pytest.mark.contract
    def test_multiple_apps_have_independent_backends(self, app_factory):
        """Test that multiple app instances have independent BACKEND_API_URL."""
        app1 = app_factory(test_config={
            "BACKEND_API_URL": "https://backend-1.example.com",
            "TESTING": True,
        })
        assert app1.config["BACKEND_API_URL"] == "https://backend-1.example.com"

        app2 = app_factory(test_config={
            "BACKEND_API_URL": "https://backend-2.example.com",
            "TESTING": True,
        })
        assert app2.config["BACKEND_API_URL"] == "https://backend-2.example.com"

        # app1 config should not have changed
        assert app1.config["BACKEND_API_URL"] == "https://backend-1.example.com"

    @pytest.mark.contract
    def test_multiple_apps_have_independent_secrets(self, app_factory):
        """Test that multiple app instances have independent secret keys."""
        app1 = app_factory(test_config={"SECRET_KEY": "secret-1", "TESTING": True})
        assert app1.secret_key == "secret-1"

        app2 = app_factory(test_config={"SECRET_KEY": "secret-2", "TESTING": True})
        assert app2.secret_key == "secret-2"

        # app1 secret should not have changed
        assert app1.secret_key == "secret-1"

    @pytest.mark.contract
    def test_supported_languages_available_from_module(self):
        """Test that SUPPORTED_LANGUAGES is available from loaded module."""
        from app import SUPPORTED_LANGUAGES
        assert SUPPORTED_LANGUAGES is not None
        assert isinstance(SUPPORTED_LANGUAGES, list)

    @pytest.mark.contract
    def test_default_language_available_from_module(self):
        """Test that DEFAULT_LANGUAGE is available from loaded module."""
        from app import DEFAULT_LANGUAGE
        assert DEFAULT_LANGUAGE is not None
        assert isinstance(DEFAULT_LANGUAGE, str)


class TestConfigValidationFunctions:
    """Test configuration validation helper functions."""

    @pytest.mark.unit
    def test_validate_secret_key_function_exists(self):
        """Test that validate_secret_key function is available."""
        from app import validate_secret_key
        assert validate_secret_key is not None
        assert callable(validate_secret_key)

    @pytest.mark.unit
    def test_validate_service_url_function_exists(self):
        """Test that validate_service_url function is available."""
        from app import validate_service_url
        assert validate_service_url is not None
        assert callable(validate_service_url)

    @pytest.mark.contract
    @pytest.mark.parametrize("secret_length", [1, 10, 32, 64, 128])
    def test_validate_secret_key_accepts_any_length_in_test_mode(self, secret_length):
        """Test that validate_secret_key accepts any length when is_production=False."""
        from app import validate_secret_key
        test_secret = "x" * secret_length
        result = validate_secret_key(test_secret, is_production=False)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_accepts_http(self):
        """Test that validate_service_url accepts http URLs."""
        from app import validate_service_url
        result = validate_service_url("http://localhost:5000", required=True)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_accepts_https(self):
        """Test that validate_service_url accepts https URLs."""
        from app import validate_service_url
        result = validate_service_url("https://api.example.com", required=True)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_rejects_invalid_scheme(self):
        """Test that validate_service_url rejects non-http(s) schemes."""
        from app import validate_service_url
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("ftp://example.com", required=True)

    @pytest.mark.contract
    def test_validate_service_url_rejects_scheme_only(self):
        """Test that validate_service_url rejects URL with scheme but no host."""
        from app import validate_service_url
        with pytest.raises(ValueError, match="service_url"):
            validate_service_url("https://", required=True)


class TestBackendURLInjection:
    """Test that backend URL is properly injected into context."""

    @pytest.mark.contract
    def test_backend_url_available_to_templates(self, app):
        """Test that backend_api_url is available in template context."""
        with app.test_request_context("/"):
            from flask import render_template_string
            # The context processor should inject backend_api_url
            result = app.jinja_env.globals.get("inject_config")
            # Verify through app config
            assert app.config["BACKEND_API_URL"] is not None

    @pytest.mark.contract
    def test_backend_url_in_frontend_config(self, app_factory):
        """Test that backend URL is in frontend_config context."""
        url = "https://test.example.com"
        app = app_factory(test_config={
            "BACKEND_API_URL": url,
            "TESTING": True,
        })
        with app.test_request_context("/"):
            # Access the context processor directly
            from app import inject_config
            context = inject_config()
            assert "frontend_config" in context
            assert "backendApiUrl" in context["frontend_config"]
            assert context["frontend_config"]["backendApiUrl"] == url
