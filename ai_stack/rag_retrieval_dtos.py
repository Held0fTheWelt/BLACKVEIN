"""
Retrieval request/hit/result and context pack dataclasses (DS-003
optional: slim ``rag`` facade).

Also contains ``RuntimeRetrievalConfig`` — the resolved operator-governed
retrieval posture injected into ``RuntimeTurnGraphExecutor`` at build time.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from ai_stack.rag_types import RetrievalDomain, RetrievalStatus


@dataclass(slots=True)
class RuntimeRetrievalConfig:
    """Resolved operator-governed retrieval posture for a live turn.

    Constructed once at executor build time from ``governed_runtime_config``,
    passed to ``RuntimeTurnGraphExecutor``, read by ``_retrieve_context``.

    Defaults match the ``hybrid_dense_sparse`` posture so that an executor
    built without explicit config behaves identically to the previous
    hardcoded behaviour.
    """

    retrieval_execution_mode: str = "hybrid_dense_sparse"
    max_chunks: int = 4
    retrieval_profile: str = "runtime_turn_support"
    retrieval_min_score: float | None = None
    embeddings_enabled: bool = True

    @property
    def use_sparse_only(self) -> bool:
        """True when mode is sparse_only or embeddings_enabled is False."""
        return self.retrieval_execution_mode == "sparse_only" or not self.embeddings_enabled

    @property
    def retrieval_disabled(self) -> bool:
        """True when retrieval is intentionally disabled by config."""
        return self.retrieval_execution_mode == "disabled"


def retrieval_config_from_governed(governed_runtime_config: dict[str, Any] | None) -> RuntimeRetrievalConfig:
    """Extract ``RuntimeRetrievalConfig`` from the resolved governed config dict.

    Reads ``retrieval_execution_mode`` from the top-level key (set by
    bootstrap) and granular ``retrieval_settings`` sub-dict (set by scope
    settings).  Falls back to safe defaults when config is absent or
    partially populated.
    """
    if not isinstance(governed_runtime_config, dict):
        return RuntimeRetrievalConfig()
    rs: dict[str, Any] = governed_runtime_config.get("retrieval_settings") or {}
    # retrieval_execution_mode lives at top level (from bootstrap) and may
    # also be overridden by retrieval_settings scope.
    mode_top = str(governed_runtime_config.get("retrieval_execution_mode") or "").strip()
    mode_rs = str(rs.get("retrieval_execution_mode") or "").strip()
    mode = mode_top or mode_rs or "hybrid_dense_sparse"
    max_k_raw = rs.get("retrieval_top_k")
    try:
        max_k = int(max_k_raw)
    except (TypeError, ValueError):
        max_k = 4
    max_k = max(1, min(max_k, 12))
    profile = str(rs.get("retrieval_profile") or "runtime_turn_support").strip() or "runtime_turn_support"
    min_score_raw = rs.get("retrieval_min_score")
    try:
        min_score: float | None = float(min_score_raw) if min_score_raw is not None else None
    except (TypeError, ValueError):
        min_score = None
    embeddings_ok = bool(rs.get("embeddings_enabled", True))
    return RuntimeRetrievalConfig(
        retrieval_execution_mode=mode,
        max_chunks=max_k,
        retrieval_profile=profile,
        retrieval_min_score=min_score,
        embeddings_enabled=embeddings_ok,
    )


@dataclass(slots=True)
class RetrievalRequest:
    """``RetrievalRequest`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    domain: RetrievalDomain
    profile: str
    query: str
    module_id: str | None = None
    scene_id: str | None = None
    max_chunks: int = 4
    use_sparse_only: bool = False


@dataclass(slots=True)
class RetrievalHit:
    """``RetrievalHit`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
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
    """``RetrievalResult`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
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


def filter_retrieval_result_by_min_score(
    result: RetrievalResult,
    min_score: float | None,
) -> tuple[RetrievalResult, int]:
    """Return a result with below-threshold hits removed before pack assembly."""
    if min_score is None:
        return result, 0
    try:
        threshold = float(min_score)
    except (TypeError, ValueError):
        return result, 0
    kept = [hit for hit in result.hits if float(hit.score) >= threshold]
    removed_count = len(result.hits) - len(kept)
    notes = list(result.ranking_notes)
    notes.append(f"retrieval_min_score={threshold:g};filtered_out={removed_count}")
    if removed_count == 0:
        return replace(result, ranking_notes=notes), 0
    return replace(result, hits=kept, ranking_notes=notes), removed_count


@dataclass(slots=True)
class ContextPack:
    """``ContextPack`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
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
