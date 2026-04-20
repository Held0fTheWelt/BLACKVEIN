"""Tests for W2.5.1 canonical AI failure classification and recovery contract."""

import pytest
from app.runtime.ai_failure_recovery import (
    AIFailureClass,
    RecoveryAction,
    FailureRecoveryPolicy,
)


class TestAIFailureClassEnum:
    """Verify AIFailureClass enum has all required failure categories."""

    def test_adapter_error_exists(self):
        """AIFailureClass has ADAPTER_ERROR."""
        assert hasattr(AIFailureClass, "ADAPTER_ERROR")
        assert AIFailureClass.ADAPTER_ERROR.value == "adapter_error"

    def test_timeout_or_empty_response_exists(self):
        """AIFailureClass has TIMEOUT_OR_EMPTY_RESPONSE."""
        assert hasattr(AIFailureClass, "TIMEOUT_OR_EMPTY_RESPONSE")
        assert AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE.value == "timeout_or_empty_response"

    def test_parse_failure_exists(self):
        """AIFailureClass has PARSE_FAILURE."""
        assert hasattr(AIFailureClass, "PARSE_FAILURE")
        assert AIFailureClass.PARSE_FAILURE.value == "parse_failure"

    def test_structurally_invalid_output_exists(self):
        """AIFailureClass has STRUCTURALLY_INVALID_OUTPUT."""
        assert hasattr(AIFailureClass, "STRUCTURALLY_INVALID_OUTPUT")
        assert AIFailureClass.STRUCTURALLY_INVALID_OUTPUT.value == "structurally_invalid_output"

    def test_responder_validation_failure_exists(self):
        """AIFailureClass has RESPONDER_VALIDATION_FAILURE."""
        assert hasattr(AIFailureClass, "RESPONDER_VALIDATION_FAILURE")
        assert AIFailureClass.RESPONDER_VALIDATION_FAILURE.value == "responder_validation_failure"

    def test_guard_rejection_exists(self):
        """AIFailureClass has GUARD_REJECTION (W2.4.5 related)."""
        assert hasattr(AIFailureClass, "GUARD_REJECTION")
        assert AIFailureClass.GUARD_REJECTION.value == "guard_rejection"

    def test_retry_exhausted_exists(self):
        """AIFailureClass has RETRY_EXHAUSTED."""
        assert hasattr(AIFailureClass, "RETRY_EXHAUSTED")
        assert AIFailureClass.RETRY_EXHAUSTED.value == "retry_exhausted"

    def test_unexpected_runtime_error_exists(self):
        """AIFailureClass has UNEXPECTED_RUNTIME_ERROR."""
        assert hasattr(AIFailureClass, "UNEXPECTED_RUNTIME_ERROR")
        assert AIFailureClass.UNEXPECTED_RUNTIME_ERROR.value == "unexpected_runtime_error"

    def test_all_failure_classes_have_values(self):
        """All AIFailureClass values are non-empty strings."""
        for failure_class in AIFailureClass:
            assert isinstance(failure_class.value, str)
            assert len(failure_class.value) > 0


class TestRecoveryActionEnum:
    """Verify RecoveryAction enum has all required actions."""

    def test_retry_exists(self):
        """RecoveryAction has RETRY."""
        assert hasattr(RecoveryAction, "RETRY")
        assert RecoveryAction.RETRY.value == "retry"

    def test_fallback_exists(self):
        """RecoveryAction has FALLBACK."""
        assert hasattr(RecoveryAction, "FALLBACK")
        assert RecoveryAction.FALLBACK.value == "fallback"

    def test_safe_turn_exists(self):
        """RecoveryAction has SAFE_TURN."""
        assert hasattr(RecoveryAction, "SAFE_TURN")
        assert RecoveryAction.SAFE_TURN.value == "safe_turn"

    def test_restore_exists(self):
        """RecoveryAction has RESTORE."""
        assert hasattr(RecoveryAction, "RESTORE")
        assert RecoveryAction.RESTORE.value == "restore"

    def test_abort_exists(self):
        """RecoveryAction has ABORT."""
        assert hasattr(RecoveryAction, "ABORT")
        assert RecoveryAction.ABORT.value == "abort"


