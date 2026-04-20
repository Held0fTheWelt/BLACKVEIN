"""
Pytest configuration for smoke tests (testing_isolated profile).

Smoke tests validate production-like startup and initialization without bootstrap.
Uses production config (not TestingConfig), so ROUTING_REGISTRY_BOOTSTRAP is enabled
and tests run against production-like initialization behavior.

This conftest imports fixtures from the backend test suite.
"""

import pytest
import sys
import os

# ====== PYTHONPATH SETUP FOR CLEAN-ENVIRONMENT TESTS ======
# Ensure backend module is importable in isolated environments.
# This allows smoke tests to run in a fresh Python environment without
# relying on IDE-specific PYTHONPATH setup or pre-installed packages.
backend_path = os.path.join(os.path.dirname(__file__), '../../backend')
if backend_path not in sys.path:
    sys.path.insert(0, backend_path)


# ====== IMPORT BACKEND TEST FIXTURES ======
# Re-export key fixtures from backend/tests/conftest.py
# so smoke tests have access to database, auth, and app fixtures.
#
# Note: Smoke tests use production-like config, NOT TestingConfig.
# This tests real startup behavior (e.g., ROUTING_REGISTRY_BOOTSTRAP=True by default).
pytest_plugins = ['backend.tests.conftest']


@pytest.fixture(scope='session')
def backend_app():
    """
    Create Flask app for smoke testing (production-like config).

    Unlike unit tests that use TestingConfig (in-memory DB, no bootstrap),
    smoke tests use production-like config to validate real startup behavior.
    """
    from app import create_app

    # Production config: ROUTING_REGISTRY_BOOTSTRAP defaults to True
    app = create_app()
    return app


@pytest.fixture
def app_context(backend_app):
    """
    Provide app context for database operations in smoke tests.

    Tests that need database access should use this fixture to ensure
    they have a valid Flask app_context.
    """
    with backend_app.app_context():
        yield backend_app


@pytest.fixture
def runner(backend_app):
    """
    CLI test runner for smoke tests.

    Tests can use this to invoke Flask CLI commands.
    """
    return backend_app.test_cli_runner()
