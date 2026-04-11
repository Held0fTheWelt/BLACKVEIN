"""Hybrid retrieval orchestration: scoring, pool phase, and hit assembly (DS-003 stage 8)."""

from __future__ import annotations

from typing import Any

import numpy as np

from ai_stack.rag_embedding_index import CorpusEmbeddingIndex
from ai_stack.rag_governance import governance_view_for_chunk
from ai_stack.rag_retrieval_hybrid_encoding import _resolve_retrieval_hybrid_encoding_state
from ai_stack.rag_retrieval_lexical import _cosine_similarity, _hybrid_core_initial
from ai_stack.rag_retrieval_policy_pool import (
    _dedup_select,
    _hit_policy_note,
    _pack_role_for_hit,
    _profile_policy_influence,
)
from ai_stack.rag_retrieval_support import (
    _RetrievalEncodeScorePoolPhase,
    _append_dedup_suppression_quality_notes,
    _build_retrieval_prefix_notes,
    _build_retrieval_quality_seed_notes,
    _build_retrieval_query_profile_context,
    _rerank_retrieval_candidate_pool,
    _retrieval_result_degraded_empty_corpus,
    _retrieval_result_fallback_empty_hits,
    _retrieval_result_ok_with_hits,
    _sorted_candidates_to_hard_filtered_pool,
)
from ai_stack.rag_constants import (
    DOMAIN_CONTENT_ACCESS,
    HYBRID_CORE_SCALE,
    INITIAL_MODULE_MATCH_BOOST,
    INITIAL_SCENE_HINT_BOOST,
    RETRIEVAL_POLICY_VERSION,
)
from ai_stack.rag_types import RetrievalDomainError
from ai_stack.semantic_embedding import EMBEDDING_INDEX_VERSION

from ai_stack.rag_corpus import InMemoryRetrievalCorpus, _ScoredCandidate
from ai_stack.rag_retrieval_dtos import RetrievalHit, RetrievalRequest, RetrievalResult


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

    def _score_initial_candidates(
        self,
        request: RetrievalRequest,
        *,
        allowed_classes: set[Any],
        query_terms: dict[str, float],
        query_norm: float,
        use_hybrid: bool,
        query_vec: np.ndarray | None,
        profile_name: str,
        profile_boosts: dict[Any, float],
        canonical_weight: float,
        w_dense: float,
        w_sparse: float,
    ) -> list[_ScoredCandidate]:
        """Dense/sparse hybrid scoring over corpus chunks (initial pool, pre-policy rerank)."""
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
        return candidates

    def _build_retrieval_hits_from_selection(
        self,
        selected_tuples: list[tuple[float, _ScoredCandidate, list[str]]],
        *,
        profile_name: str,
        published_canonical_in_pool: bool,
    ) -> list[RetrievalHit]:
        """Map reranked/scored candidates to ``RetrievalHit`` rows (governance + policy notes)."""
        hits: list[RetrievalHit] = []
        for rerank_score, cand, rparts in selected_tuples:
            reason_core = cand.initial_reason
            if rparts:
                reason_core = reason_core + " | " + "; ".join(rparts)
            gov = governance_view_for_chunk(cand.chunk)
            pack_role = _pack_role_for_hit(profile=profile_name, chunk=cand.chunk, gov=gov)
            policy_note = _hit_policy_note(
                profile_name,
                gov,
                published_canonical_in_pool=published_canonical_in_pool,
                chunk=cand.chunk,
            )
            rule = _profile_policy_influence(profile_name, gov)
            why = (
                f"score={rerank_score:.2f}; lane={gov.evidence_lane.value}; pack_role={pack_role}; policy={policy_note}"
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
                    source_evidence_lane=gov.evidence_lane.value,
                    source_visibility_class=gov.visibility_class.value,
                    policy_note=policy_note,
                    profile_policy_influence=rule,
                )
            )
        return hits

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

        if not self.corpus.chunks:
            return _retrieval_result_degraded_empty_corpus(
                request=request,
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                dense_index_build_action=dense_action,
                dense_rebuild_reason=dense_rebuild_reason,
                dense_artifact_validity=dense_validity,
                embedding_reason_codes=c.rag_dense_load_reason_codes,
                embedding_index_version=emb_idx_ver,
                embedding_cache_dir_identity=emb_cache_id,
            )

        phase = _run_retrieval_encode_score_pool_phase(self, request)
        qpc = phase.qpc
        hybrid_state = phase.hybrid_state
        use_hybrid = hybrid_state.use_hybrid
        query_enc_codes = hybrid_state.query_enc_codes
        query_encode_failed = hybrid_state.query_encode_failed
        retrieval_route = hybrid_state.retrieval_route
        embedding_mid = hybrid_state.embedding_mid
        degradation_mode = hybrid_state.degradation_mode
        prefix_notes = phase.prefix_notes
        quality_notes = phase.quality_notes
        pool = phase.pool
        hard_policy_notes = phase.hard_policy_notes
        strong_authored = phase.strong_authored
        published_canonical_in_pool = phase.published_canonical_in_pool

        policy_notes: list[str] = [f"retrieval_policy_version={RETRIEVAL_POLICY_VERSION}"]
        policy_notes.extend(hard_policy_notes)

        reranked = _rerank_retrieval_candidate_pool(
            pool,
            profile_name=qpc.profile_name,
            request=request,
            use_hybrid=use_hybrid,
            strong_authored_for_module=strong_authored,
        )
        selected_tuples, dup_notes = _dedup_select(
            reranked,
            max_chunks=request.max_chunks,
            profile_name=qpc.profile_name,
        )
        _append_dedup_suppression_quality_notes(quality_notes, dup_notes)

        hits = self._build_retrieval_hits_from_selection(
            selected_tuples,
            profile_name=qpc.profile_name,
            published_canonical_in_pool=published_canonical_in_pool,
        )

        emb_codes_fallback = query_enc_codes if query_encode_failed else c.rag_dense_load_reason_codes
        emb_codes_ok = query_enc_codes if query_encode_failed else ()

        if not hits:
            return _retrieval_result_fallback_empty_hits(
                request=request,
                index_version=trace[0],
                corpus_fingerprint=trace[1],
                storage_path=trace[2],
                prefix_notes=prefix_notes,
                quality_notes=quality_notes,
                policy_notes=policy_notes,
                retrieval_route=retrieval_route,
                embedding_model_id=embedding_mid,
                degradation_mode=degradation_mode,
                dense_index_build_action=dense_action,
                dense_rebuild_reason=dense_rebuild_reason,
                dense_artifact_validity=dense_validity,
                embedding_reason_codes=emb_codes_fallback,
                embedding_index_version=emb_idx_ver,
                embedding_cache_dir_identity=emb_cache_id,
            )
        return _retrieval_result_ok_with_hits(
            request=request,
            index_version=trace[0],
            corpus_fingerprint=trace[1],
            storage_path=trace[2],
            hits=hits,
            prefix_notes=prefix_notes,
            quality_notes=quality_notes,
            policy_notes=policy_notes,
            retrieval_route=retrieval_route,
            embedding_model_id=embedding_mid,
            degradation_mode=degradation_mode,
            dense_index_build_action=dense_action,
            dense_rebuild_reason=dense_rebuild_reason,
            dense_artifact_validity=dense_validity,
            embedding_reason_codes=emb_codes_ok,
            embedding_index_version=emb_idx_ver,
            embedding_cache_dir_identity=emb_cache_id,
        )


