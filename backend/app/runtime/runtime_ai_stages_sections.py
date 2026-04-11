from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter, generate_with_timeout
from app.runtime.runtime_models import SessionState
from app.runtime.ai_failure_recovery import AIFailureClass, RetryPolicy
from app.runtime.adapter_registry import get_adapter
from app.runtime.model_routing_contracts import RoutingDecision, RoutingRequest
from app.runtime.model_routing_evidence import attach_stage_routing_evidence
from app.runtime.operator_audit import build_runtime_operator_audit, runtime_additive_orchestration_fields
from app.runtime.runtime_stage_ids import (
    RANKING_SLM_ONLY_SKIP_REASON,
    RUNTIME_STAGE_META_KEY,
    RUNTIME_STAGE_SCHEMA_META_KEY,
    RUNTIME_STAGE_SCHEMA_VERSION,
    RuntimeStageId,
)


def annotate_runtime_stage_request(
    base: AdapterRequest,
    stage_id: RuntimeStageId,
    *,
    request_role_structured_output: bool,
) -> AdapterRequest:
    """Attach runtime stage metadata to an adapter request (same contract as legacy orchestrator)."""

    meta = dict(base.metadata or {})
    meta[RUNTIME_STAGE_META_KEY] = stage_id.value
    meta[RUNTIME_STAGE_SCHEMA_META_KEY] = RUNTIME_STAGE_SCHEMA_VERSION
    return base.model_copy(
        update={
            "metadata": meta,
            "request_role_structured_output": request_role_structured_output,
        }
    )


@dataclass
class PreflightSignalRankingGateOutcome:
    """State after preflight → signal → optional ranking; feeds synthesis or SLM-only finalizers."""

    traces: list[dict[str, Any]]
    packaging_notes: list[str]
    needs_llm: bool
    preflight_out: Any
    signal_out: Any | None
    ranking_out: Any | None
    ranked_skip_synthesis: bool
    synth_gate_reason: str
    final_path: Any
    ranking_effect: str
    ranking_suppressed_slm_only: bool
    base_needs_llm: bool
    ranking_bounded_ran: bool
    ranking_no_eligible: bool
    preflight_skipped: bool
    signal_skipped: bool
    signal_rr: RoutingRequest
    signal_dec: RoutingDecision
    signal_adapter: StoryAIAdapter
    signal_resolved_via: bool
    ranking_rr: RoutingRequest
    ranking_dec_for_rollup: RoutingDecision | None
    ranking_exec_for_rollup: StoryAIAdapter | None
    ranking_resolved_for_rollup: bool | None


def resolve_routed_adapter(
    routing_decision: RoutingDecision,
    passed_adapter: StoryAIAdapter,
) -> tuple[StoryAIAdapter, Any]:
    resolved = None
    if routing_decision.selected_adapter_name:
        resolved = get_adapter(routing_decision.selected_adapter_name)
    execution = resolved if resolved is not None else passed_adapter
    return execution, resolved


def trace_dict_for_routed_model_stage(
    *,
    stage_id: RuntimeStageId,
    routing_request: RoutingRequest,
    routing_decision: RoutingDecision,
    passed_adapter: StoryAIAdapter,
    execution_adapter: StoryAIAdapter,
    resolved_via_registry: bool,
    bounded_model_call: bool,
    skip_reason: str | None,
    output_summary: dict[str, Any],
    errors: list[str],
) -> dict[str, Any]:
    trace: dict[str, Any] = {
        "stage_id": stage_id.value,
        "stage_kind": "routed_model_stage",
        "bounded_model_call": bounded_model_call,
        "skip_reason": skip_reason,
        "request": routing_request.model_dump(mode="json"),
        "decision": routing_decision.model_dump(mode="json"),
        "passed_adapter_name": passed_adapter.adapter_name,
        "executed_adapter_name": execution_adapter.adapter_name if bounded_model_call else None,
        "selected_adapter_name": routing_decision.selected_adapter_name,
        "resolved_via_get_adapter": resolved_via_registry,
        "fallback_to_passed_adapter": not resolved_via_registry,
        "output_summary": output_summary,
        "errors": errors,
    }
    attach_stage_routing_evidence(
        trace,
        routing_request,
        executed_adapter_name=execution_adapter.adapter_name if bounded_model_call else None,
        bounded_model_call=bounded_model_call,
        skip_reason=skip_reason,
        execution_deviation_note=None,
    )
    return trace


