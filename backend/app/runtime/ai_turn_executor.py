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
from app.runtime.ai_decision import ParseResult, ParsedAIDecision, process_adapter_response
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.decision_policy import AIDecisionPolicy
from app.runtime.event_log import RuntimeEventLog
from app.runtime.turn_executor import (
    MockDecision,
    ProposedStateDelta,
    TurnExecutionResult,
    execute_turn,
)
from app.runtime.role_structured_decision import ParsedRoleAwareDecision
from app.runtime.validators import validate_action_type, validate_action_structure
from app.runtime.w2_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaType,
    DeltaValidationStatus,
    ExecutionFailureReason,
    GuardOutcome,
    ProposalSource,
    SessionState,
    StateDelta,
)


def process_role_structured_decision(
    role_aware_decision: ParsedRoleAwareDecision,
) -> MockDecision:
    """Extract responder candidates from role-structured decision, mark as RESPONDER_DERIVED.

    This function bridges W2.4 role separation (interpreter, director, responder)
    into the canonical guarded execution path. It extracts state_change_candidates
    from the responder section and marks them with RESPONDER_DERIVED source.

    Only responder-derived proposals are authorized to enter the canonical
    execution path when enforce_responder_only=True is set.

    Args:
        role_aware_decision: ParsedRoleAwareDecision with role sections preserved

    Returns:
        MockDecision with proposal_source=ProposalSource.RESPONDER_DERIVED

    Process:
    1. Extract state_change_candidates from responder section
    2. Convert to ProposedStateDelta format (responder candidates are already in that form)
    3. Return MockDecision marked RESPONDER_DERIVED
    """
    # Get responder candidates (state_change_candidates from responder section)
    responder_candidates = role_aware_decision.responder.state_change_candidates or []

    # Convert responder StateChangeCandidate to ProposedStateDelta
    # StateChangeCandidate has: target_path, proposed_value, rationale
    # ProposedStateDelta expects: target, next_value, delta_type, source
    proposed_deltas = []
    for candidate in responder_candidates:
        proposed_deltas.append(
            ProposedStateDelta(
                target=candidate.target_path,
                next_value=candidate.proposed_value,
                delta_type=None,  # Will be inferred during validation
                source="ai_proposal",
            )
        )

    # Return decision marked RESPONDER_DERIVED
    return MockDecision(
        detected_triggers=[],
        proposed_deltas=proposed_deltas,
        proposed_scene_id=None,
        narrative_text="",
        rationale="",
        proposal_source=ProposalSource.RESPONDER_DERIVED,
    )


