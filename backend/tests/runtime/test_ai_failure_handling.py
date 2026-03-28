"""Tests for W2.1.6 — AI Execution Failure Handling

Comprehensive test suite for safe handling of AI execution failures:
- Adapter/generation failures
- Empty outputs
- Malformed structured outputs
- Normalization failures
- Pre-validation failures
- Severe validation rejections (all deltas rejected)
- State safety guarantees
- Logging coherence across failure modes
"""

import asyncio
import pytest
from app.runtime.turn_executor import MockDecision


def test_execution_failure_reason_enum_exists():
    """ExecutionFailureReason enum available for explicit error classification."""
    from app.runtime.w2_models import ExecutionFailureReason

    # Should have these failure reasons
    assert hasattr(ExecutionFailureReason, 'GENERATION_ERROR')
    assert hasattr(ExecutionFailureReason, 'PARSING_ERROR')
    assert hasattr(ExecutionFailureReason, 'VALIDATION_ERROR')
    assert hasattr(ExecutionFailureReason, 'NONE')  # For successful executions


def test_turn_execution_result_has_failure_reason():
    """TurnExecutionResult tracks explicit failure reason."""
    from app.runtime.turn_executor import TurnExecutionResult
    from app.runtime.w2_models import ExecutionFailureReason

    result = TurnExecutionResult(
        turn_number=1,
        session_id="test",
        execution_status="system_error",
        decision=MockDecision(),
        failure_reason=ExecutionFailureReason.GENERATION_ERROR,
    )

    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR
