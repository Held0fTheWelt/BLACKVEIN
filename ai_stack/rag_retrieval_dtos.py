"""Retrieval request/hit/result and context pack dataclasses (DS-003 optional: slim ``rag`` facade)."""

from __future__ import annotations

from dataclasses import dataclass, field

from ai_stack.rag_types import RetrievalDomain, RetrievalStatus


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
    source_evidence_lane: str = ""
    source_visibility_class: str = ""
    policy_note: str = ""
    profile_policy_influence: str = ""


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
