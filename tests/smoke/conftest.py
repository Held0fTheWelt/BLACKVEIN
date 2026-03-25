"""
Pytest configuration for smoke tests.

Smoke tests validate production-like startup and initialization.
This conftest provides minimal fixtures for smoke testing.
"""

import pytest
import sys
import os

# Add backend to path for imports
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


@pytest.fixture(scope='session')
def backend_app():
    """Create Flask app for testing."""
    from app import create_app

    app = create_app()
    return app


@pytest.fixture
def client(backend_app):
    """Test client for Flask app."""
    return backend_app.test_client()


@pytest.fixture
def app_context(backend_app):
    """App context for database operations."""
    with backend_app.app_context():
        yield backend_app


@pytest.fixture
def runner(backend_app):
    """CLI test runner."""
    return backend_app.test_cli_runner()