def trace_ranking_suppressed_for_slm_only(
    *,
    ranking_request: RoutingRequest,
    passed_adapter: StoryAIAdapter,
) -> dict[str, Any]:
    """Ranking stage trace when ``base_needs_llm`` is false: no ``route_model``, no bounded call."""

    return {
        "stage_id": RuntimeStageId.ranking.value,
        "stage_kind": "routed_model_stage",
        "bounded_model_call": False,
        "skip_reason": RANKING_SLM_ONLY_SKIP_REASON,
        "request": ranking_request.model_dump(mode="json"),
        "decision": None,
        "passed_adapter_name": passed_adapter.adapter_name,
        "executed_adapter_name": None,
        "selected_adapter_name": None,
        "resolved_via_get_adapter": None,
        "fallback_to_passed_adapter": None,
        "output_summary": {"suppressed": True, "routing_not_invoked": True},
        "errors": [],
    }


def run_bounded_routed_model_stage(
    *,
    stage_id: RuntimeStageId,
    routing_request: RoutingRequest,
    routing_decision: RoutingDecision,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    annotate_request_fn: Callable[[AdapterRequest], AdapterRequest],
    parse_payload_fn: Callable[[dict[str, Any] | None], tuple[Any, list[str]]],
    no_adapter_skip_reason: str,
    adapter_error_skip_label: str,
    empty_payload_error: str,
) -> tuple[dict[str, Any], str | None, Any | None, list[str], bool, StoryAIAdapter, bool]:
    """Run one routed SLM stage (preflight, signal, or ranking) or record a no-adapter skip.

    Returns:
        trace dict, optional packaging note, parsed structured output (or None), error list,
        whether the stage was skipped for no eligible adapter, execution adapter, resolved_via_registry.
    """
    execution_adapter, resolved = resolve_routed_adapter(routing_decision, passed_adapter)
    resolved_via_registry = resolved is not None
    skipped = not bool(routing_decision.selected_adapter_name)

    if skipped:
        trace = trace_dict_for_routed_model_stage(
            stage_id=stage_id,
            routing_request=routing_request,
            routing_decision=routing_decision,
            passed_adapter=passed_adapter,
            execution_adapter=execution_adapter,
            resolved_via_registry=resolved_via_registry,
            bounded_model_call=False,
            skip_reason=no_adapter_skip_reason,
            output_summary={"skipped": True},
            errors=[no_adapter_skip_reason],
        )
        return trace, no_adapter_skip_reason, None, [], True, execution_adapter, resolved_via_registry

    base_req = build_adapter_request_fn(1)
    enrich_request_fn(base_req)
    request = annotate_request_fn(base_req)
    response = generate_with_timeout(
        adapter=execution_adapter,
        request=request,
        timeout_ms=adapter_generate_timeout_ms,
    )
    parsed, errors = parse_payload_fn(response.structured_payload)
    if response.error or not response.structured_payload:
        errors = errors or [empty_payload_error]
        parsed = None
    trace = trace_dict_for_routed_model_stage(
        stage_id=stage_id,
        routing_request=routing_request,
        routing_decision=routing_decision,
        passed_adapter=passed_adapter,
        execution_adapter=execution_adapter,
        resolved_via_registry=resolved_via_registry,
        bounded_model_call=True,
        skip_reason=None if not response.error else adapter_error_skip_label,
        output_summary=(parsed.model_dump(mode="json") if parsed else {"parse_failed": True}),
        errors=errors,
    )
    return trace, None, parsed, errors, False, execution_adapter, resolved_via_registry