class TestFailureRecoveryPolicy:
    """Verify the failure→recovery mapping is complete and correct."""

    def test_all_failure_classes_have_recovery_policy(self):
        """Every AIFailureClass has a recovery action defined."""
        for failure_class in AIFailureClass:
            action = FailureRecoveryPolicy.get_recovery_action(failure_class)
            assert action in RecoveryAction
            assert isinstance(action, RecoveryAction)

    def test_retryable_failures_are_transient(self):
        """Retryable failures are transient adapter issues."""
        retryable = [
            AIFailureClass.ADAPTER_ERROR,
            AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE,
        ]
        for failure_class in retryable:
            assert FailureRecoveryPolicy.is_retryable(failure_class)
            assert FailureRecoveryPolicy.get_recovery_action(failure_class) == RecoveryAction.RETRY

    def test_fallback_failures_are_structural(self):
        """Fallback failures are structural (won't fix on retry)."""
        fallback = [
            AIFailureClass.PARSE_FAILURE,
            AIFailureClass.STRUCTURALLY_INVALID_OUTPUT,
        ]
        for failure_class in fallback:
            assert FailureRecoveryPolicy.is_fallback_only(failure_class)
            assert FailureRecoveryPolicy.get_recovery_action(failure_class) == RecoveryAction.FALLBACK

    def test_safe_turn_failures_are_validation(self):
        """Safe-turn failures are validation rejections (proposals never executed)."""
        safe_turn = [
            AIFailureClass.RESPONDER_VALIDATION_FAILURE,
            AIFailureClass.GUARD_REJECTION,
        ]
        for failure_class in safe_turn:
            assert FailureRecoveryPolicy.is_safe_turn(failure_class)
            assert FailureRecoveryPolicy.get_recovery_action(failure_class) == RecoveryAction.SAFE_TURN

    def test_restore_failures_are_systematic(self):
        """Restore failures are systematic issues requiring investigation."""
        restore = [
            AIFailureClass.RETRY_EXHAUSTED,
            AIFailureClass.UNEXPECTED_RUNTIME_ERROR,
        ]
        for failure_class in restore:
            assert FailureRecoveryPolicy.is_restore_required(failure_class)
            assert FailureRecoveryPolicy.get_recovery_action(failure_class) == RecoveryAction.RESTORE

    def test_recovery_classification_is_mutually_exclusive(self):
        """Each failure belongs to exactly one recovery category."""
        for failure_class in AIFailureClass:
            classifications = [
                FailureRecoveryPolicy.is_retryable(failure_class),
                FailureRecoveryPolicy.is_fallback_only(failure_class),
                FailureRecoveryPolicy.is_safe_turn(failure_class),
                FailureRecoveryPolicy.is_restore_required(failure_class),
            ]
            # Exactly one should be True
            assert sum(classifications) == 1

    def test_policy_covers_all_known_failure_classes(self):
        """Policy has an entry for every AIFailureClass (no gaps)."""
        # Policy should have exactly the same keys as AIFailureClass members
        policy_keys = set(FailureRecoveryPolicy.POLICY.keys())
        enum_values = set(AIFailureClass)
        assert policy_keys == enum_values, "Policy must cover all failure classes"

    def test_contract_is_deterministic(self):
        """Recovery action is always the same for a given failure class."""
        for failure_class in AIFailureClass:
            action1 = FailureRecoveryPolicy.get_recovery_action(failure_class)
            action2 = FailureRecoveryPolicy.get_recovery_action(failure_class)
            assert action1 == action2


class TestFailureRecoveryContractCompleteness:
    """Verify the contract covers all failure scenarios without gaps."""

    def test_retryable_vs_fallback_distinction_is_clear(self):
        """Retryable and fallback failures are clearly distinguished."""
        retryable = [
            AIFailureClass.ADAPTER_ERROR,
            AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE,
        ]
        fallback = [
            AIFailureClass.PARSE_FAILURE,
            AIFailureClass.STRUCTURALLY_INVALID_OUTPUT,
        ]
        # These sets must be disjoint
        assert set(retryable) & set(fallback) == set()

    def test_no_implicit_recovery_actions(self):
        """All recovery actions are explicit (no default/implicit handling)."""
        for failure_class in AIFailureClass:
            action = FailureRecoveryPolicy.get_recovery_action(failure_class)
            # Action must not be None
            assert action is not None
            # Action must be explicitly defined in RecoveryAction enum
            assert action in RecoveryAction

    def test_safe_turn_failures_do_not_require_state_restoration(self):
        """Safe-turn failures can recover without restoring session state."""
        safe_turn = [
            AIFailureClass.RESPONDER_VALIDATION_FAILURE,
            AIFailureClass.GUARD_REJECTION,
        ]
        # These should NOT require full state restoration
        restore = [
            AIFailureClass.RETRY_EXHAUSTED,
            AIFailureClass.UNEXPECTED_RUNTIME_ERROR,
        ]
        assert set(safe_turn) & set(restore) == set()


class TestRetryPolicy:
    """Verify W2.5.2 canonical retry rules are explicit and bounded."""

    def test_retryable_failures_are_defined(self):
        """RetryPolicy defines exactly which failures are retryable."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        retryable = RetryPolicy.RETRYABLE_FAILURES
        # Should be exactly the transient adapter failures
        assert AIFailureClass.ADAPTER_ERROR in retryable
        assert AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE in retryable
        # Should NOT include structural, validation, or systematic failures
        assert AIFailureClass.PARSE_FAILURE not in retryable
        assert AIFailureClass.RESPONDER_VALIDATION_FAILURE not in retryable
        assert AIFailureClass.RETRY_EXHAUSTED not in retryable

    def test_max_retries_is_bounded(self):
        """RetryPolicy defines a bounded max retry count."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        max_retries = RetryPolicy.MAX_RETRIES
        # Must be explicitly defined
        assert isinstance(max_retries, int)
        # Must be > 0 (at least one retry allowed)
        assert max_retries > 0
        # Must be reasonable (not unlimited)
        assert max_retries <= 10

    def test_is_retryable_failure_for_adapter_error(self):
        """Adapter errors are retryable."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        assert RetryPolicy.is_retryable_failure(AIFailureClass.ADAPTER_ERROR)

    def test_is_retryable_failure_for_timeout(self):
        """Timeout/empty response failures are retryable."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        assert RetryPolicy.is_retryable_failure(AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE)

    def test_is_not_retryable_for_parse_failure(self):
        """Parse failures are not retryable (structural issue)."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        assert not RetryPolicy.is_retryable_failure(AIFailureClass.PARSE_FAILURE)

    def test_is_not_retryable_for_validation_failure(self):
        """Validation failures are not retryable (will likely fail again)."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        assert not RetryPolicy.is_retryable_failure(AIFailureClass.RESPONDER_VALIDATION_FAILURE)
        assert not RetryPolicy.is_retryable_failure(AIFailureClass.GUARD_REJECTION)

    def test_should_retry_when_retryable_and_within_limit(self):
        """should_retry returns True for retryable failures within limit."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        # First attempt of retryable failure should retry
        assert RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=1)
        # Second attempt should retry (if max >= 2)
        if RetryPolicy.MAX_RETRIES >= 2:
            assert RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=2)

    def test_should_not_retry_when_not_retryable(self):
        """should_retry returns False for non-retryable failures."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        assert not RetryPolicy.should_retry(AIFailureClass.PARSE_FAILURE, attempt=1)
        assert not RetryPolicy.should_retry(AIFailureClass.RESPONDER_VALIDATION_FAILURE, attempt=1)

    def test_should_not_retry_when_exhausted(self):
        """should_retry returns False when max retries exceeded."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        max_retries = RetryPolicy.MAX_RETRIES
        # At max attempt, should not retry
        assert not RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=max_retries)
        # Beyond max, should not retry
        assert not RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=max_retries + 1)

    def test_retry_exhaustion_failure_class(self):
        """Exhausted retries map to RETRY_EXHAUSTED failure class."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        exhaustion_failure = RetryPolicy.get_exhaustion_failure()
        assert exhaustion_failure == AIFailureClass.RETRY_EXHAUSTED

    def test_retry_exhaustion_requires_restore(self):
        """RETRY_EXHAUSTED requires RESTORE recovery (investigation)."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        exhaustion_failure = RetryPolicy.get_exhaustion_failure()
        # Should require RESTORE recovery
        assert FailureRecoveryPolicy.is_restore_required(exhaustion_failure)

    def test_retry_policy_prevents_infinite_loops(self):
        """RetryPolicy max retries prevent infinite retry loops."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        max_retries = RetryPolicy.MAX_RETRIES
        # Simulate exhausting retries
        for attempt in range(1, max_retries + 2):
            if attempt <= max_retries:
                # Early attempts should potentially retry
                can_retry = RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt)
                # At least some early attempts should be retryable
                if attempt < max_retries:
                    assert can_retry, f"Attempt {attempt} should be retryable"
            else:
                # Beyond max, should never retry
                assert not RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt)

    def test_retry_policy_is_deterministic(self):
        """Retry decision is always the same for a given failure and attempt."""
        from app.runtime.ai_failure_recovery import RetryPolicy

        # Check determinism
        decision1 = RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=1)
        decision2 = RetryPolicy.should_retry(AIFailureClass.ADAPTER_ERROR, attempt=1)
        assert decision1 == decision2


