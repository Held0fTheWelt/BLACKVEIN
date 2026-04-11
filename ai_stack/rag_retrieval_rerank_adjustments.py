"""Deep rerank delta logic extracted from ``rag.py`` (DS-033) — behavior-preserving."""

from __future__ import annotations

from ai_stack.rag_corpus import _ScoredCandidate
from ai_stack.rag_retrieval_dtos import RetrievalRequest
from ai_stack.rag_retrieval_rerank_adjustments_profile_deltas import (
    apply_module_match_and_agreement_deltas,
    apply_pool_redundancy_penalty,
    apply_profile_content_class_deltas,
)


def compute_rerank_adjustments(
    cand: _ScoredCandidate,
    *,
    profile_name: str,
    request: RetrievalRequest,
    pool: list[_ScoredCandidate],
    use_hybrid: bool,
    strong_authored_for_module: bool,
) -> tuple[float, list[str]]:
    """Additive rerank deltas; inspectable string fragments."""
    d0, p0 = apply_module_match_and_agreement_deltas(
        cand, profile_name=profile_name, request=request, use_hybrid=use_hybrid
    )
    d1, p1 = apply_profile_content_class_deltas(
        cand, profile_name=profile_name, strong_authored_for_module=strong_authored_for_module
    )
    d2, p2 = apply_pool_redundancy_penalty(cand, pool)
    return d0 + d1 + d2, p0 + p1 + p2
