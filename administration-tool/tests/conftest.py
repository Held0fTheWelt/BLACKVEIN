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
    return module


@pytest.fixture
def frontend_module(monkeypatch: pytest.MonkeyPatch):
    return load_frontend_module(monkeypatch)


@pytest.fixture
def app(frontend_module):
    frontend_module.app.config.update(TESTING=True)
    return frontend_module.app


@pytest.fixture
def client(app):
    return app.test_client()


@contextmanager
def captured_templates(app) -> Iterator[list[tuple[str, dict]]]:
    recorded: list[tuple[str, dict]] = []

    def record(sender, template, context, **extra):
        recorded.append((template.name, context))

    template_rendered.connect(record, app)
    try:
        yield recorded
    finally:
        template_rendered.disconnect(record, app)
