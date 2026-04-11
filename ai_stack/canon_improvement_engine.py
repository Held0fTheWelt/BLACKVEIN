"""Deterministic canon issue detection and proposal generation."""

from __future__ import annotations

from typing import Any

from ai_stack.canon_improvement_contract import proposal_for_issue
from ai_stack.research_contract import (
    CanonIssueRecord,
    CanonIssueType,
    ImprovementProposalRecord,
    ResearchStatus,
)
from ai_stack.research_store import ResearchStore


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
    lowered = statement.lower()
    for issue_type, tokens, severity in _ISSUE_KEYWORDS:
        if any(token in lowered for token in tokens):
            return issue_type, severity
    return CanonIssueType.UNCLEAR_SCENE_FUNCTION, "medium"


def _preview_payload(module_id: str, proposal_type: str, claim_ids: list[str]) -> dict[str, Any]:
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
    issues: list[dict[str, Any]] = []
    proposals: list[dict[str, Any]] = []

    ordered_claims = sorted(
        [c for c in claims if c.get("status") in {ResearchStatus.APPROVED_RESEARCH.value, ResearchStatus.CANON_APPLICABLE.value}],
        key=lambda row: (str(row.get("claim_id", "")), str(row.get("statement", ""))),
    )
    for claim in ordered_claims:
        claim_id = str(claim.get("claim_id", ""))
        statement = str(claim.get("statement", ""))
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