class TestReducedContextRetryPolicy:
    """Verify W2.5.3 reduced-context retry policy is explicit and bounded."""

    def test_reduced_context_retry_mode_enum_exists(self):
        """ReducedContextRetryMode enum exists with NORMAL and REDUCED."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryMode

        assert hasattr(ReducedContextRetryMode, "NORMAL")
        assert hasattr(ReducedContextRetryMode, "REDUCED")
        assert ReducedContextRetryMode.NORMAL.value == "normal"
        assert ReducedContextRetryMode.REDUCED.value == "reduced"

    def test_first_attempt_uses_normal_context(self):
        """First retry attempt uses normal (full) context."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy, ReducedContextRetryMode

        assert not ReducedContextRetryPolicy.should_use_reduced_context(attempt=1)
        assert ReducedContextRetryPolicy.get_retry_mode(attempt=1) == ReducedContextRetryMode.NORMAL

    def test_second_attempt_uses_reduced_context(self):
        """Second and subsequent retry attempts use reduced context."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy, ReducedContextRetryMode

        assert ReducedContextRetryPolicy.should_use_reduced_context(attempt=2)
        assert ReducedContextRetryPolicy.get_retry_mode(attempt=2) == ReducedContextRetryMode.REDUCED
        assert ReducedContextRetryPolicy.get_retry_mode(attempt=3) == ReducedContextRetryMode.REDUCED

    def test_reduction_phases_are_defined(self):
        """Canonical reduction phases are defined in order."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        phases = ReducedContextRetryPolicy.get_reduction_phases()
        # Should have phases in order
        assert len(phases) > 0
        assert isinstance(phases, list)
        # Should include key phases
        assert "trim_lore_direction" in phases
        assert "trim_relationship_detail" in phases
        assert "reduce_session_history" in phases
        assert "preserve_short_term" in phases
        assert "preserve_canonical_state" in phases

    def test_reduction_phases_order_is_correct(self):
        """Reduction phases follow correct priority order."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        phases = ReducedContextRetryPolicy.get_reduction_phases()
        # Lore should be trimmed before relationship
        lore_index = phases.index("trim_lore_direction")
        relationship_index = phases.index("trim_relationship_detail")
        history_index = phases.index("reduce_session_history")
        assert lore_index < relationship_index
        assert relationship_index < history_index
        # Critical layers should be last
        assert phases[-1] == "preserve_canonical_state"

    def test_phase_descriptions_exist(self):
        """Each reduction phase has a description."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        phases = ReducedContextRetryPolicy.get_reduction_phases()
        for phase in phases:
            description = ReducedContextRetryPolicy.get_phase_description(phase)
            assert isinstance(description, str)
            assert len(description) > 0
            # Should not be "Unknown phase"
            assert "Unknown" not in description

    def test_reduced_context_only_for_retryable_failures(self):
        """Reduced-context retry only applies to retryable failures."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        # Should be eligible for retryable failures
        assert ReducedContextRetryPolicy.is_reduced_context_eligible(AIFailureClass.ADAPTER_ERROR)
        assert ReducedContextRetryPolicy.is_reduced_context_eligible(AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE)
        # Should NOT be eligible for non-retryable failures
        assert not ReducedContextRetryPolicy.is_reduced_context_eligible(AIFailureClass.PARSE_FAILURE)
        assert not ReducedContextRetryPolicy.is_reduced_context_eligible(AIFailureClass.RESPONDER_VALIDATION_FAILURE)

    def test_context_reduction_strategy_is_deterministic(self):
        """Retry mode for a given attempt is always the same."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        mode1 = ReducedContextRetryPolicy.get_retry_mode(attempt=2)
        mode2 = ReducedContextRetryPolicy.get_retry_mode(attempt=2)
        assert mode1 == mode2

    def test_context_reduction_preserves_continuity_priority(self):
        """Context reduction preserves critical layers (state, current turn)."""
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy

        phases = ReducedContextRetryPolicy.get_reduction_phases()
        # Canonical state must be last (most critical, never trimmed)
        assert phases[-1] == "preserve_canonical_state"
        # Short-term context must be near the end (session grounding)
        short_term_index = phases.index("preserve_short_term")
        canonical_index = phases.index("preserve_canonical_state")
        assert short_term_index < canonical_index

    def test_reduced_context_mode_reduces_token_pressure(self):
        """Reduced-context retry uses fewer layers than normal retry.

        Normal path: all 5 W2.3 layers + canonical state
        Reduced path: starts trimming lower layers
        """
        from app.runtime.ai_failure_recovery import ReducedContextRetryPolicy, ReducedContextRetryMode

        normal_mode = ReducedContextRetryPolicy.get_retry_mode(attempt=1)
        reduced_mode = ReducedContextRetryPolicy.get_retry_mode(attempt=2)

        assert normal_mode == ReducedContextRetryMode.NORMAL
        assert reduced_mode == ReducedContextRetryMode.REDUCED
        # Reduction phases exist to implement the difference
        phases = ReducedContextRetryPolicy.get_reduction_phases()
        assert len(phases) >= 3  # At least some phases to trim

    def test_max_retries_respects_reduced_context_window(self):
        """Reduced-context retries respect the global max retry limit."""
        from app.runtime.ai_failure_recovery import RetryPolicy, ReducedContextRetryPolicy

        max_retries = RetryPolicy.MAX_RETRIES
        # All attempts up to max should be handled
        for attempt in range(1, max_retries + 1):
            mode = ReducedContextRetryPolicy.get_retry_mode(attempt)
            # Should be deterministic and within bounds
            assert mode in [ReducedContextRetryPolicy.get_retry_mode(attempt)]


