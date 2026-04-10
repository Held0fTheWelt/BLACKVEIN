# ai_stack/tests/test_canon_improvement_contract.py
from __future__ import annotations

import pytest

from ai_stack.canon_improvement_contract import (
    ensure_issue_type,
    ensure_proposal_type,
    proposal_for_issue,
    ISSUE_TO_PROPOSAL_DEFAULT,
)
from ai_stack.research_contract import CanonIssueType, ImprovementProposalType


def test_ensure_issue_type_raises_on_invalid_value() -> None:
    with pytest.raises(ValueError) as exc_info:
        ensure_issue_type("INVALID_ENUM_NAME")
    assert "invalid_issue_type:INVALID_ENUM_NAME" in str(exc_info.value)


def test_ensure_issue_type_valid_by_value() -> None:
    result = ensure_issue_type("weak_escalation")
    assert result == CanonIssueType.WEAK_ESCALATION


def test_ensure_proposal_type_raises_on_invalid_value() -> None:
    with pytest.raises(ValueError) as exc_info:
        ensure_proposal_type("FAKE_PROPOSAL")
    assert "invalid_proposal_type:FAKE_PROPOSAL" in str(exc_info.value)


def test_ensure_proposal_type_valid_by_value() -> None:
    result = ensure_proposal_type("restructure_pressure_curve")
    assert result == ImprovementProposalType.RESTRUCTURE_PRESSURE_CURVE


def test_proposal_for_issue_returns_mapped_proposal() -> None:
    issue = CanonIssueType.WEAK_ESCALATION
    proposal = proposal_for_issue(issue)
    assert proposal == ISSUE_TO_PROPOSAL_DEFAULT[issue]


def test_proposal_for_issue_all_issue_types_mapped() -> None:
    for issue_type in CanonIssueType:
        proposal = proposal_for_issue(issue_type)
        assert isinstance(proposal, ImprovementProposalType)
        assert proposal in ISSUE_TO_PROPOSAL_DEFAULT.values()
