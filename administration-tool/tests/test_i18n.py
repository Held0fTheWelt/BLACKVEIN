from __future__ import annotations

import json
from pathlib import Path

from conftest import load_frontend_module


def test_load_translations_falls_back_to_default_language(monkeypatch, tmp_path: Path):
    module = load_frontend_module(monkeypatch)
    translations_dir = tmp_path / "translations"
    translations_dir.mkdir()
    (translations_dir / "de.json").write_text(json.dumps({"hello": "Hallo"}), encoding="utf-8")
    module.app.root_path = str(tmp_path)

    assert module._load_translations("fr") == {"hello": "Hallo"}


def test_load_translations_returns_empty_dict_for_invalid_json(monkeypatch, tmp_path: Path):
    module = load_frontend_module(monkeypatch)
    translations_dir = tmp_path / "translations"
    translations_dir.mkdir()
    (translations_dir / "de.json").write_text("{not valid json", encoding="utf-8")
    module.app.root_path = str(tmp_path)

    assert module._load_translations("de") == {}


def test_resolve_language_prefers_query_parameter_and_persists_session(monkeypatch):
    module = load_frontend_module(monkeypatch)

    with module.app.test_request_context("/?lang=en"):
        language = module._resolve_language()
        assert language == "en"
        assert module.session["lang"] == "en"


def test_resolve_language_uses_session_before_accept_language(monkeypatch):
    module = load_frontend_module(monkeypatch)

    with module.app.test_request_context("/", headers={"Accept-Language": "de-DE,de;q=0.9"}):
        module.session["lang"] = "en"
        assert module._resolve_language() == "en"


def test_resolve_language_uses_accept_language_when_session_is_missing(monkeypatch):
    module = load_frontend_module(monkeypatch)

    with module.app.test_request_context("/", headers={"Accept-Language": "en-US,en;q=0.8,de;q=0.5"}):
        assert module._resolve_language() == "en"


def test_resolve_language_falls_back_to_default_for_unknown_input(monkeypatch):
    module = load_frontend_module(monkeypatch)

    with module.app.test_request_context("/?lang=fr", headers={"Accept-Language": "es-ES,es;q=0.8"}):
        assert module._resolve_language() == module.DEFAULT_LANGUAGE


def test_inject_config_exposes_translations_and_frontend_settings(monkeypatch):
    module = load_frontend_module(monkeypatch, backend_url="https://split-backend.example.test")

    with module.app.test_request_context("/?lang=de"):
        context = module.inject_config()

    assert context["backend_api_url"] == "https://split-backend.example.test"
    assert context["frontend_config"]["backendApiUrl"] == "https://split-backend.example.test"
    assert context["frontend_config"]["currentLanguage"] == "de"
    assert "supportedLanguages" in context["frontend_config"]
    assert isinstance(context["t"], dict)