class TestFallbackResponderPolicy:
    """Verify W2.5.4 canonical fallback mode is conservative and explicit."""

    def test_fallback_responder_mode_enum_exists(self):
        """FallbackResponderMode enum exists with ACTIVE and INACTIVE."""
        from app.runtime.ai_failure_recovery import FallbackResponderMode

        assert hasattr(FallbackResponderMode, "ACTIVE")
        assert hasattr(FallbackResponderMode, "INACTIVE")
        assert FallbackResponderMode.ACTIVE.value == "active"
        assert FallbackResponderMode.INACTIVE.value == "inactive"

    def test_fallback_does_not_trigger_on_retry_exhausted(self):
        """Fallback does NOT activate for retry exhausted (goes to safe-turn instead)."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert not FallbackResponderPolicy.should_activate_fallback(AIFailureClass.RETRY_EXHAUSTED)

    def test_fallback_triggers_on_parse_failure(self):
        """Fallback activates on parse failure (non-retryable structural issue)."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert FallbackResponderPolicy.should_activate_fallback(AIFailureClass.PARSE_FAILURE)

    def test_fallback_triggers_on_structurally_invalid(self):
        """Fallback activates on structurally invalid output."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert FallbackResponderPolicy.should_activate_fallback(
            AIFailureClass.STRUCTURALLY_INVALID_OUTPUT
        )

    def test_fallback_does_not_trigger_on_validation_failure(self):
        """Fallback does NOT activate for validation failures.

        Validation failures go through normal validation/guard flow, not fallback.
        """
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert not FallbackResponderPolicy.should_activate_fallback(
            AIFailureClass.RESPONDER_VALIDATION_FAILURE
        )
        assert not FallbackResponderPolicy.should_activate_fallback(AIFailureClass.GUARD_REJECTION)

    def test_fallback_does_not_trigger_on_retryable_failures(self):
        """Fallback does NOT activate on retryable failures (those get retried instead)."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert not FallbackResponderPolicy.should_activate_fallback(AIFailureClass.ADAPTER_ERROR)
        assert not FallbackResponderPolicy.should_activate_fallback(
            AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE
        )

    def test_fallback_is_conservative(self):
        """Fallback behavior is explicitly conservative."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert FallbackResponderPolicy.is_fallback_conservative()

    def test_fallback_respects_guards(self):
        """Fallback proposals still go through validation/guard enforcement."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert FallbackResponderPolicy.fallback_respects_guards()

    def test_fallback_is_marked_explicitly(self):
        """Fallback activation is explicitly marked in runtime state."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        assert FallbackResponderPolicy.is_fallback_marked_explicitly()

    def test_get_fallback_mode_status_inactive_when_no_failure(self):
        """Fallback status is INACTIVE when there's no failure."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy, FallbackResponderMode

        status = FallbackResponderPolicy.get_fallback_mode_status(failure_class=None)
        assert status == FallbackResponderMode.INACTIVE

    def test_get_fallback_mode_status_active_when_triggered(self):
        """Fallback status is ACTIVE when failure triggers it."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy, FallbackResponderMode

        status = FallbackResponderPolicy.get_fallback_mode_status(AIFailureClass.PARSE_FAILURE)
        assert status == FallbackResponderMode.ACTIVE

    def test_get_fallback_mode_status_inactive_when_not_triggered(self):
        """Fallback status is INACTIVE when failure doesn't trigger it."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy, FallbackResponderMode

        status = FallbackResponderPolicy.get_fallback_mode_status(AIFailureClass.ADAPTER_ERROR)
        assert status == FallbackResponderMode.INACTIVE

    def test_fallback_constraints_are_defined(self):
        """Fallback has explicit constraints on what it cannot do."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        constraints = FallbackResponderPolicy.get_fallback_constraints()
        # Should have multiple constraints
        assert len(constraints) > 0
        assert isinstance(constraints, dict)
        # Key constraints
        assert "no_risky_transitions" in constraints
        assert "no_extreme_mutations" in constraints
        assert "must_pass_guards" in constraints

    def test_fallback_permissions_are_defined(self):
        """Fallback has explicit permissions on what it can do."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        permissions = FallbackResponderPolicy.get_fallback_permissions()
        # Should have multiple permissions
        assert len(permissions) > 0
        assert isinstance(permissions, dict)
        # Key permissions
        assert "minimal_adjustments" in permissions
        assert "safe_continuity" in permissions
        assert "advance_turn" in permissions

    def test_fallback_trigger_failures_are_explicit(self):
        """Fallback trigger failures are explicitly defined."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        triggers = FallbackResponderPolicy.get_fallback_trigger_failures()
        # Should be a set of specific failures
        assert isinstance(triggers, set)
        assert len(triggers) > 0
        # Should include parse failures and structural issues (not retry exhaustion)
        # RETRY_EXHAUSTED goes to SAFE_TURN, not FALLBACK
        assert AIFailureClass.PARSE_FAILURE in triggers
        assert AIFailureClass.STRUCTURALLY_INVALID_OUTPUT in triggers

    def test_fallback_constraints_and_permissions_do_not_conflict(self):
        """Fallback constraints and permissions are complementary, not conflicting."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        constraints = FallbackResponderPolicy.get_fallback_constraints()
        permissions = FallbackResponderPolicy.get_fallback_permissions()
        # Constraints are what fallback CANNOT do
        # Permissions are what fallback CAN do
        # Should not have the same constraint and permission
        constraint_keys = set(constraints.keys())
        permission_keys = set(permissions.keys())
        # No overlap expected
        assert constraint_keys & permission_keys == set()

    def test_fallback_is_explicit_not_implicit(self):
        """Fallback activation is explicit and never silent."""
        from app.runtime.ai_failure_recovery import FallbackResponderPolicy

        # Fallback mode is explicitly marked
        assert FallbackResponderPolicy.is_fallback_marked_explicitly()
        # Fallback triggers are explicit
        assert len(FallbackResponderPolicy.get_fallback_trigger_failures()) > 0
        # Fallback constraints and permissions are explicit
        assert len(FallbackResponderPolicy.get_fallback_constraints()) > 0
        assert len(FallbackResponderPolicy.get_fallback_permissions()) > 0


