"""Shared pytest markers for embedding-backed RAG tests."""

from __future__ import annotations

import os

import pytest

from ai_stack.semantic_embedding import embedding_backend_probe


def embedding_backend_ready() -> bool:
    """True when hybrid embedding path can run (fastembed + successful sample encode)."""
    prev = os.environ.get("WOS_RAG_DISABLE_EMBEDDINGS")
    try:
        os.environ.pop("WOS_RAG_DISABLE_EMBEDDINGS", None)
        return embedding_backend_probe().available
    finally:
        if prev is not None:
            os.environ["WOS_RAG_DISABLE_EMBEDDINGS"] = prev


requires_embeddings = pytest.mark.skipif(
    not embedding_backend_ready(),
    reason=(
        "Embedding backend not available: install fastembed + numpy, allow model download or set "
        "WOS_RAG_EMBEDDING_CACHE_DIR to a primed cache; see rag_in_world_of_shadows.md"
    ),
)
