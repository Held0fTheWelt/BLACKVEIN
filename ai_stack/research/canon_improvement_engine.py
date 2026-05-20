"""Deterministic canon issue detection and proposal generation."""

from __future__ import annotations

from typing import Any

from ai_stack.research.canon_improvement_contract import proposal_for_issue
from ai_stack.research.research_contract import (
    CanonIssueRecord,
    CanonIssueType,
    ImprovementProposalRecord,
    ResearchStatus,
)
from ai_stack.research.research_store import ResearchStore


# Keyword tuples tie informal reviewer language to ``CanonIssueType`` plus a
# coarse severity hint so downstream proposals stay consistent across modules.
_ISSUE_KEYWORDS: tuple[tuple[CanonIssueType, tuple[str, ...], str], ...] = (
    (CanonIssueType.WEAK_ESCALATION, ("flat", "no escalation", "weak escalation"), "medium"),
    (CanonIssueType.UNCLEAR_SCENE_FUNCTION, ("unclear function", "scene unclear"), "high"),
    (CanonIssueType.INSUFFICIENT_SUBTEXT, ("on the nose", "insufficient subtext", "explicit"), "medium"),
    (CanonIssueType.REDUNDANT_DIALOGUE, ("redundant", "repetition"), "medium"),
    (CanonIssueType.MISSING_PAYOFF_PREPARATION, ("missing payoff", "not prepared"), "high"),
    (CanonIssueType.UNDERPOWERED_STATUS_SHIFT, ("status unchanged", "underpowered status"), "medium"),
    (CanonIssueType.NARROW_ACTION_SPACE, ("limited options", "narrow action"), "medium"),
    (CanonIssueType.THEME_NOT_EMBODIED, ("theme not embodied", "theme abstract"), "medium"),
    (CanonIssueType.MOTIVATION_GAP, ("motivation gap", "unclear motivation"), "high"),
    (CanonIssueType.UNUSED_STAGING_POTENTIAL, ("staging potential", "unused staging"), "low"),
)


def _classify_issue(statement: str) -> tuple[CanonIssueType, str]:
    """Infer a canon issue type and severity label from natural-language text.
    
    Args:
        statement: Claim or reviewer sentence describing a dramatic
            weakness.
    
    Returns:
        tuple[CanonIssueType, str]:
            Best-matching ``CanonIssueType`` and a ``low`` /
                ``medium`` / ``high``
            severity string; defaults to unclear scene function at
                medium weight
            when no token hits.
    """
    lowered = statement.lower()
    # Walk the curated keyword table so the first lexical hit wins; ordering
    # therefore matters when phrases overlap between adjacent issue families.
    for issue_type, tokens, severity in _ISSUE_KEYWORDS:
        if any(token in lowered for token in tokens):
            return issue_type, severity
    return CanonIssueType.UNCLEAR_SCENE_FUNCTION, "medium"


def _preview_payload(module_id: str, proposal_type: str, claim_ids: list[str]) -> dict[str, Any]:
    """Build a preview-only payload describing a hypothetical canon patch.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        proposal_type: ``proposal_type`` (str); meaning follows the type and call sites.
        claim_ids: ``claim_ids`` (list[str]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    return {
        "module_id": module_id,
        "proposal_type": proposal_type,
        "supporting_claim_ids": list(claim_ids),
        "preview_kind": "recommendation_only",
        "mutation_allowed": False,
        "patch_outline": [
            "analyze_claim_links",
            "apply_structural_adjustment",
            "review_before_publish",
        ],
    }


def derive_canon_improvements(
    *,
    store: ResearchStore,
    module_id: str,
    claims: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist canon issues and improvement proposals from validated
    research claims.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        store: ``store`` (ResearchStore); meaning follows the type and call sites.
        module_id: ``module_id`` (str); meaning follows the type and call sites.
        claims: ``claims`` (list[dict[str, Any]]); meaning follows the type and call sites.
    
    Returns:
        dict[str, Any]:
            Returns a value of type ``dict[str, Any]``; see the function body for structure, error paths, and sentinels.
    """
    issues: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []

    # Stable ordering keeps regression tests and operator diffs deterministic when
    # the same claim batch is reprocessed after partial failures or retries.
    ordered_claims = sorted(
        [c for c in claims if c.get("status") in {ResearchStatus.APPROVED_RESEARCH.value, ResearchStatus.CANON_APPLICABLE.value}],
        key=lambda row: (str(row.get("claim_id", "")), str(row.get("statement", ""))),
    )
    for claim in ordered_claims:
        claim_id = str(claim.get("claim_id", ""))
        statement = str(claim.get("statement", ""))
        # Classify narrative risk from natural language so downstream proposal
        # templates align with the closest canon issue archetype.
        issue_type, severity = _classify_issue(statement)
        issue = CanonIssueRecord(
            issue_id=store.next_id("issue"),
            module_id=module_id,
            issue_type=issue_type,
            severity=severity,
            description=f"{issue_type.value}: derived from validated claim",
            supporting_claim_ids=[claim_id],
            status=ResearchStatus.APPROVED_RESEARCH,
        ).to_dict()
        stored_issue = store.upsert_issue(issue)
        issues.append(stored_issue)

        # Map the classified issue to a default improvement shape so operators see a
        # concrete next step without inventing proposal types ad hoc in the UI.
        proposal_type = proposal_for_issue(issue_type)
        proposal = ImprovementProposalRecord(
            proposal_id=store.next_id("proposal"),
            module_id=module_id,
            proposal_type=proposal_type,
            rationale=f"Mapped from issue {issue_type.value}",
            expected_effect=f"Improve canon signal for {issue_type.value}",
            supporting_claim_ids=[claim_id],
            preview_patch_ref=_preview_payload(module_id, proposal_type.value, [claim_id]),
            status=ResearchStatus.APPROVED_RESEARCH,
        ).to_dict()
        stored_proposal = store.upsert_proposal(proposal)
        proposals.append(stored_proposal)

    return {
        "issues": issues,
        "proposals": proposals,
    }
