"""
Turn-level retrieval governance visibility for operator diagnostics (G5
/ G10).

Aggregates evidence-lane and visibility-class histograms from retrieval
hit rows without changing ranking or retrieval policy. Authored vs
derived provenance lists are built once here and projected into turn
seams and traces (single canonical path).
"""

from __future__ import annotations

from typing import Any

from ai_stack.rag import (
    RETRIEVAL_POLICY_VERSION,
    ContentClass,
    SourceVisibilityClass,
)

# Cap compact ref lists for bounded turn / trace payloads.
_MAX_COMPACT_REFS_PER_PARTITION = 48


def _visibility_tie_break_order() -> dict[str, int]:
    """Canonical ordering for SourceVisibilityClass (enum declaration order
    in rag_types.py).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Returns:
        dict[str, int]:
            Returns a value of type ``dict[str, int]``; see the function body for structure, error paths, and sentinels.
    """
    return {m.value: i for i, m in enumerate(SourceVisibilityClass)}


def dominant_visibility_class_from_counts(visibility_counts: dict[str, int]) -> str | None:
    """Highest count wins; ties broken by SourceVisibilityClass declaration
    order; empty → None.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        visibility_counts: ``visibility_counts`` (dict[str, int]); meaning follows the type and call sites.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    if not visibility_counts:
        return None
    max_n = max(visibility_counts.values())
    tied = [k for k, v in visibility_counts.items() if v == max_n]
    order = _visibility_tie_break_order()
    tied.sort(key=lambda k: (order.get(k, len(SourceVisibilityClass)), k))
    return tied[0]


def _compact_ref_from_row(row: dict[str, Any]) -> dict[str, Any]:
    """``_compact_ref_from_row`` — see implementation for behaviour and contracts.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        row: ``row`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "chunk_id": row.get("chunk_id"),
        "source_path": row.get("source_path"),
        "content_class": str(row.get("content_class") or "unspecified_content_class"),
        "source_evidence_lane": str(
            row.get("source_evidence_lane") or row.get("evidence_lane") or "unspecified_lane"
        ),
        "source_visibility_class": str(
            row.get("source_visibility_class")
            or row.get("visibility_class")
            or "unspecified_visibility"
        ),
    }


def summarize_retrieval_governance_from_hit_rows(sources: Any) -> dict[str, Any]:
    """Build a bounded summary dict from ``retrieval["sources"]`` rows.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        sources: ``sources`` (Any); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    authored_val = ContentClass.AUTHORED_MODULE.value
    base: dict[str, Any] = {
        "source_row_count": 0,
        "lane_counts": {},
        "visibility_counts": {},
        "content_class_counts": {},
        "authored_truth_refs": [],
        "derived_artifact_refs": [],
        "dominant_visibility_class": None,
        "retrieval_policy_version": RETRIEVAL_POLICY_VERSION,
    }
    if not isinstance(sources, list):
        return base

    lane_counts: dict[str, int] = {}
    vis_counts: dict[str, int] = {}
    cc_counts: dict[str, int] = {}
    authored_refs: list[dict[str, Any]] = []
    derived_refs: list[dict[str, Any]] = []

    for row in sources:
        if not isinstance(row, dict):
            continue
        lane = str(
            row.get("source_evidence_lane") or row.get("evidence_lane") or "unspecified_lane"
        )
        vis = str(
            row.get("source_visibility_class")
            or row.get("visibility_class")
            or "unspecified_visibility"
        )
        cc = str(row.get("content_class") or "unspecified_content_class")
        lane_counts[lane] = lane_counts.get(lane, 0) + 1
        vis_counts[vis] = vis_counts.get(vis, 0) + 1
        cc_counts[cc] = cc_counts.get(cc, 0) + 1
        ref = _compact_ref_from_row(row)
        if cc == authored_val:
            if len(authored_refs) < _MAX_COMPACT_REFS_PER_PARTITION:
                authored_refs.append(ref)
        else:
            if len(derived_refs) < _MAX_COMPACT_REFS_PER_PARTITION:
                derived_refs.append(ref)

    base.update(
        {
            "source_row_count": len(sources),
            "lane_counts": lane_counts,
            "visibility_counts": vis_counts,
            "content_class_counts": cc_counts,
            "authored_truth_refs": authored_refs,
            "derived_artifact_refs": derived_refs,
            "dominant_visibility_class": dominant_visibility_class_from_counts(vis_counts),
        }
    )
    return base


def attach_retrieval_governance_summary(retrieval: dict[str, Any]) -> None:
    """Mutate ``retrieval`` in place with ``retrieval_governance_summary``.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        retrieval: ``retrieval`` (dict[str, Any]); meaning follows the type and call sites.
    """
    if not isinstance(retrieval, dict):
        return
    retrieval["retrieval_governance_summary"] = summarize_retrieval_governance_from_hit_rows(
        retrieval.get("sources")
    )
