import pytest
from app.runtime.mutation_policy import MutationPolicyDecision, MutationPolicy

def test_mutation_policy_decision_allowed():
    """MutationPolicyDecision represents allowed mutation."""
    decision = MutationPolicyDecision(allowed=True)
    assert decision.allowed is True
    assert decision.reason_code is None
    assert decision.reason_message is None

def test_mutation_policy_decision_blocked():
    """MutationPolicyDecision represents blocked mutation."""
    decision = MutationPolicyDecision(
        allowed=False,
        reason_code="blocked_root_domain",
        reason_message="Protected domain: session"
    )
    assert decision.allowed is False
    assert decision.reason_code == "blocked_root_domain"
    assert decision.reason_message == "Protected domain: session"


class TestMutationPolicyStructure:
    """Test the policy structure and domain definitions."""

    def test_allowed_domains_defined(self):
        """Allowed domains are explicitly defined."""
        assert hasattr(MutationPolicy, 'ALLOWED_DOMAINS')
        assert MutationPolicy.ALLOWED_DOMAINS == {
            "characters", "relationships", "scene_state", "conflict_state"
        }

    def test_protected_domains_defined(self):
        """Protected domains are explicitly defined."""
        assert hasattr(MutationPolicy, 'PROTECTED_DOMAINS')
        assert MutationPolicy.PROTECTED_DOMAINS == {
            "metadata", "runtime", "system", "logs", "decision", "session", "turn", "cache"
        }

    def test_whitelist_patterns_defined(self):
        """Whitelist patterns are defined for allowed domains."""
        assert hasattr(MutationPolicy, 'WHITELIST_PATTERNS')
        assert len(MutationPolicy.WHITELIST_PATTERNS) == 8
        assert "characters.*.emotional_state" in MutationPolicy.WHITELIST_PATTERNS
        assert "conflict_state.escalation" in MutationPolicy.WHITELIST_PATTERNS

    def test_blocked_patterns_defined(self):
        """Blocked patterns prevent mutations of protected/technical fields."""
        assert hasattr(MutationPolicy, 'BLOCKED_PATTERNS')
        assert len(MutationPolicy.BLOCKED_PATTERNS) > 0
        assert "session.*" in MutationPolicy.BLOCKED_PATTERNS
        assert "*._*" in MutationPolicy.BLOCKED_PATTERNS
