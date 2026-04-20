"""Tests for dense embedding backend probing, env flags, and cache path wiring."""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from ai_stack.semantic_embedding import (
    EMBEDDING_MODEL_ID,
    clear_embedding_model_singleton,
    embedding_backend_probe,
    embedding_cache_dir_from_env,
    encode_texts,
    encode_texts_detailed,
)
from ai_stack.tests.embedding_markers import requires_embeddings


def test_probe_reports_disabled_when_env_disables_embeddings(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("WOS_RAG_DISABLE_EMBEDDINGS", "1")
    monkeypatch.delenv("WOS_RAG_EMBEDDING_CACHE_DIR", raising=False)
    report = embedding_backend_probe()
    assert report.disabled_by_env is True
    assert report.available is False
    assert report.import_ok is False
    assert report.encode_ok is False
    assert "embeddings_disabled_by_env" in report.messages
    assert report.primary_reason_code == "embeddings_disabled_by_env"
    assert report.cache_dir_identity == "__default__"


def test_probe_reports_import_failure_when_fastembed_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    real_import_module = importlib.import_module

    def fake_import_module(name: str, package: str | None = None):
        if name == "fastembed":
            raise ImportError("simulated_missing_fastembed")
        return real_import_module(name, package)

    monkeypatch.setattr(importlib, "import_module", fake_import_module)
    report = embedding_backend_probe()
    assert report.available is False
    assert report.disabled_by_env is False
    assert report.import_ok is False
    assert report.encode_ok is False
    assert "fastembed_import_failed" in report.messages
    assert report.primary_reason_code == "fastembed_import_failed"


def test_embedding_cache_dir_from_env_none_when_unset(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("WOS_RAG_EMBEDDING_CACHE_DIR", raising=False)
    assert embedding_cache_dir_from_env() is None


def test_embedding_cache_dir_from_env_respects_set_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("WOS_RAG_EMBEDDING_CACHE_DIR", str(tmp_path))
    assert embedding_cache_dir_from_env() == str(tmp_path)


@requires_embeddings
def test_text_embedding_constructor_receives_cache_dir_from_env(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Deterministic cache: WOS_RAG_EMBEDDING_CACHE_DIR is passed to fastembed.TextEmbedding."""
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    monkeypatch.setenv("WOS_RAG_EMBEDDING_CACHE_DIR", str(tmp_path))
    clear_embedding_model_singleton()
    import fastembed

    captured: list[str | None] = []
    Real = fastembed.TextEmbedding

    def spy(*args, **kwargs):
        captured.append(kwargs.get("cache_dir"))
        return Real(*args, **kwargs)

    monkeypatch.setattr(fastembed, "TextEmbedding", spy)
    clear_embedding_model_singleton()
    out = encode_texts(["cache_wiring_probe"], batch_size=1)
    assert out is not None
    assert captured, "TextEmbedding should have been constructed"
    assert captured[0] == str(tmp_path)


@requires_embeddings
def test_singleton_reuses_model_across_encode_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    monkeypatch.setenv("WOS_RAG_EMBEDDING_CACHE_DIR", str(tmp_path))
    clear_embedding_model_singleton()
    import fastembed

    constructed = {"n": 0}
    Real = fastembed.TextEmbedding

    def spy(*args, **kwargs):
        constructed["n"] += 1
        return Real(*args, **kwargs)

    monkeypatch.setattr(fastembed, "TextEmbedding", spy)
    clear_embedding_model_singleton()
    assert encode_texts(["a"], batch_size=1) is not None
    assert encode_texts(["b"], batch_size=1) is not None
    assert constructed["n"] == 1


@requires_embeddings
def test_probe_available_when_backend_works(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv("WOS_RAG_DISABLE_EMBEDDINGS", raising=False)
    monkeypatch.setenv("WOS_RAG_EMBEDDING_CACHE_DIR", str(tmp_path))
    clear_embedding_model_singleton()
    report = embedding_backend_probe(sample_text="ok")
    assert report.available is True
    assert report.disabled_by_env is False
    assert report.import_ok is True
    assert report.encode_ok is True
    assert report.model_id == EMBEDDING_MODEL_ID
    assert report.cache_dir == str(tmp_path)
    assert report.messages == ()
    assert report.primary_reason_code == "embedding_backend_ok"
    assert report.cache_dir_identity == str(tmp_path.resolve())


def test_encode_texts_detailed_empty_input() -> None:
    out = encode_texts_detailed([])
    assert not out.ok
    assert "embedding_empty_input" in out.reason_codes
