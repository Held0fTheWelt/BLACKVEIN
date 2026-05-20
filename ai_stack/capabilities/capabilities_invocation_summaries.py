"""
Workflow-safe invocation result summaries for capability audit (no full
payloads).
"""

from __future__ import annotations

import json
from typing import Any, Callable

_Handler = Callable[[dict[str, Any]], dict[str, Any] | None]


def _summarize_wos_context_pack_build(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_context_pack_build`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    from ai_stack.capabilities import build_retrieval_trace  # noqa: PLC0415 — avoid import cycle at load time

    retrieval = result.get("retrieval")
    if not isinstance(retrieval, dict):
        return {"kind": "context_pack", "hit_count": 0, "note": "missing_retrieval_dict"}
    hit_count = int(retrieval.get("hit_count") or 0)
    summary: dict[str, Any] = {
        "kind": "context_pack",
        "hit_count": hit_count,
        "status": retrieval.get("status"),
        "domain": retrieval.get("domain"),
        "profile": retrieval.get("profile"),
    }
    fp = retrieval.get("corpus_fingerprint")
    if isinstance(fp, str) and fp:
        summary["corpus_fingerprint_prefix"] = fp[:24]
    iv = retrieval.get("index_version")
    if isinstance(iv, str) and iv:
        summary["index_version"] = iv
    route = retrieval.get("retrieval_route")
    if isinstance(route, str) and route:
        summary["retrieval_route"] = route
    top_hit = retrieval.get("top_hit_score")
    if isinstance(top_hit, str) and top_hit:
        summary["top_hit_score"] = top_hit
    trace_hint = build_retrieval_trace(retrieval)
    summary["evidence_tier"] = trace_hint.get("evidence_tier")
    summary["evidence_rationale"] = trace_hint.get("evidence_rationale")
    summary["evidence_lane_mix"] = trace_hint.get("evidence_lane_mix")
    summary["readiness_label"] = trace_hint.get("readiness_label")
    summary["retrieval_quality_hint"] = trace_hint.get("retrieval_quality_hint")
    summary["policy_outcome_hint"] = trace_hint.get("policy_outcome_hint")
    summary["dedup_shaped_selection"] = trace_hint.get("dedup_shaped_selection")
    summary["retrieval_trace_schema_version"] = trace_hint.get("retrieval_trace_schema_version")
    from ai_stack.rag import RETRIEVAL_POLICY_VERSION  # noqa: PLC0415

    summary["retrieval_policy_version"] = retrieval.get("retrieval_policy_version") or RETRIEVAL_POLICY_VERSION
    if hit_count > 0:
        sources = retrieval.get("sources")
        if isinstance(sources, list) and sources:
            first = sources[0]
            if isinstance(first, dict):
                lane = first.get("source_evidence_lane")
                if isinstance(lane, str) and lane:
                    summary["primary_source_evidence_lane"] = lane
                inf = first.get("profile_policy_influence")
                if isinstance(inf, str) and inf:
                    summary["primary_profile_policy_influence"] = inf
    return summary


def _summarize_wos_review_bundle_build(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_review_bundle_build`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    evidence = result.get("evidence_sources", [])
    n_evidence = len(evidence) if isinstance(evidence, list) else 0
    return {
        "kind": "review_bundle",
        "bundle_id": result.get("bundle_id"),
        "status": result.get("status"),
        "evidence_source_count": n_evidence,
        "workflow_impact": "feeds_governance_review_package" if n_evidence else "metadata_only_bundle",
    }


def _summarize_wos_transcript_read(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_transcript_read`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    content = result.get("content", "")
    turn_count = 0
    repetition_turns = 0
    try:
        parsed = json.loads(str(content))
        if isinstance(parsed, dict):
            turns = parsed.get("transcript")
            if isinstance(turns, list):
                turn_count = len(turns)
                repetition_turns = sum(1 for row in turns if isinstance(row, dict) and row.get("repetition_flag"))
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return {
        "kind": "transcript_read",
        "run_id": result.get("run_id"),
        "content_length": len(str(content)),
        "transcript_turn_count": turn_count,
        "repetition_turn_count": repetition_turns,
        "workflow_impact": (
            "drives_improvement_recommendation_suffix"
            if turn_count
            else "no_parsed_transcript_rows"
        ),
    }


def _summarize_wos_research_explore(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_research_explore`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    summary = result.get("exploration_summary", {})
    if not isinstance(summary, dict):
        summary = {}
    consumed = summary.get("consumed_budget")
    effective = summary.get("effective_budget")
    return {
        "kind": "research_explore",
        "run_id": result.get("run_id"),
        "node_count": summary.get("node_count", 0),
        "edge_count": summary.get("edge_count", 0),
        "abort_reason": summary.get("abort_reason"),
        "promoted_candidate_count": summary.get("promoted_candidate_count", 0),
        "consumed_budget": consumed if isinstance(consumed, dict) else {},
        "effective_budget": effective if isinstance(effective, dict) else {},
    }


def _summarize_wos_research_bundle_build(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_research_bundle_build`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    bundle = result.get("bundle", {})
    if not isinstance(bundle, dict):
        bundle = {}
    return {
        "kind": "research_bundle",
        "run_id": bundle.get("run_id"),
        "section_count": len(bundle.get("sections", [])) if isinstance(bundle.get("sections"), list) else 0,
        "review_safe": (bundle.get("governance") or {}).get("review_safe"),
    }


def _summarize_wos_canon_improvement_propose(result: dict[str, Any]) -> dict[str, Any] | None:
    """Describe what ``_summarize_wos_canon_improvement_propose`` does in
    one line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    issues = result.get("issues", [])
    proposals = result.get("proposals", [])
    return {
        "kind": "canon_improvement_propose",
        "issue_count": len(issues) if isinstance(issues, list) else 0,
        "proposal_count": len(proposals) if isinstance(proposals, list) else 0,
    }


_INVOCATION_SUMMARY_HANDLERS: dict[str, _Handler] = {
    "wos.context_pack.build": _summarize_wos_context_pack_build,
    "wos.review_bundle.build": _summarize_wos_review_bundle_build,
    "wos.transcript.read": _summarize_wos_transcript_read,
    "wos.research.explore": _summarize_wos_research_explore,
    "wos.research.bundle.build": _summarize_wos_research_bundle_build,
    "wos.canon.improvement.propose": _summarize_wos_canon_improvement_propose,
}


def summarize_invocation_result(capability_name: str, result: dict[str, Any]) -> dict[str, Any] | None:
    """Small, workflow-safe audit hints (no full payloads).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        capability_name: ``capability_name`` (str); meaning follows the type and call sites.
        result: ``result`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any] | None:
            Returns a value of type ``dict[str, Any] | None``; see the function body for structure, error paths, and sentinels.
    """
    handler = _INVOCATION_SUMMARY_HANDLERS.get(capability_name)
    if handler is None:
        return None
    return handler(result)
