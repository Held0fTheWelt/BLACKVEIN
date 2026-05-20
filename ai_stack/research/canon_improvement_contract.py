"""Canonical contract helpers for canon issues and improvement proposals."""

from __future__ import annotations

from ai_stack.research.research_contract import CanonIssueType, ImprovementProposalType


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
    """Parse *value* into a ``CanonIssueType`` member for validated
    payloads.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        CanonIssueType:
            Returns a value of type ``CanonIssueType``; see the function body for structure, error paths, and sentinels.
    """
    try:
        return CanonIssueType(value)
    except ValueError as exc:
        raise ValueError(f"invalid_issue_type:{value}") from exc


def ensure_proposal_type(value: str) -> ImprovementProposalType:
    """Parse *value* into an ``ImprovementProposalType`` member.
    
    Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
    
    Args:
        value: ``value`` (str); meaning follows the type and call sites.
    
    Returns:
        ImprovementProposalType:
            Returns a value of type ``ImprovementProposalType``; see the function body for structure, error paths, and sentinels.
    """
    try:
        return ImprovementProposalType(value)
    except ValueError as exc:
        raise ValueError(f"invalid_proposal_type:{value}") from exc


def proposal_for_issue(issue_type: CanonIssueType) -> ImprovementProposalType:
    """Return the default improvement proposal kind for a canon issue
        archetype.
    
    Args:
        issue_type: Classified issue used when mapping research to
            actionables.
    
    Returns:
        ImprovementProposalType:
            Default proposal template from
                ``ISSUE_TO_PROPOSAL_DEFAULT`` for the
            given *issue_type*.
    """
    return ISSUE_TO_PROPOSAL_DEFAULT[issue_type]