@dataclass
class _RankingSynthesisGateBundle:
    needs_llm: bool
    synth_gate_reason: str
    ranking_effect: str
    ranking_out: Any
    ranking_bounded_parse_ok: bool
    ranking_bounded_ran: bool
    ranking_no_eligible: bool
    ranking_dec_for_rollup: RoutingDecision | None
    ranking_exec_for_rollup: StoryAIAdapter | None
    ranking_resolved_for_rollup: bool | None


def _gate_preflight_trace(
    ras: Any,
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    route_model: Callable[[RoutingRequest], RoutingDecision],
) -> tuple[
    RoutingRequest,
    RoutingDecision,
    dict[str, Any],
    str | None,
    Any,
    list[str],
    bool,
]:
    preflight_rr = ras.build_preflight_routing_request(session)
    preflight_dec = route_model(preflight_rr)
    pf_trace, pf_note, preflight_out, preflight_errors, preflight_skipped, _, _ = (
        run_bounded_routed_model_stage(
            stage_id=RuntimeStageId.preflight,
            routing_request=preflight_rr,
            routing_decision=preflight_dec,
            passed_adapter=passed_adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=build_adapter_request_fn,
            enrich_request_fn=enrich_request_fn,
            annotate_request_fn=lambda base: annotate_runtime_stage_request(
                base, RuntimeStageId.preflight, request_role_structured_output=False
            ),
            parse_payload_fn=ras.parse_preflight_payload,
            no_adapter_skip_reason="no_eligible_adapter_for_preflight_stage",
            adapter_error_skip_label="preflight_adapter_error",
            empty_payload_error="preflight: adapter error or empty payload",
        )
    )
    return (
        preflight_rr,
        preflight_dec,
        pf_trace,
        pf_note,
        preflight_out,
        preflight_errors,
        preflight_skipped,
    )


def _gate_signal_trace(
    ras: Any,
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    route_model: Callable[[RoutingRequest], RoutingDecision],
    preflight_out: Any,
) -> tuple[
    RoutingRequest,
    RoutingDecision,
    dict[str, Any],
    str | None,
    Any,
    list[str],
    bool,
    StoryAIAdapter,
    bool,
]:
    extra_hints = ras.escalation_hints_from_preflight(preflight_out)
    signal_rr = ras.build_signal_routing_request(session, extra_hints=extra_hints)
    signal_dec = route_model(signal_rr)
    sg_trace, sg_note, signal_out, signal_errors, signal_skipped, signal_adapter, signal_resolved_via = (
        run_bounded_routed_model_stage(
            stage_id=RuntimeStageId.signal_consistency,
            routing_request=signal_rr,
            routing_decision=signal_dec,
            passed_adapter=passed_adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=build_adapter_request_fn,
            enrich_request_fn=enrich_request_fn,
            annotate_request_fn=lambda base: annotate_runtime_stage_request(
                base, RuntimeStageId.signal_consistency, request_role_structured_output=False
            ),
            parse_payload_fn=ras.parse_signal_payload,
            no_adapter_skip_reason="no_eligible_adapter_for_signal_stage",
            adapter_error_skip_label="signal_adapter_error",
            empty_payload_error="signal: adapter error or empty payload",
        )
    )
    return (
        signal_rr,
        signal_dec,
        sg_trace,
        sg_note,
        signal_out,
        signal_errors,
        signal_skipped,
        signal_adapter,
        signal_resolved_via,
    )


def _gate_ranking_synthesis_bundle(
    ras: Any,
    *,
    base_needs_llm: bool,
    base_reason: str,
    signal_out: Any,
    signal_parse_ok: bool,
    ranking_rr: RoutingRequest,
    traces: list[dict[str, Any]],
    packaging_notes: list[str],
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    route_model: Callable[[RoutingRequest], RoutingDecision],
) -> _RankingSynthesisGateBundle:
    if not base_needs_llm:
        traces.append(
            trace_ranking_suppressed_for_slm_only(
                ranking_request=ranking_rr,
                passed_adapter=passed_adapter,
            )
        )
        needs_llm, synth_gate_reason, ranking_effect = ras.compute_synthesis_gate_after_ranking(
            base_needs_llm=False,
            base_reason=base_reason,
            signal=signal_out,
            signal_parse_ok=signal_parse_ok,
            ranking_out=None,
            ranking_parse_ok=False,
            ranking_bounded_ran=False,
            ranking_no_eligible_adapter=False,
        )
        return _RankingSynthesisGateBundle(
            needs_llm=needs_llm,
            synth_gate_reason=synth_gate_reason,
            ranking_effect=ranking_effect,
            ranking_out=None,
            ranking_bounded_parse_ok=False,
            ranking_bounded_ran=False,
            ranking_no_eligible=False,
            ranking_dec_for_rollup=None,
            ranking_exec_for_rollup=None,
            ranking_resolved_for_rollup=None,
        )

    ranking_dec = route_model(ranking_rr)
    rk_trace, rk_note, ranking_out, ranking_errors, ranking_no_eligible, ranking_adapter, rk_resolved_via = (
        run_bounded_routed_model_stage(
            stage_id=RuntimeStageId.ranking,
            routing_request=ranking_rr,
            routing_decision=ranking_dec,
            passed_adapter=passed_adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=build_adapter_request_fn,
            enrich_request_fn=enrich_request_fn,
            annotate_request_fn=lambda base: annotate_runtime_stage_request(
                base, RuntimeStageId.ranking, request_role_structured_output=False
            ),
            parse_payload_fn=ras.parse_ranking_payload,
            no_adapter_skip_reason="no_eligible_adapter_for_ranking_stage",
            adapter_error_skip_label="ranking_adapter_error",
            empty_payload_error="ranking: adapter error or empty payload",
        )
    )
    traces.append(rk_trace)
    if rk_note:
        packaging_notes.append(rk_note)
    ranking_bounded_ran = not ranking_no_eligible
    ranking_bounded_parse_ok = ranking_out is not None and not ranking_errors
    needs_llm, synth_gate_reason, ranking_effect = ras.compute_synthesis_gate_after_ranking(
        base_needs_llm=True,
        base_reason=base_reason,
        signal=signal_out,
        signal_parse_ok=signal_parse_ok,
        ranking_out=ranking_out,
        ranking_parse_ok=ranking_bounded_parse_ok,
        ranking_bounded_ran=ranking_bounded_ran,
        ranking_no_eligible_adapter=ranking_no_eligible,
    )
    return _RankingSynthesisGateBundle(
        needs_llm=needs_llm,
        synth_gate_reason=synth_gate_reason,
        ranking_effect=ranking_effect,
        ranking_out=ranking_out,
        ranking_bounded_parse_ok=ranking_bounded_parse_ok,
        ranking_bounded_ran=ranking_bounded_ran,
        ranking_no_eligible=ranking_no_eligible,
        ranking_dec_for_rollup=ranking_dec,
        ranking_exec_for_rollup=ranking_adapter,
        ranking_resolved_for_rollup=rk_resolved_via,
    )


