"""
Dense embedding backend for hybrid RAG (C1-next).

Uses ``fastembed`` with a small ONNX model when available. When the
dependency is missing, the environment disables embeddings, or encoding
fails, callers receive ``None`` from :func:`encode_texts` /
:func:`encode_query` and the retriever falls back to the sparse path
explicitly (``retrieval_route=sparse_fallback`` in :mod:`ai_stack.rag`).
Use :func:`encode_texts_detailed` / :func:`encode_query_detailed` for
stable machine-readable reason codes without silent downgrade.

**Dependency stance:** ``fastembed`` is optional for sparse-only RAG.
For full BC-next / C1-next verification that exercises the hybrid path,
install ``fastembed`` (see ``world-engine/requirements.txt`` /
``backend/requirements.txt``) and provide a writable model cache
(``WOS_RAG_EMBEDDING_CACHE_DIR`` and/or standard Hugging Face hub cache
env vars).

Retrieval routes and degradation flags surfaced in ``ai_stack.rag`` /
``build_retrieval_trace`` are the authoritative operator truth when
embeddings are absent or encode fails (sparse fallback).

**Cache:** ``WOS_RAG_EMBEDDING_CACHE_DIR`` pins fastembed's ONNX/model
download location for reproducible CI and local runs. If unset,
fastembed uses its default (typically under the user cache / HF hub
layout).

Use :func:`embedding_backend_probe` for explicit available/unavailable
reporting without guessing from retrieval routes alone.
"""

from __future__ import annotations

import contextlib
import logging
import os
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBEDDING_INDEX_VERSION = "c1_next_embed_v1"

_ENV_DISABLE = "WOS_RAG_DISABLE_EMBEDDINGS"
_ENV_CACHE_DIR = "WOS_RAG_EMBEDDING_CACHE_DIR"


@contextlib.contextmanager
def _suppress_hf_hub_anonymous_download_hint() -> object:
    """Drop huggingface_hub's noisy anonymous-download hint during model fetch.

    Operators who omit ``HF_TOKEN`` still get working pulls; the library logs a
    rate-limit reminder on stderr. Document ``HF_TOKEN`` in ``.env.example``; here
    we only avoid cluttering Docker/gunicorn logs during ``TextEmbedding`` init.
    """

    class _DropAnonymousHFHint(logging.Filter):
        def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
            return "unauthenticated requests to the HF Hub" not in record.getMessage()

    filt = _DropAnonymousHFHint()
    hub = logging.getLogger("huggingface_hub")
    hub.addFilter(filt)
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message=r".*[Uu]nauthenticated requests to the HF Hub.*",
            category=Warning,
        )
        try:
            yield
        finally:
            hub.removeFilter(filt)

# One TextEmbedding instance per process (keyed by model id + resolved cache dir).
_model_singleton: object | None = None
_model_singleton_key: tuple[str, str | None] = None


def embeddings_disabled_by_env() -> bool:
    """Describe what ``embeddings_disabled_by_env`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return os.environ.get(_ENV_DISABLE, "").strip().lower() in ("1", "true", "yes")


def embedding_cache_dir_from_env() -> str | None:
    """Return fastembed ``cache_dir`` from ``WOS_RAG_EMBEDDING_CACHE_DIR``,
    or ``None``.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    raw = os.environ.get(_ENV_CACHE_DIR, "").strip()
    return raw if raw else None


def embedding_cache_dir_identity_for_meta() -> str:
    """Stable string for RAG dense-index metadata (resolved path or
    sentinels).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        str:
            Returns a value of type ``str``; see the function body for structure, error paths, and sentinels.
    """
    raw = embedding_cache_dir_from_env()
    if not raw:
        return "__default__"
    try:
        return str(Path(raw).resolve())
    except OSError:
        return raw


def clear_embedding_model_singleton() -> None:
    """Drop the in-process FastEmbed singleton.
    
    Call after changing ``WOS_RAG_EMBEDDING_CACHE_DIR`` or when tests
    need a clean runtime (for example before reloading configuration).
    """
    global _model_singleton, _model_singleton_key
    _model_singleton = None
    _model_singleton_key = None


