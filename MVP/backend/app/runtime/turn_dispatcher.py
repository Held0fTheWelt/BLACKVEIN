"""DEPRECATED (transitional): in-process turn router for W2 ``SessionState``.

``dispatch_turn()`` chooses mock vs AI **inside this Python process only**. It is
**not** the live play entry point (World Engine). Kept for unit tests, preview, and
offline tooling until callers migrate to engine APIs.

Core function:
- dispatch_turn() — mock vs AI path by ``execution_mode`` (in-process only).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.content.module_models import ContentModule
    from app.runtime.ai_adapter import StoryAIAdapter
    from app.runtime.turn_executor import TurnExecutionResult
    from app.runtime.runtime_models import SessionState

from app.observability.trace import get_trace_id, ensure_trace_id
from app.observability.audit_log import log_turn_execution


async def dispatch_turn(
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    *,
    mock_decision_provider: callable | None = None,
    ai_adapter: StoryAIAdapter | None = None,
    operator_input: str = "",
) -> TurnExecutionResult:
    """Canonical turn execution dispatcher.

    Routes turn execution to either mock or AI path based on session.execution_mode.

    When execution_mode == "ai":
    - Resolves adapter from session.adapter_name (via adapter registry)
    - Can be overridden by explicit ai_adapter parameter (for tests)
    - Calls execute_turn_with_ai() with the resolved adapter
    - AI path: request → adapter → parse → normalize → validate → execute

    When execution_mode == "mock":
    - Uses provided mock_decision_provider (if given) or MockDecision default
    - Calls execute_turn() with the mock decision
    - Mock path: deterministic decision → validate → execute

    Args:
        session: Current session state
        current_turn: Current turn number
        module: Loaded content module
        mock_decision_provider: Optional callable that returns MockDecision for mock mode
        ai_adapter: Optional adapter for AI mode (overrides session.adapter_name)
        operator_input: Optional operator context

    Returns:
        TurnExecutionResult with execution_status, deltas, state, and events

    Raises:
        ValueError: If execution_mode=="ai" but adapter cannot be resolved
    """
    # Import here to avoid circular imports
    from app.runtime.adapter_registry import get_adapter
    from app.runtime.ai_turn_executor import execute_turn_with_ai
    from app.runtime.turn_executor import MockDecision, execute_turn

    execution_mode = session.execution_mode.lower() if session.execution_mode else "mock"

    # Ensure trace_id is set for observability (works with/without Flask request context)
    trace_id = get_trace_id() or ensure_trace_id(None)

    # W2 Helper-Role Layer: Deferred to W4
    # The following bounded helpers are implemented in helper_functions.py
    # but are deferred for actual integration into the dispatcher path:
    # - compress_context_for_llm: prepare token-efficient context
    # - extract_active_triggers: match state against decision policy rules
    # - normalize_proposed_deltas: fix structural issues before guard evaluation
    # - precheck_guard_routing: recommend guard path based on delta validity
    # Integration is blocked pending: decision on whether compression affects
    # AI adapter input format, whether triggers inform actual dispatcher routing,
    # and whether delta normalization belongs before or after LLM output parsing.

    result: TurnExecutionResult
    if execution_mode == "ai":
        # AI execution path
        # Resolve adapter: explicit parameter overrides session configuration
        resolved_adapter = ai_adapter
        if not resolved_adapter:
            # Look up adapter from session.adapter_name
            resolved_adapter = get_adapter(session.adapter_name)

        if not resolved_adapter:
            raise ValueError(
                f"AI execution mode selected but adapter '{session.adapter_name}' "
                f"not found in registry. Register it with register_adapter()."
            )

        result = await execute_turn_with_ai(
            session,
            current_turn,
            resolved_adapter,
            module,
            operator_input=operator_input,
        )

    else:
        # Mock execution path (default)
        # Use provided mock_decision_provider or default to empty MockDecision
        if mock_decision_provider:
            decision = mock_decision_provider()
        else:
            decision = MockDecision()

        result = await execute_turn(session, current_turn, decision, module)

    # Log turn execution event for observability (A2 runtime boundary)
    log_turn_execution(
        trace_id=trace_id,
        session_id=session.session_id,
        execution_mode=execution_mode,
        turn_before=current_turn,
        turn_after=result.turn_number,
        outcome=result.execution_status,
    )

    return result