def run_preflight_signal_ranking_gate(
    *,
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    route_model: Callable[[RoutingRequest], RoutingDecision],
) -> PreflightSignalRankingGateOutcome:
    """Preflight → signal → optional ranking, synthesis gate, and final-path resolution."""

    from app.runtime import runtime_ai_stages as ras

    traces: list[dict[str, Any]] = []
    packaging_notes: list[str] = []

    _, _, pf_trace, pf_note, preflight_out, preflight_errors, preflight_skipped = _gate_preflight_trace(
        ras,
        session=session,
        passed_adapter=passed_adapter,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_adapter_request_fn,
        enrich_request_fn=enrich_request_fn,
        route_model=route_model,
    )
    traces.append(pf_trace)
    if pf_note:
        packaging_notes.append(pf_note)
    preflight_parse_ok = preflight_out is not None and not preflight_errors

    signal_rr, signal_dec, sg_trace, sg_note, signal_out, signal_errors, signal_skipped, signal_adapter, signal_resolved_via = _gate_signal_trace(
        ras,
        session=session,
        passed_adapter=passed_adapter,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_adapter_request_fn,
        enrich_request_fn=enrich_request_fn,
        route_model=route_model,
        preflight_out=preflight_out,
    )
    traces.append(sg_trace)
    if sg_note:
        packaging_notes.append(sg_note)
    signal_parse_ok = signal_out is not None and not signal_errors

    base_needs_llm, base_reason = ras.compute_needs_llm_synthesis(
        signal=signal_out,
        signal_parse_ok=signal_parse_ok,
        preflight_parse_ok=preflight_parse_ok,
    )
    ranking_rr = ras.build_ranking_routing_request(
        session, extra_hints=ras.escalation_hints_from_preflight(preflight_out)
    )
    rb = _gate_ranking_synthesis_bundle(
        ras,
        base_needs_llm=base_needs_llm,
        base_reason=base_reason,
        signal_out=signal_out,
        signal_parse_ok=signal_parse_ok,
        ranking_rr=ranking_rr,
        traces=traces,
        packaging_notes=packaging_notes,
        passed_adapter=passed_adapter,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_adapter_request_fn,
        enrich_request_fn=enrich_request_fn,
        route_model=route_model,
    )

    final_path = ras.resolve_staged_orchestration_final_path(
        needs_llm=rb.needs_llm,
        synth_gate_reason=rb.synth_gate_reason,
        preflight_skipped=preflight_skipped,
        signal_skipped=signal_skipped,
        ranking_bounded_parse_ok=rb.ranking_bounded_parse_ok,
        ranking_bounded_ran=rb.ranking_bounded_ran,
        base_reason=base_reason,
    )
    ranked_skip_synthesis = rb.needs_llm is False and rb.synth_gate_reason == "ranking_skip_synthesis"
    ranking_suppressed_slm_only = not base_needs_llm

    return PreflightSignalRankingGateOutcome(
        traces=traces,
        packaging_notes=packaging_notes,
        needs_llm=rb.needs_llm,
        preflight_out=preflight_out,
        signal_out=signal_out,
        ranking_out=rb.ranking_out,
        ranked_skip_synthesis=ranked_skip_synthesis,
        synth_gate_reason=rb.synth_gate_reason,
        final_path=final_path,
        ranking_effect=rb.ranking_effect,
        ranking_suppressed_slm_only=ranking_suppressed_slm_only,
        base_needs_llm=base_needs_llm,
        ranking_bounded_ran=rb.ranking_bounded_ran,
        ranking_no_eligible=rb.ranking_no_eligible,
        preflight_skipped=preflight_skipped,
        signal_skipped=signal_skipped,
        signal_rr=signal_rr,
        signal_dec=signal_dec,
        signal_adapter=signal_adapter,
        signal_resolved_via=signal_resolved_via,
        ranking_rr=ranking_rr,
        ranking_dec_for_rollup=rb.ranking_dec_for_rollup,
        ranking_exec_for_rollup=rb.ranking_exec_for_rollup,
        ranking_resolved_for_rollup=rb.ranking_resolved_for_rollup,
    )


def run_synthesis_with_retry(
    *,
    synthesis_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    annotate_request_for_stage_fn: Callable[[AdapterRequest, bool], AdapterRequest],
    mark_retry_context_fn: Callable[[], None] | None = None,
) -> tuple[AdapterResponse, int]:
    retry_policy = RetryPolicy()
    response: AdapterResponse | None = None
    attempt = 1
    while attempt <= retry_policy.MAX_RETRIES:
        if attempt > 1 and mark_retry_context_fn is not None:
            mark_retry_context_fn()
        base_request = build_adapter_request_fn(attempt)
        enrich_request_fn(base_request)
        request = annotate_request_for_stage_fn(base_request, True)
        response = generate_with_timeout(
            adapter=synthesis_adapter,
            request=request,
            timeout_ms=adapter_generate_timeout_ms,
        )
        has_error = response.error is not None
        is_empty = not response.raw_output or not response.raw_output.strip()
        if has_error or is_empty:
            failure_class = AIFailureClass.ADAPTER_ERROR
            if has_error and isinstance(response.error, str) and response.error.startswith(
                "adapter_generate_timeout:"
            ):
                failure_class = AIFailureClass.TIMEOUT_OR_EMPTY_RESPONSE
            if retry_policy.is_retryable_failure(failure_class) and attempt < retry_policy.MAX_RETRIES:
                attempt += 1
                continue
        break

    assert response is not None
    return response, attempt


