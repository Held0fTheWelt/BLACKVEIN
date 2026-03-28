import pytest
from app.runtime.reference_policy import ReferencePolicyDecision


def test_reference_policy_decision_allowed():
    """ReferencePolicyDecision represents allowed reference."""
    decision = ReferencePolicyDecision(allowed=True)
    assert decision.allowed is True
    assert decision.reason_code is None
    assert decision.reason_message is None


def test_reference_policy_decision_blocked():
    """ReferencePolicyDecision represents blocked reference."""
    decision = ReferencePolicyDecision(
        allowed=False,
        reason_code="unknown_character",
        reason_message="Character 'nonexistent' not in module"
    )
    assert decision.allowed is False
    assert decision.reason_code == "unknown_character"
    assert decision.reason_message == "Character 'nonexistent' not in module"
