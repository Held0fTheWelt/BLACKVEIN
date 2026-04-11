"""Parse validation, policy gate, and success-path execution with decision logging.

Async pipeline extracted from ``ai_turn_executor`` (DS-001): keeps the executor file
focused on pre-adapter setup, routing, generation, and tool-loop orchestration.
"""

from __future__ import annotations

from typing import Any

from app.content.module_models import ContentModule
from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_decision import ParseResult, process_adapter_response
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.ai_turn_adapter_bridge import (
    decision_from_parsed,
    process_role_structured_decision,
)
from app.runtime.ai_turn_orchestration_logging import (
    build_turn_orchestration_attachments as _build_turn_orchestration_attachments,
)
from app.runtime.ai_turn_parse_helpers import (
    collect_policy_validation_errors as _collect_policy_validation_errors_impl,
    preview_diagnostics_after_parse as _preview_diagnostics_after_parse_impl,
)
from app.runtime.ai_turn_preview import (
    build_preview_diagnostics_payload,
    set_preview_improvement_metric,
)
from app.runtime.ai_turn_recovery_paths import (
    run_standard_fallback_responder as _run_standard_fallback_responder,
    store_decision_log as _store_decision_log,
)
from app.runtime.ai_turn_shared_types import _AiTurnOrchestrationLogBundle
from app.runtime.turn_executor import TurnExecutionResult, execute_turn
from app.runtime.runtime_models import ExecutionFailureReason, SessionState


def _collect_policy_validation_errors(
    parse_result: ParseResult,
    module: ContentModule,
    session: SessionState,
) -> list[str]:
    return _collect_policy_validation_errors_impl(
        parse_result=parse_result,
        module=module,
        session=session,
    )


async def _execute_success_path_with_decision_log(
    *,
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    parse_result: ParseResult,
    response: AdapterResponse,
    preview_diagnostics: dict[str, Any] | None,
    tool_loop_summary: dict[str, Any] | None,
    tool_call_transcript: list[dict[str, Any]],
    last_successful_tool_sequence: int | None,
    supervisor_plan: Any,
    subagent_invocations: Any,
    subagent_results: Any,
    merge_finalization: Any,
    orchestration_budget_summary: Any,
    orchestration_failover: Any,
    orchestration_cache: Any,
    tool_audit: Any,
    model_routing_trace: dict[str, Any] | None,
    runtime_stage_traces_for_log: list[dict[str, Any]] | None,
    runtime_orchestration_summary_for_log: dict[str, Any] | None,
    operator_audit_for_log: dict[str, Any] | None,
) -> TurnExecutionResult:
    """Bridge parsed decision, run canonical execute_turn, log, set failure_reason."""
    enforce_responder_gate = False
    if parse_result.role_aware_decision is not None:
        mock_decision = process_role_structured_decision(parse_result.role_aware_decision)
        enforce_responder_gate = True
    else:
        mock_decision = decision_from_parsed(parse_result.decision)

    turn_result = await execute_turn(
        session,
        current_turn,
        mock_decision,
        module,
        enforce_responder_only=enforce_responder_gate,
    )
    set_preview_improvement_metric(
        preview_diagnostics,
        final_accepted_count=len(turn_result.accepted_deltas),
    )

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
        role_aware_decision=parse_result.role_aware_decision,
        guard_outcome=turn_result.guard_outcome,
        accepted_deltas=turn_result.accepted_deltas,
        rejected_deltas=turn_result.rejected_deltas,
        guard_notes=guard_notes,
        **_build_turn_orchestration_attachments(
            tool_loop_summary=tool_loop_summary,
            tool_call_transcript=tool_call_transcript,
            last_successful_tool_sequence=last_successful_tool_sequence,
            preview_diagnostics=preview_diagnostics,
            supervisor_plan=supervisor_plan,
            subagent_invocations=subagent_invocations,
            subagent_results=subagent_results,
            merge_finalization=merge_finalization,
            orchestration_budget_summary=orchestration_budget_summary,
            orchestration_failover=orchestration_failover,
            orchestration_cache=orchestration_cache,
            tool_audit=tool_audit,
            model_routing_trace=model_routing_trace,
            runtime_stage_traces_for_log=runtime_stage_traces_for_log,
            runtime_orchestration_summary_for_log=runtime_orchestration_summary_for_log,
            operator_audit_for_log=operator_audit_for_log,
        ),
    )
    _store_decision_log(session, decision_log)

    if turn_result.execution_status == "success":
        if len(turn_result.accepted_deltas) == 0 and len(turn_result.rejected_deltas) > 0:
            turn_result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR
        else:
            turn_result.failure_reason = ExecutionFailureReason.NONE
    else:
        turn_result.failure_reason = ExecutionFailureReason.VALIDATION_ERROR

    return turn_result


def _preview_diagnostics_after_parse(
    parse_result: ParseResult,
    preview_records: list[dict[str, Any]],
) -> dict[str, Any] | None:
    return _preview_diagnostics_after_parse_impl(
        parse_result=parse_result,
        preview_records=preview_records,
        build_preview_payload_fn=build_preview_diagnostics_payload,
    )


async def run_parse_policy_success_pipeline(
    *,
    response: AdapterResponse,
    preview_records: list[dict[str, Any]],
    session: SessionState,
    current_turn: int,
    module: ContentModule,
    bundle: _AiTurnOrchestrationLogBundle,
) -> TurnExecutionResult:
    """Parse adapter output, policy-validate, fallback or success path with decision log."""
    parse_result = process_adapter_response(response)
    preview_diagnostics = _preview_diagnostics_after_parse(parse_result, preview_records)
    bundle = bundle._replace(preview_diagnostics=preview_diagnostics)

    if not parse_result.success:
        return await _run_standard_fallback_responder(
            session=session,
            current_turn=current_turn,
            module=module,
            raw_output=parse_result.raw_output,
            errors=parse_result.errors,
            error_type="parse_error",
            fallback_guard_notes="fallback_mode_active: parse_failure_recovery",
            failure_reason=ExecutionFailureReason.PARSING_ERROR,
            bundle=bundle,
            decision_from_parsed_fn=decision_from_parsed,
        )

    policy_validation_errors = _collect_policy_validation_errors(
        parse_result, module=module, session=session
    )
    if policy_validation_errors:
        return await _run_standard_fallback_responder(
            session=session,
            current_turn=current_turn,
            module=module,
            raw_output=parse_result.raw_output,
            errors=policy_validation_errors,
            error_type="policy_validation_error",
            fallback_guard_notes="fallback_mode_active: structure_validation_failure",
            failure_reason=ExecutionFailureReason.VALIDATION_ERROR,
            bundle=bundle,
            decision_from_parsed_fn=decision_from_parsed,
        )

    return await _execute_success_path_with_decision_log(
        session=session,
        current_turn=current_turn,
        module=module,
        parse_result=parse_result,
        response=response,
        preview_diagnostics=bundle.preview_diagnostics,
        tool_loop_summary=bundle.tool_loop_summary,
        tool_call_transcript=bundle.tool_call_transcript,
        last_successful_tool_sequence=bundle.last_successful_tool_sequence,
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
    )