def build_runtime_orchestration_summary(
    *,
    traces: list[dict[str, Any]],
    packaging_notes: list[str],
    synth_gate_reason: str,
    final_path_value: str,
    ranking_effect: str,
    ranking_bounded_ran: bool,
    ranking_suppressed_slm_only: bool,
    base_needs_llm: bool,
    ranking_no_eligible: bool,
    synthesis_skipped: bool,
) -> dict[str, Any]:
    summary = {
        "stages_executed": [t["stage_id"] for t in traces],
        "stages_skipped": [t["stage_id"] for t in traces if not t.get("bounded_model_call")],
        "synthesis_skipped": synthesis_skipped,
        "synthesis_gate_reason": synth_gate_reason,
        "final_path": final_path_value,
        "packaging_notes": packaging_notes,
        "staged_pipeline_preempted": None,
        "ranking_effect": ranking_effect,
        "ranking_bounded_model_call": ranking_bounded_ran,
        "ranking_suppressed_for_slm_only": ranking_suppressed_slm_only,
        "ranking_no_eligible_adapter": bool(base_needs_llm and ranking_no_eligible),
    }
    if synthesis_skipped:
        summary["synthesis_skip_reason"] = synth_gate_reason

    summary.update(runtime_additive_orchestration_fields(traces))
    return summary


def build_operator_audit_bundle(
    *,
    traces: list[dict[str, Any]],
    summary: dict[str, Any],
    rollup: dict[str, Any],
) -> dict[str, Any]:
    return build_runtime_operator_audit(
        runtime_stage_traces=traces,
        runtime_orchestration_summary=summary,
        model_routing_trace=rollup,
    )


def _packaging_trace_passthrough_synthesis() -> dict[str, Any]:
    return {
        "stage_id": RuntimeStageId.packaging.value,
        "stage_kind": "packaging",
        "orchestration_role": "passthrough_synthesis_response",
        "bounded_model_call": False,
        "skip_reason": None,
        "output_summary": {"mode": "passthrough_synthesis_response"},
        "errors": [],
    }


def _packaging_trace_slm_only_structured() -> dict[str, Any]:
    return {
        "stage_id": RuntimeStageId.packaging.value,
        "stage_kind": "packaging",
        "orchestration_role": "deterministic_slm_only_structured_payload",
        "bounded_model_call": False,
        "skip_reason": None,
        "output_summary": {"mode": "deterministic_slm_only_structured_payload"},
        "errors": [],
    }


