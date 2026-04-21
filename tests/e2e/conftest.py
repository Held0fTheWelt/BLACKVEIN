"""Pytest configuration for E2E gameplay seam repair tests.

Sets up Flask app fixtures for testing the gameplay flow
from frontend through backend to world-engine.
"""

import pytest
import sys
import os

# ====== PYTHONPATH SETUP ======
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
frontend_path = os.path.join(os.path.dirname(__file__), '../../frontend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)
if frontend_path not in sys.path:
    sys.path.insert(0, frontend_path)

pytest_plugins = ['backend.tests.conftest']


@pytest.fixture
def frontend_app():
    """Create Flask app for frontend E2E testing."""
    from app import create_app as create_frontend_app

    app = create_frontend_app(testing=True)
    return app


@pytest.fixture
def client(frontend_app):
    """Flask test client for making requests."""
    return frontend_app.test_client()


@pytest.fixture
def runner(frontend_app):
    """CLI test runner."""
    return frontend_app.test_cli_runner()
