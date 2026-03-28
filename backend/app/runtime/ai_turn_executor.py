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
from app.runtime.decision_policy import AIDecisionPolicy
from app.runtime.event_log import RuntimeEventLog
from app.runtime.turn_executor import (
    MockDecision,
    ProposedStateDelta,
    TurnExecutionResult,
    execute_turn,
)
from app.runtime.validators import validate_action_type, validate_action_structure
from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaType,
    DeltaValidationStatus,
    ExecutionFailureReason,
    GuardOutcome,
    SessionState,
    StateDelta,
)


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


def _convert_proposed_delta_to_state_delta(
    proposed_delta: ProposedStateDelta,
    validation_status: DeltaValidationStatus,
    turn_number: int,
) -> StateDelta:
    """Convert a runtime ProposedStateDelta to a canonical StateDelta for logging.

    Args:
        proposed_delta: Runtime delta from execute_turn
        validation_status: Whether this delta was accepted/rejected
        turn_number: Turn when delta was proposed

    Returns:
        StateDelta suitable for AIDecisionLog.accepted_deltas or rejected_deltas
    """
    # Extract target entity from target path (e.g., "characters.veronique.emotional_state" → "veronique")
    target_entity = None
    path_parts = proposed_delta.target.split(".")
    if len(path_parts) >= 2:
        target_entity = path_parts[1]  # characters.<entity>...

    return StateDelta(
        delta_type=proposed_delta.delta_type,
        target_path=proposed_delta.target,
        target_entity=target_entity,
        previous_value=proposed_delta.previous_value,
        next_value=proposed_delta.next_value,
        source="ai_proposal",
        validation_status=validation_status,
        turn_number=turn_number,
    )


def _create_decision_log(
    session: SessionState,
    current_turn: int,
    parsed_decision: Any,
    adapter_response: AdapterResponse,
    turn_result: TurnExecutionResult,
) -> AIDecisionLog:
    """Create AIDecisionLog from successful turn execution.

    Args:
        session: Current session
        current_turn: Turn number
        parsed_decision: Parsed AI decision
        adapter_response: Raw adapter response
        turn_result: Result from execute_turn

    Returns:
        AIDecisionLog with complete tracing information
    """
    # Determine overall validation outcome from canonical guard_outcome
    if turn_result.execution_status == "success":
        _outcome_map = {
            GuardOutcome.ACCEPTED: AIValidationOutcome.ACCEPTED,
            GuardOutcome.PARTIALLY_ACCEPTED: AIValidationOutcome.PARTIAL,
            GuardOutcome.REJECTED: AIValidationOutcome.REJECTED,
            GuardOutcome.STRUCTURALLY_INVALID: AIValidationOutcome.ERROR,
        }
        validation_outcome = _outcome_map.get(turn_result.guard_outcome, AIValidationOutcome.ERROR)
    else:
        validation_outcome = AIValidationOutcome.ERROR

    # Accepted and rejected deltas are already StateDelta objects from execute_turn
    # Just use them directly
    accepted_state_deltas = turn_result.accepted_deltas
    rejected_state_deltas = turn_result.rejected_deltas

    # Normalize guard notes with count and outcome label
    guard_notes = None
    if turn_result.validation_errors:
        errors = turn_result.validation_errors
        count = len(errors)
        outcome_label = turn_result.guard_outcome.value
        sample = "; ".join(errors[:3])
        guard_notes = f"{count} error{'s' if count != 1 else ''}; {outcome_label}: {sample}"

    return AIDecisionLog(
        session_id=session.session_id,
        turn_number=current_turn,
        raw_output=adapter_response.raw_output,
        parsed_output={
            "scene_interpretation": parsed_decision.scene_interpretation,
            "detected_triggers": parsed_decision.detected_triggers,
            "rationale": parsed_decision.rationale,
            "proposed_scene_id": parsed_decision.proposed_scene_id,
            "proposed_deltas_count": len(parsed_decision.proposed_deltas),
        },
        validation_outcome=validation_outcome,
        accepted_deltas=accepted_state_deltas,
        rejected_deltas=rejected_state_deltas,
        guard_notes=guard_notes,
    )


def _create_error_decision_log(
    session: SessionState,
    current_turn: int,
    raw_output: str,
    errors: list[str],
    error_type: str,
) -> AIDecisionLog:
    """Create AIDecisionLog for error paths (parse error, adapter error).

    Args:
        session: Current session
        current_turn: Turn number
        raw_output: Raw adapter output (may be partial or malformed)
        errors: List of error messages
        error_type: Type of error ("parse_error", "adapter_error", etc.)

    Returns:
        AIDecisionLog with ERROR outcome
    """
    count = len(errors)
    sample = "; ".join(errors[:3])
    guard_notes = f"{count} error{'s' if count != 1 else ''}; {error_type}: {sample}"

    return AIDecisionLog(
        session_id=session.session_id,
        turn_number=current_turn,
        raw_output=raw_output,
        parsed_output=None,
        validation_outcome=AIValidationOutcome.ERROR,
        accepted_deltas=[],
        rejected_deltas=[],
        guard_notes=guard_notes,
    )


