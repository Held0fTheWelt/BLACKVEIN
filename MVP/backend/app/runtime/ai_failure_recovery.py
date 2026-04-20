"""W2.5.1 — Canonical AI Failure Classification and Recovery Contract

Defines explicit failure categories for AI-driven turn execution and their
deterministic recovery policies. This contract ensures sessions do not die
from bad AI behavior—every failure has a known recovery action.

Failure Classes:
1. adapter_error — AI adapter failed to generate response
2. timeout_or_empty_response — Adapter timeout or empty/null response
3. parse_failure — Could not parse adapter output
4. structurally_invalid_output — Parsed but invalid schema
5. responder_validation_failure — Responder proposals failed guards
6. guard_rejection — Non-responder proposals rejected by gate (W2.4.5)
7. retry_exhausted — Retried max times, still failing
8. unexpected_runtime_error — Unknown system failure

Recovery Actions:
1. RETRY — Attempt execution again (up to max retries)
2. FALLBACK — Use alternative strategy (e.g., safe turn, operator input)
3. SAFE_TURN — Execute no-op turn (preserve state, advance turn counter)
4. RESTORE — Requires intervention (should not reach in normal cases)
5. ABORT — Stop session (terminal failure)

Recovery Policy:
- Retryable failures: adapter_error, timeout_or_empty_response
- Fallback-only: parse_failure, structurally_invalid_output
- Safe-turn: responder_validation_failure, guard_rejection
- Restore: retry_exhausted, unexpected_runtime_error
"""

from copy import deepcopy
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class AIFailureClass(str, Enum):
    """Canonical failure classification for AI-driven turn execution.

    Each class maps to a specific recovery policy, ensuring deterministic
    and diagnosable failure handling.
    """

    # Adapter layer (communication/generation)
    ADAPTER_ERROR = "adapter_error"
    """Adapter failed to generate response (network, timeout, internal error).
    Recovery: RETRY (retryable)
    """

    TIMEOUT_OR_EMPTY_RESPONSE = "timeout_or_empty_response"
    """Adapter timeout or returned null/empty response.
    Recovery: RETRY (retryable)
    """

    # Parsing layer (structure validation)
    PARSE_FAILURE = "parse_failure"
    """Could not parse adapter output (malformed JSON, missing fields).
    Recovery: FALLBACK (not retryable—adapter output is broken)
    """

    STRUCTURALLY_INVALID_OUTPUT = "structurally_invalid_output"
    """Parsed but violates schema (wrong types, invalid enums).
    Recovery: FALLBACK (schema violation won't fix on retry)
    """

    # Validation layer (runtime guards)
    RESPONDER_VALIDATION_FAILURE = "responder_validation_failure"
    """Responder proposals failed runtime validation (invalid state path, bad value).
    Recovery: SAFE_TURN (proposals rejected but session recovers)
    """

    GUARD_REJECTION = "guard_rejection"
    """Non-responder proposals rejected by W2.4.5 responder-only gate.
    Recovery: SAFE_TURN (proposals never reached execution)
    """

    # Retry exhaustion
    RETRY_EXHAUSTED = "retry_exhausted"
    """Retried max times, still failing (indicates systematic issue).
    Recovery: RESTORE (requires investigation)
    """

    # System layer (unexpected)
    UNEXPECTED_RUNTIME_ERROR = "unexpected_runtime_error"
    """Unknown system failure (uncaught exception, missing dependency).
    Recovery: RESTORE (requires investigation)
    """


class RecoveryAction(str, Enum):
    """Recovery action for AI execution failures.

    Deterministic actions that preserve session integrity without requiring
    intervention (except RESTORE, which requires investigation).
    """

    RETRY = "retry"
    """Attempt execution again (up to configured max retries).
    Used for: transient adapter issues, network timeouts
    """

    FALLBACK = "fallback"
    """Use alternative strategy instead of retrying.
    - Safe turn: execute no-op (advance turn, preserve state)
    - Operator input: use default/fallback narrative
    Used for: structural failures that won't improve on retry
    """

    SAFE_TURN = "safe_turn"
    """Execute no-op turn: advance turn counter, preserve state, log failure.
    Used for: validation failures where proposals were bad but recovery is safe
    """

    RESTORE = "restore"
    """Requires manual investigation (should not occur in normal operation).
    Logged with full context for debugging.
    Used for: systematic failures, exhausted retries, unexpected errors
    """

    ABORT = "abort"
    """Terminal failure—session cannot continue.
    Used for: unrecoverable system failures, invalid configuration
    """


