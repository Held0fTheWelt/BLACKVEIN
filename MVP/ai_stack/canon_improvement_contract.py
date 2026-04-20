"""Canonical contract helpers for canon issues and improvement proposals."""

from __future__ import annotations

from ai_stack.research_contract import CanonIssueType, ImprovementProposalType


ISSUE_TO_PROPOSAL_DEFAULT: dict[CanonIssueType, ImprovementProposalType] = {
    CanonIssueType.WEAK_ESCALATION: ImprovementProposalType.RESTRUCTURE_PRESSURE_CURVE,
    CanonIssueType.UNCLEAR_SCENE_FUNCTION: ImprovementProposalType.TIGHTEN_CONFLICT_CORE,
    CanonIssueType.INSUFFICIENT_SUBTEXT: ImprovementProposalType.SHARPEN_SUBTEXT,
    CanonIssueType.REDUNDANT_DIALOGUE: ImprovementProposalType.CONVERT_EXPOSITION_TO_PLAYABLE_ACTION,
    CanonIssueType.MISSING_PAYOFF_PREPARATION: ImprovementProposalType.IMPROVE_PAYOFF_PREPARATION,
    CanonIssueType.UNDERPOWERED_STATUS_SHIFT: ImprovementProposalType.STRENGTHEN_STATUS_REVERSAL,
    CanonIssueType.NARROW_ACTION_SPACE: ImprovementProposalType.WIDEN_ACTION_SPACE,
    CanonIssueType.THEME_NOT_EMBODIED: ImprovementProposalType.EMBODY_THEME_THROUGH_FRICTION,
    CanonIssueType.MOTIVATION_GAP: ImprovementProposalType.INTRODUCE_EARLIER_TACTIC_SHIFT,
    CanonIssueType.UNUSED_STAGING_POTENTIAL: ImprovementProposalType.ACTIVATE_STAGING_LEVERAGE,
}


def ensure_issue_type(value: str) -> CanonIssueType:
    try:
        return CanonIssueType(value)
    except ValueError as exc:
        raise ValueError(f"invalid_issue_type:{value}") from exc


def ensure_proposal_type(value: str) -> ImprovementProposalType:
    try:
        return ImprovementProposalType(value)
    except ValueError as exc:
        raise ValueError(f"invalid_proposal_type:{value}") from exc


def proposal_for_issue(issue_type: CanonIssueType) -> ImprovementProposalType:
    return ISSUE_TO_PROPOSAL_DEFAULT[issue_type]
