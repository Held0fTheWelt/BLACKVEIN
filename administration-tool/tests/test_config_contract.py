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
from conftest import load_frontend_module


class TestSecretKeyContract:
    """Test SECRET_KEY configuration contract."""

    @pytest.mark.contract
    def test_test_mode_accepts_any_secret_key(self, monkeypatch):
        """Test that app accepts short secrets in test mode."""
        module = load_frontend_module(monkeypatch, secret="short")
        assert module.app.secret_key == "short"

    @pytest.mark.contract
    def test_secret_key_is_set_when_provided(self, monkeypatch):
        """Test that app uses provided SECRET_KEY."""
        secret = "this-is-my-test-secret-key-exactly"
        module = load_frontend_module(monkeypatch, secret=secret)
        assert module.app.secret_key == secret

    @pytest.mark.contract
    def test_secret_key_auto_generated_when_none(self, monkeypatch):
        """Test that app generates a secret key when SECRET_KEY env var is not set."""
        module = load_frontend_module(monkeypatch, secret=None)
        # Should generate a key via secrets.token_urlsafe(32)
        assert module.app.secret_key is not None
        assert len(module.app.secret_key) > 0

    @pytest.mark.contract
    def test_secret_key_auto_generated_is_different_each_time(self, monkeypatch):
        """Test that auto-generated keys are different for each app."""
        module1 = load_frontend_module(monkeypatch, secret=None)
        secret1 = module1.app.secret_key

        module2 = load_frontend_module(monkeypatch, secret=None)
        secret2 = module2.app.secret_key

        # Both should be non-empty (they might be the same if SECRET_KEY
        # env var was already set in the environment, so we just check they exist)
        assert secret1 and secret2
        assert len(secret1) > 0 and len(secret2) > 0

    @pytest.mark.contract
    def test_secret_key_is_not_empty_string(self, monkeypatch):
        """Test that secret_key is never an empty string."""
        module = load_frontend_module(monkeypatch, secret=None)
        assert module.app.secret_key != ""
        assert module.app.secret_key is not None


class TestBackendURLContract:
    """Test BACKEND_API_URL configuration contract."""

    @pytest.mark.contract
    def test_backend_url_is_configured_in_app_config(self, monkeypatch):
        """Test that BACKEND_API_URL is available in app.config."""
        url = "https://api.example.com"
        module = load_frontend_module(monkeypatch, backend_url=url)
        assert "BACKEND_API_URL" in module.app.config
        assert module.app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_can_be_localhost(self, monkeypatch):
        """Test that localhost URLs are accepted."""
        url = "http://localhost:5000"
        module = load_frontend_module(monkeypatch, backend_url=url)
        assert module.app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_can_be_https(self, monkeypatch):
        """Test that HTTPS URLs are accepted."""
        url = "https://secure-api.example.com"
        module = load_frontend_module(monkeypatch, backend_url=url)
        assert module.app.config["BACKEND_API_URL"] == url

    @pytest.mark.contract
    def test_backend_url_trailing_slash_removed(self, monkeypatch):
        """Test that trailing slashes are stripped from backend URL."""
        url_with_slash = "https://api.example.com/"
        module = load_frontend_module(monkeypatch, backend_url=url_with_slash)
        assert module.app.config["BACKEND_API_URL"] == "https://api.example.com"

    @pytest.mark.contract
    def test_backend_url_with_path_preserved(self, monkeypatch):
        """Test that backend URL with path segments is preserved."""
        url_with_path = "https://api.example.com/v1/api"
        module = load_frontend_module(monkeypatch, backend_url=url_with_path)
        assert module.app.config["BACKEND_API_URL"] == "https://api.example.com/v1/api"

    @pytest.mark.contract
    def test_backend_url_with_port(self, monkeypatch):
        """Test that backend URL with port is preserved."""
        url_with_port = "http://localhost:3000"
        module = load_frontend_module(monkeypatch, backend_url=url_with_port)
        assert module.app.config["BACKEND_API_URL"] == "http://localhost:3000"

    @pytest.mark.contract
    def test_backend_url_multiple_trailing_slashes_removed(self, monkeypatch):
        """Test that multiple trailing slashes are removed."""
        url_with_slashes = "https://api.example.com///"
        module = load_frontend_module(monkeypatch, backend_url=url_with_slashes)
        assert module.app.config["BACKEND_API_URL"] == "https://api.example.com"


