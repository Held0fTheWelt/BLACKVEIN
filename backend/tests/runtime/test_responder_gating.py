"""Tests for W2.4.5 responder-only proposal gating."""

import pytest
from app.runtime.w2_models import MockDecision, ProposalSource, ProposedStateDelta


def test_mock_decision_requires_proposal_source():
    """MockDecision requires explicit proposal_source (not defaulted to responder)."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    # Test that creating without proposal_source uses conservative MOCK default
    decision = MockDecision(
        proposed_deltas=[delta],
    )

    # Default must be MOCK (non-authoritative), not RESPONDER_DERIVED
    assert decision.proposal_source == ProposalSource.MOCK
    assert len(decision.proposed_deltas) == 1


def test_mock_decision_accepts_explicit_proposal_source():
    """MockDecision accepts explicit proposal_source field."""
    delta = ProposedStateDelta(
        target="characters.alice.emotional_state",
        next_value=75,
        delta_type=None,
        source="ai_proposal",
    )

    decision = MockDecision(
        proposed_deltas=[delta],
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )

    assert decision.proposal_source == ProposalSource.RESPONDER_DERIVED


def test_proposal_source_enum_has_all_values():
    """ProposalSource enum has all required values."""
    assert hasattr(ProposalSource, "RESPONDER_DERIVED")
    assert hasattr(ProposalSource, "MOCK")
    assert hasattr(ProposalSource, "ENGINE")
    assert hasattr(ProposalSource, "OPERATOR")
