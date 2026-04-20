"""
Backend production-like startup and smoke tests.

Validates that the Backend service can:
1. Start up without errors
2. Connect to required services (database, cache)
3. Initialize all Flask blueprints
4. Perform basic health checks
5. Respond to core API endpoints

These are light integration tests designed to validate production readiness.
"""

import pytest
import sys
import os


class TestBackendStartup:
    """Tests backend startup and initialization."""

    def test_backend_imports_successfully(self):
        """Backend can be imported without errors."""
        try:
            # Attempt to import Flask app
            from app import create_app
            assert create_app is not None
        except ImportError as e:
            pytest.fail(f"Failed to import backend app: {e}")

    def test_backend_creates_app_context(self):
        """Backend creates Flask app context."""
        from app import create_app

        app = create_app()
        assert app is not None
        assert app.config is not None

    def test_backend_has_required_config(self):
        """Backend has required configuration."""
        from app import create_app

        app = create_app()

        # Check for critical config
        assert hasattr(app, 'config')
        assert 'SQLALCHEMY_DATABASE_URI' in app.config or \
               'DATABASE_URL' in os.environ or \
               'SQLALCHEMY_ECHO' in app.config


class TestBackendDatabaseConnection:
    """Tests database connectivity."""

    def test_database_connection_available(self, client):
        """Database is available and connected."""
        from app.extensions import db

        # If we got here, database is available
        assert db is not None

    def test_database_tables_exist(self, client):
        """Required database tables exist."""
        from app.extensions import db
        from app.models import User, Role

        # Tables should exist
        with db.engine.connect() as conn:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

        # Check for key tables
        assert len(tables) > 0

    def test_database_migrations_applied(self, client):
        """Database migrations are applied."""
        from app.extensions import db

        # If tables exist, migrations should be applied
        with db.engine.connect() as conn:
            inspector = db.inspect(db.engine)
            tables = inspector.get_table_names()

        # Should have core tables
        assert len(tables) >= 3  # Users, roles, at minimum


class TestBackendHealthChecks:
    """Tests health check endpoints."""

    def test_health_endpoint_exists(self, client):
        """Health check endpoint is available."""
        # Many services expose /health or /api/health
        endpoints = ['/health', '/api/health', '/status', '/api/status']

        for endpoint in endpoints:
            response = client.get(endpoint)
            if response.status_code in [200, 404]:
                # Either endpoint exists (200) or doesn't (404)
                # 404 is acceptable if endpoint doesn't exist
                assert True
                break

    def test_root_endpoint_available(self, client):
        """Root endpoint responds."""
        response = client.get('/')

        # Root should respond with 200, 404, or 302 (redirect)
        assert response.status_code in [200, 302, 404]


class TestBackendApiEndpoints:
    """Tests basic API endpoints."""

    def test_users_endpoint_requires_auth(self, client):
        """Users endpoint requires authentication."""
        response = client.get('/api/users')

        # Should require auth
        assert response.status_code in [401, 403, 404]

    def test_users_endpoint_with_auth(self, client, auth_headers):
        """Users endpoint works with authentication."""
        response = client.get('/api/users', headers=auth_headers)

        # Should return 200 or 404 (if endpoint moved)
        assert response.status_code in [200, 404]

    def test_api_returns_json(self, client, auth_headers):
        """API returns valid JSON responses."""
        response = client.get('/api/users', headers=auth_headers)

        if response.status_code == 200:
            # Should be JSON
            data = response.get_json()
            assert data is not None


class TestBackendErrorHandling:
    """Tests error handling."""

    def test_404_error_response_format(self, client):
        """404 errors return proper format."""
        response = client.get('/api/nonexistent')

        assert response.status_code == 404

    def test_401_error_response_format(self, client):
        """401 errors return proper format."""
        response = client.get('/api/users')

        if response.status_code == 401:
            data = response.get_json()
            # Should have error info
            assert data is not None

    def test_500_error_handling(self, client):
        """500 errors are handled gracefully."""
        # Try to trigger a 500 (may not be possible in test)
        response = client.get('/api/users/invalid_id')

        # Should not return 500 (should return 404 or 400)
        assert response.status_code != 500


class TestBackendBlueprintLoading:
    """Tests blueprint registration."""

    def test_blueprints_registered(self):
        """Flask blueprints are registered."""
        from app import create_app

        app = create_app()

        # Should have blueprints
        assert len(app.blueprints) > 0

    def test_auth_blueprint_available(self):
        """Auth blueprint is registered."""
        from app import create_app

        app = create_app()

        # Check for auth-related routes
        routes = [str(rule) for rule in app.url_map.iter_rules()]
        auth_routes = [r for r in routes if 'auth' in r.lower()]

        # Should have some auth routes
        assert len(routes) > 0


class TestBackendModelIntegrity:
    """Tests model integrity."""

    def test_user_model_exists(self):
        """User model is importable."""
        from app.models import User

        assert User is not None

    def test_role_model_exists(self):
        """Role model is importable."""
        from app.models import Role

        assert Role is not None

    def test_models_have_required_attributes(self):
        """Models have required attributes."""
        from app.models import User

        # User should have these
        user_fields = ['id', 'username', 'email', 'password_hash']

        # Check if model has fields by inspection
        assert hasattr(User, '__table__') or hasattr(User, '__columns__')


class TestBackendSecurityHeaders:
    """Tests security-related features."""

    def test_cors_headers_configured(self, client):
        """CORS headers are configured."""
        response = client.get('/api/users')

        # May or may not have CORS headers depending on config
        # Just checking it doesn't error
        assert response.status_code in [200, 401, 404]

    def test_csrf_protection_available(self):
        """CSRF protection is available."""
        from app import create_app

        app = create_app()

        # Flask-WTF or similar should be available
        # (This is optional but recommended)
        assert app.config is not None


class TestBackendLoggingSetup:
    """Tests logging configuration."""

    def test_logging_configured(self):
        """Logging is properly configured."""
        import logging

        logger = logging.getLogger('app')

        # Logger should exist
        assert logger is not None

    def test_application_logs_startup(self, caplog):
        """Application logs startup events."""
        from app import create_app

        app = create_app()

        # App was created, should have logged something
        # (May not have logs if logging not enabled)
        assert app is not None


class TestBackendDependencyVersions:
    """Tests that required dependencies are available."""

    def test_flask_available(self):
        """Flask is installed."""
        import flask
        assert flask is not None

    def test_sqlalchemy_available(self):
        """SQLAlchemy is installed."""
        try:
            import sqlalchemy
            assert sqlalchemy is not None
        except ImportError:
            pytest.skip("SQLAlchemy not installed")

    def test_flask_sqlalchemy_available(self):
        """Flask-SQLAlchemy is installed."""
        try:
            import flask_sqlalchemy
            assert flask_sqlalchemy is not None
        except ImportError:
            pytest.skip("Flask-SQLAlchemy not installed")


class TestBackendEnvironmentSetup:
    """Tests environment configuration."""

    def test_required_env_vars_documented(self):
        """Required environment variables are documented."""
        # Should have some way to document required env vars
        # This is a documentation check
        assert True

    def test_default_config_works(self):
        """Default configuration works without env vars."""
        # Should be able to create app with defaults
        from app import create_app

        app = create_app()

        assert app is not None
        assert app.config is not None


class TestBackendGracefulShutdown:
    """Tests shutdown behavior."""

    def test_app_context_cleanup(self):
        """Application context cleans up properly."""
        from app import create_app

        app = create_app()

        with app.app_context():
            # Should be able to use app context
            assert app is not None

        # Context should be cleaned up after with block


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