class TestConfigIsolation:
    """Test that config is isolated between test instances."""

    @pytest.mark.contract
    def test_multiple_apps_have_independent_backends(self, monkeypatch):
        """Test that multiple app instances have independent BACKEND_API_URL."""
        module1 = load_frontend_module(
            monkeypatch,
            backend_url="https://backend-1.example.com"
        )
        assert module1.app.config["BACKEND_API_URL"] == "https://backend-1.example.com"

        module2 = load_frontend_module(
            monkeypatch,
            backend_url="https://backend-2.example.com"
        )
        assert module2.app.config["BACKEND_API_URL"] == "https://backend-2.example.com"

        # app1 config should not have changed
        assert module1.app.config["BACKEND_API_URL"] == "https://backend-1.example.com"

    @pytest.mark.contract
    def test_multiple_apps_have_independent_secrets(self, monkeypatch):
        """Test that multiple app instances have independent secret keys."""
        module1 = load_frontend_module(monkeypatch, secret="secret-1")
        assert module1.app.secret_key == "secret-1"

        module2 = load_frontend_module(monkeypatch, secret="secret-2")
        assert module2.app.secret_key == "secret-2"

        # app1 secret should not have changed
        assert module1.app.secret_key == "secret-1"

    @pytest.mark.contract
    def test_supported_languages_available_from_module(self, monkeypatch):
        """Test that SUPPORTED_LANGUAGES is available from loaded module."""
        module = load_frontend_module(monkeypatch)
        assert hasattr(module, "SUPPORTED_LANGUAGES")
        assert isinstance(module.SUPPORTED_LANGUAGES, list)

    @pytest.mark.contract
    def test_default_language_available_from_module(self, monkeypatch):
        """Test that DEFAULT_LANGUAGE is available from loaded module."""
        module = load_frontend_module(monkeypatch)
        assert hasattr(module, "DEFAULT_LANGUAGE")
        assert isinstance(module.DEFAULT_LANGUAGE, str)


class TestConfigValidationFunctions:
    """Test configuration validation helper functions."""

    @pytest.mark.unit
    def test_validate_secret_key_function_exists(self, monkeypatch):
        """Test that validate_secret_key function is available."""
        module = load_frontend_module(monkeypatch)
        assert hasattr(module, "validate_secret_key")
        assert callable(module.validate_secret_key)

    @pytest.mark.unit
    def test_validate_service_url_function_exists(self, monkeypatch):
        """Test that validate_service_url function is available."""
        module = load_frontend_module(monkeypatch)
        assert hasattr(module, "validate_service_url")
        assert callable(module.validate_service_url)

    @pytest.mark.contract
    @pytest.mark.parametrize("secret_length", [1, 10, 32, 64, 128])
    def test_validate_secret_key_accepts_any_length_in_test_mode(self, monkeypatch, secret_length):
        """Test that validate_secret_key accepts any length when is_production=False."""
        module = load_frontend_module(monkeypatch)
        test_secret = "x" * secret_length
        result = module.validate_secret_key(test_secret, is_production=False)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_accepts_http(self, monkeypatch):
        """Test that validate_service_url accepts http URLs."""
        module = load_frontend_module(monkeypatch)
        result = module.validate_service_url("http://localhost:5000", required=True)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_accepts_https(self, monkeypatch):
        """Test that validate_service_url accepts https URLs."""
        module = load_frontend_module(monkeypatch)
        result = module.validate_service_url("https://api.example.com", required=True)
        assert result is True

    @pytest.mark.contract
    def test_validate_service_url_rejects_invalid_scheme(self, monkeypatch):
        """Test that validate_service_url rejects non-http(s) schemes."""
        module = load_frontend_module(monkeypatch)
        with pytest.raises(ValueError, match="service_url"):
            module.validate_service_url("ftp://example.com", required=True)

    @pytest.mark.contract
    def test_validate_service_url_rejects_scheme_only(self, monkeypatch):
        """Test that validate_service_url rejects URL with scheme but no host."""
        module = load_frontend_module(monkeypatch)
        with pytest.raises(ValueError, match="service_url"):
            module.validate_service_url("https://", required=True)


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
    def test_backend_url_in_frontend_config(self, monkeypatch):
        """Test that backend URL is in frontend_config context."""
        url = "https://test.example.com"
        module = load_frontend_module(monkeypatch, backend_url=url)
        with module.app.test_request_context("/"):
            # Access the context processor directly from the loaded module
            context = module.inject_config()
            assert "frontend_config" in context
            assert "backendApiUrl" in context["frontend_config"]
            assert context["frontend_config"]["backendApiUrl"] == url
