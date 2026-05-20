"""Claim-shape helpers for deterministic research promotion."""

from __future__ import annotations

from typing import Any


RECOGNIZED_CLAIM_TYPES: tuple[str, ...] = (
    "dramatic_function",
    "conflict_pattern",
    "status_shift",
    "staging_leverage",
    "subtext_signal",
    "motivation_link",
    "theme_linkage",
    "improvement_lead",
)


def is_recognized_claim_type(value: Any) -> bool:
    """Describe what ``is_recognized_claim_type`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (Any); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    return isinstance(value, str) and value in RECOGNIZED_CLAIM_TYPES


def is_schema_valid_claim_payload(payload: dict[str, Any]) -> bool:
    """Describe what ``is_schema_valid_claim_payload`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        payload: ``payload`` (dict[str, Any]); meaning follows the type and call sites.
    
    Returns:
        bool:
            Returns a value of type ``bool``; see the function body for structure, error paths, and sentinels.
    """
    required = (
        "claim_type",
        "statement",
        "evidence_anchor_ids",
        "perspective",
    )
    for key in required:
        if key not in payload:
            return False
    if not is_recognized_claim_type(payload.get("claim_type")):
        return False
    if not isinstance(payload.get("statement"), str) or not payload["statement"].strip():
        return False
    anchors = payload.get("evidence_anchor_ids")
    if not isinstance(anchors, list) or not anchors:
        return False
    if any(not isinstance(anchor_id, str) or not anchor_id.strip() for anchor_id in anchors):
        return False
    return True
