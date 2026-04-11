"""Integration: vollständiger AI-Turn-Pfad (Pre-Adapter → Routing/Gen → Tool-Loop → Parse-Pipeline)."""

from __future__ import annotations

from typing import Any

from app.runtime.ai_failure_recovery import RetryPolicy
from app.content.module_models import ContentModule
from app.runtime.ai_adapter import StoryAIAdapter
from app.runtime.ai_turn_orchestration_sections import (
    build_routing_and_generation_bundle,
    make_adapter_request_pipeline,
    resolve_first_adapter_response,
)
from app.runtime.ai_turn_adapter_bridge import build_adapter_request
from app.runtime.ai_turn_post_parse_pipeline import run_parse_policy_success_pipeline
from app.runtime.ai_turn_pre_adapter import build_ai_turn_pre_adapter_state
from app.runtime.ai_turn_recovery_paths import (
    handle_generation_failure_or_empty,
    handle_tool_loop_stop_recovery,
)
from app.runtime.ai_turn_runtime_sections import (
    build_orchestration_log_bundle,
    run_primary_tool_loop_section,
)
from app.runtime.turn_executor import TurnExecutionResult
from app.runtime.runtime_models import SessionState


async def run_execute_turn_with_ai_integration(
    session: SessionState,
    current_turn: int,
    adapter: StoryAIAdapter,
    module: ContentModule,
    *,
    operator_input: str = "",
    recent_events: list[dict[str, Any]] | None = None,
    preview_diagnostics_before_parse: dict[str, Any] | None = None,
) -> TurnExecutionResult:
    pa = build_ai_turn_pre_adapter_state(session)
    started_at = pa.started_at
    pre_execution_snapshot = pa.pre_execution_snapshot
    orchestration_enabled = pa.orchestration_enabled
    staged_enabled = pa.staged_enabled
    tool_loop_policy = pa.tool_loop_policy
    tool_loop_enabled = pa.tool_loop_enabled
    execution_controls = pa.execution_controls
    tool_call_transcript = pa.tool_call_transcript
    tool_results = pa.tool_results
    tool_loop_stop_reason = pa.tool_loop_stop_reason
    tool_limit_hit = pa.tool_limit_hit
    finalized_after_tool_use = pa.finalized_after_tool_use
    last_successful_tool_sequence = pa.last_successful_tool_sequence
    tool_call_count = pa.tool_call_count
    tool_loop_summary = pa.tool_loop_summary
    preview_records = pa.preview_records

    build_request, enrich_mcp, mark_reduced = make_adapter_request_pipeline(
        session=session,
        module=module,
        current_turn=current_turn,
        operator_input=operator_input,
        recent_events=recent_events,
        tool_loop_enabled=tool_loop_enabled,
        tool_loop_policy=tool_loop_policy,
        tool_results=tool_results,
        tool_call_count_supplier=lambda: tool_call_count,
        interpretation_logged=pa.interpretation_logged,
        build_adapter_request_fn=build_adapter_request,
    )

    retry_policy = RetryPolicy()
    bundle = build_routing_and_generation_bundle(
        session=session,
        passed_adapter=adapter,
        orchestration_enabled=orchestration_enabled,
        staged_enabled=staged_enabled,
        adapter_generate_timeout_ms=pa.adapter_generate_timeout_ms,
        retry_policy=retry_policy,
        build_request=build_request,
        enrich_request=enrich_mcp,
        mark_retry_context=mark_reduced,
    )
    execution_adapter = bundle.execution_adapter
    staged_result_holder = bundle.staged_result_holder
    generate_wp = bundle.generate_with_runtime_policy

    fa = resolve_first_adapter_response(
        orchestration_enabled=orchestration_enabled,
        staged_enabled=staged_enabled,
        staged_result_holder=staged_result_holder,
        execution_adapter=execution_adapter,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
        build_request=build_request,
        enrich_request=enrich_mcp,
        execution_controls=execution_controls,
        tool_call_transcript=tool_call_transcript,
        preview_records=preview_records,
        generate_wp=generate_wp,
    )
    log_bundle = build_orchestration_log_bundle(
        routing=bundle,
        fa=fa,
        tool_call_transcript=tool_call_transcript,
        last_successful_tool_sequence=last_successful_tool_sequence,
        tool_loop_summary=fa.tool_loop_summary,
        preview_diagnostics=preview_diagnostics_before_parse,
    )

    generation_failure_result = await handle_generation_failure_or_empty(
        session=session,
        current_turn=current_turn,
        module=module,
        response=fa.response,
        current_attempt=fa.current_attempt,
        max_retries=retry_policy.MAX_RETRIES,
        started_at=started_at,
        pre_execution_snapshot=pre_execution_snapshot,
        log_bundle=log_bundle,
    )
    if generation_failure_result is not None:
        return generation_failure_result

    tl = run_primary_tool_loop_section(
        tool_loop_enabled=tool_loop_enabled,
        response=fa.response,
        tool_loop_policy=tool_loop_policy,
        session=session,
        module=module,
        current_turn=current_turn,
        recent_events=recent_events,
        generate_pair=lambda: generate_wp(starting_attempt=1),
        execution_controls=execution_controls,
        tool_call_transcript=tool_call_transcript,
        tool_results=tool_results,
        tool_call_count=tool_call_count,
        tool_loop_stop_reason=tool_loop_stop_reason,
        tool_limit_hit=tool_limit_hit,
        finalized_after_tool_use=finalized_after_tool_use,
        last_successful_tool_sequence=last_successful_tool_sequence,
        preview_records=preview_records,
        tool_loop_summary_existing=fa.tool_loop_summary,
    )
    log_bundle = log_bundle._replace(
        tool_loop_summary=tl.tool_loop_summary,
        tool_call_transcript=tl.tool_call_transcript,
        last_successful_tool_sequence=tl.last_successful_tool_sequence,
    )

    tool_loop_stop_recovery_result = await handle_tool_loop_stop_recovery(
        session=session,
        current_turn=current_turn,
        module=module,
        tool_loop_enabled=tool_loop_enabled,
        tool_loop_stop_reason=tl.tool_loop_stop_reason,
        response=tl.response,
        preview_records=preview_records,
        log_bundle=log_bundle,
    )
    if tool_loop_stop_recovery_result is not None:
        return tool_loop_stop_recovery_result

    return await run_parse_policy_success_pipeline(
        response=tl.response,
        preview_records=preview_records,
        session=session,
        current_turn=current_turn,
        module=module,
        bundle=log_bundle,
    )
