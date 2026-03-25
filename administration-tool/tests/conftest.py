from __future__ import annotations

import importlib.util
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator
from uuid import uuid4

import pytest
from flask import template_rendered

ROOT = Path(__file__).resolve().parents[1]
APP_FILE = ROOT / "app.py"


def load_frontend_module(
    monkeypatch: pytest.MonkeyPatch,
    *,
    backend_url: str = "https://backend.example.test",
    secret: str | None = "test-secret-key",
):
    """Load the frontend module with environment variable overrides.

    This function is used for testing module-level imports in isolation.
    For new code, prefer using the create_app() factory directly.

    Args:
        monkeypatch: pytest monkeypatch fixture
        backend_url: BACKEND_API_URL to set
        secret: SECRET_KEY to set, or None to not set it

    Returns:
        Loaded module object with app instance
    """
    monkeypatch.setenv("BACKEND_API_URL", backend_url)
    if secret is None:
        monkeypatch.delenv("SECRET_KEY", raising=False)
    else:
        monkeypatch.setenv("SECRET_KEY", secret)

    module_name = f"administration_tool_app_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_name, APP_FILE)
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load administration-tool app module")

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Fix the app's root_path to point to the administration-tool directory
    # (module loading via spec_from_file_location sets it to the project root)
    module.app.root_path = str(ROOT)

    return module


@pytest.fixture
def frontend_module(monkeypatch: pytest.MonkeyPatch):
    """Fixture providing the loaded frontend module for tests."""
    return load_frontend_module(monkeypatch)


@pytest.fixture
def app(app_factory):
    """Fixture providing a test app instance.

    Uses app_factory to ensure correct root_path for template loading in test environment.
    The app is configured in TESTING mode for isolated test execution.
    """
    return app_factory(test_config={
        "TESTING": True,
        "BACKEND_API_URL": "https://backend.example.test",
        "SECRET_KEY": "test-secret-key",
    })


@pytest.fixture
def app_factory(monkeypatch):
    """Fixture providing direct access to the create_app() factory.

    Allows tests to create apps with arbitrary test_config without
    module reloading. New tests should prefer this fixture.
    """
    import sys
    import importlib.util

    # Load the app module fresh if not already loaded
    app_module_name = "administration_tool_app_factory"
    if app_module_name in sys.modules:
        mod = sys.modules[app_module_name]
    else:
        spec = importlib.util.spec_from_file_location(app_module_name, ROOT / "app.py")
        if spec is None or spec.loader is None:
            raise RuntimeError("Could not load administration-tool app module")
        mod = importlib.util.module_from_spec(spec)
        sys.modules[app_module_name] = mod
        spec.loader.exec_module(mod)

    return mod.create_app


@pytest.fixture
def client(app):
    """Fixture providing a test client for the app instance."""
    return app.test_client()


@contextmanager
def captured_templates(app) -> Iterator[list[tuple[str, dict]]]:
    """Context manager to capture template rendering events during test execution.

    Yields a list of (template_name, context_dict) tuples for inspection.
    """
    recorded: list[tuple[str, dict]] = []

    def record(sender, template, context, **extra):
        recorded.append((template.name, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)
