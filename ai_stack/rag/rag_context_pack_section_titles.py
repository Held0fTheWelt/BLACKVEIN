"""
Profile/role → human-readable section headings for context-pack
``compact_context`` (DS-009 optional).
"""

from __future__ import annotations


def section_title_for_pack_role(profile: str, role: str) -> str | None:
    """Describe what ``section_title_for_pack_role`` does in one line
    (verb-led summary for this function).
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        profile: ``profile`` (str); meaning follows the type and call sites.
        role: ``role`` (str); meaning follows the type and call sites.
    
    Returns:
        str | None:
            Returns a value of type ``str | None``; see the function body for structure, error paths, and sentinels.
    """
    if profile == "runtime_turn_support":
        if role == "canonical_evidence":
            return "Canonical evidence"
        if role == "policy_evidence":
            return "Policy evidence"
        if role == "supporting_context":
            return "Supporting context"
    elif profile == "improvement_eval":
        if role == "evaluative_evidence":
            return "Evaluative evidence"
        if role == "supporting_context":
            return "Supporting context"
    elif profile == "writers_review":
        if role == "authored_context":
            return "Authored context"
        if role == "draft_working_context":
            return "Draft / working material"
        if role == "review_context":
            return "Review context"
        if role == "supporting_context":
            return "Supporting context"
    return None
