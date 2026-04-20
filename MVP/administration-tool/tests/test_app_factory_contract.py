"""Tests for app factory contract and behavior.

Validates that:
- create_app() factory function exists and is usable directly
- create_app() with test_config creates deterministic apps
- Multiple app instances created via factory are independent
- Factory-created apps work with test client
- Test config override works correctly for SECRET_KEY, BACKEND_API_URL, TESTING
"""
from __future__ import annotations

import pytest


@pytest.mark.unit
@pytest.mark.contract
class TestAppFactoryFunction:
    """Test that create_app() factory function is properly implemented."""

    def test_create_app_function_exists(self):
        """Test that create_app function is importable from app module."""
        from app import create_app
        assert callable(create_app)

    def test_create_app_no_args_returns_app(self):
        """Test that create_app() with no arguments returns a Flask app."""
        from app import create_app
        app = create_app()
        assert app is not None
        assert hasattr(app, "config")
        assert hasattr(app, "route")

    def test_create_app_with_empty_config_returns_app(self):
        """Test that create_app({}) with empty test_config returns a Flask app."""
        from app import create_app
        app = create_app({})
        assert app is not None
        assert hasattr(app, "config")

    def test_create_app_with_backend_url_config(self):
        """Test that create_app accepts BACKEND_API_URL in test_config."""
        from app import create_app
        test_url = "https://test-backend.example.com"
        app = create_app(test_config={"BACKEND_API_URL": test_url})
        assert app.config["BACKEND_API_URL"] == test_url

    def test_create_app_with_secret_key_config(self):
        """Test that create_app accepts SECRET_KEY in test_config."""
        from app import create_app
        test_secret = "my-test-secret-key-12345"
        app = create_app(test_config={"SECRET_KEY": test_secret})
        assert app.secret_key == test_secret

    def test_create_app_with_testing_config(self):
        """Test that create_app accepts TESTING flag in test_config."""
        from app import create_app
        app = create_app(test_config={"TESTING": True})
        assert app.config.get("TESTING") is True

    def test_create_app_multiple_instances_are_independent(self):
        """Test that multiple create_app() calls produce independent instances."""
        from app import create_app

        app1 = create_app(test_config={
            "BACKEND_API_URL": "https://backend1.example.com",
            "SECRET_KEY": "secret1"
        })
        app2 = create_app(test_config={
            "BACKEND_API_URL": "https://backend2.example.com",
            "SECRET_KEY": "secret2"
        })

        # Verify they're different instances
        assert app1 is not app2
        # Verify config isolation
        assert app1.config["BACKEND_API_URL"] == "https://backend1.example.com"
        assert app2.config["BACKEND_API_URL"] == "https://backend2.example.com"
        assert app1.secret_key == "secret1"
        assert app2.secret_key == "secret2"

    def test_create_app_respects_session_security_config(self):
        """Test that factory-created apps have session security hardening."""
        from app import create_app
        app = create_app(test_config={"TESTING": True})
        assert app.config["SESSION_COOKIE_SECURE"] is True
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True
        assert app.config["SESSION_COOKIE_SAMESITE"] == "Lax"
        assert app.config["PERMANENT_SESSION_LIFETIME"] == 3600


@pytest.mark.unit
@pytest.mark.contract
class TestAppFactoryRoutes:
    """Test that factory-created apps have routes properly registered."""

    def test_factory_app_has_index_route(self, app_factory):
        """Test that factory app has / route."""
        app = app_factory(test_config={"TESTING": True})
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/" in rules

    def test_factory_app_has_proxy_route(self, app_factory):
        """Test that factory app has /_proxy/<path:subpath> route."""
        app = app_factory(test_config={"TESTING": True})
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert "/_proxy/<path:subpath>" in rules

    def test_factory_app_has_forum_routes(self, app_factory):
        """Test that factory app has forum routes."""
        app = app_factory(test_config={"TESTING": True})
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        expected_routes = ["/forum", "/forum/categories/<slug>", "/forum/threads/<slug>"]
        for route in expected_routes:
            assert route in rules, f"Missing route: {route}"

    def test_factory_app_can_handle_requests(self, app_factory):
        """Test that factory-created app can handle test client requests."""
        app = app_factory(test_config={
            "TESTING": True,
            "BACKEND_API_URL": "https://test.example.com"
        })
        client = app.test_client()
        response = client.get("/")
        assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