def _run_retrieval_encode_score_pool_phase(
    retriever: ContextRetriever,
    request: RetrievalRequest,
) -> _RetrievalEncodeScorePoolPhase:
    c = retriever.corpus
    hybrid_state = _resolve_retrieval_hybrid_encoding_state(
        c,
        request,
        embedding_index_ready=retriever._embedding_ready(),
        embedding_model_id=retriever._embedding_model_id,
    )
    qpc = _build_retrieval_query_profile_context(request)
    prefix_notes = _build_retrieval_prefix_notes(c, hybrid_state=hybrid_state)
    quality_notes = _build_retrieval_quality_seed_notes(w_dense=qpc.w_dense, w_sparse=qpc.w_sparse)
    candidates = retriever._score_initial_candidates(
        request,
        allowed_classes=qpc.allowed_classes,
        query_terms=qpc.query_terms,
        query_norm=qpc.query_norm,
        use_hybrid=hybrid_state.use_hybrid,
        query_vec=hybrid_state.query_vec,
        profile_name=qpc.profile_name,
        profile_boosts=qpc.profile_boosts,
        canonical_weight=qpc.canonical_weight,
        w_dense=qpc.w_dense,
        w_sparse=qpc.w_sparse,
    )
    pool, hard_policy_notes, strong_authored, published_canonical_in_pool, pool_sz_note = (
        _sorted_candidates_to_hard_filtered_pool(
            candidates,
            request=request,
            profile_name=qpc.profile_name,
        )
    )
    quality_notes.append(pool_sz_note)
    return _RetrievalEncodeScorePoolPhase(
        qpc=qpc,
        hybrid_state=hybrid_state,
        prefix_notes=prefix_notes,
        quality_notes=quality_notes,
        pool=pool,
        hard_policy_notes=hard_policy_notes,
        strong_authored=strong_authored,
        published_canonical_in_pool=published_canonical_in_pool,
    )