def _normalize_reason_codes(codes: tuple[str, ...]) -> tuple[str, ...]:
    """``_normalize_reason_codes`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        codes: ``codes`` (tuple[str, ...]); meaning follows the type and call sites.
    
    Returns:
        tuple[str, ...]:
            Returns a value of type ``tuple[str, ...]``; see the function body for structure, error paths, and sentinels.
    """
    return tuple(codes) if codes else ("embedding_unknown_failure",)


@dataclass(frozen=True, slots=True)
class EncodeOutcome:
    """Result of a dense encode attempt; always carries explicit reason codes."""

    vectors: "np.ndarray | None"
    reason_codes: tuple[str, ...]
    """Stable machine-oriented codes; empty tuple only when ``ok``."""

    @property
    def ok(self) -> bool:
        """Describe what ``ok`` does in one line (verb-led summary for this
        method).
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Returns:
            bool:
                Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
        """
        return self.vectors is not None


@dataclass(frozen=True, slots=True)
class EmbeddingBackendReport:
    """Outcome of :func:`embedding_backend_probe` (explicit, no silent
    downgrade).
    """

    available: bool
    """True only if embeddings are enabled, fastembed imports, and a sample encode succeeds."""
    disabled_by_env: bool
    """True when ``WOS_RAG_DISABLE_EMBEDDINGS`` is set to a truthy value."""
    import_ok: bool
    """True when ``fastembed.TextEmbedding`` can be imported."""
    encode_ok: bool
    """True when a sample one-row encode succeeded (meaningful only if ``import_ok``)."""
    model_id: str
    cache_dir: str | None
    """Effective ``cache_dir`` passed to fastembed (from env or ``None`` for default)."""
    cache_dir_identity: str
    """Resolved cache path identity for metadata (see :func:`embedding_cache_dir_identity_for_meta`)."""
    primary_reason_code: str
    """Single dominant code for operators and tests; ``embedding_backend_ok`` when available."""
    messages: tuple[str, ...]
    """Full reason chain; empty when ``available`` is True."""


def embedding_backend_probe(*, sample_text: str = "ping") -> EmbeddingBackendReport:
    """Probe dense embedding availability without relying on RAG retrieval
    side effects.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sample_text: ``sample_text`` (str); meaning follows the type and call sites.
    
    Returns:
        EmbeddingBackendReport:
            Returns a value of type ``EmbeddingBackendReport``; see the function body for structure, error paths, and sentinels.
    """
    cache_dir = embedding_cache_dir_from_env()
    identity = embedding_cache_dir_identity_for_meta()
    if embeddings_disabled_by_env():
        return EmbeddingBackendReport(
            available=False,
            disabled_by_env=True,
            import_ok=False,
            encode_ok=False,
            model_id=EMBEDDING_MODEL_ID,
            cache_dir=cache_dir,
            cache_dir_identity=identity,
            primary_reason_code="embeddings_disabled_by_env",
            messages=("embeddings_disabled_by_env",),
        )
    try:
        import importlib

        importlib.import_module("fastembed")
    except ImportError:
        return EmbeddingBackendReport(
            available=False,
            disabled_by_env=False,
            import_ok=False,
            encode_ok=False,
            model_id=EMBEDDING_MODEL_ID,
            cache_dir=cache_dir,
            cache_dir_identity=identity,
            primary_reason_code="fastembed_import_failed",
            messages=("fastembed_import_failed",),
        )

    outcome = encode_texts_detailed([sample_text], batch_size=1)
    if not outcome.ok:
        codes = _normalize_reason_codes(outcome.reason_codes)
        return EmbeddingBackendReport(
            available=False,
            disabled_by_env=False,
            import_ok=True,
            encode_ok=False,
            model_id=EMBEDDING_MODEL_ID,
            cache_dir=cache_dir,
            cache_dir_identity=identity,
            primary_reason_code=codes[0],
            messages=codes,
        )
    return EmbeddingBackendReport(
        available=True,
        disabled_by_env=False,
        import_ok=True,
        encode_ok=True,
        model_id=EMBEDDING_MODEL_ID,
        cache_dir=cache_dir,
        cache_dir_identity=identity,
        primary_reason_code="embedding_backend_ok",
        messages=(),
    )


