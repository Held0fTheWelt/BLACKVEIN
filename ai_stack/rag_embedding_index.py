"""Dense embedding index persistence and load for the local RAG corpus (DS-003 split from rag.py)."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np

from ai_stack.rag_constants import DENSE_INDEX_META_SCHEMA, INDEX_VERSION
from ai_stack.rag_types import RetrievalDegradationMode
from ai_stack.semantic_embedding import (
    EMBEDDING_INDEX_VERSION,
    EMBEDDING_MODEL_ID,
    embedding_backend_probe,
    embedding_cache_dir_identity_for_meta,
    embeddings_disabled_by_env,
    encode_texts_detailed,
)


class _EmbeddingChunkLike(Protocol):
    text: str


class EmbeddingIndexCorpus(Protocol):
    """Structural type for corpus objects passed to dense index helpers."""

    chunks: list[_EmbeddingChunkLike]
    corpus_fingerprint: str
    rag_embedding_cache_dir_identity: str | None
    rag_embedding_index_version: str
    rag_embedding_backend_primary_code: str
    rag_dense_load_reason_codes: tuple[str, ...]
    rag_dense_artifact_validity: str
    rag_dense_index_build_action: str
    rag_dense_rebuild_reason: str | None


@dataclass(slots=True)
class CorpusEmbeddingIndex:
    """Dense vectors aligned with ``corpus.chunks`` row order (L2-normalized float32)."""

    vectors: np.ndarray
    model_id: str


def _embedding_meta_path(corpus_json: Path) -> Path:
    return corpus_json.parent / "runtime_embeddings.meta.json"


def _embedding_npz_path(corpus_json: Path) -> Path:
    return corpus_json.parent / "runtime_embeddings.npz"


def _canonical_dense_vectors_fingerprint(vectors: np.ndarray) -> str:
    """SHA-256 over canonical row-major float32 bytes (not NPZ container bytes)."""
    canon = np.ascontiguousarray(vectors.astype(np.float32, copy=False))
    return hashlib.sha256(canon.tobytes()).hexdigest()


@dataclass(frozen=True, slots=True)
class DenseIndexLoadResult:
    index: CorpusEmbeddingIndex | None
    reason_codes: tuple[str, ...]
    artifact_validity: str


def _load_corpus_embedding_index(corpus: EmbeddingIndexCorpus, corpus_json: Path) -> DenseIndexLoadResult:
    """Load dense index only when committed meta matches NPZ canonical fingerprint.

    Orphan ``runtime_embeddings.npz`` without valid meta is never reused.
    """
    meta_path = _embedding_meta_path(corpus_json)
    npz_path = _embedding_npz_path(corpus_json)
    if not meta_path.is_file():
        if npz_path.is_file():
            return DenseIndexLoadResult(
                None,
                ("dense_meta_missing_or_uncommitted", "dense_npz_present_without_meta"),
                "uncommitted_vectors_only",
            )
        return DenseIndexLoadResult(None, ("dense_meta_missing",), "missing")
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return DenseIndexLoadResult(None, ("dense_meta_json_invalid",), "invalid")
    if not isinstance(meta, dict):
        return DenseIndexLoadResult(None, ("dense_meta_not_object",), "invalid")
    if str(meta.get("dense_meta_schema", "")) != DENSE_INDEX_META_SCHEMA:
        return DenseIndexLoadResult(None, ("dense_meta_schema_mismatch",), "invalid")
    codes: list[str] = []
    if str(meta.get("corpus_fingerprint", "")) != corpus.corpus_fingerprint:
        codes.append("dense_corpus_fingerprint_mismatch")
    if str(meta.get("corpus_index_version", "")) != INDEX_VERSION:
        codes.append("dense_corpus_index_version_mismatch")
    if str(meta.get("embedding_index_version", "")) != EMBEDDING_INDEX_VERSION:
        codes.append("dense_embedding_index_version_mismatch")
    model_id = str(meta.get("embedding_model_id", ""))
    if model_id != EMBEDDING_MODEL_ID:
        codes.append("dense_embedding_model_id_mismatch")
    n = int(meta.get("num_chunks", -1))
    if n != len(corpus.chunks):
        codes.append("dense_num_chunks_mismatch")
    dim = int(meta.get("embedding_dim", -1))
    expected_fp = str(meta.get("vectors_canonical_sha256", ""))
    if not expected_fp:
        codes.append("dense_vectors_hash_missing")
    if codes:
        return DenseIndexLoadResult(None, tuple(codes), "invalid")
    if not npz_path.is_file():
        return DenseIndexLoadResult(None, ("dense_npz_missing",), "invalid")
    try:
        data = np.load(npz_path)
        vectors = data["vectors"]
    except Exception:
        return DenseIndexLoadResult(None, ("dense_npz_load_failed",), "invalid")
    if not isinstance(vectors, np.ndarray) or vectors.shape[0] != n:
        return DenseIndexLoadResult(None, ("dense_npz_shape_mismatch",), "invalid")
    if vectors.ndim != 2 or vectors.shape[1] != dim:
        return DenseIndexLoadResult(None, ("dense_npz_dim_mismatch",), "invalid")
    vectors_f = vectors.astype(np.float32, copy=False)
    got_fp = _canonical_dense_vectors_fingerprint(vectors_f)
    if got_fp != expected_fp:
        return DenseIndexLoadResult(None, ("dense_vectors_canonical_hash_mismatch",), "invalid")
    return DenseIndexLoadResult(
        CorpusEmbeddingIndex(vectors=vectors_f, model_id=model_id),
        (),
        "valid",
    )


def _save_corpus_embedding_index(
    corpus: EmbeddingIndexCorpus,
    vectors: np.ndarray,
    corpus_json: Path,
) -> None:
    """Write NPZ first, then meta. Meta is the sole commit marker for a valid index."""
    meta_path = _embedding_meta_path(corpus_json)
    npz_path = _embedding_npz_path(corpus_json)
    corpus_json.parent.mkdir(parents=True, exist_ok=True)
    canon = np.ascontiguousarray(vectors.astype(np.float32, copy=False))
    if canon.ndim != 2:
        raise ValueError("dense vectors must be 2-D")
    fp = _canonical_dense_vectors_fingerprint(canon)
    dim = int(canon.shape[1])
    meta = {
        "dense_meta_schema": DENSE_INDEX_META_SCHEMA,
        "corpus_fingerprint": corpus.corpus_fingerprint,
        "corpus_index_version": INDEX_VERSION,
        "embedding_index_version": EMBEDDING_INDEX_VERSION,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "num_chunks": len(corpus.chunks),
        "embedding_dim": dim,
        "vectors_canonical_sha256": fp,
        "embedding_cache_dir_identity": embedding_cache_dir_identity_for_meta(),
    }
    tmp_meta: str | None = None
    tmp_npz: str | None = None
    try:
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=corpus_json.parent,
            prefix=".emb_vec_",
            suffix=".npz",
        ) as tmp:
            tmp_npz = tmp.name
        np.savez_compressed(tmp_npz, vectors=canon)
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            dir=corpus_json.parent,
            prefix=".emb_meta_",
            suffix=".json",
        ) as tmp:
            tmp.write(json.dumps(meta, ensure_ascii=True, indent=2))
            tmp_meta = tmp.name
        if tmp_npz:
            os.replace(tmp_npz, npz_path)
        if tmp_meta:
            os.replace(tmp_meta, meta_path)
    except Exception:
        if tmp_meta:
            try:
                Path(tmp_meta).unlink(missing_ok=True)
            except OSError:
                pass
        if tmp_npz:
            try:
                Path(tmp_npz).unlink(missing_ok=True)
            except OSError:
                pass
        raise


def _ensure_corpus_embedding_index(corpus: EmbeddingIndexCorpus, corpus_json: Path) -> CorpusEmbeddingIndex | None:
    corpus.rag_embedding_cache_dir_identity = embedding_cache_dir_identity_for_meta()
    corpus.rag_embedding_index_version = EMBEDDING_INDEX_VERSION
    probe = embedding_backend_probe()
    corpus.rag_embedding_backend_primary_code = probe.primary_reason_code

    if embeddings_disabled_by_env():
        corpus.rag_dense_index_build_action = "unavailable"
        corpus.rag_dense_artifact_validity = "skipped_env"
        corpus.rag_dense_load_reason_codes = ("embeddings_disabled_by_env",)
        corpus.rag_dense_rebuild_reason = None
        return None

    load_result = _load_corpus_embedding_index(corpus, corpus_json)
    corpus.rag_dense_load_reason_codes = load_result.reason_codes
    corpus.rag_dense_artifact_validity = load_result.artifact_validity

    if load_result.index is not None:
        corpus.rag_dense_index_build_action = "reused_persisted"
        corpus.rag_dense_rebuild_reason = None
        return load_result.index

    partial = load_result.artifact_validity == "uncommitted_vectors_only"
    if partial:
        corpus.rag_dense_rebuild_reason = "reload_after_uncommitted_npz"
    else:
        corpus.rag_dense_rebuild_reason = "reload_after_invalid_or_missing_dense_index"

    if not corpus.chunks:
        corpus.rag_dense_index_build_action = "none"
        return None

    if not probe.available:
        corpus.rag_dense_index_build_action = "unavailable"
        return None

    texts = [chunk.text for chunk in corpus.chunks]
    enc = encode_texts_detailed(texts)
    if not enc.ok or enc.vectors is None:
        corpus.rag_dense_index_build_action = "unavailable"
        corpus.rag_dense_rebuild_reason = "dense_corpus_encode_failed"
        return None
    if enc.vectors.shape[0] != len(corpus.chunks):
        corpus.rag_dense_index_build_action = "unavailable"
        corpus.rag_dense_rebuild_reason = "dense_corpus_encode_row_mismatch"
        return None
    try:
        _save_corpus_embedding_index(corpus, enc.vectors, corpus_json)
    except Exception:
        corpus.rag_dense_index_build_action = "unavailable"
        corpus.rag_dense_artifact_validity = "partial_write_failure"
        corpus.rag_dense_rebuild_reason = "dense_save_failed"
        return None
    corpus.rag_dense_index_build_action = RetrievalDegradationMode.REBUILT_DENSE_INDEX.value
    corpus.rag_dense_artifact_validity = "valid"
    corpus.rag_dense_load_reason_codes = ()
    return CorpusEmbeddingIndex(vectors=enc.vectors, model_id=EMBEDDING_MODEL_ID)
