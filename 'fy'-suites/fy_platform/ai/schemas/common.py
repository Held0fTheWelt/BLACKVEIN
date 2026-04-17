from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class SuiteRunRecord:
    run_id: str
    suite: str
    mode: str
    started_at: str
    ended_at: str | None
    workspace_root: str
    target_repo_root: str | None
    target_repo_id: str | None
    status: str


@dataclass(frozen=True)
class EvidenceRecord:
    evidence_id: str
    suite: str
    run_id: str
    kind: str
    source_uri: str
    ownership_zone: str
    content_hash: str
    mime_type: str
    deterministic: bool
    review_state: str
    created_at: str


@dataclass(frozen=True)
class ArtifactRecord:
    artifact_id: str
    suite: str
    run_id: str
    format: str
    role: str
    path: str
    created_at: str


@dataclass(frozen=True)
class EvidenceLink:
    src_id: str
    dst_id: str
    relation: str


@dataclass(frozen=True)
class RetrievalHit:
    chunk_id: str
    score_lexical: float
    score_semantic: float
    score_hybrid: float
    source_path: str
    excerpt: str


@dataclass(frozen=True)
class ContextPack:
    pack_id: str
    query: str
    suite_scope: list[str]
    audience: str
    hits: list[RetrievalHit]
    summary: str
    artifact_paths: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ModelRouteDecision:
    task_type: str
    selected_tier: str
    selected_model: str
    reason: str
    budget_class: str
    fallback_chain: list[str]


def to_jsonable(value: Any) -> Any:
    if hasattr(value, "__dataclass_fields__"):
        return {k: to_jsonable(v) for k, v in asdict(value).items()}
    if isinstance(value, list):
        return [to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): to_jsonable(v) for k, v in value.items()}
    return value
