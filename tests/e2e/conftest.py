"""Pytest configuration for E2E gameplay seam repair tests.

Sets up Flask app fixtures for testing the gameplay flow
from frontend through backend to world-engine.
"""

import pytest
import sys
import os
from unittest import mock

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
    """Create Flask app for frontend E2E testing with login bypassed."""
    from frontend.app import create_app as create_frontend_app

    app = create_frontend_app(testing=True)
    app.config["BYPASS_LOGIN_FOR_TESTS"] = True
    return app


class _MockerCompat:
    """Minimal pytest-mock-compatible helper for environments without plugin."""

    MagicMock = mock.MagicMock

    def __init__(self) -> None:
        self._patchers: list[mock._patch] = []

    def patch(self, target: str, *args, **kwargs):
        patcher = mock.patch(target, *args, **kwargs)
        started = patcher.start()
        self._patchers.append(patcher)
        return started

    def stopall(self) -> None:
        while self._patchers:
            self._patchers.pop().stop()


@pytest.fixture
def mocker():
    compat = _MockerCompat()
    try:
        yield compat
    finally:
        compat.stopall()


@pytest.fixture
def client(frontend_app):
    """Flask test client for making requests."""
    test_client = frontend_app.test_client()
    if not hasattr(test_client, "cookie_jar") and hasattr(test_client, "_cookies"):
        class _CompatCookieJar:
            def __init__(self, client):
                self._client = client

            @property
            def _cookies(self):
                return self._client._cookies

        test_client.cookie_jar = _CompatCookieJar(test_client)

    original_open = test_client.open

    def _open_with_template_attr(*args, **kwargs):
        response = original_open(*args, **kwargs)
        if not hasattr(response, "template"):
            response.template = ""
        return response

    test_client.open = _open_with_template_attr
    return test_client


@pytest.fixture
def runner(frontend_app):
    """CLI test runner."""
    return frontend_app.test_cli_runner()


@pytest.fixture
def player_backend_mock(mocker):
    """Mock player backend requests for testing."""
    mocker.patch(
        "frontend.app.player_backend.request_backend",
        return_value=mocker.MagicMock(
            ok=True,
            json=lambda: {
                "run": {"id": "test_run_123"},
                "session_id": "test_session_456",
                "opening_turn": {"turn_kind": "opening", "turn_number": 0},
                "turn": {
                    "turn_number": 1,
                    "turn_kind": "player",
                    "interpreted_input": {"kind": "action"},
                    "visible_output_bundle": {"gm_narration": ["Test narration."]},
                    "validation_outcome": {"status": "approved"},
                    "narrative_commit": {"committed_scene_id": "test_scene"},
                },
                "state": {
                    "current_scene_id": "test_scene",
                    "committed_state": {},
                },
                "diagnostics": {},
            },
        ),
    )
