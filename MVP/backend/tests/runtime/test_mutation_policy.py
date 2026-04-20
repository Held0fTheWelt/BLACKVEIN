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


class TestMutationPolicyEvaluation:
    """Test the core policy evaluation logic."""

    def test_whitelisted_character_emotional_state_allowed(self):
        """characters.*.emotional_state is whitelisted."""
        decision = MutationPolicy.evaluate("characters.veronique.emotional_state")
        assert decision.allowed is True
        assert decision.reason_code is None

    def test_whitelisted_relationship_value_allowed(self):
        """relationships.*.value is whitelisted."""
        decision = MutationPolicy.evaluate("relationships.veronique_alain.value")
        assert decision.allowed is True

    def test_whitelisted_conflict_escalation_allowed(self):
        """conflict_state.escalation (global) is whitelisted."""
        decision = MutationPolicy.evaluate("conflict_state.escalation")
        assert decision.allowed is True

    def test_blocked_session_domain(self):
        """session.* is blocked."""
        decision = MutationPolicy.evaluate("session.id")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_root_domain"
        assert "session" in decision.reason_message.lower()

    def test_blocked_internal_field(self):
        """*._* pattern blocks internal fields."""
        decision = MutationPolicy.evaluate("characters.veronique._cache")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_internal_field"

    def test_valid_path_but_blocked_mutation(self):
        """Path exists but mutation is blocked (valid path ≠ allowed mutation)."""
        # characters is allowed domain, but secret_backstory is not whitelisted
        decision = MutationPolicy.evaluate("characters.veronique.secret_backstory")
        assert decision.allowed is False
        assert decision.reason_code == "not_whitelisted"

    def test_unknown_root_denied_by_default(self):
        """Unknown root domain denied by default."""
        decision = MutationPolicy.evaluate("unknown_domain.field")
        assert decision.allowed is False
        assert decision.reason_code == "out_of_scope_root"

    def test_conflict_state_nested_rejected(self):
        """conflict_state is global, not per-scene (conflict_state.kitchen.escalation rejected)."""
        decision = MutationPolicy.evaluate("conflict_state.kitchen.escalation")
        assert decision.allowed is False
        # Either blocked by pattern mismatch or not whitelisted
        assert decision.reason_code in ["not_whitelisted", "blocked_root_domain"]


class TestMutationPolicyEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_characters_metadata_blocked(self):
        """characters.veronique.metadata is blocked (metadata is protected)."""
        decision = MutationPolicy.evaluate("characters.veronique.metadata")
        assert decision.allowed is False

    def test_characters_cached_score_blocked(self):
        """*.cached_* pattern blocks cached fields."""
        decision = MutationPolicy.evaluate("characters.veronique.cached_score")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_technical_field"

    def test_characters_cache_field_blocked(self):
        """*.cache pattern blocks .cache fields."""
        decision = MutationPolicy.evaluate("characters.veronique.cache")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_technical_field"

    def test_characters_dunder_field_blocked(self):
        """*.__* pattern blocks double-underscore fields."""
        decision = MutationPolicy.evaluate("characters.veronique.__internal")
        assert decision.allowed is False
        assert decision.reason_code == "blocked_internal_field"

    def test_relationships_complex_path(self):
        """relationships.*.value matches relationships with any character pair."""
        decision = MutationPolicy.evaluate("relationships.veronique_alain.value")
        assert decision.allowed is True

        decision = MutationPolicy.evaluate("relationships.catherine_serge.value")
        assert decision.allowed is True

    def test_scene_state_pressure_allowed(self):
        """scene_state.*.pressure is whitelisted."""
        decision = MutationPolicy.evaluate("scene_state.kitchen.pressure")
        assert decision.allowed is True

        decision = MutationPolicy.evaluate("scene_state.living_room.pressure")
        assert decision.allowed is True

    def test_scene_state_invalid_field_blocked(self):
        """scene_state.*.invalid_field is not whitelisted."""
        decision = MutationPolicy.evaluate("scene_state.kitchen.invalid_field")
        assert decision.allowed is False
        assert decision.reason_code == "not_whitelisted"

    def test_multiple_component_underscores(self):
        """Fields with underscores in the middle (like emotion_state) are ok if whitelisted."""
        # emotional_state is whitelisted, so underscore in middle is ok
        decision = MutationPolicy.evaluate("characters.veronique.emotional_state")
        assert decision.allowed is True

    def test_blocked_rules_win(self):
        """Blocked rules take priority over whitelist intent."""
        # Even if pattern could theoretically match, blocked patterns win
        decision = MutationPolicy.evaluate("characters.veronique._secret")
        assert decision.allowed is False

    def test_empty_path_rejected(self):
        """Empty path is rejected."""
        decision = MutationPolicy.evaluate("")
        assert decision.allowed is False

    def test_none_path_rejected(self):
        """None path is rejected."""
        decision = MutationPolicy.evaluate(None)
        assert decision.allowed is False

    def test_characters_tension_allowed(self):
        """characters.*.tension is whitelisted."""
        decision = MutationPolicy.evaluate("characters.veronique.tension")
        assert decision.allowed is True

    def test_characters_stance_allowed(self):
        """characters.*.stance is whitelisted."""
        decision = MutationPolicy.evaluate("characters.catherine.stance")
        assert decision.allowed is True

    def test_scene_state_conflict_allowed(self):
        """scene_state.*.conflict is whitelisted."""
        decision = MutationPolicy.evaluate("scene_state.kitchen.conflict")
        assert decision.allowed is True

    def test_conflict_state_intensity_allowed(self):
        """conflict_state.intensity is whitelisted."""
        decision = MutationPolicy.evaluate("conflict_state.intensity")
        assert decision.allowed is True


class TestMutationPolicyIntegration:
    """Integration tests with validators."""

    def test_validate_delta_rejects_blocked_path(self):
        """Blocked mutations are rejected in validation pipeline."""
        from app.runtime.turn_executor import ProposedStateDelta
        from app.runtime.validators import _validate_delta

        delta = ProposedStateDelta(
            target="session.id",
            next_value="new_session"
        )

        class MockModule:
            characters = {}
            relationship_axes = {}
            scene_phases = {}
            phase_transitions = {}

        class MockSession:
            pass

        errors = _validate_delta(delta, MockSession(), MockModule())
        assert len(errors) > 0
        # Should have mutation permission error
        assert any("mutation" in e.lower() or "blocked" in e.lower() for e in errors)

    def test_validate_delta_accepts_allowed_path(self):
        """Allowed mutations are accepted in validation pipeline."""
        from app.runtime.turn_executor import ProposedStateDelta
        from app.runtime.validators import _validate_delta

        delta = ProposedStateDelta(
            target="characters.veronique.emotional_state",
            next_value=75
        )

        class MockModule:
            characters = {"veronique": {}}
            relationship_axes = {}
            scene_phases = {}
            phase_transitions = {}

        class MockSession:
            pass

        errors = _validate_delta(delta, MockSession(), MockModule())
        # May have other validation errors, but not mutation permission error
        mutation_errors = [e for e in errors if "mutation" in e.lower() or "blocked" in e.lower()]
        assert len(mutation_errors) == 0
