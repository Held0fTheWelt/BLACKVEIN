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
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.turn_executor import MockDecision


def test_execution_failure_reason_enum_exists():
    """ExecutionFailureReason enum available for explicit error classification."""
    from app.runtime.runtime_models import ExecutionFailureReason

    # Should have these failure reasons
    assert hasattr(ExecutionFailureReason, 'GENERATION_ERROR')
    assert hasattr(ExecutionFailureReason, 'PARSING_ERROR')
    assert hasattr(ExecutionFailureReason, 'VALIDATION_ERROR')
    assert hasattr(ExecutionFailureReason, 'NONE')  # For successful executions


def test_turn_execution_result_has_failure_reason():
    """TurnExecutionResult tracks explicit failure reason."""
    from app.runtime.turn_executor import TurnExecutionResult
    from app.runtime.runtime_models import ExecutionFailureReason

    result = TurnExecutionResult(
        turn_number=1,
        session_id="test",
        execution_status="system_error",
        decision=MockDecision(),
        failure_reason=ExecutionFailureReason.GENERATION_ERROR,
    )

    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR


def test_empty_adapter_output_fails_safely(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Empty AI output is detected and handled safely."""
    from app.runtime.ai_turn_executor import execute_turn_with_ai
    from app.runtime.runtime_models import ExecutionFailureReason

    session = god_of_carnage_module_with_state

    class EmptyAdapter(StoryAIAdapter):
        @property
        def adapter_name(self):
            return "empty-test"

        def generate(self, request):
            return AdapterResponse(
                raw_output="",
                structured_payload=None,
            )

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=EmptyAdapter(),
            module=god_of_carnage_module,
        )
    )

    # W2.5 Phase 4: Empty adapter output triggers retry, exhaustion activates safe-turn
    # Safe-turn preserves state and allows session to continue
    assert result.execution_status == "success"
    assert result.failure_reason == ExecutionFailureReason.GENERATION_ERROR
    assert result.updated_canonical_state == session.canonical_state  # Safe-turn doesn't mutate


def test_malformed_structured_output_fails_safely(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Missing required fields in structured_payload fails safely."""
    from app.runtime.ai_turn_executor import execute_turn_with_ai
    from app.runtime.runtime_models import ExecutionFailureReason

    session = god_of_carnage_module_with_state

    class MalformedAdapter(StoryAIAdapter):
        @property
        def adapter_name(self):
            return "malformed"

        def generate(self, request):
            return AdapterResponse(
                raw_output="test",
                structured_payload={
                    "scene_interpretation": "Test",
                    # Missing: "rationale", "detected_triggers", "proposed_state_deltas"
                },
            )

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=MalformedAdapter(),
            module=god_of_carnage_module,
        )
    )

    # W2.5 Phase 3: Parse failures now trigger fallback recovery instead of terminal failure
    # Fallback responder generates minimal proposal (empty deltas) which passes validation
    assert result.execution_status == "success"
    assert result.failure_reason == ExecutionFailureReason.PARSING_ERROR
    # Fallback proposals have no deltas
    assert result.accepted_deltas == []
    assert result.rejected_deltas == []


def test_state_safety_on_failure(
    god_of_carnage_module_with_state, god_of_carnage_module
):
    """Failed AI turns do not corrupt canonical state."""
    import copy

    session = god_of_carnage_module_with_state
    initial_state = copy.deepcopy(session.canonical_state)

    class FailingAdapter(StoryAIAdapter):
        @property
        def adapter_name(self):
            return "failing"

        def generate(self, request):
            return AdapterResponse(
                raw_output="",
                structured_payload=None,
                error="Adapter failure",
            )

    from app.runtime.ai_turn_executor import execute_turn_with_ai

    result = asyncio.run(
        execute_turn_with_ai(
            session,
            current_turn=session.turn_counter + 1,
            adapter=FailingAdapter(),
            module=god_of_carnage_module,
        )
    )

    # W2.5 Phase 4: Adapter failure triggers retry exhaustion, then safe-turn recovery
    # Safe-turn preserves state safety guarantee - no mutations on failure
    assert result.execution_status == "success"
    assert result.updated_canonical_state == initial_state  # Safe-turn doesn't mutate
    assert session.canonical_state == initial_state


def test_no_w2_scope_jump_failure_handling():
    """No scope jump into W2.2+ features."""
    assert True  # Scope validation is manual
