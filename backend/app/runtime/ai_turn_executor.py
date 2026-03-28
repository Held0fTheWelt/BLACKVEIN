"""W2.1.4 — Integrate Canonical AI Execution Path into Turn Loop

Bridges the AI adapter layer (W2.1.1–3) into the existing turn runtime (W2.0.3).
The AI path wraps the mock path; no existing code is modified.

Core functions:
1. build_adapter_request — Maps session/module to AdapterRequest
2. decision_from_parsed — Bridge: ProposedDelta.target_path → ProposedStateDelta.target
3. _make_parse_failure_result — Error handling with state safety guarantee
4. execute_turn_with_ai — Integration entry point delegating to execute_turn
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_decision import ParseResult, process_adapter_response
from app.runtime.event_log import RuntimeEventLog
from app.runtime.turn_executor import (
    MockDecision,
    ProposedStateDelta,
    TurnExecutionResult,
    execute_turn,
)
from app.runtime.w2_models import DeltaType, SessionState


def build_adapter_request(
    session: SessionState,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
) -> AdapterRequest:
    """Build an AdapterRequest from session and module context.

    Maps canonical runtime state into the AI adapter contract.

    Args:
        session: Current session state
        module: Loaded content module
        operator_input: Optional operator instruction (empty string → None)
        recent_events: Optional list of recent events

    Returns:
        AdapterRequest ready for adapter.generate()
    """
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=recent_events or [],
        operator_input=operator_input or None,
        metadata={
            "module_id": module.metadata.module_id,
            "module_version": module.metadata.version,
        },
    )


def decision_from_parsed(parsed_decision: Any) -> MockDecision:
    """Bridge ParsedAIDecision to MockDecision for runtime consumption.

    This is the structural seam: ProposedDelta.target_path → ProposedStateDelta.target.

    Maps:
    - parsed_decision.proposed_deltas (ProposedDelta[]) → MockDecision.proposed_deltas (ProposedStateDelta[])
    - ProposedDelta.target_path → ProposedStateDelta.target
    - ProposedDelta.delta_type (str|None) → DeltaType(value) with try/except fallback to None
    - parsed_decision.scene_interpretation → MockDecision.narrative_text
    - parsed_decision.rationale → MockDecision.rationale

    Args:
        parsed_decision: ParsedAIDecision from process_adapter_response

    Returns:
        MockDecision ready for execute_turn
    """
    # Map proposed_deltas: ProposedDelta[] → ProposedStateDelta[]
    proposed_deltas: list[ProposedStateDelta] = []
    for delta in parsed_decision.proposed_deltas:
        # Coerce delta_type: str|None → DeltaType|None
        delta_type: DeltaType | None = None
        if delta.delta_type is not None:
            try:
                delta_type = DeltaType(delta.delta_type)
            except ValueError:
                # Invalid DeltaType string — fallback to None
                delta_type = None

        proposed_deltas.append(
            ProposedStateDelta(
                target=delta.target_path,  # Seam: target_path → target
                next_value=delta.next_value,
                delta_type=delta_type,
            )
        )

    # Create MockDecision with mapped fields
    return MockDecision(
        detected_triggers=parsed_decision.detected_triggers,
        proposed_deltas=proposed_deltas,
        proposed_scene_id=parsed_decision.proposed_scene_id,
        narrative_text=parsed_decision.scene_interpretation,  # Maps to narrative_text
        rationale=parsed_decision.rationale,
    )


def _make_parse_failure_result(
    session: SessionState,
    turn_number: int,
    errors: list[str],
    raw_output: str,
    started_at: datetime,
) -> TurnExecutionResult:
    """Create a TurnExecutionResult for parse failures with safety guarantees.

    State is unchanged — critical safety guarantee that malformed output cannot corrupt state.

    Args:
        session: Current session (state not modified)
        turn_number: Current turn number
        errors: List of parse errors
        raw_output: Raw adapter output for diagnostics
        started_at: Execution start time

    Returns:
        TurnExecutionResult with execution_status="system_error" and unchanged state
    """
    completed_at = datetime.now(timezone.utc)
    duration_ms = (completed_at - started_at).total_seconds() * 1000

    # Create audit events using RuntimeEventLog
    event_log = RuntimeEventLog(session_id=session.session_id, turn_number=turn_number)

    event_log.log(
        "turn_started",
        f"Turn {turn_number} started",
        payload={
            "turn_number": turn_number,
            "scene_id": session.current_scene_id,
        },
    )

    event_log.log(
        "ai_parse_failed",
        f"AI adapter output parse failed: {len(errors)} errors",
        payload={
            "error_count": len(errors),
            "errors": errors,
            "raw_output": raw_output,
        },
    )

    # Create failure result with state unchanged
    return TurnExecutionResult(
        turn_number=turn_number,
        session_id=session.session_id,
        execution_status="system_error",
        decision=MockDecision(),  # Empty mock decision for failed parse
        validation_outcome=None,
        validation_errors=errors,
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state=session.canonical_state.copy(),  # State unchanged
        updated_scene_id=session.current_scene_id,  # Scene unchanged
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        events=event_log.flush(),
    )


async def execute_turn_with_ai(
    session: SessionState,
    current_turn: int,
    adapter: StoryAIAdapter,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
) -> TurnExecutionResult:
    """Execute a turn with AI-generated decision.

    Full integration pipeline:
    1. Build adapter request from session/module
    2. Call adapter.generate()
    3. Parse adapter response
    4. If parse fails, return system_error result with unchanged state
    5. Bridge parsed decision to MockDecision
    6. Delegate to execute_turn for validation/execution

    Args:
        session: Current session state
        current_turn: Current turn number
        adapter: StoryAIAdapter implementation
        module: Loaded content module
        operator_input: Optional operator context (empty string → None)
        recent_events: Optional list of recent events

    Returns:
        TurnExecutionResult with execution status, deltas, state, and events
    """
    started_at = datetime.now(timezone.utc)

    # Step 1: Build adapter request
    request = build_adapter_request(
        session,
        module,
        operator_input=operator_input,
        recent_events=recent_events,
    )

    # Step 2: Generate response
    response: AdapterResponse = adapter.generate(request)

    # Step 3: Parse response
    parse_result: ParseResult = process_adapter_response(response)

    # Step 4: If parse failed, return system_error result
    if not parse_result.success:
        return _make_parse_failure_result(
            session,
            current_turn,
            parse_result.errors,
            parse_result.raw_output,
            started_at,
        )

    # Step 5: Bridge parsed decision to MockDecision
    mock_decision = decision_from_parsed(parse_result.decision)

    # Step 6: Delegate to execute_turn (full validation/execution)
    return await execute_turn(session, current_turn, mock_decision, module)
