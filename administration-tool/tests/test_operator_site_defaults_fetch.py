"""Tests for server-side fetch of operator defaults from backend GET /api/v1/site/settings."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load_admin_app_module():
    """Load administration-tool app.py as an isolated module (same pattern as tests/conftest app_factory)."""
    name = "administration_tool_app_operator_defaults_tests"
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, _ROOT / "app.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("Could not load administration-tool app module")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.mark.unit
def test_fetch_operator_defaults_parses_site_settings_json(monkeypatch):
    from urllib.request import Request

    admin_app = _load_admin_app_module()
    captured: dict[str, str] = {}

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "content_module_id": "mod_a",
                    "default_runtime_template_id": "tpl_b",
                }
            ).encode("utf-8")

    def _fake_urlopen(req: Request, timeout: int = 0):
        captured["url"] = req.full_url
        return _Resp()

    monkeypatch.setattr(admin_app, "urlopen", _fake_urlopen)
    admin_app.reset_operator_defaults_remote_cache()
    mod, tpl = admin_app._fetch_operator_defaults_from_backend_public_settings(
        "https://api.example.com/"
    )
    assert mod == "mod_a"
    assert tpl == "tpl_b"
    assert captured["url"] == "https://api.example.com/api/v1/site/settings"


@pytest.mark.unit
def test_fetch_operator_defaults_returns_empty_on_bad_json(monkeypatch):
    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return b"not-json"

    admin_app = _load_admin_app_module()
    monkeypatch.setattr(admin_app, "urlopen", lambda req, timeout=0: _Resp())
    admin_app.reset_operator_defaults_remote_cache()
    mod, tpl = admin_app._fetch_operator_defaults_from_backend_public_settings(
        "https://api.example.com"
    )
    assert mod == "" and tpl == ""


@pytest.mark.unit
def test_fetch_operator_defaults_accepts_default_site_settings_keys(monkeypatch):
    from urllib.request import Request

    admin_app = _load_admin_app_module()

    class _Resp:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def read(self):
            return json.dumps(
                {
                    "content_module_id": "default_mod",
                    "default_runtime_template_id": "default_tpl",
                }
            ).encode("utf-8")

    monkeypatch.setattr(admin_app, "urlopen", lambda req, timeout=0: _Resp())
    admin_app.reset_operator_defaults_remote_cache()
    mod, tpl = admin_app._fetch_operator_defaults_from_backend_public_settings("https://api.example.com")
    assert mod == "default_mod"
    assert tpl == "default_tpl"
