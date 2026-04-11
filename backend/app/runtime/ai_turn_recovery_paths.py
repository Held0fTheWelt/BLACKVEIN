from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_decision import ParsedAIDecision
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.ai_turn_orchestration_logging import (
    attachments_from_orchestration_bundle,
    build_turn_orchestration_attachments,
)
from app.runtime.ai_turn_preview import build_preview_diagnostics_payload, set_preview_improvement_metric
from app.runtime.ai_turn_shared_types import _AiTurnOrchestrationLogBundle
from app.runtime.runtime_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DegradedMarker,
    ExecutionFailureReason,
    GuardOutcome,
    SessionState,
)
from app.runtime.tool_loop import ToolLoopStopReason
from app.runtime.turn_executor import MockDecision, TurnExecutionResult, execute_turn


def store_decision_log(session: SessionState, log: AIDecisionLog) -> None:
    if "ai_decision_logs" not in session.metadata:
        session.metadata["ai_decision_logs"] = []
    session.metadata["ai_decision_logs"].append(log)


def _activate_degraded_marker(session: SessionState, marker: DegradedMarker) -> None:
    if marker not in session.degraded_state.active_markers:
        session.degraded_state.active_markers.add(marker)
        session.degraded_state.marker_timestamps[marker] = datetime.now(timezone.utc)
    if not session.degraded_state.is_degraded:
        session.degraded_state.is_degraded = True
        session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = datetime.now(timezone.utc)


def _create_error_decision_log(
    session: SessionState,
    current_turn: int,
    raw_output: str,
    errors: list[str],
    error_type: str,
    *,
    model_routing_trace: dict[str, Any] | None = None,
    runtime_stage_traces: list[dict[str, Any]] | None = None,
    runtime_orchestration_summary: dict[str, Any] | None = None,
    operator_audit: dict[str, Any] | None = None,
) -> AIDecisionLog:
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
        model_routing_trace=model_routing_trace,
        runtime_stage_traces=runtime_stage_traces,
        runtime_orchestration_summary=runtime_orchestration_summary,
        operator_audit=operator_audit,
    )


def _make_parse_failure_result(
    session: SessionState,
    turn_number: int,
    errors: list[str],
    raw_output: str,
    started_at: datetime,
) -> TurnExecutionResult:
    completed_at = datetime.now(timezone.utc)
    duration_ms = (completed_at - started_at).total_seconds() * 1000
    return TurnExecutionResult(
        turn_number=turn_number,
        session_id=session.session_id,
        execution_status="system_error",
        decision=MockDecision(),
        validation_outcome=None,
        validation_errors=errors,
        accepted_deltas=[],
        rejected_deltas=[],
        updated_canonical_state=session.canonical_state.copy(),
        updated_scene_id=session.current_scene_id,
        started_at=started_at,
        completed_at=completed_at,
        duration_ms=duration_ms,
        events=[],
    )


async def _execute_fallback_responder_recovery(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    raw_output: str,
    errors: list[str],
    error_type: str,
    fallback_guard_notes: str,
    failure_reason: ExecutionFailureReason,
    bundle: _AiTurnOrchestrationLogBundle,
    decision_from_parsed_fn: Callable[[Any], MockDecision],
) -> TurnExecutionResult:
    error_log = _create_error_decision_log(
        session,
        current_turn,
        raw_output,
        errors,
        error_type,
        model_routing_trace=bundle.model_routing_trace,
        runtime_stage_traces=bundle.runtime_stage_traces_for_log,
        runtime_orchestration_summary=bundle.runtime_orchestration_summary_for_log,
        operator_audit=bundle.operator_audit_for_log,
    )
    store_decision_log(session, error_log)

    from app.runtime.ai_failure_recovery import generate_fallback_responder_proposal

    _activate_degraded_marker(session, DegradedMarker.FALLBACK_ACTIVE)
    fallback_parsed_decision = generate_fallback_responder_proposal()
    mock_decision = decision_from_parsed_fn(fallback_parsed_decision)
    turn_result = await execute_turn(
        session,
        current_turn,
        mock_decision,
        module,
        enforce_responder_only=False,
    )
    turn_result.failure_reason = failure_reason

    decision_log = construct_ai_decision_log(
        session_id=session.session_id,
        turn_number=current_turn,
        parsed_decision=fallback_parsed_decision,
        raw_output=raw_output,
        role_aware_decision=None,
        guard_outcome=turn_result.guard_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes=fallback_guard_notes,
        **build_turn_orchestration_attachments(
            tool_loop_summary=bundle.tool_loop_summary,
            tool_call_transcript=bundle.tool_call_transcript,
            last_successful_tool_sequence=bundle.last_successful_tool_sequence,
            preview_diagnostics=bundle.preview_diagnostics,
            supervisor_plan=bundle.supervisor_plan,
            subagent_invocations=bundle.subagent_invocations,
            subagent_results=bundle.subagent_results,
            merge_finalization=bundle.merge_finalization,
            orchestration_budget_summary=bundle.orchestration_budget_summary,
            orchestration_failover=bundle.orchestration_failover,
            orchestration_cache=bundle.orchestration_cache,
            tool_audit=bundle.tool_audit,
            model_routing_trace=bundle.model_routing_trace,
            runtime_stage_traces_for_log=bundle.runtime_stage_traces_for_log,
            runtime_orchestration_summary_for_log=bundle.runtime_orchestration_summary_for_log,
            operator_audit_for_log=bundle.operator_audit_for_log,
        ),
    )
    store_decision_log(session, decision_log)
    return turn_result