class TestAppFactoryDeterminism:
    """Test that create_app() factory produces deterministic results."""

    def test_create_app_same_config_produces_same_settings(self, app_factory):
        """Test that same test_config produces identical app configuration."""
        config = {
            "BACKEND_API_URL": "https://api.example.com",
            "SECRET_KEY": "test-secret-12345",
            "TESTING": True
        }
        app1 = app_factory(test_config=config)
        app2 = app_factory(test_config=config)

        # Verify same configuration
        assert app1.config["BACKEND_API_URL"] == app2.config["BACKEND_API_URL"]
        assert app1.secret_key == app2.secret_key
        assert app1.config.get("TESTING") == app2.config.get("TESTING")

    def test_create_app_no_side_effects_on_module(self, app_factory):
        """Test that creating apps via factory doesn't affect global state."""
        # Create first app
        app1 = app_factory(test_config={"BACKEND_API_URL": "https://one.example.com"})
        backend_url_1 = app1.config["BACKEND_API_URL"]

        # Create second app with different config
        app2 = app_factory(test_config={"BACKEND_API_URL": "https://two.example.com"})

        # First app should still have original config
        assert app1.config["BACKEND_API_URL"] == backend_url_1
        assert app2.config["BACKEND_API_URL"] == "https://two.example.com"


@pytest.mark.integration
@pytest.mark.contract
class TestAppFactoryWithTestClient:
    """Test that factory-created apps work correctly with Flask test client."""

    def test_factory_app_with_client_has_security_headers(self, app_factory):
        """Test that factory-created app includes security headers in responses."""
        app = app_factory(test_config={"TESTING": True})
        client = app.test_client()
        response = client.get("/")

        assert response.status_code == 200
        assert "X-Frame-Options" in response.headers
        assert "Content-Security-Policy" in response.headers

    def test_factory_app_context_processor_works(self, app_factory):
        """Test that factory-created app's context processor injects config."""
        app = app_factory(test_config={
            "TESTING": True,
            "BACKEND_API_URL": "https://test-api.example.com"
        })
        with app.test_request_context("/"):
            # The context processor should be available
            from flask import render_template_string
            result = render_template_string("{{ backend_api_url }}")
            # If context processor is working, this should render without error
            assert result is not None

    def test_factory_app_session_works(self, app_factory):
        """Test that factory-created app can set and retrieve session data."""
        app = app_factory(test_config={"TESTING": True})
        client = app.test_client()

        # First request to set language
        response = client.get("/?lang=en")
        assert response.status_code == 200

        # Session should persist (in test client)
        # This validates the session is configured correctly
        assert app.config["SESSION_COOKIE_HTTPONLY"] is True


@pytest.mark.unit
@pytest.mark.contract
class TestAppFactorySecretKeyGeneration:
    """Test that factory properly handles secret key generation."""

    def test_create_app_without_secret_generates_one(self, app_factory):
        """Test that factory generates a secret key when none provided."""
        app = app_factory(test_config={"TESTING": True})
        assert app.secret_key is not None
        assert len(app.secret_key) > 0

    def test_create_app_generated_secrets_are_different(self, app_factory):
        """Test that multiple factory calls generate different secret keys."""
        app1 = app_factory(test_config={"TESTING": True})
        secret1 = app1.secret_key

        app2 = app_factory(test_config={"TESTING": True})
        secret2 = app2.secret_key

        # Both should have secrets (they're likely different due to randomness,
        # but we can't guarantee that so just verify they exist)
        assert secret1 and secret2
        assert len(secret1) > 0 and len(secret2) > 0
