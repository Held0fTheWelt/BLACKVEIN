"""Hybrid vs sparse encoding resolution for RAG retrieve (DS-033) — behavior-preserving."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from ai_stack.rag_corpus import InMemoryRetrievalCorpus
    from ai_stack.rag_retrieval_dtos import RetrievalRequest


@dataclass(frozen=True, slots=True)
class _RetrievalHybridEncodingState:
    """Dense/hybrid vs sparse route, query encoding outcome, and degradation label (retrieve pre-rerank)."""

    use_hybrid: bool
    query_vec: np.ndarray | None
    query_enc_codes: tuple[str, ...]
    query_encode_failed: bool
    retrieval_route: str
    embedding_mid: str
    degradation_mode: str


def _sparse_fallback_degradation_mode(
    *,
    dense_validity: str,
    backend_code: str,
    query_encode_failed: bool,
    embeddings_env_disabled: bool,
    rdm: type,
) -> str:
    """Pick degradation label when not on hybrid OK path (flat branches for lower AST nesting)."""
    if embeddings_env_disabled:
        return rdm.SPARSE_FALLBACK_NO_BACKEND.value
    if query_encode_failed:
        return rdm.SPARSE_FALLBACK_ENCODE_FAILURE.value
    if dense_validity == "uncommitted_vectors_only":
        return rdm.DEGRADED_PARTIAL_PERSISTENCE.value
    if dense_validity == "partial_write_failure":
        return rdm.DEGRADED_PARTIAL_PERSISTENCE.value
    if backend_code != "embedding_backend_ok":
        return rdm.SPARSE_FALLBACK_NO_BACKEND.value
    return rdm.SPARSE_FALLBACK_INVALID_OR_MISSING_DENSE_INDEX.value


def _resolve_retrieval_hybrid_encoding_state(
    corpus: InMemoryRetrievalCorpus,
    request: RetrievalRequest,
    *,
    embedding_index_ready: bool,
    embedding_model_id: str,
) -> _RetrievalHybridEncodingState:
    # Bind through ``ai_stack.rag`` so tests and callers can monkeypatch
    # ``rag.encode_query_detailed`` / ``rag.embeddings_disabled_by_env``.
    from ai_stack.rag import (
        RetrievalDegradationMode,
        embeddings_disabled_by_env,
        encode_query_detailed,
    )

    c = corpus
    dense_validity = c.rag_dense_artifact_validity
    backend_code = c.rag_embedding_backend_primary_code

    use_hybrid = embedding_index_ready and not request.use_sparse_only and not embeddings_disabled_by_env()
    query_vec: np.ndarray | None = None
    query_enc_codes: tuple[str, ...] = ()
    query_encode_failed = False
    if use_hybrid:
        qo = encode_query_detailed(request.query)
        query_vec = qo.vectors
        query_enc_codes = qo.reason_codes
        if query_vec is None:
            use_hybrid = False
            query_encode_failed = True

    retrieval_route = "hybrid" if use_hybrid else "sparse_fallback"
    embedding_mid = embedding_model_id if use_hybrid else ""

    if request.use_sparse_only or use_hybrid:
        degradation_mode = RetrievalDegradationMode.HYBRID_OK.value
    else:
        degradation_mode = _sparse_fallback_degradation_mode(
            dense_validity=dense_validity,
            backend_code=backend_code,
            query_encode_failed=query_encode_failed,
            embeddings_env_disabled=embeddings_disabled_by_env(),
            rdm=RetrievalDegradationMode,
        )

    return _RetrievalHybridEncodingState(
        use_hybrid=use_hybrid,
        query_vec=query_vec,
        query_enc_codes=query_enc_codes,
        query_encode_failed=query_encode_failed,
        retrieval_route=retrieval_route,
        embedding_mid=embedding_mid,
        degradation_mode=degradation_mode,
    )
