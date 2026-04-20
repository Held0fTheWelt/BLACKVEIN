from __future__ import annotations

import importlib
import importlib.util
import os
import sys
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

# Explicitly load pytest-asyncio plugin for async test support
pytest_plugins = ("pytest_asyncio",)

# CRITICAL: Set FLASK_ENV to test before any imports from app.config
# This allows lenient validation for PLAY_SERVICE_SECRET in test mode
if "FLASK_ENV" not in os.environ:
    os.environ["FLASK_ENV"] = "test"

# Provide test secret if not already set
# Tests that need to verify missing secret behavior will override this
if "PLAY_SERVICE_SECRET" not in os.environ:
    os.environ["PLAY_SERVICE_SECRET"] = "test-secret-key-for-unit-tests"

# Disable backend content sync in tests to use only builtin templates
if "BACKEND_CONTENT_SYNC_ENABLED" not in os.environ:
    os.environ["BACKEND_CONTENT_SYNC_ENABLED"] = "false"

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None



@pytest.fixture
def sqlalchemy_available() -> bool:
    return SQLALCHEMY_AVAILABLE



def receive_until_snapshot(websocket, predicate, attempts: int = 10, timeout: float = 0.1):
    """Receive WebSocket messages until a snapshot matching the predicate is received.

    Args:
        websocket: WebSocket connection
        predicate: Function to test snapshot data
        attempts: Maximum number of receive attempts
        timeout: Timeout in seconds for each receive attempt (default 0.1)

    Raises:
        AssertionError: If no matching snapshot received after all attempts
        TimeoutError: If timeout exceeded on any receive attempt
    """
    import socket
    last = None
    for attempt in range(attempts):
        try:
            # Set a timeout on the underlying socket to prevent infinite blocking
            if hasattr(websocket, 'sock') and websocket.sock:
                websocket.sock.settimeout(timeout)
            last = websocket.receive_json()
            if last.get("type") == "snapshot" and predicate(last["data"]):
                return last
        except socket.timeout:
            raise TimeoutError(f"WebSocket receive timeout on attempt {attempt + 1}/{attempts}") from None
        except Exception as e:
            # If we can't set the timeout, raise an error so the test fails fast
            # rather than hanging indefinitely
            raise RuntimeError(f"WebSocket receive failed on attempt {attempt + 1}/{attempts}: {e}") from e
    raise AssertionError(f"Did not receive matching snapshot after {attempts} attempts; last payload was: {last}")



def build_test_app(tmp_path: Path, *, store_backend: str = "json", store_url: str | None = None) -> FastAPI:
    # Import modules
    tickets_module = importlib.import_module("app.auth.tickets")
    runtime_manager_module = importlib.import_module("app.runtime.manager")
    story_runtime_module = importlib.import_module("app.story_runtime")

    # Check if app.config has been mocked/patched by a test
    # If the current PLAY_SERVICE_INTERNAL_API_KEY value doesn't match the environment,
    # it might be a mock, so we should NOT reload (to preserve the mock)
    import app.config
    current_value = app.config.PLAY_SERVICE_INTERNAL_API_KEY
    env_value = os.getenv("PLAY_SERVICE_INTERNAL_API_KEY", "").strip() or None

    # Only reload if the current value matches the environment value
    # This handles monkeypatch.setenv (both env and current value are in sync)
    # and avoids reloading when using unittest.mock.patch (current != env)
    if current_value == env_value:
        importlib.reload(app.config)
        # Also reload modules that depend on config
        runtime_manager_module = importlib.reload(runtime_manager_module)

    # Reload http and ws modules - they will import the current config values
    http_module = importlib.import_module("app.api.http")
    http_module = importlib.reload(http_module)

    ws_module = importlib.import_module("app.api.ws")
    ws_module = importlib.reload(ws_module)

    from app.middleware.trace_middleware import install_trace_middleware

    app = FastAPI()
    install_trace_middleware(app)
    app.state.manager = runtime_manager_module.RuntimeManager(
        store_root=tmp_path,
        store_backend=store_backend,
        store_url=store_url,
    )
    app.state.story_manager = story_runtime_module.StoryRuntimeManager()
    app.state.ticket_manager = tickets_module.TicketManager("test-secret")
    app.include_router(http_module.router)
    app.include_router(ws_module.router)
    return app


@pytest.fixture
def app(tmp_path: Path):
    return build_test_app(tmp_path)


@pytest.fixture
def client(app):
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def internal_api_key() -> str:
    """Get the internal API key from environment (loaded from .env file).

    This fixture provides the correct API key for tests that call
    /api/internal/* endpoints. It reads the actual configured value
    from the environment/config so tests use the correct key.
    """
    import app.config
    # Return the configured key, or a default if not configured
    return (os.getenv("PLAY_SERVICE_INTERNAL_API_KEY") or
            getattr(app.config, "PLAY_SERVICE_INTERNAL_API_KEY", None) or
            "internal-api-key-for-ops")
