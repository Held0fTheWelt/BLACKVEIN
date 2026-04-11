"""Retrieval query context, ranking notes, rerank merge, and RetrievalResult builders (DS-003 stage 6)."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Protocol

from ai_stack.rag_constants import DOMAIN_CONTENT_ACCESS, RETRIEVAL_PIPELINE_VERSION
from ai_stack.rag_governance import governance_view_for_chunk
from ai_stack.rag_retrieval_hybrid_encoding import _RetrievalHybridEncodingState
from ai_stack.rag_retrieval_lexical import (
    DOMAIN_DEFAULT_PROFILE,
    PROFILE_CANONICAL_WEIGHT,
    PROFILE_CONTENT_BOOSTS,
    _build_semantic_terms,
    _profile_hybrid_weights,
)
from ai_stack.rag_retrieval_policy_pool import (
    _apply_hard_policy_pool_filter,
    _policy_soft_adjustments,
    _pool_has_published_canonical_for_module,
    _pool_has_strong_authored_for_module,
    _pool_size,
)
from ai_stack.rag_retrieval_dtos import RetrievalResult
from ai_stack.rag_types import RetrievalDegradationMode, RetrievalDomain, RetrievalStatus


class _CorpusPrefixLike(Protocol):
    rag_dense_index_build_action: str
    rag_dense_artifact_validity: str
    rag_dense_rebuild_reason: str | None


class _RequestForQPC(Protocol):
    domain: RetrievalDomain
    profile: str
    query: str


class _RequestForPoolSort(Protocol):
    module_id: str | None
    max_chunks: int


class _ChunkIdLike(Protocol):
    chunk_id: str


class _InitialScoredLike(Protocol):
    initial_score: float
    chunk: _ChunkIdLike


class _RerankCandidateLike(Protocol):
    chunk: Any
    initial_score: float


class _HitRankLineLike(Protocol):
    source_path: str
    score: float
    source_evidence_lane: str
    pack_role: str
    profile_policy_influence: str
    selection_reason: str


@dataclass(slots=True)
class _RetrievalQueryProfileContext:
    allowed_classes: set[Any]
    query_terms: dict[str, float]
    query_norm: float
    profile_name: str
    profile_boosts: dict[Any, float]
    canonical_weight: float
    w_dense: float
    w_sparse: float


def _build_retrieval_query_profile_context(request: _RequestForQPC) -> _RetrievalQueryProfileContext:
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
    return _RetrievalQueryProfileContext(
        allowed_classes=allowed_classes,
        query_terms=query_terms,
        query_norm=query_norm,
        profile_name=profile_name,
        profile_boosts=profile_boosts,
        canonical_weight=canonical_weight,
        w_dense=w_dense,
        w_sparse=w_sparse,
    )


def _build_retrieval_prefix_notes(
    corpus: _CorpusPrefixLike,
    *,
    hybrid_state: _RetrievalHybridEncodingState,
) -> list[str]:
    c = corpus
    dense_action = c.rag_dense_index_build_action
    dense_validity = c.rag_dense_artifact_validity
    dense_rebuild_reason = c.rag_dense_rebuild_reason

    prefix_notes: list[str] = [
        f"retrieval_route={hybrid_state.retrieval_route}",
        f"degradation_mode={hybrid_state.degradation_mode}",
        f"dense_index_build_action={dense_action}",
        f"dense_artifact_validity={dense_validity}",
    ]
    if dense_rebuild_reason:
        prefix_notes.append(f"dense_rebuild_reason={dense_rebuild_reason}")
    if hybrid_state.use_hybrid and hybrid_state.embedding_mid:
        prefix_notes.append(f"embedding_model_id={hybrid_state.embedding_mid}")
    if hybrid_state.query_encode_failed and hybrid_state.query_enc_codes:
        prefix_notes.append("embedding_query_encode_failed=" + ",".join(hybrid_state.query_enc_codes))
    elif hybrid_state.query_encode_failed:
        prefix_notes.append("embedding_query_encode_failed")
    return prefix_notes


def _build_retrieval_quality_seed_notes(*, w_dense: float, w_sparse: float) -> list[str]:
    return [
        f"retrieval_pipeline_version={RETRIEVAL_PIPELINE_VERSION}",
        f"hybrid_v2_weights_dense={w_dense:.2f}_sparse={w_sparse:.2f}",
    ]


def _rerank_retrieval_candidate_pool(
    pool: list[_RerankCandidateLike],
    *,
    profile_name: str,
    request: Any,
    use_hybrid: bool,
    strong_authored_for_module: bool,
) -> list[tuple[float, _RerankCandidateLike, list[str]]]:
    """Task 2 rerank + Task 3 policy-soft adjustments over the hard-filtered pool."""
    from ai_stack.rag_retrieval_rerank_adjustments import compute_rerank_adjustments as _rerank_adjustments

    reranked: list[tuple[float, _RerankCandidateLike, list[str]]] = []
    for cand in pool:
        gov = governance_view_for_chunk(cand.chunk)
        pdelta, pparts = _policy_soft_adjustments(
            cand,
            profile_name=profile_name,
            request=request,
            strong_authored_for_module=strong_authored_for_module,
            gov=gov,
        )
        rdelta, rparts = _rerank_adjustments(
            cand,
            profile_name=profile_name,
            request=request,
            pool=pool,
            use_hybrid=use_hybrid,
            strong_authored_for_module=strong_authored_for_module,
        )
        policy_delta = pdelta + rdelta
        merged_parts: list[str] = []
        if pparts:
            merged_parts.extend(pparts)
        merged_parts.extend(rparts)
        if policy_delta != 0:
            merged_parts.insert(0, f"score_delta_task2_rerank_plus_task3_policy={policy_delta:+.3f}")
        rerank_score = cand.initial_score + policy_delta
        reranked.append((rerank_score, cand, merged_parts))

    reranked.sort(key=lambda x: (x[0], x[1].chunk.chunk_id), reverse=True)
    return reranked


def _append_dedup_suppression_quality_notes(quality_notes: list[str], dup_notes: list[str]) -> None:
    quality_notes.extend(dup_notes[:8])
    if len(dup_notes) > 8:
        quality_notes.append(f"dup_suppressed_more={len(dup_notes) - 8}")


def _retrieval_hit_ranking_detail_lines(hits: list[_HitRankLineLike]) -> list[str]:
    return [
        (
            f"{h.source_path} score={h.score:.2f} lane={h.source_evidence_lane} "
            f"pack_role={h.pack_role} influence={h.profile_policy_influence} ({h.selection_reason})"
        )
        for h in hits
    ]


def _retrieval_result_fallback_empty_hits(
    *,
    request: Any,
    index_version: str,
    corpus_fingerprint: str,
    storage_path: str,
    prefix_notes: list[str],
    quality_notes: list[str],
    policy_notes: list[str],
    retrieval_route: str,
    embedding_model_id: str,
    degradation_mode: str,
    dense_index_build_action: str,
    dense_rebuild_reason: str | None,
    dense_artifact_validity: str,
    embedding_reason_codes: tuple[str, ...],
    embedding_index_version: str,
    embedding_cache_dir_identity: str | None,
) -> Any:
    notes = prefix_notes + quality_notes + policy_notes + ["no_ranked_hits_for_query"]
    return RetrievalResult(
        request=request,
        status=RetrievalStatus.FALLBACK,
        hits=[],
        ranking_notes=notes,
        error="no_ranked_hits",
        index_version=index_version,
        corpus_fingerprint=corpus_fingerprint,
        storage_path=storage_path,
        retrieval_route=retrieval_route,
        embedding_model_id=embedding_model_id,
        degradation_mode=degradation_mode,
        dense_index_build_action=dense_index_build_action,
        dense_rebuild_reason=dense_rebuild_reason,
        dense_artifact_validity=dense_artifact_validity,
        embedding_reason_codes=embedding_reason_codes,
        embedding_index_version=embedding_index_version,
        embedding_cache_dir_identity=embedding_cache_dir_identity,
    )


def _retrieval_result_ok_with_hits(
    *,
    request: Any,
    index_version: str,
    corpus_fingerprint: str,
    storage_path: str,
    hits: list[Any],
    prefix_notes: list[str],
    quality_notes: list[str],
    policy_notes: list[str],
    retrieval_route: str,
    embedding_model_id: str,
    degradation_mode: str,
    dense_index_build_action: str,
    dense_rebuild_reason: str | None,
    dense_artifact_validity: str,
    embedding_reason_codes: tuple[str, ...],
    embedding_index_version: str,
    embedding_cache_dir_identity: str | None,
) -> Any:
    detail_lines = _retrieval_hit_ranking_detail_lines(hits)
    ranking_notes = prefix_notes + quality_notes + policy_notes + detail_lines
    return RetrievalResult(
        request=request,
        status=RetrievalStatus.OK,
        hits=hits,
        ranking_notes=ranking_notes,
        error=None,
        index_version=index_version,
        corpus_fingerprint=corpus_fingerprint,
        storage_path=storage_path,
        retrieval_route=retrieval_route,
        embedding_model_id=embedding_model_id,
        degradation_mode=degradation_mode,
        dense_index_build_action=dense_index_build_action,
        dense_rebuild_reason=dense_rebuild_reason,
        dense_artifact_validity=dense_artifact_validity,
        embedding_reason_codes=embedding_reason_codes,
        embedding_index_version=embedding_index_version,
        embedding_cache_dir_identity=embedding_cache_dir_identity,
    )


def _retrieval_result_degraded_empty_corpus(
    *,
    request: Any,
    index_version: str,
    corpus_fingerprint: str,
    storage_path: str,
    dense_index_build_action: str,
    dense_rebuild_reason: str | None,
    dense_artifact_validity: str,
    embedding_reason_codes: tuple[str, ...],
    embedding_index_version: str,
    embedding_cache_dir_identity: str | None,
) -> Any:
    return RetrievalResult(
        request=request,
        status=RetrievalStatus.DEGRADED,
        hits=[],
        ranking_notes=[
            "retrieval_corpus_empty",
            f"degradation_mode={RetrievalDegradationMode.CORPUS_EMPTY.value}",
        ],
        error="retrieval_corpus_empty",
        index_version=index_version,
        corpus_fingerprint=corpus_fingerprint,
        storage_path=storage_path,
        retrieval_route="",
        embedding_model_id="",
        degradation_mode=RetrievalDegradationMode.CORPUS_EMPTY.value,
        dense_index_build_action=dense_index_build_action,
        dense_rebuild_reason=dense_rebuild_reason,
        dense_artifact_validity=dense_artifact_validity,
        embedding_reason_codes=embedding_reason_codes,
        embedding_index_version=embedding_index_version,
        embedding_cache_dir_identity=embedding_cache_dir_identity,
    )


def _sorted_candidates_to_hard_filtered_pool(
    candidates: list[_InitialScoredLike],
    *,
    request: _RequestForPoolSort,
    profile_name: str,
) -> tuple[list[_InitialScoredLike], list[str], bool, bool, str]:
    """Sort by initial score, cap pool, apply hard policy; return pool metadata for rerank."""

    candidates.sort(key=lambda x: (x.initial_score, x.chunk.chunk_id), reverse=True)
    pool_n = _pool_size(request.max_chunks)
    pool = candidates[:pool_n]
    pool, hard_policy_notes, _hard_excl = _apply_hard_policy_pool_filter(
        pool,
        profile_name=profile_name,
        request=request,
    )
    strong_authored = _pool_has_strong_authored_for_module(pool, request.module_id)
    published_canonical_in_pool = _pool_has_published_canonical_for_module(pool, request.module_id)
    pool_size_note = f"rerank_pool_size={len(pool)}"
    return pool, hard_policy_notes, strong_authored, published_canonical_in_pool, pool_size_note


@dataclass(frozen=True, slots=True)
class _RetrievalEncodeScorePoolPhase:
    """Hybrid/query encoding, initial scoring, and hard-filtered rerank pool (pre-dedup)."""

    qpc: _RetrievalQueryProfileContext
    hybrid_state: _RetrievalHybridEncodingState
    prefix_notes: list[str]
    quality_notes: list[str]
    pool: list[Any]
    hard_policy_notes: list[str]
    strong_authored: bool
    published_canonical_in_pool: bool
