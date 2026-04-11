"""Project-scoped retrieval for World of Shadows (RAG layer C).

Hybrid retrieval (Task 2 quality pass): with a committed local embedding index,
queries use profile-tuned dense/sparse fusion (hybrid v2), a deterministic
reranking pass over a candidate pool, near-duplicate suppression, and profile-aware
context packing. Dense/sparse agreement is applied once in reranking (explicit
bonus), not duplicated in the initial hybrid core. Without embeddings, the path
is sparse-only with ``retrieval_route=sparse_fallback`` in ranking notes.

Task 3 (source governance): explicit evidence lanes, visibility classes, a hard
policy gate on the rerank pool (runtime draft suppression when published canonical
exists for the same module), and additive ``policy_soft_*`` adjustments that are
separate from Task 2 rerank signals. Lifecycle/degradation notes (Task 1) and
quality/rerank notes (Task 2) stay distinct from ``policy_*`` notes.

Persistence: JSON corpus under ``.wos/rag/runtime_corpus.json`` (``PersistentRagStore``)
plus optional ``runtime_embeddings.npz`` + ``runtime_embeddings.meta.json`` for
reproducible local dense indices. The dense index uses `runtime_embeddings.meta.json`
as the **commit marker**: a canonical SHA-256 over row-major float32 vector bytes
(not NPZ container bytes) must match the committed meta; orphan NPZ without valid
meta is never reused. NPZ is replaced first, then meta, so a crash after NPZ but
before meta leaves the previous meta authoritative and the next load rejects the
mismatch safely. This remains a single-host local design, not a distributed vector database.
"""

from __future__ import annotations

from pathlib import Path

from ai_stack.semantic_embedding import (
    EMBEDDING_MODEL_ID,
    embedding_backend_probe,
    embedding_cache_dir_identity_for_meta,
    embeddings_disabled_by_env,
    encode_query,
    encode_query_detailed,
    encode_texts,
    encode_texts_detailed,
)

from ai_stack.rag_constants import (
    DENSE_INDEX_META_SCHEMA,
    INDEX_VERSION,
    RERANK_MODULE_MATCH_EXTRA,
    RETRIEVAL_PIPELINE_VERSION,
    RETRIEVAL_POLICY_VERSION,
)
from ai_stack.rag_types import (
    ContentClass,
    RetrievalDegradationMode,
    RetrievalDomain,
    RetrievalDomainError,
    RetrievalStatus,
    SourceEvidenceLane,
    SourceGovernanceView,
    SourceVisibilityClass,
)
from ai_stack.rag_corpus import CorpusChunk, InMemoryRetrievalCorpus, _ScoredCandidate
from ai_stack.rag_ingestion import RagIngestionPipeline
from ai_stack.rag_embedding_index import (
    DenseIndexLoadResult,
    _ensure_corpus_embedding_index,
    _load_corpus_embedding_index,
    _save_corpus_embedding_index,
)
from ai_stack.rag_retrieval_dtos import ContextPack, RetrievalHit, RetrievalRequest, RetrievalResult
from ai_stack.rag_retrieval_lexical import (
    SEMANTIC_CANON,
    SEMANTIC_EXPANSIONS,
    _char_trigram_jaccard,
    _normalize_for_dup,
    _normalize_token,
    _raw_tokens,
    _rerank_agreement_bonus,
)
from ai_stack.rag_context_pack_assembler import ContextPackAssembler
from ai_stack.rag_governance import governance_view_for_chunk
from ai_stack.rag_persistent_store import PersistentRagStore


from ai_stack.rag_context_retriever import ContextRetriever


def build_runtime_retriever(repo_root: Path) -> tuple[ContextRetriever, ContextPackAssembler, InMemoryRetrievalCorpus]:
    """Delegate to ``rag_runtime_bootstrap`` after ``rag`` is fully initialized (avoids import cycles)."""
    from ai_stack.rag_runtime_bootstrap import build_runtime_retriever as _build_runtime_retriever

    return _build_runtime_retriever(repo_root)