async def run_standard_fallback_responder(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    raw_output: str,
    errors: list[str],
    error_type: str,
    fallback_guard_notes: str,
    failure_reason: ExecutionFailureReason,
    bundle: _AiTurnOrchestrationLogBundle,
    decision_from_parsed_fn: Callable[[Any], MockDecision],
) -> TurnExecutionResult:
    return await _execute_fallback_responder_recovery(
        session=session,
        current_turn=current_turn,
        module=module,
        raw_output=raw_output,
        errors=errors,
        error_type=error_type,
        fallback_guard_notes=fallback_guard_notes,
        failure_reason=failure_reason,
        bundle=bundle,
        decision_from_parsed_fn=decision_from_parsed_fn,
    )


async def handle_generation_failure_or_empty(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    response: AdapterResponse,
    current_attempt: int,
    max_retries: int,
    started_at: datetime,
    pre_execution_snapshot: Any,
    log_bundle: _AiTurnOrchestrationLogBundle,
) -> TurnExecutionResult | None:
    if not (response.error or (not response.raw_output or not response.raw_output.strip())):
        return None

    errors = [response.error] if response.error else ["Empty AI response"]
    error_type = "adapter_error" if response.error else "generation_error"
    error_log = _create_error_decision_log(
        session,
        current_turn,
        response.raw_output or "",
        errors,
        error_type,
        model_routing_trace=log_bundle.model_routing_trace,
        runtime_stage_traces=log_bundle.runtime_stage_traces_for_log,
        runtime_orchestration_summary=log_bundle.runtime_orchestration_summary_for_log,
        operator_audit=log_bundle.operator_audit_for_log,
    )
    store_decision_log(session, error_log)

    if current_attempt < max_retries:
        result = _make_parse_failure_result(
            session,
            current_turn,
            errors,
            response.raw_output or "",
            started_at,
        )
        result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
        return result

    from app.runtime.ai_failure_recovery import (
        AIFailureClass,
        FailureRecoveryPolicy,
        RecoveryAction,
        RestorePolicy,
    )
    from app.runtime.ai_turn_recovery_generation_failure_exhausted import (
        run_safe_turn_after_generation_retry_exhausted,
        try_restore_turn_after_generation_retry_exhausted,
    )

    failure_class = AIFailureClass.RETRY_EXHAUSTED
    _activate_degraded_marker(session, DegradedMarker.RETRY_EXHAUSTED)
    recovery_action = FailureRecoveryPolicy.get_recovery_action(failure_class)

    if (
        recovery_action == RecoveryAction.RESTORE
        and RestorePolicy.should_require_restore(failure_class, recovery_action)
    ):
        restored = try_restore_turn_after_generation_retry_exhausted(
            session=session,
            current_turn=current_turn,
            response=response,
            started_at=started_at,
            pre_execution_snapshot=pre_execution_snapshot,
            log_bundle=log_bundle,
        )
        if restored is not None:
            return restored

    return await run_safe_turn_after_generation_retry_exhausted(
        session=session,
        current_turn=current_turn,
        module=module,
        response=response,
        log_bundle=log_bundle,
    )


async def handle_tool_loop_stop_recovery(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    tool_loop_enabled: bool,
    tool_loop_stop_reason: ToolLoopStopReason,
    response: AdapterResponse,
    preview_records: list[dict[str, Any]],
    log_bundle: _AiTurnOrchestrationLogBundle,
) -> TurnExecutionResult | None:
    if not (tool_loop_enabled and tool_loop_stop_reason != ToolLoopStopReason.FINALIZED):
        return None

    preview_diagnostics = log_bundle.preview_diagnostics
    if preview_records:
        preview_diagnostics = build_preview_diagnostics_payload(
            records=preview_records,
            final_targets=[],
        )

    safe_turn_decision = MockDecision(
        detected_triggers=[],
        proposed_deltas=[],
    )
    turn_result = await execute_turn(
        session,
        current_turn,
        safe_turn_decision,
        module,
        enforce_responder_only=False,
    )
    turn_result.execution_status = "system_error"
    set_preview_improvement_metric(
        preview_diagnostics,
        final_accepted_count=len(turn_result.accepted_deltas),
    )
    turn_result.failure_reason = ExecutionFailureReason.GENERATION_ERROR
    decision_log = construct_ai_decision_log(
        session_id=session.session_id,
        turn_number=current_turn,
        parsed_decision=ParsedAIDecision(
            scene_interpretation="[tool-loop stop: deterministic no-op recovery]",
            detected_triggers=[],
            proposed_deltas=[],
            proposed_scene_id=None,
            rationale=f"[tool-loop stop reason: {tool_loop_stop_reason}]",
            raw_output=response.raw_output if response else "",
            parsed_source="tool_loop_executor",
        ),
        raw_output=response.raw_output if response else "",
        role_aware_decision=None,
        guard_outcome=turn_result.guard_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes=(
            f"tool_loop_failure_recovery_active: true; "
            f"tool_loop_stop_reason: {tool_loop_stop_reason}"
        ),
        **attachments_from_orchestration_bundle(
            log_bundle._replace(preview_diagnostics=preview_diagnostics),
        ),
    )
    store_decision_log(session, decision_log)
    return turn_result
