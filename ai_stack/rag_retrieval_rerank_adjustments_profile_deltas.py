"""Profil-spezifische Rerank-Deltas (DS-045) — flache Helfer für ``compute_rerank_adjustments``."""

from __future__ import annotations

from ai_stack.rag_constants import RERANK_MODULE_MATCH_EXTRA
from ai_stack.rag_corpus import _ScoredCandidate
from ai_stack.rag_retrieval_dtos import RetrievalRequest
from ai_stack.rag_types import ContentClass
from ai_stack.rag_retrieval_lexical import (
    DOMAIN_DEFAULT_PROFILE,
    _char_trigram_jaccard,
    _rerank_agreement_bonus,
)


def apply_module_match_and_agreement_deltas(
    cand: _ScoredCandidate,
    *,
    profile_name: str,
    request: RetrievalRequest,
    use_hybrid: bool,
) -> tuple[float, list[str]]:
    delta = 0.0
    parts: list[str] = []
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
    return delta, parts


def apply_runtime_turn_support_content_deltas(
    cand: _ScoredCandidate,
    *,
    strong_authored_for_module: bool,
) -> tuple[float, list[str]]:
    delta = 0.0
    parts: list[str] = []
    cc = cand.chunk.content_class
    if cc in (ContentClass.TRANSCRIPT, ContentClass.RUNTIME_PROJECTION) and strong_authored_for_module:
        pen = 0.95
        delta -= pen
        parts.append(f"runtime_clutter_penalty=-{pen:.2f}")
    if cc == ContentClass.AUTHORED_MODULE and cand.chunk.canonical_priority >= 3:
        b = 0.18
        delta += b
        parts.append(f"runtime_canonical_rerank=+{b:.2f}")
    return delta, parts


def apply_writers_review_content_deltas(cand: _ScoredCandidate) -> tuple[float, list[str]]:
    delta = 0.0
    parts: list[str] = []
    cc = cand.chunk.content_class
    if cc == ContentClass.REVIEW_NOTE:
        b = 0.32
        delta += b
        parts.append(f"writers_review_boost=+{b:.2f}")
    if cc == ContentClass.TRANSCRIPT:
        b = 0.14
        delta += b
        parts.append(f"writers_transcript_boost=+{b:.2f}")
    return delta, parts


def apply_improvement_eval_content_deltas(cand: _ScoredCandidate) -> tuple[float, list[str]]:
    delta = 0.0
    parts: list[str] = []
    cc = cand.chunk.content_class
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
    return delta, parts


def apply_profile_content_class_deltas(
    cand: _ScoredCandidate,
    *,
    profile_name: str,
    strong_authored_for_module: bool,
) -> tuple[float, list[str]]:
    if profile_name == "runtime_turn_support":
        return apply_runtime_turn_support_content_deltas(
            cand, strong_authored_for_module=strong_authored_for_module
        )
    if profile_name == "writers_review":
        return apply_writers_review_content_deltas(cand)
    if profile_name == "improvement_eval":
        return apply_improvement_eval_content_deltas(cand)
    return 0.0, []


def apply_pool_redundancy_penalty(cand: _ScoredCandidate, pool: list[_ScoredCandidate]) -> tuple[float, list[str]]:
    higher = [p for p in pool if p.initial_score > cand.initial_score + 1e-9]
    if not higher:
        return 0.0, []
    best_j = max(_char_trigram_jaccard(cand.chunk.text, h.chunk.text) for h in higher[:12])
    if best_j < 0.87:
        return 0.0, []
    pen = 0.38 + 0.4 * (best_j - 0.87) / (1.0 - 0.87)
    return -pen, [f"rerank_redundancy=-{pen:.2f}"]