def finalize_synthesis_staged_generation(
    *,
    traces: list[dict[str, Any]],
    packaging_notes: list[str],
    session: SessionState,
    passed_adapter: StoryAIAdapter,
    adapter_generate_timeout_ms: int,
    build_adapter_request_fn: Callable[[int], AdapterRequest],
    enrich_request_fn: Callable[[AdapterRequest], None],
    annotate_request_for_stage_fn: Callable[[AdapterRequest, bool], AdapterRequest],
    mark_retry_context_fn: Callable[[], None] | None,
    route_model: Callable[[RoutingRequest], RoutingDecision],
    signal_rr: RoutingRequest,
    signal_dec: RoutingDecision,
    signal_adapter: StoryAIAdapter,
    signal_resolved_via: bool,
    ranking_rr: RoutingRequest,
    ranking_dec_for_rollup: RoutingDecision | None,
    ranking_exec_for_rollup: StoryAIAdapter | None,
    ranking_resolved_for_rollup: bool | None,
    ranking_suppressed_slm_only: bool,
    synth_gate_reason: str,
    final_path: Any,
    ranking_effect: str,
    ranking_bounded_ran: bool,
    ranking_no_eligible: bool,
    base_needs_llm: bool,
) -> Any:
    """Synthesis routing + retry, packaging trace, rollup/summary/audit, ``StagedGenerationResult``."""
    from app.runtime.runtime_ai_stages import (
        StagedGenerationResult,
        build_legacy_model_routing_rollup,
        build_synthesis_routing_request,
    )

    synthesis_rr = build_synthesis_routing_request(session)
    synthesis_dec = route_model(synthesis_rr)
    synthesis_adapter, syn_resolved = resolve_routed_adapter(synthesis_dec, passed_adapter)
    synthesis_resolved = syn_resolved is not None
    resp_syn, syn_attempt = run_synthesis_with_retry(
        synthesis_adapter=synthesis_adapter,
        adapter_generate_timeout_ms=adapter_generate_timeout_ms,
        build_adapter_request_fn=build_adapter_request_fn,
        enrich_request_fn=enrich_request_fn,
        annotate_request_for_stage_fn=annotate_request_for_stage_fn,
        mark_retry_context_fn=mark_retry_context_fn,
    )
    traces.append(
        trace_dict_for_routed_model_stage(
            stage_id=RuntimeStageId.synthesis,
            routing_request=synthesis_rr,
            routing_decision=synthesis_dec,
            passed_adapter=passed_adapter,
            execution_adapter=synthesis_adapter,
            resolved_via_registry=synthesis_resolved,
            bounded_model_call=True,
            skip_reason=None if not resp_syn.error else "synthesis_adapter_error",
            output_summary={
                "raw_output_len": len(resp_syn.raw_output or ""),
                "synthesis_attempts": syn_attempt,
            },
            errors=[resp_syn.error] if resp_syn.error else [],
        )
    )
    traces.append(_packaging_trace_passthrough_synthesis())
    rollup = build_legacy_model_routing_rollup(
        synthesis_ran=True,
        synthesis_request=synthesis_rr,
        synthesis_decision=synthesis_dec,
        synthesis_execution_adapter=synthesis_adapter,
        synthesis_resolved_via_registry=synthesis_resolved,
        passed_adapter=passed_adapter,
        signal_request=signal_rr,
        signal_decision=signal_dec,
        signal_execution_adapter=signal_adapter,
        signal_resolved=signal_resolved_via,
        final_path=final_path,
        ranking_request=ranking_rr,
        ranking_decision=ranking_dec_for_rollup,
        ranking_execution_adapter=ranking_exec_for_rollup,
        ranking_resolved_via_registry=ranking_resolved_for_rollup,
        ranking_suppressed_slm_only=ranking_suppressed_slm_only,
        ranked_skip_synthesis=False,
        synthesis_gate_reason=synth_gate_reason,
    )
    summary = build_runtime_orchestration_summary(
        traces=traces,
        packaging_notes=packaging_notes,
        synth_gate_reason=synth_gate_reason,
        final_path_value=final_path.value,
        ranking_effect=ranking_effect,
        ranking_bounded_ran=ranking_bounded_ran,
        ranking_suppressed_slm_only=ranking_suppressed_slm_only,
        base_needs_llm=base_needs_llm,
        ranking_no_eligible=ranking_no_eligible,
        synthesis_skipped=False,
    )
    operator_audit = build_operator_audit_bundle(
        traces=traces,
        summary=summary,
        rollup=rollup,
    )
    return StagedGenerationResult(
        response=resp_syn,
        runtime_stage_traces=traces,
        runtime_orchestration_summary=summary,
        model_routing_trace=rollup,
        operator_audit=operator_audit,
        synthesis_skipped=False,
        final_path=final_path,
        synthesis_attempt_count=syn_attempt,
        final_execution_adapter=synthesis_adapter,
    )


