"""
Phased body for `run_research_pipeline` — intake, aspects, exploration
candidates (DS-003 slice).
"""

from __future__ import annotations

from typing import Any

from ai_stack.research_aspect_extraction import extract_and_store_aspects
from ai_stack.research_ingestion import ingest_resource, normalize_resource
from ai_stack.research_store import ResearchStore
from ai_stack.research_validation import evaluate_candidate_from_exploration_node


def review_safe_flag(*, claims: list[dict[str, Any]], exploration_summary: dict[str, Any]) -> bool:
    """``review_safe_flag`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        claims: ``claims`` (list[dict[str, Any]]); meaning follows the type and call sites.
        exploration_summary: ``exploration_summary`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    if any(str(claim.get("contradiction_status", "")) == "hard_conflict" for claim in claims):
        return False
    if any(not claim.get("evidence_anchor_ids") for claim in claims):
        return False
    abort_reason = str(exploration_summary.get("abort_reason", ""))
    unsafe_abort_reasons = {"token_budget_exhausted", "llm_budget_exhausted", "time_budget_exhausted"}
    if abort_reason in unsafe_abort_reasons:
        return False
    return True


def canon_relevance_hint(node: dict[str, Any]) -> bool:
    """``canon_relevance_hint`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        node: ``node`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    hypothesis = str(node.get("hypothesis", "")).lower()
    return "improvement_probe" in hypothesis or "tension_probe" in hypothesis


def run_pipeline_intake(
    *,
    store: ResearchStore,
    work_id: str,
    source_inputs: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """``run_pipeline_intake`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        store: ``store`` (ResearchStore); meaning follows the type and call sites.
        work_id: ``work_id`` (str); meaning follows the type and call sites.
        source_inputs: ``source_inputs`` (list[dict[str,
            Any]]); meaning follows the type and call sites.
    
    Returns:
        tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[...:
            Returns a value of type ``tuple[list[dict[str, Any]], list[dict[str,
            Any]], list[dict[s...``; see the function body for structure, error paths, and sentinels.
    """
    intake_sources: list[dict[str, Any]] = []
    all_segments: list[dict[str, Any]] = []
    all_anchors: list[dict[str, Any]] = []
    for source_input in source_inputs:
        normalized = normalize_resource(
            work_id=work_id,
            source_type=str(source_input.get("source_type", "note")),
            title=str(source_input.get("title", "untitled")),
            raw_text=str(source_input.get("raw_text", "")),
            provenance=dict(source_input.get("provenance", {})),
            visibility=str(source_input.get("visibility", "internal")),
            copyright_posture=source_input.get("copyright_posture"),
            metadata=dict(source_input.get("metadata", {})),
        )
        intake = ingest_resource(store=store, normalized_source=normalized)
        intake_sources.append(intake["source"])
        all_segments.extend(intake["segments"])
        all_anchors.extend(intake["anchors"])
    return intake_sources, all_segments, all_anchors


def run_pipeline_aspects(
    *,
    store: ResearchStore,
    intake_sources: list[dict[str, Any]],
    all_segments: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """``run_pipeline_aspects`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        store: ``store`` (ResearchStore); meaning follows the type and call sites.
        intake_sources: ``intake_sources`` (list[dict[str, Any]]); meaning follows the type and call sites.
        all_segments: ``all_segments`` (list[dict[str,
            Any]]); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    aspects: list[dict[str, Any]] = []
    for source in intake_sources:
        source_id = str(source["source_id"])
        source_segments = [s for s in all_segments if s.get("source_id") == source_id and s.get("segment_ref")]
        aspects.extend(extract_and_store_aspects(store=store, source_id=source_id, segments=source_segments))
    return aspects


def improvement_lead_candidate_payloads(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Describe what ``improvement_lead_candidate_payloads`` does in one
    line (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        nodes: ``nodes`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        list[dict[str, Any]]:
            Returns a value of type ``list[dict[str, Any]]``; see the function body for structure, error paths, and sentinels.
    """
    candidate_payloads: list[dict[str, Any]] = []
    for node in nodes:
        is_candidate, reason = evaluate_candidate_from_exploration_node(node)
        if not is_candidate:
            continue
        candidate_payloads.append(
            {
                "claim_type": "improvement_lead",
                "statement": node.get("hypothesis"),
                "evidence_anchor_ids": list(node.get("evidence_anchor_ids", [])),
                "perspective": node.get("perspective"),
                "notes": reason,
                "canon_relevance_hint": canon_relevance_hint(node),
            }
        )
    return candidate_payloads