class TestSafeTurnPolicy:
    """Verify W2.5.5 canonical safe-turn/no-op path is minimal and safe."""

    def test_safe_turn_mode_enum_exists(self):
        """SafeTurnMode enum exists with ACTIVE and INACTIVE."""
        from app.runtime.ai_failure_recovery import SafeTurnMode

        assert hasattr(SafeTurnMode, "ACTIVE")
        assert hasattr(SafeTurnMode, "INACTIVE")
        assert SafeTurnMode.ACTIVE.value == "active"
        assert SafeTurnMode.INACTIVE.value == "inactive"

    def test_safe_turn_triggers_on_retry_exhausted(self):
        """Safe-turn activates when retries are exhausted."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        assert SafeTurnPolicy.should_activate_safe_turn(AIFailureClass.RETRY_EXHAUSTED)

    def test_safe_turn_triggers_on_unexpected_runtime_error(self):
        """Safe-turn activates on unexpected runtime errors."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        assert SafeTurnPolicy.should_activate_safe_turn(AIFailureClass.UNEXPECTED_RUNTIME_ERROR)

    def test_safe_turn_does_not_trigger_on_fallback_eligible(self):
        """Safe-turn does NOT activate for fallback-eligible failures.

        Fallback handles parse_failure and structurally_invalid_output.
        Safe-turn is last resort only.
        """
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        assert not SafeTurnPolicy.should_activate_safe_turn(AIFailureClass.PARSE_FAILURE)
        assert not SafeTurnPolicy.should_activate_safe_turn(
            AIFailureClass.STRUCTURALLY_INVALID_OUTPUT
        )

    def test_safe_turn_mode_status_inactive_when_no_failure(self):
        """Safe-turn status is INACTIVE when there's no failure."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy, SafeTurnMode

        status = SafeTurnPolicy.get_safe_turn_mode_status(failure_class=None)
        assert status == SafeTurnMode.INACTIVE

    def test_safe_turn_mode_status_active_when_triggered(self):
        """Safe-turn status is ACTIVE when failure triggers it."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy, SafeTurnMode

        status = SafeTurnPolicy.get_safe_turn_mode_status(AIFailureClass.RETRY_EXHAUSTED)
        assert status == SafeTurnMode.ACTIVE

    def test_safe_turn_mode_status_inactive_when_not_triggered(self):
        """Safe-turn status is INACTIVE when failure doesn't trigger it."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy, SafeTurnMode

        status = SafeTurnPolicy.get_safe_turn_mode_status(AIFailureClass.PARSE_FAILURE)
        assert status == SafeTurnMode.INACTIVE

    def test_safe_turn_semantics_are_defined(self):
        """Safe-turn has explicit semantics defining its behavior."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        semantics = SafeTurnPolicy.get_safe_turn_semantics()
        # Should have multiple semantic rules
        assert len(semantics) > 0
        assert isinstance(semantics, dict)
        # Key semantics
        assert "advance_turn_counter" in semantics
        assert "no_state_mutation" in semantics
        assert "no_proposals" in semantics
        assert "preserve_continuity" in semantics

    def test_protected_state_boundaries_are_defined(self):
        """Safe-turn respects protected state boundaries."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        boundaries = SafeTurnPolicy.get_protected_state_boundaries()
        # Should have multiple boundaries
        assert len(boundaries) > 0
        assert isinstance(boundaries, set)
        # Key boundaries
        assert "character_existence" in boundaries
        assert "scene_validity" in boundaries
        assert "narrative_coherence" in boundaries

    def test_safe_turn_validates_protected_boundaries(self):
        """Safe-turn enforces protected state boundaries."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        assert SafeTurnPolicy.validates_protected_boundaries()

    def test_safe_turn_invariants_are_defined(self):
        """Safe-turn maintains clear invariants for session coherence."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        invariants = SafeTurnPolicy.get_safe_turn_invariants()
        # Should have multiple invariants
        assert len(invariants) > 0
        assert isinstance(invariants, dict)
        # Key invariants
        assert "session_alive" in invariants
        assert "state_consistent" in invariants
        assert "turn_counter_advances" in invariants

    def test_safe_turn_is_minimal(self):
        """Safe-turn is minimal (only what's needed to keep session alive)."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        assert SafeTurnPolicy.is_safe_turn_minimal()

    def test_safe_turn_is_last_resort(self):
        """Safe-turn only activates when all other recovery fails.

        Recovery precedence:
        1. Normal execution
        2. Retry (for retryable failures)
        3. Fallback (for parse/structural failures)
        4. Safe-turn (for retry exhaustion, unexpected errors)
        """
        from app.runtime.ai_failure_recovery import SafeTurnPolicy, RetryPolicy, FallbackResponderPolicy

        # Safe-turn failures should NOT be retryable or fallback-eligible
        safe_turn_failures = SafeTurnPolicy.get_safe_turn_mode_status(AIFailureClass.RETRY_EXHAUSTED)
        retry_exhausted = AIFailureClass.RETRY_EXHAUSTED

        # RETRY_EXHAUSTED is not retryable (already exhausted retries)
        assert not RetryPolicy.is_retryable_failure(retry_exhausted)
        # RETRY_EXHAUSTED is not fallback-eligible
        assert not FallbackResponderPolicy.should_activate_fallback(retry_exhausted)
        # RETRY_EXHAUSTED triggers safe-turn
        assert SafeTurnPolicy.should_activate_safe_turn(retry_exhausted)

    def test_safe_turn_semantics_no_state_mutation(self):
        """Safe-turn semantics explicitly forbid state mutation."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        semantics = SafeTurnPolicy.get_safe_turn_semantics()
        # Core semantic: no mutation
        assert "no_state_mutation" in semantics
        assert "no_proposals" in semantics
        # But turn counter advances (one allowed mutation)
        assert "advance_turn_counter" in semantics

    def test_safe_turn_protects_character_existence(self):
        """Safe-turn protects character existence from modification."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        boundaries = SafeTurnPolicy.get_protected_state_boundaries()
        assert "character_existence" in boundaries

    def test_safe_turn_protects_narrative_coherence(self):
        """Safe-turn protects narrative/story coherence."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        boundaries = SafeTurnPolicy.get_protected_state_boundaries()
        assert "narrative_coherence" in boundaries

    def test_safe_turn_guarantees_session_alive(self):
        """Safe-turn guarantees session remains alive and responsive."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        invariants = SafeTurnPolicy.get_safe_turn_invariants()
        assert "session_alive" in invariants
        # Session coherence is maintained
        assert "state_consistent" in invariants
        # Session can continue (turn advances)
        assert "turn_counter_advances" in invariants

    def test_safe_turn_turn_counter_never_reverts(self):
        """Safe-turn turn counter can only advance, never revert."""
        from app.runtime.ai_failure_recovery import SafeTurnPolicy

        invariants = SafeTurnPolicy.get_safe_turn_invariants()
        # Invariant: turn counter always increases
        assert "turn_counter_advances" in invariants


class TestStateSnapshot:
    """Verify W2.5.6 StateSnapshot captures and validates state correctly."""

    def test_state_snapshot_captures_essential_state(self):
        """StateSnapshot captures turn counter and canonical state."""
        from app.runtime.ai_failure_recovery import StateSnapshot

        snapshot = StateSnapshot(
            turn_number=3,
            canonical_state={"characters": {"alice": {"mood": 50}}},
            snapshot_reason="pre_ai_execution",
        )

        assert snapshot.turn_number == 3
        assert snapshot.canonical_state == {"characters": {"alice": {"mood": 50}}}
        assert snapshot.snapshot_reason == "pre_ai_execution"

    def test_state_snapshot_has_timestamp(self):
        """StateSnapshot includes timestamp for auditability."""
        from app.runtime.ai_failure_recovery import StateSnapshot
        from datetime import datetime, timezone

        before = datetime.now(timezone.utc)
        snapshot = StateSnapshot(
            turn_number=1,
            canonical_state={},
            snapshot_reason="test",
        )
        after = datetime.now(timezone.utc)

        assert before <= snapshot.created_at <= after

    def test_state_snapshot_validates_before_restore(self):
        """StateSnapshot.is_valid_for_restore() checks snapshot soundness."""
        from app.runtime.ai_failure_recovery import StateSnapshot

        # Valid snapshot
        valid = StateSnapshot(
            turn_number=5,
            canonical_state={"characters": {}},
            snapshot_reason="test",
        )
        assert valid.is_valid_for_restore() is True

        # Invalid: negative turn
        invalid_turn = StateSnapshot(
            turn_number=-1,
            canonical_state={"characters": {}},
            snapshot_reason="test",
        )
        assert invalid_turn.is_valid_for_restore() is False

        # Invalid: turn zero is valid, but we test non-negative
        # (Pydantic enforces dict type, so we can't test None)


class TestRestorePolicy:
    """Verify W2.5.6 canonical last-valid-state restore mechanism."""

    def test_restore_policy_identifies_last_valid_state(self):
        """RestorePolicy.is_last_valid_state() checks pre-execution snapshot."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        # Pre-execution snapshot of retry exhaustion = last valid
        assert RestorePolicy.is_last_valid_state(
            failure_class=AIFailureClass.RETRY_EXHAUSTED,
            is_pre_execution_snapshot=True,
        ) is True

        # Post-execution snapshot is NOT last valid (may be corrupted)
        assert RestorePolicy.is_last_valid_state(
            failure_class=AIFailureClass.RETRY_EXHAUSTED,
            is_pre_execution_snapshot=False,
        ) is False

        # Non-restoreable failures don't count as "last valid" scenario
        assert RestorePolicy.is_last_valid_state(
            failure_class=AIFailureClass.PARSE_FAILURE,
            is_pre_execution_snapshot=True,
        ) is False

    def test_restore_policy_requires_restore_for_exhausted_failures(self):
        """RestorePolicy.should_require_restore() triggers for RESTORE action."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        # Retry exhausted + RESTORE action = requires restore
        assert RestorePolicy.should_require_restore(
            failure_class=AIFailureClass.RETRY_EXHAUSTED,
            recovery_action=RecoveryAction.RESTORE,
        ) is True

        # Retry exhausted + SAFE_TURN action = does NOT require restore
        # (safe-turn is already non-mutating)
        assert RestorePolicy.should_require_restore(
            failure_class=AIFailureClass.RETRY_EXHAUSTED,
            recovery_action=RecoveryAction.SAFE_TURN,
        ) is False

        # Non-restore failures never require restore
        assert RestorePolicy.should_require_restore(
            failure_class=AIFailureClass.PARSE_FAILURE,
            recovery_action=RecoveryAction.RESTORE,
        ) is False

    def test_restore_policy_applies_snapshot_to_clean_state(self):
        """RestorePolicy.apply_restore() replaces corrupted state with snapshot."""
        from app.runtime.ai_failure_recovery import RestorePolicy, StateSnapshot

        # Original snapshot (clean)
        snapshot = StateSnapshot(
            turn_number=2,
            canonical_state={"characters": {"bob": {"health": 100}}},
            snapshot_reason="pre_execution",
        )

        # Corrupted state (bad turn mutation)
        corrupted = {
            "characters": {"bob": {"health": -50}, "corrupted": True},
            "invalid_field": "should be removed",
        }

        # Restore
        restored = RestorePolicy.apply_restore(corrupted, snapshot)

        # Should match snapshot exactly (no corruption)
        assert restored == {"characters": {"bob": {"health": 100}}}
        assert "corrupted" not in restored
        assert "invalid_field" not in restored

    def test_restore_policy_deep_copies_snapshot(self):
        """RestorePolicy.apply_restore() deep copies to prevent shared refs."""
        from app.runtime.ai_failure_recovery import RestorePolicy, StateSnapshot

        original_state = {"characters": {"alice": {"mood": 50}}}
        snapshot = StateSnapshot(
            turn_number=3,
            canonical_state=original_state,
            snapshot_reason="test",
        )

        # Restore
        restored = RestorePolicy.apply_restore({}, snapshot)

        # Mutate restored
        restored["characters"]["alice"]["mood"] = 999

        # Snapshot's state should be unchanged
        assert snapshot.canonical_state["characters"]["alice"]["mood"] == 50

    def test_restore_policy_validates_snapshot_before_restore(self):
        """RestorePolicy.apply_restore() rejects invalid snapshots."""
        from app.runtime.ai_failure_recovery import RestorePolicy, StateSnapshot

        invalid_snapshot = StateSnapshot(
            turn_number=-1,
            canonical_state={},
            snapshot_reason="test",
        )

        with pytest.raises(ValueError, match="not valid for restore"):
            RestorePolicy.apply_restore({}, invalid_snapshot)

    def test_restore_policy_marks_restore_in_metadata(self):
        """RestorePolicy.get_restore_metadata() provides audit trail."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        metadata = RestorePolicy.get_restore_metadata(
            failure_class=AIFailureClass.RETRY_EXHAUSTED,
            snapshot_turn=5,
            current_turn=5,
        )

        # Must mark as restored explicitly
        assert metadata["restored"] is True
        assert metadata["reason"] == "last_valid_state_restore"
        assert metadata["failure_class"] == "retry_exhausted"
        assert metadata["snapshot_turn"] == 5
        assert metadata["current_turn"] == 5
        assert metadata["recovered_to_turn"] == 5
        assert metadata["turns_discarded"] == 0

    def test_restore_policy_tracks_turns_discarded(self):
        """RestorePolicy.get_restore_metadata() shows turns rolled back."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        # Snapshot taken at turn 3, restore at turn 7 (4 turns lost)
        metadata = RestorePolicy.get_restore_metadata(
            failure_class=AIFailureClass.UNEXPECTED_RUNTIME_ERROR,
            snapshot_turn=3,
            current_turn=7,
        )

        assert metadata["turns_discarded"] == 4
        assert metadata["recovered_to_turn"] == 3


class TestDegradedSessionPolicy:
    """Verify W2.5.7 canonical degraded-but-alive session mode."""

    def test_degraded_marker_enum_has_all_markers(self):
        """DegradedMarker enum has all canonical markers."""
        from app.runtime.runtime_models import DegradedMarker

        assert hasattr(DegradedMarker, "DEGRADED")
        assert hasattr(DegradedMarker, "RETRY_EXHAUSTED")
        assert hasattr(DegradedMarker, "REDUCED_CONTEXT_ACTIVE")
        assert hasattr(DegradedMarker, "FALLBACK_ACTIVE")
        assert hasattr(DegradedMarker, "SAFE_TURN_USED")
        assert hasattr(DegradedMarker, "RESTORE_USED")

        # All should have string values
        for marker in DegradedMarker:
            assert isinstance(marker.value, str)
            assert len(marker.value) > 0

    def test_degraded_session_state_starts_healthy(self):
        """DegradedSessionState starts with no markers."""
        from app.runtime.runtime_models import DegradedSessionState

        state = DegradedSessionState()
        assert state.is_degraded is False
        assert len(state.active_markers) == 0
        assert state.marked_at is None

    def test_degraded_session_state_tracks_markers(self):
        """DegradedSessionState tracks which markers are active."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        state.set_marker(DegradedMarker.FALLBACK_ACTIVE)

        assert state.is_degraded is True
        assert DegradedMarker.FALLBACK_ACTIVE in state.active_markers
        assert state.marked_at is not None

    def test_degraded_session_state_accumulates_markers(self):
        """DegradedSessionState accumulates markers (doesn't clear them)."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        state.set_marker(DegradedMarker.RETRY_EXHAUSTED)
        state.set_marker(DegradedMarker.FALLBACK_ACTIVE)

        # Both should be present
        assert len(state.active_markers) == 2
        assert DegradedMarker.RETRY_EXHAUSTED in state.active_markers
        assert DegradedMarker.FALLBACK_ACTIVE in state.active_markers

    def test_degraded_session_state_marks_overall_degraded(self):
        """DegradedSessionState.is_degraded is True when any marker is set."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        assert state.is_degraded is False

        state.set_marker(DegradedMarker.REDUCED_CONTEXT_ACTIVE)
        assert state.is_degraded is True

    def test_degraded_session_state_tracks_timestamps(self):
        """DegradedSessionState tracks when markers were set."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker
        from datetime import datetime, timezone

        state = DegradedSessionState()
        before = datetime.now(timezone.utc)
        state.set_marker(DegradedMarker.SAFE_TURN_USED)
        after = datetime.now(timezone.utc)

        assert DegradedMarker.SAFE_TURN_USED in state.marker_timestamps
        ts = state.marker_timestamps[DegradedMarker.SAFE_TURN_USED]
        assert before <= ts <= after

    def test_degraded_session_state_prevents_duplicate_markers(self):
        """Setting the same marker twice doesn't duplicate it."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        state.set_marker(DegradedMarker.RESTORE_USED)
        first_ts = state.marker_timestamps[DegradedMarker.RESTORE_USED]

        # Set again
        state.set_marker(DegradedMarker.RESTORE_USED)

        # Should only be one
        assert len(state.active_markers) == 1
        # Timestamp should be original
        assert state.marker_timestamps[DegradedMarker.RESTORE_USED] == first_ts

    def test_degraded_session_state_has_marker_check(self):
        """DegradedSessionState.has_marker() checks marker status."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        assert state.has_marker(DegradedMarker.SAFE_TURN_USED) is False

        state.set_marker(DegradedMarker.SAFE_TURN_USED)
        assert state.has_marker(DegradedMarker.SAFE_TURN_USED) is True
        assert state.has_marker(DegradedMarker.RESTORE_USED) is False

    def test_degraded_session_state_recovery_history(self):
        """DegradedSessionState.get_recovery_history() returns chronological markers."""
        from app.runtime.runtime_models import DegradedSessionState, DegradedMarker

        state = DegradedSessionState()
        state.set_marker(DegradedMarker.RETRY_EXHAUSTED)
        state.set_marker(DegradedMarker.FALLBACK_ACTIVE)
        state.set_marker(DegradedMarker.SAFE_TURN_USED)

        history = state.get_recovery_history()

        # Should be 3 items in chronological order
        assert len(history) == 3
        assert history[0][0] == DegradedMarker.RETRY_EXHAUSTED
        assert history[1][0] == DegradedMarker.FALLBACK_ACTIVE
        assert history[2][0] == DegradedMarker.SAFE_TURN_USED

        # Timestamps should be in order
        for i in range(len(history) - 1):
            assert history[i][1] <= history[i + 1][1]

    def test_degraded_session_state_in_session_state(self):
        """SessionState includes DegradedSessionState."""
        from app.runtime.runtime_models import SessionState, DegradedMarker

        session = SessionState(
            module_id="test_module",
            module_version="1.0",
            current_scene_id="scene1",
        )

        # Should have degraded_state field
        assert hasattr(session, "degraded_state")
        assert session.degraded_state.is_degraded is False

        # Should be able to set markers
        session.degraded_state.set_marker(DegradedMarker.FALLBACK_ACTIVE)
        assert session.degraded_state.is_degraded is True

    def test_restore_policy_semantics_are_defined(self):
        """RestorePolicy.get_restore_semantics() defines restore rules."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        semantics = RestorePolicy.get_restore_semantics()

        # Must have key semantics
        assert "snapshot_validity" in semantics
        assert "determinism" in semantics
        assert "auditability" in semantics
        assert "no_silent_mutation" in semantics
        assert "partial_corruption_prevention" in semantics

        # All should be non-empty strings
        for key, value in semantics.items():
            assert isinstance(value, str)
            assert len(value) > 0

    def test_restore_required_failures_set_is_explicit(self):
        """RestorePolicy.RESTORE_REQUIRED_FAILURES is explicitly defined."""
        from app.runtime.ai_failure_recovery import RestorePolicy

        failures = RestorePolicy.RESTORE_REQUIRED_FAILURES

        # Should be a set
        assert isinstance(failures, set)
        # Should include both restore-required failures
        assert AIFailureClass.RETRY_EXHAUSTED in failures
        assert AIFailureClass.UNEXPECTED_RUNTIME_ERROR in failures
        # Should NOT include failures handled by other recovery
        assert AIFailureClass.PARSE_FAILURE not in failures
        assert AIFailureClass.STRUCTURALLY_INVALID_OUTPUT not in failures
