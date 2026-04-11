"""Retrieval trace summary lines and profile governance tags appended to ``compact_context`` (DS-009 optional)."""

from __future__ import annotations

from ai_stack.capabilities import build_retrieval_trace
from ai_stack.rag_retrieval_dtos import RetrievalResult


def append_trace_and_governance_footer(
    result: RetrievalResult,
    profile: str,
    lines: list[str],
    sources: list[dict[str, str]],
) -> None:
    rdict_for_trace = {
        "hit_count": len(result.hits),
        "status": result.status.value,
        "retrieval_route": result.retrieval_route,
        "top_hit_score": sources[0].get("score", "") if sources else "",
        "ranking_notes": result.ranking_notes,
        "sources": sources,
        "degradation_mode": result.degradation_mode,
        "domain": result.request.domain.value,
        "profile": profile,
    }
    pack_trace = build_retrieval_trace(rdict_for_trace)
    lines.append(
        "retrieval_posture: "
        f"status={result.status.value}; route={result.retrieval_route or 'n/a'}; "
        f"degradation={result.degradation_mode or 'n/a'}; hits={len(result.hits)}; "
        f"lane_mix={pack_trace.get('evidence_lane_mix')}; "
        f"confidence={pack_trace.get('confidence_posture')}"
    )
    lines.append(f"pack_trace_summary: {pack_trace.get('retrieval_posture_summary')}")
    if profile == "runtime_turn_support":
        lines.append("context_pack_governance=runtime_canonical_first_when_available")
    elif profile == "writers_review":
        lines.append("context_pack_governance=writers_broader_working_and_review_sections")
    elif profile == "improvement_eval":
        lines.append("context_pack_governance=improvement_evaluative_and_anchor_mix")
    lines.append("context_pack_order=workflow_sections_then_ordinal")