def build_adapter_request(
    session: SessionState,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
    attempt: int = 1,  # W2.5 Phase 2: track retry attempt for context trimming
) -> AdapterRequest:
    """Build an AdapterRequest from session and module context.

    Maps canonical runtime state into the AI adapter contract.
    On retry attempts (attempt > 1), context is progressively trimmed to reduce size.

    Args:
        session: Current session state
        module: Loaded content module
        operator_input: Optional operator context
        recent_events: Optional recent event list
        attempt: Retry attempt number (1 = initial, 2+ = retries with reduced context)
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
        request_role_structured_output=True,  # W2.4.2: Request role-structured format (interpreter/director/responder)
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
        guard_outcome=turn_result.guard_outcome,
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
        guard_outcome=GuardOutcome.STRUCTURALLY_INVALID,
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
    from copy import deepcopy
    from app.runtime.ai_failure_recovery import StateSnapshot

    started_at = datetime.now(timezone.utc)

    # W2.5 Phase 5: Capture pre-execution snapshot for restore
    # This snapshot is taken BEFORE any risky operation (adapter call, execution)
    # If recovery fails catastrophically, we can restore to this known-good state
    pre_execution_snapshot = StateSnapshot(
        turn_number=session.turn_counter,
        canonical_state=deepcopy(session.canonical_state),
        snapshot_reason="pre_ai_execution",
    )

    # Step 1: Build adapter request (with attempt tracking for reduced-context retry)
    request = build_adapter_request(
        session,
        module,
        operator_input=operator_input,
        recent_events=recent_events,
        attempt=1,  # Will be updated in retry loop below
    )

    # Step 2: Generate response with retry loop (W2.5 Phase 1)
    from app.runtime.ai_failure_recovery import RetryPolicy, AIFailureClass

    retry_policy = RetryPolicy()
    response: AdapterResponse | None = None
    current_attempt = 1

    while current_attempt <= retry_policy.MAX_RETRIES:
        # W2.5 Phase 2: Rebuild request with current attempt for reduced-context mode
        if current_attempt > 1:
            request = build_adapter_request(
                session,
                module,
                operator_input=operator_input,
                recent_events=recent_events,
                attempt=current_attempt,
            )

        response = adapter.generate(request)

        # Check if adapter call succeeded or failed
        has_error = response.error is not None
        is_empty = not response.raw_output or not response.raw_output.strip()

        if has_error or is_empty:
            # Adapter error or empty response occurred
            failure_class = AIFailureClass.ADAPTER_ERROR if has_error else AIFailureClass.ADAPTER_ERROR

            # Check if this failure is retryable
            if (
                retry_policy.is_retryable_failure(failure_class)
                and current_attempt < retry_policy.MAX_RETRIES
            ):
                # Retryable and attempts remain - continue to next iteration
                current_attempt += 1
                continue
            else:
                # Not retryable or max attempts reached - break out of loop
                break
        else:
            # Success - no error, no empty response
            break

    # Step 2b: Handle adapter error or empty output
    # W2.5 Phase 4-5: If retries exhausted, check if restore is needed
    if response.error or (not response.raw_output or not response.raw_output.strip()):
        error_log = _create_error_decision_log(
            session,
            current_turn,
            response.raw_output or "",
            [response.error] if response.error else ["Empty AI response"],
            "adapter_error" if response.error else "generation_error",
        )
        _store_decision_log(session, error_log)

        # Check if retries are exhausted
        if current_attempt >= retry_policy.MAX_RETRIES:
            # W2.5 Phase 5: Retry exhausted - check if restore is required
            from app.runtime.ai_failure_recovery import (
                SafeTurnPolicy,
                RestorePolicy,
                AIFailureClass,
                FailureRecoveryPolicy,
                RecoveryAction,
            )

            failure_class = AIFailureClass.RETRY_EXHAUSTED
            recovery_action = FailureRecoveryPolicy.get_recovery_action(failure_class)

            # Check if we need to apply restore
            if (
                recovery_action == RecoveryAction.RESTORE
                and RestorePolicy.should_require_restore(failure_class, recovery_action)
            ):
                # W2.5 Phase 5: Apply last-valid-state restore
                try:
                    restored_state = RestorePolicy.apply_restore(
                        session.canonical_state, pre_execution_snapshot
                    )
                    session.canonical_state = restored_state

                    # Mark restore in metadata
                    restore_metadata = RestorePolicy.get_restore_metadata(
                        failure_class, pre_execution_snapshot.turn_number, current_turn
                    )

                    # Create result with restored state
                    completed_at = datetime.now(timezone.utc)
                    duration_ms = (completed_at - started_at).total_seconds() * 1000

                    turn_result = TurnExecutionResult(
                        turn_number=current_turn,
                        session_id=session.session_id,
                        execution_status="success",
                        decision=MockDecision(),  # Empty decision - restore only
                        validation_outcome=None,
                        validation_errors=[],
                        accepted_deltas=[],
                        rejected_deltas=[],
                        updated_canonical_state=restored_state,
                        updated_scene_id=session.current_scene_id,
                        started_at=started_at,
                        completed_at=completed_at,
                        duration_ms=duration_ms,
                        events=[],
                    )
                    turn_result.failure_reason = ExecutionFailureReason.GENERATION_ERROR

                    # Log restore execution with recovery notes
                    # Format restore metadata as recovery_notes string
                    restore_notes = (
                        f"restore_mode_active: last_valid_state_restore; "
                        f"failure_class={restore_metadata['failure_class']}; "
                        f"snapshot_turn={restore_metadata['snapshot_turn']}; "
                        f"turns_discarded={restore_metadata['turns_discarded']}"
                    )

                    decision_log = construct_ai_decision_log(
                        session_id=session.session_id,
                        turn_number=current_turn,
                        parsed_decision=ParsedAIDecision(
                            scene_interpretation="[restore: last valid state recovered]",
                            detected_triggers=[],
                            proposed_deltas=[],
                            proposed_scene_id=None,
                            rationale="[restore: retry exhaustion triggered state recovery]",
                            raw_output="",
                            parsed_source="restore_executor",
                        ),
                        raw_output=response.raw_output or "",
                        role_aware_decision=None,
                        guard_outcome=GuardOutcome.ACCEPTED,
                        accepted_deltas=[],
                        rejected_deltas=[],
                        guard_notes="restore_mode_active: last_valid_state_restore",
                    )
                    # Set recovery_notes with restore metadata
                    decision_log.recovery_notes = restore_notes
                    _store_decision_log(session, decision_log)

                    return turn_result
                except ValueError as e:
                    # Snapshot validation failed - fall back to safe-turn
                    pass

            # Fallback: If restore is not applicable or failed, use safe-turn
            # W2.5 Phase 4: Retry exhausted - activate safe-turn (no-op recovery)
            safe_turn_decision = MockDecision(
                detected_triggers=[],
                proposed_deltas=[],
            )

            # Execute safe-turn through normal path
            turn_result = await execute_turn(
                session,
                current_turn,
                safe_turn_decision,
                module,
                enforce_responder_only=False,
            )

            # Mark safe-turn in result
            turn_result.failure_reason = ExecutionFailureReason.GENERATION_ERROR

            # Log safe-turn execution
            decision_log = construct_ai_decision_log(
                session_id=session.session_id,
                turn_number=current_turn,
                parsed_decision=ParsedAIDecision(
                    scene_interpretation="[safe-turn: retry exhaustion recovery]",
                    detected_triggers=[],
                    proposed_deltas=[],
                    proposed_scene_id=None,
                    rationale="[safe-turn: no-op due to adapter failure after retries]",
                    raw_output="",
                    parsed_source="safe_turn_executor",
                ),
                raw_output=response.raw_output or "",
                role_aware_decision=None,
                guard_outcome=turn_result.guard_outcome,
                accepted_deltas=turn_result.accepted_deltas,
                rejected_deltas=turn_result.rejected_deltas,
                guard_notes="safe_turn_mode_active: retry_exhausted_recovery",
            )
            _store_decision_log(session, decision_log)

            return turn_result
        else:
            # Retries not yet exhausted (shouldn't reach here - retry loop should continue)
            # Return error for now
            result = _make_parse_failure_result(
                session,
                current_turn,
                [response.error] if response.error else ["Empty AI response"],
                response.raw_output or "",
                started_at,
            )
            result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
            return result

    # Step 3: Parse response
    parse_result: ParseResult = process_adapter_response(response)

    # Step 4: If parse failed, activate fallback responder (W2.5 Phase 3)
    if not parse_result.success:
        # Log the parse error
        error_log = _create_error_decision_log(
            session,
            current_turn,
            parse_result.raw_output,
            parse_result.errors,
            "parse_error",
        )
        _store_decision_log(session, error_log)

        # W2.5 Phase 3: Activate fallback responder instead of terminal failure
        from app.runtime.ai_failure_recovery import (
            generate_fallback_responder_proposal,
            FallbackResponderPolicy,
        )

        # Generate minimal conservative fallback proposal (ParsedAIDecision with empty deltas)
        fallback_parsed_decision = generate_fallback_responder_proposal()

        # Convert fallback proposal to MockDecision for execution
        mock_decision = decision_from_parsed(fallback_parsed_decision)

        # Execute fallback proposal through normal validation/guard path
        # This allows fallback to go through execute_turn and validation
        turn_result = await execute_turn(
            session,
            current_turn,
            mock_decision,
            module,
            enforce_responder_only=False,  # Fallback is not responder-derived
        )

        # Mark fallback activation explicitly in result
        # Fallback mode was active (parse failure triggered it)
        fallback_mode = FallbackResponderPolicy.get_fallback_mode_status(
            AIFailureClass.PARSE_FAILURE
        )
        turn_result.failure_reason = ExecutionFailureReason.PARSING_ERROR

        # Log the fallback execution decision
        decision_log = construct_ai_decision_log(
            session_id=session.session_id,
            turn_number=current_turn,
            parsed_decision=fallback_parsed_decision,
            raw_output=parse_result.raw_output,
            role_aware_decision=None,
            guard_outcome=turn_result.guard_outcome,
            accepted_deltas=turn_result.accepted_deltas,
            rejected_deltas=turn_result.rejected_deltas,
            guard_notes="fallback_mode_active: parse_failure_recovery",
        )
        _store_decision_log(session, decision_log)

        return turn_result

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
        # W2.5 Phase 3: Structurally invalid output triggers fallback responder
        # Log the structural validation error
        error_log = _create_error_decision_log(
            session,
            current_turn,
            parse_result.raw_output,
            policy_validation_errors,
            "policy_validation_error",
        )
        _store_decision_log(session, error_log)

        # Activate fallback responder for structural failure
        from app.runtime.ai_failure_recovery import (
            generate_fallback_responder_proposal,
            FallbackResponderPolicy,
        )

        # Generate minimal conservative fallback proposal
        fallback_parsed_decision = generate_fallback_responder_proposal()

        # Convert fallback proposal to MockDecision
        mock_decision = decision_from_parsed(fallback_parsed_decision)

        # Execute fallback through normal validation/guard path
        turn_result = await execute_turn(
            session,
            current_turn,
            mock_decision,
            module,
            enforce_responder_only=False,
        )

        # Mark fallback activation for structural failure
        turn_result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR

        # Log the fallback execution decision
        decision_log = construct_ai_decision_log(
            session_id=session.session_id,
            turn_number=current_turn,
            parsed_decision=fallback_parsed_decision,
            raw_output=parse_result.raw_output,
            role_aware_decision=None,
            guard_outcome=turn_result.guard_outcome,
            accepted_deltas=turn_result.accepted_deltas,
            rejected_deltas=turn_result.rejected_deltas,
            guard_notes="fallback_mode_active: structure_validation_failure",
        )
        _store_decision_log(session, decision_log)

        return turn_result

    # Step 5: Bridge parsed decision to MockDecision
    # Handle both role-structured (W2.4.1) and standard (W2.1.1) formats
    enforce_responder_gate = False
    if parse_result.role_aware_decision is not None:
        # W2.4.1 role-structured decision: extract responder and mark RESPONDER_DERIVED
        mock_decision = process_role_structured_decision(parse_result.role_aware_decision)
        # Enable responder-only enforcement for role-structured proposals
        enforce_responder_gate = True
    else:
        # Standard W2.1.1 decision: use standard bridge
        mock_decision = decision_from_parsed(parse_result.decision)

    # Step 6: Delegate to execute_turn with conditional canonical enforcement
    # W2.4.5: Enforce responder-only gating on role-structured AI path only.
    # Only responder-derived proposals (from role sections) are permitted
    # when enforce_responder_only=True.
    turn_result = await execute_turn(
        session,
        current_turn,
        mock_decision,
        module,
        enforce_responder_only=enforce_responder_gate,
    )

    # Step 7: Create and store decision log from execution result
    # W2.4.4: Use role-aware decision logging helper to populate interpreter/director/responder diagnostics
    guard_notes = None
    if turn_result.validation_errors:
        errors = turn_result.validation_errors
        count = len(errors)
        outcome_label = turn_result.guard_outcome.value
        sample = "; ".join(errors[:3])
        guard_notes = f"{count} error{'s' if count != 1 else ''}; {outcome_label}: {sample}"

    decision_log = construct_ai_decision_log(
        session_id=session.session_id,
        turn_number=current_turn,
        parsed_decision=parse_result.decision,
        raw_output=response.raw_output,
        role_aware_decision=parse_result.role_aware_decision,  # W2.4.4: Pass role sections for diagnostics
        guard_outcome=turn_result.guard_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes=guard_notes,
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