def _get_text_embedding():
    """Lazily construct ``TextEmbedding`` with env-resolved ``cache_dir``."""
    global _model_singleton, _model_singleton_key
    cache_dir = embedding_cache_dir_from_env()
    key = (EMBEDDING_MODEL_ID, cache_dir)
    if _model_singleton is not None and _model_singleton_key == key:
        return _model_singleton
    from fastembed import TextEmbedding

    with _suppress_hf_hub_anonymous_download_hint():
        _model_singleton = TextEmbedding(model_name=EMBEDDING_MODEL_ID, cache_dir=cache_dir)
    _model_singleton_key = key
    return _model_singleton


def encode_texts_detailed(texts: list[str], *, batch_size: int = 32) -> EncodeOutcome:
    """Encode texts to an L2-normalized float32 matrix ``(len(texts),
    dim)`` with reason codes.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        texts: ``texts`` (list[str]); meaning follows the type and call sites.
        batch_size: ``batch_size`` (int); meaning follows the type and call sites.
    
    Returns:
        EncodeOutcome:
            Returns a value of type ``EncodeOutcome``; see the function body for structure, error paths, and sentinels.
    """
    if embeddings_disabled_by_env():
        return EncodeOutcome(None, ("embeddings_disabled_by_env",))
    if not texts:
        return EncodeOutcome(None, ("embedding_empty_input",))

    try:
        import numpy as np
    except ImportError:
        return EncodeOutcome(None, ("numpy_import_failed",))

    try:
        model = _get_text_embedding()
        rows: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            for embedding in model.embed(batch):
                rows.append(list(embedding))
        if len(rows) != len(texts):
            return EncodeOutcome(None, ("embedding_encode_count_mismatch",))
        arr = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, np.float32(1e-12))
        arr = arr / norms
        return EncodeOutcome(arr, ())
    except ImportError:
        return EncodeOutcome(None, ("fastembed_import_failed",))
    except Exception:
        return EncodeOutcome(None, ("embedding_runtime_error",))


def encode_texts(texts: list[str], *, batch_size: int = 32) -> "np.ndarray | None":
    """Encode texts to an L2-normalized float32 matrix ``(len(texts),
    dim)``.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        texts: ``texts`` (list[str]); meaning follows the type and call sites.
        batch_size: ``batch_size`` (int); meaning follows the type and call sites.
    
    Returns:
        np.ndarray | None:
            Returns a value of type ``np.ndarray | None``; see the function body for structure, error paths, and sentinels.
    """
    return encode_texts_detailed(texts, batch_size=batch_size).vectors


def encode_query_detailed(text: str) -> EncodeOutcome:
    """Encode a single query; returns a 1-D L2-normalized float32 vector or
    codes.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        EncodeOutcome:
            Returns a value of type ``EncodeOutcome``; see the function body for structure, error paths, and sentinels.
    """
    if not (text or "").strip():
        return EncodeOutcome(None, ("embedding_empty_query",))
    outcome = encode_texts_detailed([text], batch_size=1)
    if not outcome.ok or outcome.vectors is None:
        return outcome
    if outcome.vectors.shape[0] < 1:
        return EncodeOutcome(None, ("embedding_encode_count_mismatch",))
    return EncodeOutcome(outcome.vectors[0], ())


def encode_query(text: str) -> "np.ndarray | None":
    """Encode a single query; returns a 1-D L2-normalized float32 vector or
    ``None``.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        text: ``text`` (str); meaning follows the type and call sites.
    
    Returns:
        np.ndarray | None:
            Returns a value of type ``np.ndarray | None``; see the function body for structure, error paths, and sentinels.
    """
    return encode_query_detailed(text).vectors