def finalize_slm_only_staged_generation(
    *,
    traces: list[dict[str, Any]],
    packaging_notes: list[str],
    preflight_out: Any,
    signal_out: Any,
    ranking_out: Any | None,
    ranked_skip_synthesis: bool,
    synth_gate_reason: str,
    final_path: Any,
    passed_adapter: StoryAIAdapter,
    signal_rr: RoutingRequest,
    signal_dec: RoutingDecision,
    signal_adapter: StoryAIAdapter,
    signal_resolved_via: bool,
    ranking_rr: RoutingRequest,
    ranking_dec_for_rollup: RoutingDecision | None,
    ranking_exec_for_rollup: StoryAIAdapter | None,
    ranking_resolved_for_rollup: bool | None,
    ranking_suppressed_slm_only: bool,
    ranking_effect: str,
    ranking_bounded_ran: bool,
    ranking_no_eligible: bool,
    base_needs_llm: bool,
) -> Any:
    """Deterministic SLM-only payload, packaging trace, rollup/summary/audit, ``StagedGenerationResult``."""
    from app.runtime.runtime_ai_stages import (
        StagedGenerationResult,
        build_legacy_model_routing_rollup,
        build_slm_only_structured_payload,
    )

    assert signal_out is not None
    payload = build_slm_only_structured_payload(
        preflight=preflight_out,
        signal=signal_out,
        ranking=ranking_out if ranked_skip_synthesis else None,
    )
    raw = f"[staged-runtime/slm_only] gate={synth_gate_reason}"
    resp = AdapterResponse(
        raw_output=raw,
        structured_payload=payload,
        backend_metadata={
            "staged_runtime": True,
            "slm_only": True,
            "synthesis_gate_reason": synth_gate_reason,
            "ranked_skip_synthesis": ranked_skip_synthesis,
        },
        error=None,
    )
    traces.append(_packaging_trace_slm_only_structured())
    rollup = build_legacy_model_routing_rollup(
        synthesis_ran=False,
        synthesis_request=None,
        synthesis_decision=None,
        synthesis_execution_adapter=None,
        synthesis_resolved_via_registry=None,
        passed_adapter=passed_adapter,
        signal_request=signal_rr,
        signal_decision=signal_dec,
        signal_execution_adapter=signal_adapter,
        signal_resolved=signal_resolved_via,
        final_path=final_path,
        ranking_request=ranking_rr,
        ranking_decision=ranking_dec_for_rollup if ranked_skip_synthesis else None,
        ranking_execution_adapter=ranking_exec_for_rollup if ranked_skip_synthesis else None,
        ranking_resolved_via_registry=ranking_resolved_for_rollup if ranked_skip_synthesis else None,
        ranking_suppressed_slm_only=ranking_suppressed_slm_only,
        ranked_skip_synthesis=ranked_skip_synthesis,
        synthesis_gate_reason=synth_gate_reason,
    )
    summary = build_runtime_orchestration_summary(
        traces=traces,
        packaging_notes=packaging_notes,
        synth_gate_reason=synth_gate_reason,
        final_path_value=final_path.value,
        ranking_effect=ranking_effect,
        ranking_bounded_ran=ranking_bounded_ran,
        ranking_suppressed_slm_only=ranking_suppressed_slm_only,
        base_needs_llm=base_needs_llm,
        ranking_no_eligible=ranking_no_eligible,
        synthesis_skipped=True,
    )
    operator_audit = build_operator_audit_bundle(
        traces=traces,
        summary=summary,
        rollup=rollup,
    )
    return StagedGenerationResult(
        response=resp,
        runtime_stage_traces=traces,
        runtime_orchestration_summary=summary,
        model_routing_trace=rollup,
        operator_audit=operator_audit,
        synthesis_skipped=True,
        final_path=final_path,
        synthesis_attempt_count=0,
        final_execution_adapter=passed_adapter,
    )
