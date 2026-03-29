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

from enum import Enum


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