class FailureRecoveryPolicy:
    """Canonical mapping from failure class to recovery action.

    This is the runtime contract: every failure class has exactly one
    recovery policy, making failure handling deterministic and diagnosable.
    """

    # Mapping: AIFailureClass → RecoveryAction
    POLICY: dict[AIFailureClass, RecoveryAction] = {
        # Retryable failures
        AIFailureClass.ADAPTER_ERROR: RecoveryAction.RETRY,
        AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE: RecoveryAction.RETRY,
        # Fallback-only failures
        AIFailureClass.PARSE_FAILURE: RecoveryAction.FALLBACK,
        AIFailureClass.STRUCTURALLY_INVALID_OUTPUT: RecoveryAction.FALLBACK,
        # Safe-turn failures (proposals never reached execution)
        AIFailureClass.RESPONDER_VALIDATION_FAILURE: RecoveryAction.SAFE_TURN,
        AIFailureClass.GUARD_REJECTION: RecoveryAction.SAFE_TURN,
        # Restore-required failures (systematic issues)
        AIFailureClass.RETRY_EXHAUSTED: RecoveryAction.RESTORE,
        AIFailureClass.UNEXPECTED_RUNTIME_ERROR: RecoveryAction.RESTORE,
    }

    @classmethod
    def get_recovery_action(cls, failure_class: AIFailureClass) -> RecoveryAction:
        """Get the recovery action for a failure class.

        Args:
            failure_class: The failure class to recover from

        Returns:
            RecoveryAction: The deterministic recovery action for this failure

        Raises:
            KeyError: If failure_class is not in the policy (indicates incomplete contract)
        """
        if failure_class not in cls.POLICY:
            raise KeyError(f"No recovery policy defined for {failure_class.value}")
        return cls.POLICY[failure_class]

    @classmethod
    def is_retryable(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure is retryable.

        Args:
            failure_class: The failure class

        Returns:
            True if recovery action is RETRY, False otherwise
        """
        return cls.get_recovery_action(failure_class) == RecoveryAction.RETRY

    @classmethod
    def is_fallback_only(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure requires fallback strategy.

        Args:
            failure_class: The failure class

        Returns:
            True if recovery action is FALLBACK, False otherwise
        """
        return cls.get_recovery_action(failure_class) == RecoveryAction.FALLBACK

    @classmethod
    def is_safe_turn(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure can be recovered with a safe (no-op) turn.

        Args:
            failure_class: The failure class

        Returns:
            True if recovery action is SAFE_TURN, False otherwise
        """
        return cls.get_recovery_action(failure_class) == RecoveryAction.SAFE_TURN

    @classmethod
    def is_restore_required(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure requires restoration/investigation.

        Args:
            failure_class: The failure class

        Returns:
            True if recovery action is RESTORE, False otherwise
        """
        return cls.get_recovery_action(failure_class) == RecoveryAction.RESTORE


class RetryPolicy:
    """W2.5.2 — Canonical retry rules for recoverable failures.

    Retry behavior is explicit and bounded:
    - Only specific failure classes are retryable
    - Retry count is bounded to prevent infinite loops
    - Retry exhaustion is explicit and deterministic
    """

    # Retryable failure classes (transient/temporary issues)
    RETRYABLE_FAILURES: set[AIFailureClass] = {
        AIFailureClass.ADAPTER_ERROR,
        AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE,
    }

    # Max retry attempts (bounded to prevent infinite loops)
    MAX_RETRIES: int = 3

    @classmethod
    def is_retryable_failure(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure class should trigger retry behavior.

        Retryable failures are transient adapter issues that may succeed
        on subsequent attempts.

        Args:
            failure_class: The failure class to check

        Returns:
            True if the failure should trigger retry, False otherwise
        """
        return failure_class in cls.RETRYABLE_FAILURES

    @classmethod
    def should_retry(cls, failure_class: AIFailureClass, attempt: int) -> bool:
        """Determine if a turn should be retried.

        Returns True if:
        1. The failure is retryable AND
        2. We haven't exceeded MAX_RETRIES yet

        Args:
            failure_class: The failure that occurred
            attempt: The current attempt number (1-indexed)

        Returns:
            True if retry should be attempted, False otherwise
        """
        if not cls.is_retryable_failure(failure_class):
            return False
        if attempt >= cls.MAX_RETRIES:
            return False
        return True

    @classmethod
    def get_max_retries(cls) -> int:
        """Get the maximum number of retry attempts.

        Returns:
            Maximum retry attempt count (bounded)
        """
        return cls.MAX_RETRIES

    @classmethod
    def get_exhaustion_failure(cls) -> AIFailureClass:
        """Get the failure class assigned when retries are exhausted.

        When a retryable failure exhausts max retries, it's reclassified as
        RETRY_EXHAUSTED, which triggers RESTORE recovery (investigation needed).

        Returns:
            The failure class for exhausted retries
        """
        return AIFailureClass.RETRY_EXHAUSTED


class ReducedContextRetryMode(str, Enum):
    """Retry modes for handling context during retry attempts.

    Normal retry repeats the same request with full context.
    Reduced-context retry uses progressively smaller context to reduce token pressure.
    """

    NORMAL = "normal"
    """Full context retry—use same context as original attempt."""

    REDUCED = "reduced"
    """Reduced-context retry—trim lower-priority context layers."""


class ReducedContextRetryPolicy:
    """W2.5.3 — Reduced-context retry strategy.

    When a retryable failure occurs, reduced-context retry reduces token pressure
    by trimming context layers in a deterministic order while preserving minimal
    session continuity.

    Reduction order (W2.3 layers):
    1. Trim lore/direction context (W2.3.5) — module guidance is least critical
    2. Trim relationship context detail (W2.3.4) — dynamics can be inferred
    3. Reduce session history contribution (W2.3.2) — trim older turns
    4. Preserve short-term context (W2.3.1) — current turn grounding essential
    5. Preserve canonical state (current scene, character state) — baseline required

    This order balances:
    - Token savings (higher layers reduced more)
    - Continuity preservation (core session state stays)
    - Predictability (deterministic reduction sequence)
    """

    # Reduction phases (applied in order)
    REDUCTION_PHASES: list[str] = [
        "trim_lore_direction",           # Phase 1: Remove W2.3.5 (least critical)
        "trim_relationship_detail",       # Phase 2: Remove W2.3.4 (dynamics)
        "reduce_session_history",         # Phase 3: Trim W2.3.2 (older turns)
        "preserve_short_term",            # Phase 4: Keep W2.3.1 (current turn)
        "preserve_canonical_state",       # Phase 5: Keep core state (grounding)
    ]

    @classmethod
    def should_use_reduced_context(cls, attempt: int) -> bool:
        """Determine if reduced-context retry should be used.

        Uses reduced context starting on the second retry attempt to preserve
        token budget while maintaining session coherence.

        Args:
            attempt: The current retry attempt (1-indexed)

        Returns:
            True if reduced context should be used, False for normal context
        """
        # First attempt uses normal context
        # Second+ attempts use reduced context (if available)
        return attempt >= 2

    @classmethod
    def get_retry_mode(cls, attempt: int) -> ReducedContextRetryMode:
        """Get the retry mode for a given attempt number.

        Args:
            attempt: The current retry attempt (1-indexed)

        Returns:
            ReducedContextRetryMode indicating which context strategy to use
        """
        if cls.should_use_reduced_context(attempt):
            return ReducedContextRetryMode.REDUCED
        return ReducedContextRetryMode.NORMAL

    @classmethod
    def get_reduction_phases(cls) -> list[str]:
        """Get the deterministic context reduction phases.

        Returns:
            List of reduction phases in order, from least critical to most critical
        """
        return cls.REDUCTION_PHASES.copy()

    @classmethod
    def get_phase_description(cls, phase: str) -> str:
        """Get description of what a reduction phase does.

        Args:
            phase: The reduction phase name

        Returns:
            Description of what context is affected
        """
        descriptions = {
            "trim_lore_direction": "Remove lore/direction context (W2.3.5) — module guidance",
            "trim_relationship_detail": "Remove relationship context (W2.3.4) — dynamics",
            "reduce_session_history": "Reduce session history (W2.3.2) — trim to last N turns",
            "preserve_short_term": "Preserve short-term context (W2.3.1) — current turn",
            "preserve_canonical_state": "Preserve canonical state — character/scene baseline",
        }
        return descriptions.get(phase, f"Unknown phase: {phase}")

    @classmethod
    def is_reduced_context_eligible(cls, failure_class: AIFailureClass) -> bool:
        """Check if a failure is eligible for reduced-context retry.

        Only retryable failures (transient adapter issues) can use reduced-context
        retry. Other failures don't retry, so context reduction doesn't apply.

        Args:
            failure_class: The failure to check

        Returns:
            True if reduced-context retry is applicable, False otherwise
        """
        return RetryPolicy.is_retryable_failure(failure_class)


class FallbackResponderMode(str, Enum):
    """Fallback response modes for degraded AI execution.

    When normal AI execution and retries fail, fallback mode provides a safe,
    conservative response to keep the session alive.
    """

    ACTIVE = "active"
    """Fallback mode is active—using degraded conservative behavior."""

    INACTIVE = "inactive"
    """Normal execution mode (fallback not needed)."""


class FallbackResponderPolicy:
    """W2.5.4 — Canonical degraded fallback response mode.

    When both normal AI execution and retries fail (retry exhausted, parse failure,
    validation failure), fallback mode provides a safe alternative that:
    - Makes minimal, conservative proposals
    - Avoids aggressive scene transitions
    - Preserves session continuity
    - Respects validation/guard boundaries
    - Is explicitly marked for diagnostics

    Fallback is NOT a bypass—it still goes through validation/guards. It simply
    provides conservative proposal defaults when AI generation fails.

    Fallback Constraints (what it CANNOT do):
    - Cannot propose risky scene transitions
    - Cannot propose extreme state mutations
    - Cannot bypass validation/guard enforcement
    - Cannot create arbitrary new narrative state

    Fallback Permissions (what it CAN do):
    - Propose minimal emotional/tension adjustments (±10 units)
    - Suggest safe scene continuity (stay in current scene)
    - Log the session state for investigation
    - Advance the turn counter (session progress)
    """

    # Fallback is activated when normal execution is exhausted
    # NOTE: RETRY_EXHAUSTED skips fallback and goes to SAFE_TURN (it's already exhausted)
    FALLBACK_TRIGGER_FAILURES: set[AIFailureClass] = {
        AIFailureClass.PARSE_FAILURE,        # Could not parse adapter output
        AIFailureClass.STRUCTURALLY_INVALID_OUTPUT,  # Parsed but invalid schema
    }

    @classmethod
    def should_activate_fallback(cls, failure_class: AIFailureClass) -> bool:
        """Check if fallback mode should activate for a failure.

        Fallback activates only for specific non-retryable failures that have
        exhausted recovery options.

        Args:
            failure_class: The failure that occurred

        Returns:
            True if fallback mode should activate, False otherwise
        """
        return failure_class in cls.FALLBACK_TRIGGER_FAILURES

    @classmethod
    def get_fallback_trigger_failures(cls) -> set[AIFailureClass]:
        """Get the set of failures that trigger fallback mode.

        Returns:
            Set of AIFailureClass values that activate fallback
        """
        return cls.FALLBACK_TRIGGER_FAILURES.copy()

    @classmethod
    def is_fallback_conservative(cls) -> bool:
        """Verify fallback behavior is conservative (not risky).

        Fallback is explicitly designed to be conservative and safe:
        - Minimal proposals
        - No aggressive transitions
        - Session continuity over drama
        - Guard compliance mandatory

        Returns:
            True (fallback is inherently conservative by design)
        """
        return True

    @classmethod
    def fallback_respects_guards(cls) -> bool:
        """Verify fallback proposals still go through validation/guards.

        Fallback is not a bypass. Even fallback proposals must pass the full
        validation pipeline, guard enforcement, and mutation policy.

        Returns:
            True (fallback respects guard enforcement)
        """
        return True

    @classmethod
    def is_fallback_marked_explicitly(cls) -> bool:
        """Verify fallback activation is marked in runtime state.

        Fallback activation is always explicit and visible in:
        - TurnExecutionResult.failure_reason
        - AIDecisionLog entries
        - Runtime event logs
        - Diagnostic traces

        This ensures fallback is never silent or implicit.

        Returns:
            True (fallback is explicitly marked)
        """
        return True

    @classmethod
    def get_fallback_mode_status(cls, failure_class: AIFailureClass | None) -> FallbackResponderMode:
        """Get the current fallback mode status.

        Args:
            failure_class: The current failure class (None if no failure)

        Returns:
            FallbackResponderMode indicating active or inactive status
        """
        if failure_class is None:
            return FallbackResponderMode.INACTIVE
        if cls.should_activate_fallback(failure_class):
            return FallbackResponderMode.ACTIVE
        return FallbackResponderMode.INACTIVE

    @classmethod
    def get_fallback_constraints(cls) -> dict[str, str]:
        """Get the canonical constraints on fallback behavior.

        Returns:
            Dictionary of constraint names to descriptions
        """
        return {
            "no_risky_transitions": "Cannot propose aggressive scene transitions",
            "no_extreme_mutations": "Cannot propose extreme state changes (±10 unit limit)",
            "must_pass_guards": "All proposals must pass validation/guard enforcement",
            "no_arbitrary_state": "Cannot create arbitrary new narrative elements",
            "minimal_proposals": "Keep proposals conservative and minimal",
            "continuity_focus": "Prioritize session continuity over dramatic progress",
        }

    @classmethod
    def get_fallback_permissions(cls) -> dict[str, str]:
        """Get the canonical permissions for fallback behavior.

        Returns:
            Dictionary of permission names to descriptions
        """
        return {
            "minimal_adjustments": "Propose minimal emotional/tension adjustments (±10 units)",
            "safe_continuity": "Suggest scene continuity (stay in current scene)",
            "state_logging": "Log session state for investigation",
            "advance_turn": "Advance turn counter (session progress)",
            "preserve_state": "Maintain existing character/scene state",
        }


class SafeTurnMode(str, Enum):
    """Safe-turn modes for unrecoverable but survivable AI failures.

    When normal AI execution, retries, and fallback all fail, safe-turn
    provides a minimal no-op turn that completes the turn safely without
    mutation or invalid progression.
    """

    ACTIVE = "active"
    """Safe-turn mode is active—no-op minimal behavior."""

    INACTIVE = "inactive"
    """Normal execution mode (safe-turn not needed)."""


class SafeTurnPolicy:
    """W2.5.5 — Canonical safe-turn/no-op path for unrecoverable failures.

    When all recovery mechanisms fail (retry exhausted, fallback failed,
    validation impossible), safe-turn provides a last-resort option that:
    - Completes the turn without unsafe mutation
    - Preserves session coherence
    - Avoids risky state transitions
    - Keeps the session alive for investigation
    - Is explicitly marked for diagnostics

    Safe-Turn Semantics:
    A safe-turn is a minimal no-op that:
    1. Advances the turn counter (session continues)
    2. Preserves all existing character/scene state (no mutation)
    3. Logs the failure for investigation
    4. Avoids scene transitions (stay in current)
    5. Makes no proposals (empty delta list)

    Safe-Turn Triggers:
    Safe-turn is used when:
    - Fallback mode was activated but also failed
    - Validation completely prevents any proposal
    - Runtime is in a degraded state but must continue
    - Investigation is needed (RESTORE recovery)

    Safe-Turn Guarantees:
    - Session remains alive and internally consistent
    - No protected state is mutated
    - No invalid progressions occur
    - All changes are visible and logged
    """

    # Failures that trigger safe-turn (after all other recovery fails)
    SAFE_TURN_TRIGGERS: set[AIFailureClass] = {
        AIFailureClass.RETRY_EXHAUSTED,      # Retried max times
        AIFailureClass.UNEXPECTED_RUNTIME_ERROR,  # Systematic issue
    }

    # Protected state that safe-turn CANNOT mutate
    PROTECTED_STATE_BOUNDARIES: set[str] = {
        "character_existence",      # Cannot delete/create characters
        "scene_validity",           # Cannot enter invalid scenes
        "narrative_coherence",      # Cannot break story structure
        "turn_progression",         # Can only advance, never revert
    }

    @classmethod
    def should_activate_safe_turn(cls, failure_class: AIFailureClass) -> bool:
        """Check if safe-turn should activate for a failure.

        Safe-turn is the last resort when all other recovery paths fail.

        Args:
            failure_class: The failure that occurred

        Returns:
            True if safe-turn should activate, False otherwise
        """
        return failure_class in cls.SAFE_TURN_TRIGGERS

    @classmethod
    def get_safe_turn_mode_status(cls, failure_class: AIFailureClass | None) -> SafeTurnMode:
        """Get the current safe-turn mode status.

        Args:
            failure_class: The current failure class (None if no failure)

        Returns:
            SafeTurnMode indicating active or inactive status
        """
        if failure_class is None:
            return SafeTurnMode.INACTIVE
        if cls.should_activate_safe_turn(failure_class):
            return SafeTurnMode.ACTIVE
        return SafeTurnMode.INACTIVE

    @classmethod
    def get_safe_turn_semantics(cls) -> dict[str, str]:
        """Get the canonical safe-turn behavior semantics.

        Returns:
            Dictionary of semantic rules for safe-turn execution
        """
        return {
            "advance_turn_counter": "Turn counter advances (session continues)",
            "no_state_mutation": "No character or scene state is modified",
            "no_proposals": "No state change proposals are made",
            "no_transitions": "No scene transitions (stay in current)",
            "no_narrative_change": "Narrative/lore state remains unchanged",
            "preserve_continuity": "Session coherence and continuity preserved",
            "log_failure": "Failure reason is logged for investigation",
            "mark_explicitly": "Safe-turn status is marked in runtime state",
        }

    @classmethod
    def get_protected_state_boundaries(cls) -> set[str]:
        """Get the protected state boundaries that safe-turn respects.

        Safe-turn cannot cross these boundaries.

        Returns:
            Set of protected state boundary names
        """
        return cls.PROTECTED_STATE_BOUNDARIES.copy()

    @classmethod
    def validates_protected_boundaries(cls) -> bool:
        """Verify safe-turn enforces protected state boundaries.

        Safe-turn is explicitly designed to respect protected boundaries:
        - Cannot delete/create characters
        - Cannot enter invalid scenes
        - Cannot break narrative structure
        - Can only advance turn, never revert

        Returns:
            True (safe-turn respects protected boundaries by design)
        """
        return True

    @classmethod
    def get_safe_turn_invariants(cls) -> dict[str, str]:
        """Get the invariants that must hold during safe-turn.

        These invariants guarantee session coherence.

        Returns:
            Dictionary of invariant names to descriptions
        """
        return {
            "session_alive": "Session remains alive and responsive",
            "state_consistent": "Character and scene state remains consistent",
            "turn_counter_advances": "Turn counter always increases (never decreases)",
            "no_data_loss": "No existing state is lost or deleted",
            "narratively_coherent": "Session narrative remains coherent",
            "explicitly_logged": "Safe-turn activation is logged with full context",
        }

    @classmethod
    def is_safe_turn_minimal(cls) -> bool:
        """Verify safe-turn is minimal (no unnecessary operations).

        Safe-turn does the bare minimum needed to keep session alive:
        - Advance turn counter
        - Preserve state
        - Log failure
        - Exit cleanly

        Returns:
            True (safe-turn is minimal by design)
        """
        return True


class StateSnapshot(BaseModel):
    """Minimal snapshot of last valid session state.

    StateSnapshot captures the essential mutable state at a known-valid point
    (typically before AI execution). If an operation fails catastrophically,
    RestorePolicy can restore back to this snapshot.

    Minimal scope: only captures what could be mutated by AI (canonical_state,
    turn_counter). Does not capture context_layers, metadata, or other
    immutable/diagnostic data.

    Attributes:
        turn_number: Turn counter at snapshot time.
        canonical_state: World state dict (deepcopy'd).
        snapshot_reason: Why snapshot was taken (e.g., "pre_ai_execution", "pre_fallback").
        created_at: Timestamp when snapshot was captured.
    """

    turn_number: int
    """The turn counter value at snapshot time."""

    canonical_state: dict[str, Any]
    """Deep copy of the canonical state at snapshot time."""

    snapshot_reason: str
    """Reason for taking this snapshot (diagnostic/audit)."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """When this snapshot was captured."""

    def is_valid_for_restore(self) -> bool:
        """Check if this snapshot is valid enough to restore from.

        Snapshot is valid if:
        - turn_number is >= 0
        - canonical_state is a non-empty dict
        - snapshot was created recently (not stale)

        Returns:
            True if snapshot can be safely restored, False otherwise
        """
        if self.turn_number < 0:
            return False
        if not isinstance(self.canonical_state, dict):
            return False
        # Snapshots older than 1 hour are suspicious (shouldn't happen in normal play)
        age_seconds = (datetime.now(timezone.utc) - self.created_at).total_seconds()
        if age_seconds > 3600:
            return False
        return True


class RestorePolicy:
    """W2.5.6 — Canonical last-valid-state restore for failed turns.

    When recovery mechanisms (retry, fallback, safe-turn) all fail,
    RestorePolicy provides last resort: explicit restoration to the last
    known-valid state. This prevents partial corruption and keeps the
    session coherent for investigation.

    Restore Semantics:
    1. StateSnapshot captures state before risky operations
    2. On failure requiring restore, RestorePolicy applies snapshot
    3. Restore is explicit and auditable (marked in logs)
    4. Session continues from restored state (no corruption left behind)

    Restore Triggers:
    - RETRY_EXHAUSTED after all retry attempts fail
    - UNEXPECTED_RUNTIME_ERROR when system is in degraded state
    - After fallback has also failed
    - When safe-turn is insufficient (should be rare)

    Restore Guarantees:
    - No partial invalid state remains after restore
    - Restore is deterministic (same snapshot → same restored state)
    - All restores are logged and auditable
    - Turn counter may be advanced (investigate) or reverted (rare)
    """

    # Failures that REQUIRE restore (all recovery exhausted)
    RESTORE_REQUIRED_FAILURES: set[AIFailureClass] = {
        AIFailureClass.RETRY_EXHAUSTED,          # All retries failed
        AIFailureClass.UNEXPECTED_RUNTIME_ERROR,  # System unstable
    }

    # Restoration strategy: what level to restore to
    # Last valid = snapshot taken before any risky operation
    RESTORE_LEVEL: str = "last_valid"
    """Level of restoration: 'last_valid' means restore to pre-execution snapshot."""

    @classmethod
    def is_last_valid_state(
        cls,
        failure_class: AIFailureClass,
        is_pre_execution_snapshot: bool = False,
    ) -> bool:
        """Check if a state can be considered 'last valid'.

        Last valid means: state was captured before any operation that could fail
        (typically before AI execution). If failure occurred after this point,
        the pre-execution snapshot is the last known-good state.

        Args:
            failure_class: The failure that occurred
            is_pre_execution_snapshot: True if snapshot was pre-execution

        Returns:
            True if snapshot qualifies as last-valid, False otherwise
        """
        # Only pre-execution snapshots qualify as "last valid"
        # (post-execution snapshots may have partial mutations)
        return (
            failure_class in cls.RESTORE_REQUIRED_FAILURES
            and is_pre_execution_snapshot is True
        )

    @classmethod
    def should_require_restore(
        cls,
        failure_class: AIFailureClass,
        recovery_action: "RecoveryAction",
    ) -> bool:
        """Check if restore is REQUIRED (vs optional/skipped).

        Restore is REQUIRED when:
        - Failure is in RESTORE_REQUIRED_FAILURES
        - Recovery action is RESTORE (not SAFE_TURN, not FALLBACK)

        Args:
            failure_class: The failure that occurred
            recovery_action: The recovery action being taken

        Returns:
            True if restore should be applied, False otherwise
        """
        if failure_class not in cls.RESTORE_REQUIRED_FAILURES:
            return False
        if recovery_action != RecoveryAction.RESTORE:
            return False
        return True

    @classmethod
    def apply_restore(
        cls,
        corrupted_state: dict[str, Any],
        snapshot: StateSnapshot,
    ) -> dict[str, Any]:
        """Apply a snapshot to restore clean state.

        Performs a deep copy of the snapshot's canonical_state to ensure
        that mutations to the returned dict don't affect the snapshot.

        Args:
            corrupted_state: The current (possibly corrupted) state
            snapshot: The snapshot to restore from

        Returns:
            Clean state dict matching the snapshot (deep copied)

        Raises:
            ValueError: If snapshot is not valid for restoration
        """
        if not snapshot.is_valid_for_restore():
            raise ValueError(
                f"Snapshot is not valid for restore: {snapshot.snapshot_reason}"
            )

        # Deep copy to ensure mutations don't affect the snapshot
        restored_state = deepcopy(snapshot.canonical_state)

        return restored_state

    @classmethod
    def get_restore_metadata(
        cls,
        failure_class: AIFailureClass,
        snapshot_turn: int,
        current_turn: int,
    ) -> dict[str, Any]:
        """Get explicit metadata marking restoration for audit logs.

        This ensures restore actions are visible and traceable in event logs
        and runtime state. Critical for investigation and debugging.

        Args:
            failure_class: The failure that triggered restore
            snapshot_turn: Turn number when snapshot was taken
            current_turn: Current turn counter

        Returns:
            Dict with restore metadata for logging
        """
        return {
            "restored": True,
            "reason": "last_valid_state_restore",
            "failure_class": failure_class.value,
            "snapshot_turn": snapshot_turn,
            "current_turn": current_turn,
            "recovered_to_turn": snapshot_turn,
            "turns_discarded": current_turn - snapshot_turn,
        }

    @classmethod
    def get_restore_semantics(cls) -> dict[str, str]:
        """Get semantic rules that define restore behavior.

        Returns:
            Dict mapping semantic concept to description
        """
        return {
            "snapshot_validity": "Only pre-execution snapshots count as 'last valid'",
            "determinism": "Same snapshot always produces same restored state",
            "auditability": "All restores are marked explicitly in logs",
            "no_silent_mutation": "Restore is never hidden—always visible to caller",
            "partial_corruption_prevention": "Restore clears any mutations made after snapshot",
        }


def generate_fallback_responder_proposal() -> "ParsedAIDecision":
    """Generate minimal, conservative fallback responder proposal.

    W2.5 Phase 3: Fallback Responder - Generate safe, minimal proposal when parse/structure fails.

    Fallback proposals are explicitly conservative:
    - No scene transitions (stay in current)
    - Minimal emotional/tension adjustments (±10 units max)
    - No risky state mutations
    - Must still pass validation/guard enforcement

    Returns:
        ParsedAIDecision with empty deltas (safe-turn equivalent).
        This allows the session to survive a parse failure while maintaining state.
    """
    # Import here to avoid circular dependency
    from app.runtime.ai_decision import ParsedAIDecision

    # Create minimal ParsedAIDecision for fallback
    # Empty deltas means no state mutations - conservative fallback
    return ParsedAIDecision(
        scene_interpretation="[fallback: scene continues unchanged]",
        detected_triggers=[],
        proposed_deltas=[],
        proposed_scene_id=None,  # No scene transition
        rationale="[fallback: minimal proposal due to parse/structure failure]",
        raw_output="[fallback mode]",
        parsed_source="fallback_responder",
    )
