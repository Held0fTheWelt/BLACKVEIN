"""Project-scoped retrieval for World of Shadows (RAG layer C).

Hybrid retrieval (Task 2 quality pass): with a committed local embedding index,
queries use profile-tuned dense/sparse fusion (hybrid v2), a deterministic
reranking pass over a candidate pool, near-duplicate suppression, and profile-aware
context packing. Dense/sparse agreement is applied once in reranking (explicit
bonus), not duplicated in the initial hybrid core. Without embeddings, the path
is sparse-only with ``retrieval_route=sparse_fallback`` in ranking notes.

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

from dataclasses import dataclass, field
from datetime import datetime, timezone
import json
import os
import tempfile
try:
    from enum import StrEnum
except ImportError:
    # Python < 3.11 fallback
    from enum import Enum
    class StrEnum(str, Enum):
        def __str__(self) -> str:
            return self.value
import hashlib
import math
from pathlib import Path
import re

import numpy as np

from ai_stack.semantic_embedding import (
    EMBEDDING_INDEX_VERSION,
    EMBEDDING_MODEL_ID,
    embedding_backend_probe,
    embedding_cache_dir_identity_for_meta,
    embeddings_disabled_by_env,
    encode_query,
    encode_query_detailed,
    encode_texts,
    encode_texts_detailed,
)


class RetrievalDomain(StrEnum):
    RUNTIME = "runtime"
    WRITERS_ROOM = "writers_room"
    IMPROVEMENT = "improvement"


class RetrievalStatus(StrEnum):
    OK = "ok"
    DEGRADED = "degraded"
    FALLBACK = "fallback"


class ContentClass(StrEnum):
    AUTHORED_MODULE = "authored_module"
    RUNTIME_PROJECTION = "runtime_projection"
    CHARACTER_PROFILE = "character_profile"
    TRANSCRIPT = "transcript"
    REVIEW_NOTE = "review_note"
    EVALUATION_ARTIFACT = "evaluation_artifact"
    POLICY_GUIDELINE = "policy_guideline"


DOMAIN_CONTENT_ACCESS: dict[RetrievalDomain, set[ContentClass]] = {
    RetrievalDomain.RUNTIME: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.CHARACTER_PROFILE,
        ContentClass.TRANSCRIPT,
        ContentClass.POLICY_GUIDELINE,
    },
    RetrievalDomain.WRITERS_ROOM: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.CHARACTER_PROFILE,
        ContentClass.TRANSCRIPT,
        ContentClass.REVIEW_NOTE,
        ContentClass.POLICY_GUIDELINE,
    },
    RetrievalDomain.IMPROVEMENT: {
        ContentClass.AUTHORED_MODULE,
        ContentClass.RUNTIME_PROJECTION,
        ContentClass.TRANSCRIPT,
        ContentClass.REVIEW_NOTE,
        ContentClass.EVALUATION_ARTIFACT,
        ContentClass.POLICY_GUIDELINE,
    },
}


INDEX_VERSION = "c1_next_hybrid_v1"

# Dense index on disk: meta JSON is the commit marker (see module docstring).
DENSE_INDEX_META_SCHEMA = "c1_dense_index_meta_v2"


class RetrievalDegradationMode(StrEnum):
    """Stable labels for retrieval health (sparse vs hybrid and why)."""

    HYBRID_OK = "hybrid_ok"
    SPARSE_FALLBACK_NO_BACKEND = "sparse_fallback_due_to_no_backend"
    SPARSE_FALLBACK_ENCODE_FAILURE = "sparse_fallback_due_to_encode_failure"
    SPARSE_FALLBACK_INVALID_OR_MISSING_DENSE_INDEX = "sparse_fallback_due_to_invalid_or_missing_dense_index"
    REBUILT_DENSE_INDEX = "rebuilt_dense_index"
    DEGRADED_PARTIAL_PERSISTENCE = "degraded_due_to_partial_persistence_problem"
    CORPUS_EMPTY = "corpus_empty"


# Retrieval ranking behavior version (not corpus/storage INDEX_VERSION).
RETRIEVAL_PIPELINE_VERSION = "task2_hybrid_v2"

# Legacy single-weight hybrid (superseded by profile maps; kept for tests/import stability).
HYBRID_DENSE_WEIGHT = 0.62
HYBRID_SPARSE_WEIGHT = 0.38

# Per-profile dense/sparse balance for initial hybrid core (both signals in ~[0, 1]).
PROFILE_HYBRID_WEIGHTS: dict[str, tuple[float, float]] = {
    "runtime_turn_support": (0.58, 0.42),
    "writers_review": (0.60, 0.38),
    "improvement_eval": (0.54, 0.46),
}

# Weak dense + strong sparse: do not let a low dense cosine collapse a strong lexical match.
HYBRID_DENSE_WEAK_THRESHOLD = 0.24
HYBRID_SPARSE_STRONG_THRESHOLD = 0.33
# Rescue blend emphasizes sparse when dense is weak (explicit, linear).
HYBRID_WEAK_DENSE_SPARSE_EMPHASIS = 0.78

# Initial score scale (keeps final scores in a band compatible with downstream heuristics).
HYBRID_CORE_SCALE = 4.0

# Reranking pool sizing (deterministic).
RERANK_POOL_FACTOR = 4
RERANK_POOL_MIN = 16
RERANK_POOL_CAP = 56

# Agreement bonus applies only in reranking when both signals exceed a floor (single stage).
RERANK_AGREEMENT_MIN_SIGNAL = 0.14
RERANK_AGREEMENT_BONUS_CAP = 0.40

# Near-duplicate suppression (character trigram Jaccard, deterministic).
DUP_TRIGRAM_JACCARD_DROP = 0.91
DUP_SAME_SOURCE_JACCARD_DROP = 0.86
DUP_IMPROVEMENT_RELAXATION = 0.94

# Initial retrieval boosts (reranking adds profile-specific module emphasis).
INITIAL_MODULE_MATCH_BOOST = 1.15
INITIAL_SCENE_HINT_BOOST = 1.12
RERANK_MODULE_MATCH_EXTRA: dict[str, float] = {
    "runtime_turn_support": 1.22,
    "writers_review": 1.05,
    "improvement_eval": 0.88,
}


class RetrievalDomainError(ValueError):
    pass


@dataclass(slots=True)
class CorpusChunk:
    chunk_id: str
    source_path: str
    source_name: str
    content_class: ContentClass
    text: str
    module_id: str | None = None
    source_version: str = ""
    source_hash: str = ""
    canonical_priority: int = 0
    semantic_terms: dict[str, float] = field(default_factory=dict)
    term_norm: float = 0.0


@dataclass(slots=True)
class InMemoryRetrievalCorpus:
    chunks: list[CorpusChunk]
    built_at: str
    source_count: int
    index_version: str = INDEX_VERSION
    corpus_fingerprint: str = ""
    storage_path: str = ""
    profile_versions: dict[str, str] = field(default_factory=dict)
    rag_dense_artifact_validity: str = ""
    rag_dense_index_build_action: str = ""
    rag_dense_rebuild_reason: str | None = None
    rag_dense_load_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    rag_embedding_index_version: str = ""
    rag_embedding_cache_dir_identity: str | None = None
    rag_embedding_backend_primary_code: str = ""

    @classmethod
    def empty(cls) -> "InMemoryRetrievalCorpus":
        return cls(
            chunks=[],
            built_at=datetime.now(timezone.utc).isoformat(),
            source_count=0,
            index_version=INDEX_VERSION,
            corpus_fingerprint="",
            storage_path="",
            profile_versions={},
            rag_dense_artifact_validity="",
            rag_dense_index_build_action="",
            rag_dense_rebuild_reason=None,
            rag_dense_load_reason_codes=(),
            rag_embedding_index_version="",
            rag_embedding_cache_dir_identity=None,
            rag_embedding_backend_primary_code="",
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "chunks": [
                {
                    "chunk_id": chunk.chunk_id,
                    "source_path": chunk.source_path,
                    "source_name": chunk.source_name,
                    "content_class": chunk.content_class.value,
                    "text": chunk.text,
                    "module_id": chunk.module_id,
                    "source_version": chunk.source_version,
                    "source_hash": chunk.source_hash,
                    "canonical_priority": chunk.canonical_priority,
                    "semantic_terms": chunk.semantic_terms,
                    "term_norm": chunk.term_norm,
                }
                for chunk in self.chunks
            ],
            "built_at": self.built_at,
            "source_count": self.source_count,
            "index_version": self.index_version,
            "corpus_fingerprint": self.corpus_fingerprint,
            "storage_path": self.storage_path,
            "profile_versions": self.profile_versions,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "InMemoryRetrievalCorpus":
        raw_chunks = payload.get("chunks", [])
        chunks: list[CorpusChunk] = []
        if isinstance(raw_chunks, list):
            for raw in raw_chunks:
                if not isinstance(raw, dict):
                    continue
                content_class_value = str(raw.get("content_class", ContentClass.REVIEW_NOTE.value))
                try:
                    content_class = ContentClass(content_class_value)
                except ValueError:
                    continue
                semantic_terms = raw.get("semantic_terms", {})
                chunks.append(
                    CorpusChunk(
                        chunk_id=str(raw.get("chunk_id", "")),
                        source_path=str(raw.get("source_path", "")),
                        source_name=str(raw.get("source_name", "")),
                        content_class=content_class,
                        text=str(raw.get("text", "")),
                        module_id=str(raw.get("module_id")) if raw.get("module_id") is not None else None,
                        source_version=str(raw.get("source_version", "")),
                        source_hash=str(raw.get("source_hash", "")),
                        canonical_priority=int(raw.get("canonical_priority", 0)),
                        semantic_terms=semantic_terms if isinstance(semantic_terms, dict) else {},
                        term_norm=float(raw.get("term_norm", 0.0)),
                    )
                )
        return cls(
            chunks=chunks,
            built_at=str(payload.get("built_at", datetime.now(timezone.utc).isoformat())),
            source_count=int(payload.get("source_count", 0)),
            index_version=str(payload.get("index_version", INDEX_VERSION)),
            corpus_fingerprint=str(payload.get("corpus_fingerprint", "")),
            storage_path=str(payload.get("storage_path", "")),
            profile_versions=payload.get("profile_versions", {}) if isinstance(payload.get("profile_versions"), dict) else {},
            rag_dense_artifact_validity="",
            rag_dense_index_build_action="",
            rag_dense_rebuild_reason=None,
            rag_dense_load_reason_codes=(),
            rag_embedding_index_version="",
            rag_embedding_cache_dir_identity=None,
            rag_embedding_backend_primary_code="",
        )


@dataclass(slots=True)
class RetrievalRequest:
    domain: RetrievalDomain
    profile: str
    query: str
    module_id: str | None = None
    scene_id: str | None = None
    max_chunks: int = 4
    use_sparse_only: bool = False


@dataclass(slots=True)
class RetrievalHit:
    chunk_id: str
    source_path: str
    source_name: str
    content_class: str
    source_version: str
    score: float
    snippet: str
    selection_reason: str
    pack_role: str = ""
    why_selected: str = ""


@dataclass(slots=True)
class RetrievalResult:
    request: RetrievalRequest
    status: RetrievalStatus
    hits: list[RetrievalHit]
    ranking_notes: list[str]
    error: str | None = None
    index_version: str = ""
    corpus_fingerprint: str = ""
    storage_path: str = ""
    retrieval_route: str = ""
    embedding_model_id: str = ""
    degradation_mode: str = ""
    dense_index_build_action: str = ""
    dense_rebuild_reason: str | None = None
    dense_artifact_validity: str = ""
    embedding_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    embedding_index_version: str = ""
    embedding_cache_dir_identity: str | None = None


@dataclass(slots=True)
class ContextPack:
    summary: str
    compact_context: str
    sources: list[dict[str, str]]
    hit_count: int
    profile: str
    domain: str
    status: str
    ranking_notes: list[str]
    index_version: str = ""
    corpus_fingerprint: str = ""
    storage_path: str = ""
    retrieval_route: str = ""
    embedding_model_id: str = ""
    degradation_mode: str = ""
    dense_index_build_action: str = ""
    dense_rebuild_reason: str | None = None
    dense_artifact_validity: str = ""
    embedding_reason_codes: tuple[str, ...] = field(default_factory=tuple)
    embedding_index_version: str = ""
    embedding_cache_dir_identity: str | None = None

PROFILE_VERSIONS = {
    "runtime_turn_support": "runtime_profile_v2",
    "writers_review": "writers_profile_v2",
    "improvement_eval": "improvement_profile_v2",
}

SEMANTIC_CANON = {
    "argument": "conflict",
    "argue": "conflict",
    "argued": "conflict",
    "dispute": "conflict",
    "fight": "conflict",
    "fighting": "conflict",
    "chaos": "escalation",
    "chaotic": "escalation",
    "collapse": "escalation",
    "escalates": "escalation",
    "escalate": "escalation",
    "families": "family",
    "parents": "family",
    "dinner": "confrontation",
    "civility": "social_norm",
    "manners": "social_norm",
    "canon": "authoritative",
    "published": "authoritative",
    "tension": "conflict",
    "strained": "conflict",
}

SEMANTIC_EXPANSIONS = {
    "conflict": ("dispute", "argument", "fight"),
    "escalation": ("chaos", "collapse", "intensify"),
    "confrontation": ("dinner", "encounter"),
    "social_norm": ("civility", "manners"),
    "authoritative": ("canon", "published"),
}

PROFILE_CONTENT_BOOSTS: dict[str, dict[ContentClass, float]] = {
    "runtime_turn_support": {
        ContentClass.AUTHORED_MODULE: 1.4,
        ContentClass.RUNTIME_PROJECTION: 0.8,
        ContentClass.CHARACTER_PROFILE: 0.5,
        ContentClass.TRANSCRIPT: 0.2,
        ContentClass.POLICY_GUIDELINE: 0.6,
    },
    "writers_review": {
        ContentClass.AUTHORED_MODULE: 1.0,
        ContentClass.REVIEW_NOTE: 0.9,
        ContentClass.POLICY_GUIDELINE: 0.7,
        ContentClass.CHARACTER_PROFILE: 0.4,
        ContentClass.TRANSCRIPT: 0.2,
    },
    "improvement_eval": {
        ContentClass.EVALUATION_ARTIFACT: 1.2,
        ContentClass.REVIEW_NOTE: 0.6,
        ContentClass.TRANSCRIPT: 0.6,
        ContentClass.AUTHORED_MODULE: 0.6,
        ContentClass.POLICY_GUIDELINE: 0.4,
    },
}

PROFILE_CANONICAL_WEIGHT = {
    "runtime_turn_support": 0.8,
    "writers_review": 0.45,
    "improvement_eval": 0.3,
}

DOMAIN_DEFAULT_PROFILE = {
    RetrievalDomain.RUNTIME: "runtime_turn_support",
    RetrievalDomain.WRITERS_ROOM: "writers_review",
    RetrievalDomain.IMPROVEMENT: "improvement_eval",
}


def _raw_tokens(text: str) -> list[str]:
    return [token for token in re.findall(r"[a-z0-9_]+", text.lower()) if len(token) >= 3]


def _normalize_token(token: str) -> str:
    normalized = token.strip().lower()
    if not normalized:
        return normalized
    if normalized in SEMANTIC_CANON:
        return SEMANTIC_CANON[normalized]
    for suffix in ("ing", "ed", "es", "s"):
        if normalized.endswith(suffix) and len(normalized) >= len(suffix) + 3:
            candidate = normalized[: -len(suffix)]
            if candidate in SEMANTIC_CANON:
                return SEMANTIC_CANON[candidate]
            normalized = candidate
            break
    return SEMANTIC_CANON.get(normalized, normalized)


def _build_semantic_terms(text: str) -> dict[str, float]:
    terms: dict[str, float] = {}
    tokens = [_normalize_token(token) for token in _raw_tokens(text)]
    tokens = [token for token in tokens if len(token) >= 3]
    for token in tokens:
        terms[token] = terms.get(token, 0.0) + 1.0
        for related in SEMANTIC_EXPANSIONS.get(token, ()):
            terms[related] = terms.get(related, 0.0) + 0.35
    for left, right in zip(tokens, tokens[1:]):
        bigram = f"{left}_{right}"
        terms[bigram] = terms.get(bigram, 0.0) + 0.25
    return terms


def _apply_sparse_vector_weights(chunks: list[CorpusChunk]) -> None:
    if not chunks:
        return
    document_frequency: dict[str, int] = {}
    for chunk in chunks:
        for term in chunk.semantic_terms.keys():
            document_frequency[term] = document_frequency.get(term, 0) + 1
    total_docs = float(len(chunks))
    for chunk in chunks:
        weighted_terms: dict[str, float] = {}
        for term, tf in chunk.semantic_terms.items():
            idf = 1.0 + math.log((1.0 + total_docs) / (1.0 + float(document_frequency.get(term, 0))))
            weighted_terms[term] = float(tf) * idf
        norm = math.sqrt(sum(weight * weight for weight in weighted_terms.values()))
        chunk.semantic_terms = weighted_terms
        chunk.term_norm = norm


def _cosine_similarity(query_terms: dict[str, float], query_norm: float, chunk: CorpusChunk) -> float:
    if query_norm <= 0 or chunk.term_norm <= 0:
        return 0.0
    dot = 0.0
    for term, query_weight in query_terms.items():
        dot += query_weight * chunk.semantic_terms.get(term, 0.0)
    if dot <= 0:
        return 0.0
    return dot / (query_norm * chunk.term_norm)


def _profile_hybrid_weights(profile_name: str, domain: RetrievalDomain) -> tuple[float, float]:
    default_prof = DOMAIN_DEFAULT_PROFILE[domain]
    key = profile_name or default_prof
    return PROFILE_HYBRID_WEIGHTS.get(key, PROFILE_HYBRID_WEIGHTS.get(default_prof, (HYBRID_DENSE_WEIGHT, HYBRID_SPARSE_WEIGHT)))


def _hybrid_core_initial(
    dense_sim: float,
    sparse_sim: float,
    *,
    use_hybrid: bool,
    w_dense: float,
    w_sparse: float,
) -> float:
    """Initial hybrid core: weighted blend plus an explicit weak-dense rescue rule."""
    if not use_hybrid:
        return sparse_sim
    linear = w_dense * dense_sim + w_sparse * sparse_sim
    if dense_sim < HYBRID_DENSE_WEAK_THRESHOLD and sparse_sim > HYBRID_SPARSE_STRONG_THRESHOLD:
        rescue = HYBRID_WEAK_DENSE_SPARSE_EMPHASIS * sparse_sim + (1.0 - HYBRID_WEAK_DENSE_SPARSE_EMPHASIS) * dense_sim
        return max(linear, rescue)
    return linear


def _rerank_agreement_bonus(dense_sim: float, sparse_sim: float, *, use_hybrid: bool) -> float:
    """Single-stage dense/sparse agreement signal (rerank only)."""
    if not use_hybrid:
        return 0.0
    if dense_sim < RERANK_AGREEMENT_MIN_SIGNAL or sparse_sim < RERANK_AGREEMENT_MIN_SIGNAL:
        return 0.0
    return RERANK_AGREEMENT_BONUS_CAP * min(dense_sim, sparse_sim)


def _normalize_for_dup(text: str) -> str:
    return " ".join(text.lower().split())


def _char_trigram_jaccard(a: str, b: str) -> float:
    def trigrams(s: str) -> set[str]:
        s = _normalize_for_dup(s)
        if len(s) < 3:
            return {s} if s else set()
        return {s[i : i + 3] for i in range(len(s) - 2)}

    ta, tb = trigrams(a), trigrams(b)
    if not ta and not tb:
        return 1.0
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


@dataclass(slots=True)
class _ScoredCandidate:
    chunk_index: int
    chunk: CorpusChunk
    dense_sim: float
    sparse_sim: float
    hybrid_core: float
    initial_score: float
    initial_reason: str
    module_match: bool
    scene_match: bool


def _pool_size(max_chunks: int) -> int:
    k = max(1, max_chunks)
    return min(RERANK_POOL_CAP, max(RERANK_POOL_MIN, k * RERANK_POOL_FACTOR))


def _pool_has_strong_authored_for_module(pool: list[_ScoredCandidate], module_id: str | None) -> bool:
    if not module_id:
        return False
    for c in pool:
        if c.chunk.content_class != ContentClass.AUTHORED_MODULE:
            continue
        if c.chunk.canonical_priority < 3:
            continue
        if c.chunk.module_id == module_id:
            return True
    return False


def _rerank_adjustments(
    cand: _ScoredCandidate,
    *,
    profile_name: str,
    request: RetrievalRequest,
    pool: list[_ScoredCandidate],
    use_hybrid: bool,
    strong_authored_for_module: bool,
) -> tuple[float, list[str]]:
    """Additive rerank deltas; inspectable string fragments."""
    delta = 0.0
    parts: list[str] = []
    cc = cand.chunk.content_class
    mod_ex = RERANK_MODULE_MATCH_EXTRA.get(
        profile_name,
        RERANK_MODULE_MATCH_EXTRA[DOMAIN_DEFAULT_PROFILE[request.domain]],
    )
    if request.module_id and cand.module_match:
        delta += mod_ex
        parts.append(f"rerank_module_extra={mod_ex:.2f}")

    agr = _rerank_agreement_bonus(cand.dense_sim, cand.sparse_sim, use_hybrid=use_hybrid)
    if agr > 0:
        delta += agr
        parts.append(f"rerank_agreement={agr:.3f}")

    if profile_name == "runtime_turn_support":
        if cc in (ContentClass.TRANSCRIPT, ContentClass.RUNTIME_PROJECTION) and strong_authored_for_module:
            pen = 0.95
            delta -= pen
            parts.append(f"runtime_clutter_penalty=-{pen:.2f}")
        if cc == ContentClass.AUTHORED_MODULE and cand.chunk.canonical_priority >= 3:
            b = 0.18
            delta += b
            parts.append(f"runtime_canonical_rerank=+{b:.2f}")
    elif profile_name == "writers_review":
        if cc == ContentClass.REVIEW_NOTE:
            b = 0.32
            delta += b
            parts.append(f"writers_review_boost=+{b:.2f}")
        if cc == ContentClass.TRANSCRIPT:
            b = 0.14
            delta += b
            parts.append(f"writers_transcript_boost=+{b:.2f}")
    elif profile_name == "improvement_eval":
        if cc == ContentClass.EVALUATION_ARTIFACT:
            b = 0.52
            delta += b
            parts.append(f"improvement_eval_boost=+{b:.2f}")
        elif cc == ContentClass.REVIEW_NOTE:
            b = 0.38
            delta += b
            parts.append(f"improvement_review_boost=+{b:.2f}")
        elif cc == ContentClass.TRANSCRIPT:
            b = 0.22
            delta += b
            parts.append(f"improvement_transcript_boost=+{b:.2f}")

    # Redundancy: penalize near-duplicates of higher initial-scoring pool members.
    higher = [p for p in pool if p.initial_score > cand.initial_score + 1e-9]
    if higher:
        best_j = max(_char_trigram_jaccard(cand.chunk.text, h.chunk.text) for h in higher[:12])
        if best_j >= 0.87:
            pen = 0.38 + 0.4 * (best_j - 0.87) / (1.0 - 0.87)
            delta -= pen
            parts.append(f"rerank_redundancy=-{pen:.2f}")

    return delta, parts


def _dedup_select(
    ordered: list[tuple[float, _ScoredCandidate, list[str]]],
    *,
    max_chunks: int,
    profile_name: str,
) -> tuple[list[tuple[float, _ScoredCandidate, list[str]]], list[str]]:
    """Greedy keep by descending rerank score; drop near-duplicates deterministically."""
    kept: list[tuple[float, _ScoredCandidate, list[str]]] = []
    notes: list[str] = []
    drop_thr = DUP_TRIGRAM_JACCARD_DROP
    src_thr = DUP_SAME_SOURCE_JACCARD_DROP
    if profile_name == "improvement_eval":
        # Allow slightly more overlap before dropping (eval workflows may repeat phrasing).
        drop_thr = max(drop_thr, DUP_IMPROVEMENT_RELAXATION)
    for rerank_score, cand, rparts in ordered:
        if len(kept) >= max(1, max_chunks):
            break
        dup_reason = None
        for ks, kcand, _ in kept:
            j = _char_trigram_jaccard(cand.chunk.text, kcand.chunk.text)
            if j >= drop_thr:
                dup_reason = f"dup_trigram_jaccard={j:.2f}>={drop_thr:.2f}"
                break
            if cand.chunk.source_path == kcand.chunk.source_path and j >= src_thr:
                relax = (
                    profile_name == "improvement_eval"
                    and cand.chunk.content_class == ContentClass.EVALUATION_ARTIFACT
                )
                if not relax:
                    dup_reason = f"dup_same_source_jaccard={j:.2f}>={src_thr:.2f}"
                    break
        if dup_reason:
            notes.append(f"dup_suppressed chunk_id={cand.chunk.chunk_id} ({dup_reason})")
            continue
        kept.append((rerank_score, cand, rparts))
    return kept, notes


def _pack_role_for_hit(
    *,
    profile: str,
    canonical_priority: int,
    content_class: ContentClass,
) -> str:
    if profile == "runtime_turn_support":
        if content_class == ContentClass.AUTHORED_MODULE and canonical_priority >= 3:
            return "canonical_evidence"
        if content_class == ContentClass.POLICY_GUIDELINE:
            return "policy_evidence"
        return "supporting_context"
    if profile == "improvement_eval":
        if content_class in (ContentClass.EVALUATION_ARTIFACT, ContentClass.REVIEW_NOTE):
            return "evaluative_evidence"
        return "supporting_context"
    if profile == "writers_review":
        if content_class == ContentClass.AUTHORED_MODULE:
            return "authored_context"
        if content_class == ContentClass.REVIEW_NOTE:
            return "review_context"
        return "supporting_context"
    return "supporting_context"


def _pack_sort_key(hit: RetrievalHit, profile: str) -> tuple[int, float, str]:
    """Order hits for compact_context: lower tuple sorts first."""
    tier_order = {
        "canonical_evidence": 0,
        "policy_evidence": 1,
        "evaluative_evidence": 0,
        "authored_context": 0,
        "review_context": 1,
        "supporting_context": 2,
    }
    role = hit.pack_role or "supporting_context"
    return (tier_order.get(role, 3), -hit.score, hit.chunk_id)


_MODULE_PATH = re.compile(r"(?i)^content/modules/([^/]+)/")
_PUBLISHED_MODULE_PATH = re.compile(r"(?i)^content/published/([^/]+)/")


def _infer_module_id(repo_root: Path, file: Path) -> str | None:
    """Resolve module_id from conventional paths; flat ``content/<stem>.md`` uses file stem."""
    try:
        rel = file.relative_to(repo_root).as_posix()
    except ValueError:
        return None
    m = _MODULE_PATH.match(rel)
    if m:
        return m.group(1)
    m = _PUBLISHED_MODULE_PATH.match(rel)
    if m:
        return m.group(1)
    parts = Path(rel).parts
    if len(parts) == 2 and parts[0].lower() == "content":
        name = parts[1]
        stem = Path(name).stem
        if stem and stem.lower() not in {"modules", "published"}:
            return stem
    return None


def _detect_content_class(path: Path) -> ContentClass | None:
    normalized = str(path).replace("\\", "/").lower()
    if "/content/" in normalized:
        return ContentClass.AUTHORED_MODULE
    if "/var/runs/" in normalized:
        return ContentClass.TRANSCRIPT
    if "/docs/architecture/" in normalized:
        return ContentClass.POLICY_GUIDELINE
    if "/docs/reports/" in normalized:
        filename = path.name.lower()
        if "eval" in filename or "acceptance" in filename:
            return ContentClass.EVALUATION_ARTIFACT
        return ContentClass.REVIEW_NOTE
    if "projection" in normalized:
        return ContentClass.RUNTIME_PROJECTION
    if "character" in normalized:
        return ContentClass.CHARACTER_PROFILE
    return None


class RagIngestionPipeline:
    def __init__(self, *, chunk_size: int = 600, overlap: int = 120, max_sources: int = 250) -> None:
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.max_sources = max_sources

    def _source_patterns(self) -> list[str]:
        return [
            "content/**/*.md",
            "content/**/*.json",
            "content/**/*.yml",
            "content/**/*.yaml",
            "docs/architecture/**/*.md",
            "docs/reports/**/*.md",
            "world-engine/app/var/runs/**/*.json",
        ]

    def _select_sources(self, repo_root: Path) -> list[Path]:
        files: list[Path] = []
        for pattern in self._source_patterns():
            files.extend(repo_root.glob(pattern))
        return sorted({file for file in files if file.is_file()})[: self.max_sources]

    def compute_source_fingerprint(self, repo_root: Path) -> str:
        selected = self._select_sources(repo_root)
        return self._fingerprint_for_selected(repo_root, selected)

    @staticmethod
    def _fingerprint_for_selected(repo_root: Path, selected: list[Path]) -> str:
        digest = hashlib.sha256()
        for file in selected:
            rel = file.relative_to(repo_root).as_posix()
            stat = file.stat()
            digest.update(f"{rel}:{stat.st_size}:{stat.st_mtime_ns}".encode("utf-8"))
        return digest.hexdigest()

    @staticmethod
    def _canonical_priority(path: Path, content_class: ContentClass) -> int:
        normalized = path.as_posix().lower()
        if content_class == ContentClass.AUTHORED_MODULE:
            if "/content/published/" in normalized:
                return 4
            if "/content/modules/" in normalized:
                return 3
            return 2
        if "/content/published/" in normalized or "canonical" in normalized:
            return 2
        if content_class == ContentClass.POLICY_GUIDELINE:
            return 1
        return 0

    def build_corpus(self, repo_root: Path, *, source_fingerprint: str | None = None) -> InMemoryRetrievalCorpus:
        selected = self._select_sources(repo_root)
        chunks: list[CorpusChunk] = []
        for file in selected:
            content_class = _detect_content_class(file)
            if content_class is None:
                continue
            text = file.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue
            source_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
            source_version = f"sha256:{source_hash[:16]}"
            module_id = _infer_module_id(repo_root, file)
            canonical_priority = self._canonical_priority(file, content_class)
            for index, chunk_text in enumerate(self._chunk_text(text)):
                if not chunk_text.strip():
                    continue
                rel_path = file.relative_to(repo_root).as_posix()
                chunks.append(
                    CorpusChunk(
                        chunk_id=f"{rel_path}@{source_version}::chunk_{index}",
                        source_path=rel_path,
                        source_name=file.name,
                        content_class=content_class,
                        text=chunk_text.strip(),
                        module_id=module_id,
                        source_version=source_version,
                        source_hash=source_hash,
                        canonical_priority=canonical_priority,
                        semantic_terms=_build_semantic_terms(chunk_text),
                    )
                )
        _apply_sparse_vector_weights(chunks)
        corpus_fingerprint = source_fingerprint or self._fingerprint_for_selected(repo_root, selected)
        return InMemoryRetrievalCorpus(
            chunks=chunks,
            built_at=datetime.now(timezone.utc).isoformat(),
            source_count=len(selected),
            index_version=INDEX_VERSION,
            corpus_fingerprint=corpus_fingerprint,
            storage_path="",
            profile_versions=dict(PROFILE_VERSIONS),
        )

    def _chunk_text(self, text: str) -> list[str]:
        if len(text) <= self.chunk_size:
            return [text]
        chunks: list[str] = []
        start = 0
        step = max(1, self.chunk_size - self.overlap)
        while start < len(text):
            end = start + self.chunk_size
            chunks.append(text[start:end])
            start += step
        return chunks


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


def _load_corpus_embedding_index(corpus: InMemoryRetrievalCorpus, corpus_json: Path) -> DenseIndexLoadResult:
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
    corpus: InMemoryRetrievalCorpus,
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


def _ensure_corpus_embedding_index(corpus: InMemoryRetrievalCorpus, corpus_json: Path) -> CorpusEmbeddingIndex | None:
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


class ContextRetriever:
    def __init__(
        self,
        corpus: InMemoryRetrievalCorpus,
        *,
        embedding_index: CorpusEmbeddingIndex | None = None,
        embedding_model_id: str = "",
    ) -> None:
        self.corpus = corpus
        self._embedding_index = embedding_index
        self._embedding_model_id = embedding_model_id or (embedding_index.model_id if embedding_index else "")

    def _corpus_trace(self) -> tuple[str, str, str]:
        corpus = self.corpus
        return corpus.index_version, corpus.corpus_fingerprint, corpus.storage_path or ""

    def _embedding_ready(self) -> bool:
        if self._embedding_index is None:
            return False
        return self._embedding_index.vectors.shape[0] == len(self.corpus.chunks)

    def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        if request.domain not in DOMAIN_CONTENT_ACCESS:
            raise RetrievalDomainError(f"Unknown retrieval domain: {request.domain}")
        trace = self._corpus_trace()
        c = self.corpus
        emb_idx_ver = c.rag_embedding_index_version or EMBEDDING_INDEX_VERSION
        emb_cache_id = c.rag_embedding_cache_dir_identity
        dense_action = c.rag_dense_index_build_action
        dense_validity = c.rag_dense_artifact_validity
        dense_rebuild_reason = c.rag_dense_rebuild_reason
        backend_code = c.rag_embedding_backend_primary_code

        if not self.corpus.chunks:
            return RetrievalResult(
                request=request,
                status=RetrievalStatus.DEGRADED,
                hits=[],
                ranking_notes=[
                    "retrieval_corpus_empty",
                    f"degradation_mode={RetrievalDegradationMode.CORPUS_EMPTY.value}",
                ],
                error="retrieval_corpus_empty",
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                retrieval_route="",
                embedding_model_id="",
                degradation_mode=RetrievalDegradationMode.CORPUS_EMPTY.value,
                dense_index_build_action=dense_action,
                dense_rebuild_reason=dense_rebuild_reason,
                dense_artifact_validity=dense_validity,
                embedding_reason_codes=c.rag_dense_load_reason_codes,
                embedding_index_version=emb_idx_ver,
                embedding_cache_dir_identity=emb_cache_id,
            )

        use_hybrid = self._embedding_ready() and not request.use_sparse_only and not embeddings_disabled_by_env()
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
        embedding_mid = self._embedding_model_id if use_hybrid else ""

        if request.use_sparse_only:
            degradation_mode = RetrievalDegradationMode.HYBRID_OK.value
        elif use_hybrid:
            degradation_mode = RetrievalDegradationMode.HYBRID_OK.value
        elif embeddings_disabled_by_env():
            degradation_mode = RetrievalDegradationMode.SPARSE_FALLBACK_NO_BACKEND.value
        elif query_encode_failed:
            degradation_mode = RetrievalDegradationMode.SPARSE_FALLBACK_ENCODE_FAILURE.value
        elif dense_validity == "uncommitted_vectors_only":
            degradation_mode = RetrievalDegradationMode.DEGRADED_PARTIAL_PERSISTENCE.value
        elif dense_validity == "partial_write_failure":
            degradation_mode = RetrievalDegradationMode.DEGRADED_PARTIAL_PERSISTENCE.value
        elif backend_code != "embedding_backend_ok":
            degradation_mode = RetrievalDegradationMode.SPARSE_FALLBACK_NO_BACKEND.value
        else:
            degradation_mode = RetrievalDegradationMode.SPARSE_FALLBACK_INVALID_OR_MISSING_DENSE_INDEX.value

        allowed_classes = DOMAIN_CONTENT_ACCESS[request.domain]
        query_terms = _build_semantic_terms(request.query)
        query_norm = math.sqrt(sum(weight * weight for weight in query_terms.values()))
        profile_name = request.profile or DOMAIN_DEFAULT_PROFILE[request.domain]
        profile_boosts = PROFILE_CONTENT_BOOSTS.get(
            profile_name,
            PROFILE_CONTENT_BOOSTS[DOMAIN_DEFAULT_PROFILE[request.domain]],
        )
        canonical_weight = PROFILE_CANONICAL_WEIGHT.get(
            profile_name,
            PROFILE_CANONICAL_WEIGHT[DOMAIN_DEFAULT_PROFILE[request.domain]],
        )
        w_dense, w_sparse = _profile_hybrid_weights(profile_name, request.domain)

        prefix_notes: list[str] = [
            f"retrieval_route={retrieval_route}",
            f"degradation_mode={degradation_mode}",
            f"dense_index_build_action={dense_action}",
            f"dense_artifact_validity={dense_validity}",
        ]
        if dense_rebuild_reason:
            prefix_notes.append(f"dense_rebuild_reason={dense_rebuild_reason}")
        if use_hybrid and embedding_mid:
            prefix_notes.append(f"embedding_model_id={embedding_mid}")
        if query_encode_failed and query_enc_codes:
            prefix_notes.append("embedding_query_encode_failed=" + ",".join(query_enc_codes))
        elif query_encode_failed:
            prefix_notes.append("embedding_query_encode_failed")

        quality_notes: list[str] = [
            f"retrieval_pipeline_version={RETRIEVAL_PIPELINE_VERSION}",
            f"hybrid_v2_weights_dense={w_dense:.2f}_sparse={w_sparse:.2f}",
        ]

        candidates: list[_ScoredCandidate] = []
        for chunk_index, chunk in enumerate(self.corpus.chunks):
            if chunk.content_class not in allowed_classes:
                continue
            sparse_sim = _cosine_similarity(query_terms, query_norm, chunk)
            dense_sim = 0.0
            if use_hybrid and query_vec is not None:
                dense_sim = float(np.dot(query_vec, self._embedding_index.vectors[chunk_index]))
                dense_sim = max(0.0, min(1.0, dense_sim))
            hybrid_core = _hybrid_core_initial(
                dense_sim,
                sparse_sim,
                use_hybrid=use_hybrid,
                w_dense=w_dense,
                w_sparse=w_sparse,
            )
            score = hybrid_core * HYBRID_CORE_SCALE
            reasons: list[str] = []
            if use_hybrid and query_vec is not None:
                reasons.append(
                    f"hybrid_core={hybrid_core:.3f}; dense_cos={dense_sim:.3f}; sparse_cos={sparse_sim:.3f}"
                )
            elif sparse_sim > 0:
                reasons.append(f"semantic_similarity={sparse_sim:.3f}")
            profile_boost = profile_boosts.get(chunk.content_class, 0.0)
            if profile_boost:
                score += profile_boost
                reasons.append(f"profile_boost={profile_boost:.2f}")
            canonical_boost = canonical_weight * float(chunk.canonical_priority)
            if canonical_boost:
                score += canonical_boost
                reasons.append(f"canonical_boost={canonical_boost:.2f}")
            module_match = bool(
                request.module_id and chunk.module_id and request.module_id == chunk.module_id
            )
            scene_match = bool(request.scene_id and request.scene_id in chunk.text)
            if module_match:
                score += INITIAL_MODULE_MATCH_BOOST
                reasons.append(f"module_match_boost={INITIAL_MODULE_MATCH_BOOST:.2f}")
            if scene_match:
                score += INITIAL_SCENE_HINT_BOOST
                reasons.append(f"scene_hint_boost={INITIAL_SCENE_HINT_BOOST:.2f}")
            if score <= 0:
                continue
            candidates.append(
                _ScoredCandidate(
                    chunk_index=chunk_index,
                    chunk=chunk,
                    dense_sim=dense_sim,
                    sparse_sim=sparse_sim,
                    hybrid_core=hybrid_core,
                    initial_score=score,
                    initial_reason="; ".join(reasons) or "semantic_match",
                    module_match=module_match,
                    scene_match=scene_match,
                )
            )

        candidates.sort(key=lambda x: (x.initial_score, x.chunk.chunk_id), reverse=True)
        pool_n = _pool_size(request.max_chunks)
        pool = candidates[:pool_n]
        quality_notes.append(f"rerank_pool_size={len(pool)}")
        strong_authored = _pool_has_strong_authored_for_module(pool, request.module_id)

        reranked: list[tuple[float, _ScoredCandidate, list[str]]] = []
        for cand in pool:
            rdelta, rparts = _rerank_adjustments(
                cand,
                profile_name=profile_name,
                request=request,
                pool=pool,
                use_hybrid=use_hybrid,
                strong_authored_for_module=strong_authored,
            )
            rerank_score = cand.initial_score + rdelta
            merged_parts = list(rparts)
            if rdelta != 0:
                merged_parts.insert(0, f"rerank_delta={rdelta:+.3f}")
            reranked.append((rerank_score, cand, merged_parts))

        reranked.sort(key=lambda x: (x[0], x[1].chunk.chunk_id), reverse=True)
        selected_tuples, dup_notes = _dedup_select(
            reranked,
            max_chunks=request.max_chunks,
            profile_name=profile_name,
        )
        quality_notes.extend(dup_notes[:8])
        if len(dup_notes) > 8:
            quality_notes.append(f"dup_suppressed_more={len(dup_notes) - 8}")

        hits: list[RetrievalHit] = []
        for rerank_score, cand, rparts in selected_tuples:
            reason_core = cand.initial_reason
            if rparts:
                reason_core = reason_core + " | " + "; ".join(rparts)
            pack_role = _pack_role_for_hit(
                profile=profile_name,
                canonical_priority=cand.chunk.canonical_priority,
                content_class=cand.chunk.content_class,
            )
            why = (
                f"initial={cand.initial_score:.2f} final={rerank_score:.2f}; "
                f"{pack_role.replace('_', ' ')}"
            )
            hits.append(
                RetrievalHit(
                    chunk_id=cand.chunk.chunk_id,
                    source_path=cand.chunk.source_path,
                    source_name=cand.chunk.source_name,
                    content_class=cand.chunk.content_class.value,
                    source_version=cand.chunk.source_version,
                    score=rerank_score,
                    snippet=cand.chunk.text[:400],
                    selection_reason=reason_core,
                    pack_role=pack_role,
                    why_selected=why,
                )
            )

        if not hits:
            notes = prefix_notes + quality_notes + ["no_ranked_hits_for_query"]
            return RetrievalResult(
                request=request,
                status=RetrievalStatus.FALLBACK,
                hits=[],
                ranking_notes=notes,
                error="no_ranked_hits",
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                retrieval_route=retrieval_route,
                embedding_model_id=embedding_mid,
                degradation_mode=degradation_mode,
                dense_index_build_action=dense_action,
                dense_rebuild_reason=dense_rebuild_reason,
                dense_artifact_validity=dense_validity,
                embedding_reason_codes=query_enc_codes if query_encode_failed else c.rag_dense_load_reason_codes,
                embedding_index_version=emb_idx_ver,
                embedding_cache_dir_identity=emb_cache_id,
            )
        detail_lines = [
            f"{h.source_path} score={h.score:.2f} pack_role={h.pack_role} ({h.selection_reason})"
            for h in hits
        ]
        ranking_notes = prefix_notes + quality_notes + detail_lines
        return RetrievalResult(
            request=request,
            status=RetrievalStatus.OK,
            hits=hits,
            ranking_notes=ranking_notes,
            error=None,
            index_version=trace[0],
            corpus_fingerprint=trace[1],
            storage_path=trace[2],
            retrieval_route=retrieval_route,
            embedding_model_id=embedding_mid,
            degradation_mode=degradation_mode,
            dense_index_build_action=dense_action,
            dense_rebuild_reason=dense_rebuild_reason,
            dense_artifact_validity=dense_validity,
            embedding_reason_codes=query_enc_codes if query_encode_failed else (),
            embedding_index_version=emb_idx_ver,
            embedding_cache_dir_identity=emb_cache_id,
        )


class ContextPackAssembler:
    def assemble(self, result: RetrievalResult) -> ContextPack:
        trace = (result.index_version, result.corpus_fingerprint, result.storage_path)
        if not result.hits:
            return ContextPack(
                summary="No retrieval context available.",
                compact_context="",
                sources=[],
                hit_count=0,
                profile=result.request.profile,
                domain=result.request.domain.value,
                status=result.status.value,
                ranking_notes=result.ranking_notes,
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                retrieval_route=result.retrieval_route,
                embedding_model_id=result.embedding_model_id,
                degradation_mode=result.degradation_mode,
                dense_index_build_action=result.dense_index_build_action,
                dense_rebuild_reason=result.dense_rebuild_reason,
                dense_artifact_validity=result.dense_artifact_validity,
                embedding_reason_codes=result.embedding_reason_codes,
                embedding_index_version=result.embedding_index_version,
                embedding_cache_dir_identity=result.embedding_cache_dir_identity,
            )
        profile = result.request.profile or DOMAIN_DEFAULT_PROFILE[result.request.domain]
        ordered_hits = sorted(result.hits, key=lambda h: _pack_sort_key(h, profile))

        def _section_title(role: str) -> str | None:
            if profile == "runtime_turn_support":
                if role == "canonical_evidence":
                    return "Canonical evidence"
                if role == "policy_evidence":
                    return "Policy evidence"
                if role == "supporting_context":
                    return "Supporting context"
            elif profile == "improvement_eval":
                if role == "evaluative_evidence":
                    return "Evaluative evidence"
                if role == "supporting_context":
                    return "Supporting context"
            elif profile == "writers_review":
                if role == "authored_context":
                    return "Authored context"
                if role == "review_context":
                    return "Review context"
                if role == "supporting_context":
                    return "Supporting context"
            return None

        lines: list[str] = [
            f"Retrieved context (profile={profile}, pipeline={RETRIEVAL_PIPELINE_VERSION}):",
        ]
        sources: list[dict[str, str]] = []
        current_section: str | None = None
        ordinal = 0
        for hit in ordered_hits:
            role = hit.pack_role or "supporting_context"
            title = _section_title(role)
            if title and title != current_section:
                current_section = title
                lines.append(f"--- {title} ---")
            ordinal += 1
            snippet = hit.snippet.strip()
            if len(snippet) > 320:
                snippet = snippet[:317].rstrip() + "..."
            lines.append(f"{ordinal}. [{hit.source_name}] ({role}) {snippet}")
            sources.append(
                {
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "snippet": snippet,
                    "content_class": hit.content_class,
                    "selection_reason": hit.selection_reason,
                    "source_version": hit.source_version,
                    "score": f"{hit.score:.4f}",
                    "pack_role": hit.pack_role,
                    "why_selected": hit.why_selected,
                }
            )
        lines.append("context_pack_order=workflow_sections_then_ordinal")
        return ContextPack(
            summary=(
                f"Retrieved {len(result.hits)} chunks for profile={profile} "
                f"({RETRIEVAL_PIPELINE_VERSION})."
            ),
            compact_context="\n".join(lines),
            sources=sources,
            hit_count=len(result.hits),
            profile=result.request.profile,
            domain=result.request.domain.value,
            status=result.status.value,
            ranking_notes=result.ranking_notes,
            index_version=trace[0],
            corpus_fingerprint=trace[1],
            storage_path=trace[2],
            retrieval_route=result.retrieval_route,
            embedding_model_id=result.embedding_model_id,
            degradation_mode=result.degradation_mode,
            dense_index_build_action=result.dense_index_build_action,
            dense_rebuild_reason=result.dense_rebuild_reason,
            dense_artifact_validity=result.dense_artifact_validity,
            embedding_reason_codes=result.embedding_reason_codes,
            embedding_index_version=result.embedding_index_version,
            embedding_cache_dir_identity=result.embedding_cache_dir_identity,
        )


def build_runtime_retriever(repo_root: Path) -> tuple[ContextRetriever, ContextPackAssembler, InMemoryRetrievalCorpus]:
    persistence_path = repo_root / ".wos" / "rag" / "runtime_corpus.json"
    pipeline = RagIngestionPipeline()
    fingerprint = pipeline.compute_source_fingerprint(repo_root)
    store = PersistentRagStore(persistence_path)
    cached = store.load(expected_fingerprint=fingerprint)
    if cached is not None:
        cached.storage_path = str(persistence_path)
        corpus = cached
    else:
        corpus = pipeline.build_corpus(repo_root, source_fingerprint=fingerprint)
        corpus.storage_path = str(persistence_path)
        store.save(corpus)
    emb_index = _ensure_corpus_embedding_index(corpus, persistence_path)
    model_id = emb_index.model_id if emb_index is not None else ""
    return ContextRetriever(corpus, embedding_index=emb_index, embedding_model_id=model_id), ContextPackAssembler(), corpus


@dataclass(slots=True)
class PersistentRagStore:
    storage_path: Path

    def load(self, *, expected_fingerprint: str) -> InMemoryRetrievalCorpus | None:
        if not self.storage_path.exists():
            return None
        try:
            payload = json.loads(self.storage_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        if not isinstance(payload, dict):
            return None
        if str(payload.get("index_version", "")) != INDEX_VERSION:
            return None
        if str(payload.get("corpus_fingerprint", "")) != expected_fingerprint:
            return None
        corpus = InMemoryRetrievalCorpus.from_dict(payload)
        corpus.storage_path = str(self.storage_path)
        return corpus

    def save(self, corpus: InMemoryRetrievalCorpus) -> None:
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = corpus.to_dict()
        payload["storage_path"] = str(self.storage_path)
        serialized = json.dumps(payload, ensure_ascii=True, indent=2)
        tmp_name: str | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w",
                encoding="utf-8",
                delete=False,
                dir=self.storage_path.parent,
                prefix=".rag_",
                suffix=".json",
            ) as tmp:
                tmp.write(serialized)
                tmp_name = tmp.name
            if tmp_name:
                os.replace(tmp_name, self.storage_path)
        except Exception:
            if tmp_name:
                try:
                    Path(tmp_name).unlink(missing_ok=True)
                except OSError:
                    pass
            raise
