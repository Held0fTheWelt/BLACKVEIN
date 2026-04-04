"""Project-scoped retrieval for World of Shadows (RAG layer C).

Hybrid retrieval (C1-next): when a local embedding index is present, queries are
scored with a weighted mix of dense cosine similarity (``fastembed`` / ONNX) and
the existing sparse semantic-term cosine. Canonical boosts, profile boosts, and
source attribution are unchanged. Without embeddings (missing dependency, env
disable, load failure, or query encode failure), the retriever uses the sparse
path only and records ``retrieval_route=sparse_fallback`` in ranking notes.

Persistence: JSON corpus under ``.wos/rag/runtime_corpus.json`` (``PersistentRagStore``)
plus optional ``runtime_embeddings.npz`` + ``runtime_embeddings.meta.json`` for
reproducible local dense indices. This remains a single-host dev-oriented design,
not a distributed vector database.
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

from wos_ai_stack.semantic_embedding import (
    EMBEDDING_INDEX_VERSION,
    EMBEDDING_MODEL_ID,
    embeddings_disabled_by_env,
    encode_query,
    encode_texts,
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

# Hybrid base score: dense + sparse cosine (both in ~[0, 1] for typical text matches).
HYBRID_DENSE_WEIGHT = 0.62
HYBRID_SPARSE_WEIGHT = 0.38


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


def _load_corpus_embedding_index(corpus: InMemoryRetrievalCorpus, corpus_json: Path) -> CorpusEmbeddingIndex | None:
    meta_path = _embedding_meta_path(corpus_json)
    npz_path = _embedding_npz_path(corpus_json)
    if not meta_path.is_file() or not npz_path.is_file():
        return None
    try:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if not isinstance(meta, dict):
        return None
    if str(meta.get("corpus_fingerprint", "")) != corpus.corpus_fingerprint:
        return None
    if str(meta.get("corpus_index_version", "")) != INDEX_VERSION:
        return None
    if str(meta.get("embedding_index_version", "")) != EMBEDDING_INDEX_VERSION:
        return None
    model_id = str(meta.get("embedding_model_id", ""))
    if model_id != EMBEDDING_MODEL_ID:
        return None
    n = int(meta.get("num_chunks", -1))
    if n != len(corpus.chunks):
        return None
    try:
        data = np.load(npz_path)
        vectors = data["vectors"]
    except Exception:
        return None
    if not isinstance(vectors, np.ndarray) or vectors.shape[0] != n:
        return None
    return CorpusEmbeddingIndex(vectors=vectors.astype(np.float32, copy=False), model_id=model_id)


def _save_corpus_embedding_index(
    corpus: InMemoryRetrievalCorpus,
    vectors: np.ndarray,
    corpus_json: Path,
) -> None:
    meta_path = _embedding_meta_path(corpus_json)
    npz_path = _embedding_npz_path(corpus_json)
    corpus_json.parent.mkdir(parents=True, exist_ok=True)
    meta = {
        "corpus_fingerprint": corpus.corpus_fingerprint,
        "corpus_index_version": INDEX_VERSION,
        "embedding_index_version": EMBEDDING_INDEX_VERSION,
        "embedding_model_id": EMBEDDING_MODEL_ID,
        "num_chunks": len(corpus.chunks),
    }
    tmp_meta: str | None = None
    tmp_npz: str | None = None
    try:
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
        with tempfile.NamedTemporaryFile(
            delete=False,
            dir=corpus_json.parent,
            prefix=".emb_vec_",
            suffix=".npz",
        ) as tmp:
            tmp_npz = tmp.name
        np.savez_compressed(tmp_npz, vectors=vectors.astype(np.float32))
        if tmp_meta:
            os.replace(tmp_meta, meta_path)
        if tmp_npz:
            os.replace(tmp_npz, npz_path)
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
    if embeddings_disabled_by_env():
        return None
    cached = _load_corpus_embedding_index(corpus, corpus_json)
    if cached is not None:
        return cached
    if not corpus.chunks:
        return None
    texts = [chunk.text for chunk in corpus.chunks]
    vectors = encode_texts(texts)
    if vectors is None:
        return None
    if vectors.shape[0] != len(corpus.chunks):
        return None
    _save_corpus_embedding_index(corpus, vectors, corpus_json)
    return CorpusEmbeddingIndex(vectors=vectors, model_id=EMBEDDING_MODEL_ID)


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
        if not self.corpus.chunks:
            return RetrievalResult(
                request=request,
                status=RetrievalStatus.DEGRADED,
                hits=[],
                ranking_notes=["retrieval_corpus_empty"],
                error="retrieval_corpus_empty",
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                retrieval_route="",
                embedding_model_id="",
            )

        use_hybrid = self._embedding_ready() and not request.use_sparse_only and not embeddings_disabled_by_env()
        query_vec: np.ndarray | None = None
        query_encode_failed = False
        if use_hybrid:
            query_vec = encode_query(request.query)
            if query_vec is None:
                use_hybrid = False
                query_encode_failed = True

        retrieval_route = "hybrid" if use_hybrid else "sparse_fallback"
        embedding_mid = self._embedding_model_id if use_hybrid else ""

        allowed_classes = DOMAIN_CONTENT_ACCESS[request.domain]
        query_terms = _build_semantic_terms(request.query)
        query_norm = math.sqrt(sum(weight * weight for weight in query_terms.values()))
        profile_name = request.profile or DOMAIN_DEFAULT_PROFILE[request.domain]
        profile_boosts = PROFILE_CONTENT_BOOSTS.get(profile_name, PROFILE_CONTENT_BOOSTS[DOMAIN_DEFAULT_PROFILE[request.domain]])
        canonical_weight = PROFILE_CANONICAL_WEIGHT.get(
            profile_name,
            PROFILE_CANONICAL_WEIGHT[DOMAIN_DEFAULT_PROFILE[request.domain]],
        )
        ranked: list[tuple[float, CorpusChunk, str]] = []
        prefix_notes: list[str] = [f"retrieval_route={retrieval_route}"]
        if use_hybrid and embedding_mid:
            prefix_notes.append(f"embedding_model_id={embedding_mid}")
        if query_encode_failed:
            prefix_notes.append("embedding_query_encode_failed")

        for chunk_index, chunk in enumerate(self.corpus.chunks):
            if chunk.content_class not in allowed_classes:
                continue
            semantic_score = _cosine_similarity(query_terms, query_norm, chunk)
            dense_sim = 0.0
            if use_hybrid and query_vec is not None:
                dense_sim = float(np.dot(query_vec, self._embedding_index.vectors[chunk_index]))
                dense_sim = max(0.0, min(1.0, dense_sim))
                hybrid_core = HYBRID_DENSE_WEIGHT * dense_sim + HYBRID_SPARSE_WEIGHT * semantic_score
            else:
                hybrid_core = semantic_score
            score = hybrid_core * 4.0
            reasons: list[str] = []
            if use_hybrid and query_vec is not None:
                reasons.append(
                    f"hybrid_core={hybrid_core:.3f}; dense_cos={dense_sim:.3f}; sparse_cos={semantic_score:.3f}"
                )
            elif semantic_score > 0:
                reasons.append(f"semantic_similarity={semantic_score:.3f}")
            profile_boost = profile_boosts.get(chunk.content_class, 0.0)
            if profile_boost:
                score += profile_boost
                reasons.append(f"profile_boost={profile_boost:.2f}")
            canonical_boost = canonical_weight * float(chunk.canonical_priority)
            if canonical_boost:
                score += canonical_boost
                reasons.append(f"canonical_boost={canonical_boost:.2f}")
            if request.module_id and chunk.module_id and request.module_id == chunk.module_id:
                score += 2.0
                reasons.append("module_match_boost=2")
            if request.scene_id and request.scene_id in chunk.text:
                score += 1.5
                reasons.append("scene_hint_boost=1.5")
            if score <= 0:
                continue
            ranked.append((score, chunk, "; ".join(reasons) or "semantic_match"))

        ranked.sort(key=lambda item: item[0], reverse=True)
        selected = ranked[: max(1, request.max_chunks)]
        hits = [
            RetrievalHit(
                chunk_id=chunk.chunk_id,
                source_path=chunk.source_path,
                source_name=chunk.source_name,
                content_class=chunk.content_class.value,
                source_version=chunk.source_version,
                score=score,
                snippet=chunk.text[:400],
                selection_reason=reason,
            )
            for score, chunk, reason in selected
        ]
        if not hits:
            notes = prefix_notes + ["no_ranked_hits_for_query"]
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
            )
        ranking_notes = prefix_notes + [f"{hit.source_path} score={hit.score:.2f} ({hit.selection_reason})" for hit in hits]
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
            )
        lines = ["Retrieved context (ranked):"]
        sources: list[dict[str, str]] = []
        for index, hit in enumerate(result.hits, start=1):
            lines.append(f"{index}. [{hit.source_name}] {hit.snippet}")
            sources.append(
                {
                    "chunk_id": hit.chunk_id,
                    "source_path": hit.source_path,
                    "content_class": hit.content_class,
                    "selection_reason": hit.selection_reason,
                    "source_version": hit.source_version,
                    "score": f"{hit.score:.4f}",
                }
            )
        return ContextPack(
            summary=f"Retrieved {len(result.hits)} chunks for profile={result.request.profile}.",
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
