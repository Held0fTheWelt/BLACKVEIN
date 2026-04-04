"""Dense embedding backend for hybrid RAG (C1-next).

Uses `fastembed` with a small ONNX model when available. When the dependency is
missing, the environment disables embeddings, or encoding fails, callers receive
``None`` and the retriever falls back to the sparse path explicitly.
"""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

EMBEDDING_MODEL_ID = "BAAI/bge-small-en-v1.5"
EMBEDDING_INDEX_VERSION = "c1_next_embed_v1"


def embeddings_disabled_by_env() -> bool:
    return os.environ.get("WOS_RAG_DISABLE_EMBEDDINGS", "").strip().lower() in ("1", "true", "yes")


def encode_texts(texts: list[str], *, batch_size: int = 32) -> "np.ndarray | None":
    """Encode texts to an L2-normalized float32 matrix ``(len(texts), dim)``.

    Returns ``None`` if embeddings are disabled, imports fail, or encoding errors occur.
    """
    if embeddings_disabled_by_env() or not texts:
        return None
    try:
        import numpy as np
        from fastembed import TextEmbedding
    except ImportError:
        return None

    try:
        model = TextEmbedding(model_name=EMBEDDING_MODEL_ID)
        rows: list[list[float]] = []
        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            for embedding in model.embed(batch):
                rows.append(list(embedding))
        if len(rows) != len(texts):
            return None
        arr = np.asarray(rows, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms = np.maximum(norms, np.float32(1e-12))
        arr = arr / norms
        return arr
    except Exception:
        return None


def encode_query(text: str) -> "np.ndarray | None":
    """Encode a single query; returns a 1-D L2-normalized float32 vector or ``None``."""
    if not (text or "").strip():
        return None
    matrix = encode_texts([text], batch_size=1)
    if matrix is None or matrix.shape[0] < 1:
        return None
    return matrix[0]
