"""Rerank pool sizing, Task 3 hard/soft policy, pack roles, and dedup (DS-003 stage 5)."""

from __future__ import annotations

from typing import Protocol

from ai_stack.rag_constants import (
    DUP_IMPROVEMENT_RELAXATION,
    DUP_SAME_SOURCE_JACCARD_DROP,
    DUP_TRIGRAM_JACCARD_DROP,
    RERANK_POOL_CAP,
    RERANK_POOL_FACTOR,
    RERANK_POOL_MIN,
)
from ai_stack.rag_governance import governance_view_for_chunk
from ai_stack.rag_retrieval_lexical import _char_trigram_jaccard
from ai_stack.rag_types import ContentClass, SourceEvidenceLane, SourceGovernanceView


class _PolicyChunkLike(Protocol):
    chunk_id: str
    source_path: str
    content_class: ContentClass
    module_id: str | None
    canonical_priority: int
    text: str


class _PolicyScoredCandidateLike(Protocol):
    chunk: _PolicyChunkLike
    module_match: bool


class _RequestWithModuleLike(Protocol):
    module_id: str | None


class _HitPackSortLike(Protocol):
    score: float
    chunk_id: str
    pack_role: str


def _pool_size(max_chunks: int) -> int:
    k = max(1, max_chunks)
    return min(RERANK_POOL_CAP, max(RERANK_POOL_MIN, k * RERANK_POOL_FACTOR))


def _pool_has_strong_authored_for_module(
    pool: list[_PolicyScoredCandidateLike], module_id: str | None
) -> bool:
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


def _pool_has_published_canonical_for_module(
    pool: list[_PolicyScoredCandidateLike], module_id: str | None
) -> bool:
    """True when the pool already contains published-tree authored module chunks for this module."""
    if not module_id:
        return False
    for c in pool:
        if c.chunk.content_class != ContentClass.AUTHORED_MODULE:
            continue
        if c.chunk.canonical_priority < 4:
            continue
        if c.chunk.module_id == module_id:
            return True
    return False


def _apply_hard_policy_pool_filter(
    pool: list[_PolicyScoredCandidateLike],
    *,
    profile_name: str,
    request: _RequestWithModuleLike,
) -> tuple[list[_PolicyScoredCandidateLike], list[str], int]:
    """Remove candidates excluded by hard visibility rules (Task 3), before reranking.

    Runtime: drop same-module ``draft_working`` authored chunks when a published canonical
    authored chunk for that module is already present in the pool. Writers/improvement
    profiles do not apply this gate so drafts and review material remain visible.
    """
    if profile_name != "runtime_turn_support" or not request.module_id:
        return pool, [], 0
    if not _pool_has_published_canonical_for_module(pool, request.module_id):
        return pool, [], 0
    kept: list[_PolicyScoredCandidateLike] = []
    excluded = 0
    detail_notes: list[str] = []
    for c in pool:
        gov = governance_view_for_chunk(c.chunk)
        if (
            gov.evidence_lane == SourceEvidenceLane.DRAFT_WORKING
            and c.chunk.content_class == ContentClass.AUTHORED_MODULE
            and c.module_match
        ):
            excluded += 1
            if len(detail_notes) < 8:
                detail_notes.append(
                    f"policy_hard_excluded chunk_id={c.chunk.chunk_id} "
                    f"reason=draft_when_published_canonical_in_pool"
                )
            continue
        kept.append(c)
    summary: list[str] = []
    if excluded:
        summary.append(f"policy_hard_excluded_pool_count={excluded}")
    summary.extend(detail_notes)
    return kept, summary, excluded


def _policy_soft_adjustments(
    cand: _PolicyScoredCandidateLike,
    *,
    profile_name: str,
    request: _RequestWithModuleLike,
    strong_authored_for_module: bool,
    gov: SourceGovernanceView,
) -> tuple[float, list[str]]:
    """Governance soft weights (Task 3). Prefix ``policy_soft_``; orthogonal to Task 2 rerank."""
    _ = request
    delta = 0.0
    parts: list[str] = []
    cc = cand.chunk.content_class

    if profile_name == "runtime_turn_support":
        if cc == ContentClass.CHARACTER_PROFILE and strong_authored_for_module:
            pen = 0.28
            delta -= pen
            parts.append(f"policy_soft_character_profile_when_strong_authored=-{pen:.2f}")
    elif profile_name == "writers_review":
        if gov.evidence_lane == SourceEvidenceLane.DRAFT_WORKING and cc == ContentClass.AUTHORED_MODULE:
            b = 0.06
            delta += b
            parts.append(f"policy_soft_writers_draft_visibility=+{b:.2f}")
    elif profile_name == "improvement_eval":
        if gov.evidence_lane == SourceEvidenceLane.SUPPORTING and cc == ContentClass.POLICY_GUIDELINE:
            b = 0.1
            delta += b
            parts.append(f"policy_soft_improvement_policy_diagnostic=+{b:.2f}")

    return delta, parts


