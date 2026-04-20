"""Transitional: AI-backed turn execution inside the backend ``SessionState`` loop.

Bridges adapters into ``execute_turn`` for **in-process** flows only — not a second
live runtime alongside the World Engine.

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
from app.runtime.ai_adapter import (
    AdapterRequest,
    AdapterResponse,
    StoryAIAdapter,
    generate_with_timeout,
)
from app.runtime.input_interpreter import interpret_operator_input
from app.runtime.narrative_threads import coerce_narrative_thread_set, compact_threads_for_adapter
from app.runtime.short_term_context import ShortTermTurnContext
from app.runtime.ai_decision import ParseResult, ParsedAIDecision, process_adapter_response
from app.runtime.ai_decision_logging import construct_ai_decision_log
from app.runtime.decision_policy import AIDecisionPolicy
from app.runtime.event_log import RuntimeEventLog
from app.runtime.supervisor_orchestrator import SupervisorOrchestrator
from app.runtime.tool_loop import (
    HostToolContext,
    ToolCallStatus,
    ToolLoopPolicy,
    ToolLoopStopReason,
    detect_tool_request_payload,
    execute_tool_request,
)
from app.runtime.turn_executor import (
    MockDecision,
    ProposedStateDelta,
    TurnExecutionResult,
    execute_turn,
)
from app.runtime.role_structured_decision import ParsedRoleAwareDecision
from app.runtime.validators import validate_action_type, validate_action_structure
from app.runtime.runtime_models import (
    AIDecisionLog,
    AIValidationOutcome,
    DeltaType,
    DeltaValidationStatus,
    DegradedMarker,
    ExecutionFailureReason,
    GuardOutcome,
    ProposalSource,
    SessionState,
    StateDelta,
)

from app.runtime.adapter_registry import get_adapter, iter_model_specs
from app.runtime.area2_operator_truth import (
    enrich_operator_audit_with_area2_truth,
    resolve_routing_bootstrap_enabled,
)
from app.runtime.area2_routing_authority import AUTHORITY_SOURCE_RUNTIME
from app.runtime.operator_audit import build_runtime_operator_audit
from app.runtime.model_routing import route_model
from app.runtime.model_routing_contracts import (
    CostSensitivity,
    EscalationHint,
    LatencyBudget,
    RoutingDecision,
    RoutingRequest,
    TaskKind,
    WorkflowPhase,
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


def _continuity_context_from_session_layers(session: SessionState) -> dict[str, Any] | None:
    """Task 1C/1D: bounded JSON snapshots from ``context_layers`` only (binding precision §1).

    Excludes diagnostic short-term blobs. Does not embed session_history, turn results,
    or raw metadata. ``active_narrative_threads`` is built only from ``context_layers.narrative_threads``.
    """
    cl = session.context_layers
    out: dict[str, Any] = {}

    st = cl.short_term_context
    if st is not None:
        if isinstance(st, ShortTermTurnContext):
            out["short_term_turn_context"] = st.model_dump(
                mode="json",
                exclude={"execution_result_full", "ai_decision_log_full"},
            )
        elif hasattr(st, "model_dump"):
            out["short_term_turn_context"] = st.model_dump(
                mode="json",
                exclude={"execution_result_full", "ai_decision_log_full"},
            )
        elif isinstance(st, dict):
            out["short_term_turn_context"] = {
                k: v for k, v in st.items() if k not in ("execution_result_full", "ai_decision_log_full")
            }

    ps = cl.progression_summary
    if ps is not None and hasattr(ps, "model_dump"):
        out["progression_summary"] = ps.model_dump(mode="json")

    rel = cl.relationship_axis_context
    if rel is not None and hasattr(rel, "model_dump"):
        out["relationship_axis_context"] = rel.model_dump(mode="json")

    lore = cl.lore_direction_context
    if lore is not None and hasattr(lore, "model_dump"):
        out["lore_direction_context"] = lore.model_dump(mode="json")

    nt = coerce_narrative_thread_set(cl.narrative_threads)
    out["active_narrative_threads"] = compact_threads_for_adapter(nt)

    return out if out else None


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
    op_raw = operator_input if operator_input is not None else ""
    input_interpretation = interpret_operator_input(op_raw)
    continuity_context = _continuity_context_from_session_layers(session)
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=recent_events or [],
        operator_input=operator_input or None,
        input_interpretation=input_interpretation,
        continuity_context=continuity_context,
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




def build_runtime_routing_request(session: SessionState) -> RoutingRequest:
    meta = session.metadata if isinstance(session.metadata, dict) else {}
    task_kind = TaskKind.narrative_formulation
    raw_tk = meta.get("routing_task_kind")
    if isinstance(raw_tk, str):
        try:
            task_kind = TaskKind(raw_tk)
        except ValueError:
            pass
    hints: list[EscalationHint] = []
    markers = session.degraded_state.active_markers
    if DegradedMarker.FALLBACK_ACTIVE in markers or DegradedMarker.RETRY_EXHAUSTED in markers:
        hints.append(EscalationHint.continuity_risk)
    latency_budget = LatencyBudget.normal
    cost_sensitivity = CostSensitivity.medium
    lb = meta.get("routing_latency_budget")
    if isinstance(lb, str):
        try:
            latency_budget = LatencyBudget(lb)
        except ValueError:
            pass
    cs = meta.get("routing_cost_sensitivity")
    if isinstance(cs, str):
        try:
            cost_sensitivity = CostSensitivity(cs)
        except ValueError:
            pass
    return RoutingRequest(
        workflow_phase=WorkflowPhase.generation,
        task_kind=task_kind,
        requires_structured_output=True,
        latency_budget=latency_budget,
        cost_sensitivity=cost_sensitivity,
        escalation_hints=hints,
    )


def build_model_routing_trace_dict(
    *,
    routing_request: RoutingRequest,
    routing_decision: RoutingDecision,
    passed_adapter: StoryAIAdapter,
    execution_adapter: StoryAIAdapter,
    resolved_via_get_adapter: bool,
) -> dict[str, Any]:
    from app.runtime.model_routing_evidence import build_routing_evidence

    return {
        "routing_invoked": True,
        "request": routing_request.model_dump(mode="json"),
        "decision": routing_decision.model_dump(mode="json"),
        "passed_adapter_name": passed_adapter.adapter_name,
        "executed_adapter_name": execution_adapter.adapter_name,
        "selected_adapter_name": routing_decision.selected_adapter_name,
        "selected_model": routing_decision.selected_model,
        "resolved_via_get_adapter": resolved_via_get_adapter,
        "fallback_to_passed_adapter": not resolved_via_get_adapter,
        "escalation_applied": routing_decision.escalation_applied,
        "degradation_applied": routing_decision.degradation_applied,
        "routing_evidence": build_routing_evidence(
            routing_request=routing_request,
            routing_decision=routing_decision,
            executed_adapter_name=execution_adapter.adapter_name,
            passed_adapter_name=passed_adapter.adapter_name,
            resolved_via_get_adapter=resolved_via_get_adapter,
            fallback_to_passed_adapter=not resolved_via_get_adapter,
            bounded_model_call=None,
            skip_reason=None,
        ),
    }


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
        model_routing_trace=model_routing_trace,
        runtime_stage_traces=runtime_stage_traces,
        runtime_orchestration_summary=runtime_orchestration_summary,
        operator_audit=operator_audit,
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
    orchestration_config = session.metadata.get("agent_orchestration")
    orchestration_enabled = False
    if isinstance(orchestration_config, dict):
        orchestration_enabled = bool(orchestration_config.get("enabled", False))
    elif isinstance(orchestration_config, bool):
        orchestration_enabled = orchestration_config

    # W2.5 Phase 5: Capture pre-execution snapshot for restore
    # This snapshot is taken BEFORE any risky operation (adapter call, execution)
    # If recovery fails catastrophically, we can restore to this known-good state
    pre_execution_snapshot = StateSnapshot(
        turn_number=session.turn_counter,
        canonical_state=deepcopy(session.canonical_state),
        snapshot_reason="pre_ai_execution",
    )

    # B2: Initialize optional bounded tool-loop policy and transcript
    tool_loop_policy = ToolLoopPolicy.from_session_metadata(session.metadata)
    tool_loop_enabled = (
        session.execution_mode == "ai"
        and tool_loop_policy.enabled
        and not orchestration_enabled
    )
    execution_controls = {
        "agent_orchestration_requested": orchestration_enabled,
        "agent_orchestration_active": orchestration_enabled,
        "tool_loop_requested": tool_loop_policy.enabled,
        "tool_loop_active": tool_loop_enabled,
    }
    tool_call_transcript: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    tool_loop_stop_reason = ToolLoopStopReason.FINALIZED
    tool_limit_hit = False
    finalized_after_tool_use = False
    last_successful_tool_sequence: int | None = None
    tool_call_count = 0
    tool_loop_summary: dict[str, Any] | None = None
    preview_records: list[dict[str, Any]] = []
    preview_diagnostics: dict[str, Any] | None = None
    supervisor_plan = None
    subagent_invocations = None
    subagent_results = None
    merge_finalization = None
    supervisor_tool_transcript: list[dict[str, Any]] = []
    orchestration_budget_summary = None
    orchestration_failover = None
    orchestration_cache = None
    tool_audit = None
    adapter_generate_timeout_ms_raw = session.metadata.get("adapter_generate_timeout_ms", 30000)
    try:
        adapter_generate_timeout_ms = max(int(adapter_generate_timeout_ms_raw), 1)
    except (TypeError, ValueError):
        adapter_generate_timeout_ms = 30000

    runtime_stage_traces_for_log: list[dict[str, Any]] | None = None
    runtime_orchestration_summary_for_log: dict[str, Any] | None = None
    staged_result_holder = None
    staged_enabled = session.metadata.get("runtime_staged_orchestration", True) is not False

    interpretation_logged_for_turn = False

    def _build_request(attempt: int) -> AdapterRequest:
        nonlocal interpretation_logged_for_turn
        request = build_adapter_request(
            session,
            module,
            operator_input=operator_input,
            recent_events=recent_events,
            attempt=attempt,
        )
        if not interpretation_logged_for_turn and request.input_interpretation is not None:
            interpretation_logged_for_turn = True
            log_key = "operator_input_interpretation_log"
            if log_key not in session.metadata:
                session.metadata[log_key] = []
            session.metadata[log_key].append(
                {
                    "turn_number": current_turn,
                    "envelope": request.input_interpretation.model_dump(mode="json"),
                }
            )
        if tool_loop_enabled:
            request.metadata["tool_loop"] = {
                "enabled": True,
                "sequence_index": tool_call_count + 1,
                "max_tool_calls_per_turn": tool_loop_policy.max_tool_calls_per_turn,
                "tool_results": tool_results[-tool_loop_policy.max_tool_calls_per_turn :],
            }
        return request

    # Step 1/2: Build request + generate response with retry loop (W2.5 Phase 1)
    from app.runtime.ai_failure_recovery import RetryPolicy, AIFailureClass

    retry_policy = RetryPolicy()
    mcp_enrichment_enabled = session.metadata.get("mcp_enrichment_enabled", False)

    def _enrich_request_with_mcp(request: AdapterRequest) -> None:
        if not mcp_enrichment_enabled:
            return
        from app.mcp_client.enrichment import build_mcp_enrichment
        from app.mcp_client.client import OperatorEndpointClient
        from app.observability.trace import get_trace_id

        _trace_id = get_trace_id()
        _client = session.metadata.get("_mcp_client_override") or OperatorEndpointClient()
        enrichment = build_mcp_enrichment(session.session_id, _trace_id, _client)
        request.metadata["mcp_context_enrichment"] = enrichment

    def _mark_reduced_context_if_needed() -> None:
        if DegradedMarker.REDUCED_CONTEXT_ACTIVE not in session.degraded_state.active_markers:
            session.degraded_state.active_markers.add(DegradedMarker.REDUCED_CONTEXT_ACTIVE)
            session.degraded_state.marker_timestamps[DegradedMarker.REDUCED_CONTEXT_ACTIVE] = (
                datetime.now(timezone.utc)
            )
            if not session.degraded_state.is_degraded:
                session.degraded_state.is_degraded = True
                session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = (
                    datetime.now(timezone.utc)
                )

    # Routing + optional multi-stage Runtime orchestration (Task 1). ``execution_adapter`` must
    # be set before ``_generate_with_runtime_policy`` is invoked (legacy / tool-loop paths).
    if orchestration_enabled:
        routing_request = build_runtime_routing_request(session)
        routing_decision = route_model(routing_request)
        resolved_from_registry = None
        if routing_decision.selected_adapter_name:
            resolved_from_registry = get_adapter(routing_decision.selected_adapter_name)
        execution_adapter = resolved_from_registry if resolved_from_registry is not None else adapter
        model_routing_trace = build_model_routing_trace_dict(
            routing_request=routing_request,
            routing_decision=routing_decision,
            passed_adapter=adapter,
            execution_adapter=execution_adapter,
            resolved_via_get_adapter=resolved_from_registry is not None,
        )
        if isinstance(session.metadata, dict):
            session.metadata["last_model_routing_trace"] = model_routing_trace
        runtime_orchestration_summary_for_log = {
            "staged_pipeline_preempted": "agent_orchestration",
            "reason": "supervisor_orchestrator_handles_full_turn_no_runtime_stages",
        }
        runtime_stage_traces_for_log = []
    elif staged_enabled:
        from app.runtime.runtime_ai_stages import run_runtime_staged_generation

        staged_result_holder = run_runtime_staged_generation(
            session=session,
            passed_adapter=adapter,
            adapter_generate_timeout_ms=adapter_generate_timeout_ms,
            build_adapter_request_fn=_build_request,
            enrich_request_fn=_enrich_request_with_mcp,
            mark_retry_context_fn=_mark_reduced_context_if_needed,
        )
        model_routing_trace = staged_result_holder.model_routing_trace
        runtime_stage_traces_for_log = staged_result_holder.runtime_stage_traces
        runtime_orchestration_summary_for_log = staged_result_holder.runtime_orchestration_summary
        execution_adapter = staged_result_holder.final_execution_adapter or adapter
        if isinstance(session.metadata, dict):
            session.metadata["last_model_routing_trace"] = model_routing_trace
    else:
        routing_request = build_runtime_routing_request(session)
        routing_decision = route_model(routing_request)
        resolved_from_registry = None
        if routing_decision.selected_adapter_name:
            resolved_from_registry = get_adapter(routing_decision.selected_adapter_name)
        execution_adapter = resolved_from_registry if resolved_from_registry is not None else adapter
        model_routing_trace = build_model_routing_trace_dict(
            routing_request=routing_request,
            routing_decision=routing_decision,
            passed_adapter=adapter,
            execution_adapter=execution_adapter,
            resolved_via_get_adapter=resolved_from_registry is not None,
        )
        if isinstance(session.metadata, dict):
            session.metadata["last_model_routing_trace"] = model_routing_trace

    if staged_result_holder is not None and staged_result_holder.operator_audit:
        operator_audit_for_log = staged_result_holder.operator_audit
    else:
        operator_audit_for_log = build_runtime_operator_audit(
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            model_routing_trace=model_routing_trace,
        )

    if isinstance(operator_audit_for_log, dict):
        _specs_rt = list(iter_model_specs())
        enrich_operator_audit_with_area2_truth(
            operator_audit_for_log,
            surface="runtime",
            authority_source=AUTHORITY_SOURCE_RUNTIME,
            bootstrap_enabled=resolve_routing_bootstrap_enabled(),
            registry_model_spec_count=len(_specs_rt),
            specs_for_coverage=_specs_rt,
            runtime_stage_traces=runtime_stage_traces_for_log,
            model_routing_trace=model_routing_trace,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
        )

    def _generate_with_runtime_policy(
        *,
        starting_attempt: int = 1,
    ) -> tuple[AdapterResponse, int]:
        response: AdapterResponse | None = None
        current_attempt = starting_attempt
        request = _build_request(attempt=current_attempt)
        _enrich_request_with_mcp(request)

        while current_attempt <= retry_policy.MAX_RETRIES:
            if current_attempt > 1:
                _mark_reduced_context_if_needed()
                request = _build_request(attempt=current_attempt)
                _enrich_request_with_mcp(request)

            response = generate_with_timeout(
                adapter=execution_adapter,
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
                if (
                    retry_policy.is_retryable_failure(failure_class)
                    and current_attempt < retry_policy.MAX_RETRIES
                ):
                    current_attempt += 1
                    continue
            break

        assert response is not None
        return response, current_attempt

    def _build_preview_snapshot(preview_result: dict[str, Any]) -> dict[str, Any]:
        return {
            "guard_outcome": preview_result.get("guard_outcome"),
            "preview_allowed": bool(preview_result.get("preview_allowed", False)),
            "accepted_delta_count": int(preview_result.get("accepted_delta_count", 0)),
            "rejected_delta_count": int(preview_result.get("rejected_delta_count", 0)),
            "partial_acceptance": bool(preview_result.get("partial_acceptance", False)),
            "input_targets": list((preview_result.get("input_targets") or [])[:20]),
            "summary": preview_result.get("summary"),
            "rejection_reasons": (preview_result.get("rejection_reasons") or [])[:5],
            "suggested_corrections": (preview_result.get("suggested_corrections") or [])[:5],
            "preview_safe_no_write": bool(preview_result.get("preview_safe_no_write", True)),
        }

    def _build_preview_diagnostics_payload(
        *,
        records: list[dict[str, Any]],
        final_targets: list[str],
    ) -> dict[str, Any]:
        last_record = records[-1]
        last_preview = last_record["result"]
        preview_targets = list(last_preview.get("input_targets", []) or [])
        return {
            "preview_count": len(records),
            "preview_iterations": [
                {
                    "sequence_index": item.get("sequence_index"),
                    "request_id": item.get("request_id"),
                    "requesting_agent_id": item.get("requesting_agent_id"),
                    "request_summary": item.get("request_summary"),
                    "result_summary": _build_preview_snapshot(item["result"]),
                }
                for item in records[-5:]
            ],
            "last_preview": _build_preview_snapshot(last_preview),
            "last_preview_request": {
                "request_id": last_record.get("request_id"),
                "requesting_agent_id": last_record.get("requesting_agent_id"),
                "request_summary": last_record.get("request_summary"),
            },
            "revised_after_preview": final_targets != preview_targets if final_targets else False,
            "improved_acceptance_vs_last_preview": False,
        }

    def _set_preview_improvement_metric(
        diagnostics: dict[str, Any] | None,
        *,
        final_accepted_count: int,
    ) -> None:
        if diagnostics is None:
            return
        last_preview = diagnostics.get("last_preview") or {}
        baseline = int(last_preview.get("accepted_delta_count", 0))
        diagnostics["improved_acceptance_vs_last_preview"] = final_accepted_count > baseline

    if orchestration_enabled:
        base_request = _build_request(attempt=1)
        _enrich_request_with_mcp(base_request)
        orchestrator = SupervisorOrchestrator()
        orchestrated = orchestrator.orchestrate(
            base_request=base_request,
            adapter=execution_adapter,
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events or [],
            tool_registry=None,
        )
        response = orchestrated.final_response
        current_attempt = 1
        supervisor_plan = orchestrated.plan
        subagent_invocations = orchestrated.invocations
        subagent_results = orchestrated.results
        merge_finalization = orchestrated.merge_finalization
        supervisor_tool_transcript = orchestrated.agent_tool_transcript
        orchestration_budget_summary = orchestrated.budget_summary
        orchestration_failover = orchestrated.failover_events
        orchestration_cache = orchestrated.cache_summary
        tool_audit = orchestrated.tool_audit
        if supervisor_tool_transcript:
            tool_call_transcript.extend(supervisor_tool_transcript)
            for entry in supervisor_tool_transcript:
                if entry.get("tool_name") != "wos.guard.preview_delta":
                    continue
                preview_result = entry.get("preview_result_summary")
                if not isinstance(preview_result, dict):
                    continue
                preview_records.append(
                    {
                        "sequence_index": entry.get("sequence_index"),
                        "request_id": entry.get("preview_request_id"),
                        "requesting_agent_id": entry.get("agent_id"),
                        "request_summary": entry.get("sanitized_arguments") or {},
                        "result": preview_result,
                    }
                )
        tool_loop_summary = {
            "enabled": False,
            "total_calls": 0,
            "stop_reason": "orchestration_enabled",
            "limit_hit": False,
            "finalized_after_tool_use": False,
            "execution_controls": execution_controls,
        }
    elif staged_enabled and staged_result_holder is not None:
        response = staged_result_holder.response
        if staged_result_holder.synthesis_skipped:
            current_attempt = 1
        else:
            current_attempt = max(1, staged_result_holder.synthesis_attempt_count)
    else:
        response, current_attempt = _generate_with_runtime_policy(starting_attempt=1)

    # Step 2b: Handle adapter error or empty output
    # W2.5 Phase 4-5: If retries exhausted, check if restore is needed
    if response.error or (not response.raw_output or not response.raw_output.strip()):
        error_log = _create_error_decision_log(
            session,
            current_turn,
            response.raw_output or "",
            [response.error] if response.error else ["Empty AI response"],
            "adapter_error" if response.error else "generation_error",
            model_routing_trace=model_routing_trace,
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
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

            # W2.5 Phase 6: Mark retry exhaustion in degradation state
            if DegradedMarker.RETRY_EXHAUSTED not in session.degraded_state.active_markers:
                session.degraded_state.active_markers.add(DegradedMarker.RETRY_EXHAUSTED)
                session.degraded_state.marker_timestamps[DegradedMarker.RETRY_EXHAUSTED] = (
                    datetime.now(timezone.utc)
                )
                if not session.degraded_state.is_degraded:
                    session.degraded_state.is_degraded = True
                    session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = (
                        datetime.now(timezone.utc)
                    )

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

                    # W2.5 Phase 6: Mark restore usage in degradation state
                    if DegradedMarker.RESTORE_USED not in session.degraded_state.active_markers:
                        session.degraded_state.active_markers.add(DegradedMarker.RESTORE_USED)
                        session.degraded_state.marker_timestamps[DegradedMarker.RESTORE_USED] = (
                            datetime.now(timezone.utc)
                        )

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
                        tool_loop_summary=tool_loop_summary,
                        tool_call_transcript=tool_call_transcript or None,
                        tool_influence=(
                            {"influencing_tool_sequence": last_successful_tool_sequence}
                            if last_successful_tool_sequence
                            else None
                        ),
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
                        runtime_stage_traces=runtime_stage_traces_for_log,
                        runtime_orchestration_summary=runtime_orchestration_summary_for_log,
                        operator_audit=operator_audit_for_log,
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

            # W2.5 Phase 6: Mark safe-turn activation in degradation state
            if DegradedMarker.SAFE_TURN_USED not in session.degraded_state.active_markers:
                session.degraded_state.active_markers.add(DegradedMarker.SAFE_TURN_USED)
                session.degraded_state.marker_timestamps[DegradedMarker.SAFE_TURN_USED] = (
                    datetime.now(timezone.utc)
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
                tool_loop_summary=tool_loop_summary,
                tool_call_transcript=tool_call_transcript or None,
                tool_influence=(
                    {"influencing_tool_sequence": last_successful_tool_sequence}
                    if last_successful_tool_sequence
                    else None
                ),
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
                runtime_stage_traces=runtime_stage_traces_for_log,
                runtime_orchestration_summary=runtime_orchestration_summary_for_log,
                operator_audit=operator_audit_for_log,
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

    # B2: Optional bounded MCP-style tool request loop.
    if tool_loop_enabled and response and not response.error and response.raw_output.strip():
        tool_context = HostToolContext(
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events or [],
        )
        while True:
            tool_request = detect_tool_request_payload(
                response.structured_payload,
                sequence_index=tool_call_count + 1,
            )
            if tool_request is None:
                tool_loop_stop_reason = ToolLoopStopReason.FINALIZED
                finalized_after_tool_use = tool_call_count > 0
                break

            if tool_call_count >= tool_loop_policy.max_tool_calls_per_turn:
                tool_loop_stop_reason = ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
                tool_limit_hit = True
                break

            if tool_request.tool_name == "wos.guard.preview_delta":
                tool_request.arguments.setdefault("requested_by_agent_id", "primary_ai")

            transcript_entry, tool_result = execute_tool_request(
                tool_request,
                policy=tool_loop_policy,
                context=tool_context,
            )
            transcript_entry_payload = transcript_entry.model_dump()
            transcript_entry_payload["agent_id"] = "primary_ai"
            tool_results.append(tool_result)
            tool_call_count += 1
            if (
                tool_result.get("tool_name") == "wos.guard.preview_delta"
                and tool_result.get("status") == ToolCallStatus.SUCCESS
                and isinstance(tool_result.get("result"), dict)
            ):
                preview_result = tool_result["result"]
                transcript_entry_payload["preview_request_id"] = tool_result.get("request_id")
                transcript_entry_payload["preview_result_summary"] = _build_preview_snapshot(
                    preview_result
                )
                preview_records.append(
                    {
                        "sequence_index": transcript_entry.sequence_index,
                        "request_id": tool_result.get("request_id"),
                        "requesting_agent_id": "primary_ai",
                        "request_summary": transcript_entry_payload.get("sanitized_arguments")
                        or {},
                        "result": preview_result,
                    }
                )
            tool_call_transcript.append(transcript_entry_payload)

            if transcript_entry.status == ToolCallStatus.SUCCESS:
                last_successful_tool_sequence = transcript_entry.sequence_index
            elif transcript_entry.status == ToolCallStatus.REJECTED:
                tool_loop_stop_reason = ToolLoopStopReason.POLICY_REJECTED
                break
            elif transcript_entry.status == ToolCallStatus.TIMEOUT:
                tool_loop_stop_reason = ToolLoopStopReason.TOOL_TIMEOUT_EXHAUSTED
                break
            elif transcript_entry.status == ToolCallStatus.ERROR:
                tool_loop_stop_reason = ToolLoopStopReason.TOOL_ERROR_EXHAUSTED
                break

            if tool_call_count >= tool_loop_policy.max_tool_calls_per_turn:
                tool_loop_stop_reason = ToolLoopStopReason.TOOL_CALL_LIMIT_REACHED
                tool_limit_hit = True
                break

            # Continue model loop with shared runtime generation policy
            response, _ = _generate_with_runtime_policy(starting_attempt=1)
            if response.error or (not response.raw_output or not response.raw_output.strip()):
                tool_loop_stop_reason = ToolLoopStopReason.TOOL_ERROR_EXHAUSTED
                break

        # Mark the last successful tool as influencing finalization when a final output was reached.
        if tool_loop_stop_reason == ToolLoopStopReason.FINALIZED and last_successful_tool_sequence:
            for entry in tool_call_transcript:
                if entry.get("sequence_index") == last_successful_tool_sequence:
                    entry["influenced_final_output"] = True
                    break

    if tool_loop_enabled:
        tool_loop_summary = {
            "enabled": True,
            "total_calls": tool_call_count,
            "stop_reason": tool_loop_stop_reason,
            "limit_hit": tool_limit_hit,
            "finalized_after_tool_use": finalized_after_tool_use,
            "execution_controls": execution_controls,
        }

    # Deterministic stop when loop did not finalize to a final story payload.
    # Includes zero-call exits (e.g. max_tool_calls_per_turn == 0 with a pending tool request).
    if tool_loop_enabled and tool_loop_stop_reason != ToolLoopStopReason.FINALIZED:
        if preview_records:
            preview_diagnostics = _build_preview_diagnostics_payload(
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
        _set_preview_improvement_metric(
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
            tool_loop_summary=tool_loop_summary,
            tool_call_transcript=tool_call_transcript or None,
            tool_influence=(
                {"influencing_tool_sequence": last_successful_tool_sequence}
                if last_successful_tool_sequence
                else None
            ),
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
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
        )
        _store_decision_log(session, decision_log)
        return turn_result

    # Step 3: Parse response
    parse_result: ParseResult = process_adapter_response(response)
    if preview_records:
        final_targets = (
            [delta.target_path for delta in (parse_result.decision.proposed_deltas or [])]
            if parse_result.success and parse_result.decision
            else []
        )
        preview_diagnostics = _build_preview_diagnostics_payload(
            records=preview_records,
            final_targets=final_targets,
        )

    # Step 4: If parse failed, activate fallback responder (W2.5 Phase 3)
    if not parse_result.success:
        # Log the parse error
        error_log = _create_error_decision_log(
            session,
            current_turn,
            parse_result.raw_output,
            parse_result.errors,
            "parse_error",
            model_routing_trace=model_routing_trace,
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
        )
        _store_decision_log(session, error_log)

        # W2.5 Phase 3: Activate fallback responder instead of terminal failure
        from app.runtime.ai_failure_recovery import (
            generate_fallback_responder_proposal,
            FallbackResponderPolicy,
        )

        # W2.5 Phase 6: Mark fallback activation in degradation state
        if DegradedMarker.FALLBACK_ACTIVE not in session.degraded_state.active_markers:
            session.degraded_state.active_markers.add(DegradedMarker.FALLBACK_ACTIVE)
            session.degraded_state.marker_timestamps[DegradedMarker.FALLBACK_ACTIVE] = (
                datetime.now(timezone.utc)
            )
            if not session.degraded_state.is_degraded:
                session.degraded_state.is_degraded = True
                session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = (
                    datetime.now(timezone.utc)
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
            tool_loop_summary=tool_loop_summary,
            tool_call_transcript=tool_call_transcript or None,
            tool_influence=(
                {"influencing_tool_sequence": last_successful_tool_sequence}
                if last_successful_tool_sequence
                else None
            ),
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
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
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
            model_routing_trace=model_routing_trace,
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
        )
        _store_decision_log(session, error_log)

        # Activate fallback responder for structural failure
        from app.runtime.ai_failure_recovery import (
            generate_fallback_responder_proposal,
            FallbackResponderPolicy,
        )

        # W2.5 Phase 6: Mark fallback activation in degradation state
        if DegradedMarker.FALLBACK_ACTIVE not in session.degraded_state.active_markers:
            session.degraded_state.active_markers.add(DegradedMarker.FALLBACK_ACTIVE)
            session.degraded_state.marker_timestamps[DegradedMarker.FALLBACK_ACTIVE] = (
                datetime.now(timezone.utc)
            )
            if not session.degraded_state.is_degraded:
                session.degraded_state.is_degraded = True
                session.degraded_state.marker_timestamps[DegradedMarker.DEGRADED] = (
                    datetime.now(timezone.utc)
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
            tool_loop_summary=tool_loop_summary,
            tool_call_transcript=tool_call_transcript or None,
            tool_influence=(
                {"influencing_tool_sequence": last_successful_tool_sequence}
                if last_successful_tool_sequence
                else None
            ),
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
            runtime_stage_traces=runtime_stage_traces_for_log,
            runtime_orchestration_summary=runtime_orchestration_summary_for_log,
            operator_audit=operator_audit_for_log,
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
    _set_preview_improvement_metric(
        preview_diagnostics,
        final_accepted_count=len(turn_result.accepted_deltas),
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
        tool_loop_summary=tool_loop_summary,
        tool_call_transcript=tool_call_transcript or None,
        tool_influence=(
            {"influencing_tool_sequence": last_successful_tool_sequence}
            if last_successful_tool_sequence
            else None
        ),
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
        runtime_stage_traces=runtime_stage_traces_for_log,
        runtime_orchestration_summary=runtime_orchestration_summary_for_log,
        operator_audit=operator_audit_for_log,
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