def _store_decision_log(session: SessionState, log: AIDecisionLog) -> None:
    """Store decision log in session metadata.

    Args:
        session: Current session (modified in-place)
        log: AIDecisionLog to store
    """
    if "ai_decision_logs" not in session.metadata:
        session.metadata["ai_decision_logs"] = []

    session.metadata["ai_decision_logs"].append(log)


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

    # Step 2b: If adapter error, create error log and return early
    if response.error:
        error_log = _create_error_decision_log(
            session,
            current_turn,
            response.raw_output,
            [response.error],
            "adapter_error",
        )
        _store_decision_log(session, error_log)

        result = _make_parse_failure_result(
            session,
            current_turn,
            [f"Adapter error: {response.error}"],
            response.raw_output,
            started_at,
        )
        result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
        return result

    # Step 2c: Check for empty output
    if not response.raw_output or not response.raw_output.strip():
        error_log = _create_error_decision_log(
            session,
            current_turn,
            response.raw_output or "",
            ["Empty AI response"],
            "generation_error",
        )
        _store_decision_log(session, error_log)

        result = _make_parse_failure_result(
            session,
            current_turn,
            ["Empty AI response"],
            response.raw_output or "",
            started_at,
        )
        result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
        return result

    # Step 3: Parse response
    parse_result: ParseResult = process_adapter_response(response)

    # Step 4: If parse failed, create error decision log and return system_error result
    if not parse_result.success:
        error_log = _create_error_decision_log(
            session,
            current_turn,
            parse_result.raw_output,
            parse_result.errors,
            "parse_error",
        )
        _store_decision_log(session, error_log)

        result = _make_parse_failure_result(
            session,
            current_turn,
            parse_result.errors,
            parse_result.raw_output,
            started_at,
        )
        result.failure_reason = ExecutionFailureReason.PARSING_ERROR
        return result

    # Step 4b: Validate that proposed actions comply with canonical policy
    # Check each proposed delta's action type and structure before state mutation
    policy_validation_errors = []
    for delta in parse_result.decision.proposed_deltas:
        # Infer action type from delta: default to STATE_UPDATE
        # (In future, AI output might explicitly specify action_type)
        delta_type = delta.delta_type or "state_update"

        # Step 4b.1: Validate the action type is allowed
        is_valid, error = validate_action_type(delta_type)
        if not is_valid:
            # Invalid action type - fail parse before state mutation
            policy_validation_errors.append(error)
            continue

        # Step 4b.2: Validate action structure (W2.2.1 canonical enforcement)
        # Create action_data dict from delta for validate_action_structure
        action_data = {
            "target_path": delta.target_path,
            "next_value": delta.next_value,
        }
        is_valid, structure_errors = validate_action_structure(
            delta_type, action_data, module=module, session=session
        )
        if not is_valid:
            # Invalid action structure - fail before state mutation
            policy_validation_errors.extend(structure_errors)

    if policy_validation_errors:
        # Policy validation failed - create error log and return early
        error_log = _create_error_decision_log(
            session,
            current_turn,
            parse_result.raw_output,
            policy_validation_errors,
            "policy_validation_error",
        )
        _store_decision_log(session, error_log)

        result = _make_parse_failure_result(
            session,
            current_turn,
            policy_validation_errors,
            parse_result.raw_output,
            started_at,
        )
        result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR
        return result

    # Step 5: Bridge parsed decision to MockDecision
    mock_decision = decision_from_parsed(parse_result.decision)

    # Step 6: Delegate to execute_turn (full validation/execution)
    turn_result = await execute_turn(session, current_turn, mock_decision, module)

    # Step 7: Create and store decision log from execution result
    decision_log = _create_decision_log(
        session=session,
        current_turn=current_turn,
        parsed_decision=parse_result.decision,
        adapter_response=response,
        turn_result=turn_result,
    )
    _store_decision_log(session, decision_log)

    # Step 8: Set failure_reason based on execution outcome
    if turn_result.execution_status == "success":
        if len(turn_result.accepted_deltas) == 0 and len(turn_result.rejected_deltas) > 0:
            # All deltas were rejected - this is a severe validation failure
            turn_result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR
        else:
            turn_result.failure_reason = ExecutionFailureReason.NONE
    else:
        turn_result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR

    return turn_result