def _pack_role_for_hit(
    *,
    profile: str,
    chunk: _PolicyChunkLike,
    gov: SourceGovernanceView,
) -> str:
    if profile == "runtime_turn_support":
        if gov.evidence_lane == SourceEvidenceLane.CANONICAL and chunk.content_class == ContentClass.AUTHORED_MODULE:
            return "canonical_evidence"
        if chunk.content_class == ContentClass.POLICY_GUIDELINE:
            return "policy_evidence"
        return "supporting_context"
    if profile == "improvement_eval":
        if gov.evidence_lane in (SourceEvidenceLane.EVALUATIVE, SourceEvidenceLane.INTERNAL_REVIEW):
            return "evaluative_evidence"
        return "supporting_context"
    if profile == "writers_review":
        if gov.evidence_lane == SourceEvidenceLane.DRAFT_WORKING and chunk.content_class == ContentClass.AUTHORED_MODULE:
            return "draft_working_context"
        if chunk.content_class == ContentClass.AUTHORED_MODULE:
            return "authored_context"
        if chunk.content_class == ContentClass.REVIEW_NOTE:
            return "review_context"
        return "supporting_context"
    return "supporting_context"


def _hit_policy_note(
    profile_name: str,
    gov: SourceGovernanceView,
    *,
    published_canonical_in_pool: bool,
    chunk: _PolicyChunkLike,
) -> str:
    """One compact English line: allow/exclude semantics for operators (final hits are always allowed)."""
    if profile_name == "runtime_turn_support":
        if gov.evidence_lane == SourceEvidenceLane.CANONICAL:
            return "allowed:canonical_lane_for_runtime"
        if gov.evidence_lane == SourceEvidenceLane.DRAFT_WORKING:
            return "allowed:draft_lane_retained_no_published_canonical_anchor_in_pool"
        if gov.evidence_lane == SourceEvidenceLane.SUPPORTING:
            if published_canonical_in_pool and chunk.content_class != ContentClass.AUTHORED_MODULE:
                return "allowed:supporting_lane_downranked_when_canonical_present_task2_rerank"
            return "allowed:supporting_lane_runtime_safe"
        return "allowed:runtime_default_lane"
    if profile_name == "writers_review":
        if gov.evidence_lane == SourceEvidenceLane.INTERNAL_REVIEW:
            return "allowed:internal_review_visible_in_writers_room"
        if gov.evidence_lane == SourceEvidenceLane.DRAFT_WORKING:
            return "allowed:draft_working_visible_in_writers_room"
        return "allowed:writers_broader_working_material"
    if profile_name == "improvement_eval":
        if gov.evidence_lane == SourceEvidenceLane.EVALUATIVE:
            return "allowed:evaluative_lane_preferred_for_improvement"
        if gov.evidence_lane == SourceEvidenceLane.INTERNAL_REVIEW:
            return "allowed:review_lane_for_improvement_contrast"
        if gov.evidence_lane == SourceEvidenceLane.CANONICAL:
            return "allowed:canonical_anchor_for_improvement"
        return "allowed:improvement_diagnostic_or_supporting"
    return "allowed:default_policy_note"


def _profile_policy_influence(profile_name: str, gov: SourceGovernanceView) -> str:
    """Which named profile rule most influenced inclusion (compact trace)."""
    if profile_name == "runtime_turn_support":
        if gov.evidence_lane == SourceEvidenceLane.CANONICAL:
            return "runtime_canonical_first"
        return "runtime_safe_sources_only_domain_gate_plus_soft_policy"
    if profile_name == "writers_review":
        return "writers_broader_working_and_review_visibility"
    if profile_name == "improvement_eval":
        if gov.evidence_lane in (SourceEvidenceLane.EVALUATIVE, SourceEvidenceLane.INTERNAL_REVIEW):
            return "improvement_evaluative_and_review_material"
        return "improvement_mixed_anchor_and_diagnostic"
    return "profile_policy_default"


def _dedup_select(
    ordered: list[tuple[float, _PolicyScoredCandidateLike, list[str]]],
    *,
    max_chunks: int,
    profile_name: str,
) -> tuple[list[tuple[float, _PolicyScoredCandidateLike, list[str]]], list[str]]:
    """Greedy keep by descending rerank score; drop near-duplicates deterministically."""
    kept: list[tuple[float, _PolicyScoredCandidateLike, list[str]]] = []
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


def _pack_sort_key(hit: _HitPackSortLike, profile: str) -> tuple[int, float, str]:
    """Order hits for compact_context: lower tuple sorts first."""
    _ = profile
    tier_order = {
        "canonical_evidence": 0,
        "policy_evidence": 1,
        "evaluative_evidence": 0,
        "authored_context": 0,
        "draft_working_context": 1,
        "review_context": 1,
        "supporting_context": 2,
    }
    role = hit.pack_role or "supporting_context"
    return (tier_order.get(role, 3), -hit.score, hit.chunk_id)
