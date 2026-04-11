"""Corpus chunk model, in-memory corpus container, and scored retrieval candidates (DS-003 stage 10)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone

from ai_stack.rag_constants import INDEX_VERSION
from ai_stack.rag_types import ContentClass


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
