"""C1 supervisor orchestrator with real bounded subagent invocations."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.runtime.agent_registry import (
    AgentConfig,
    AgentRegistry,
    SupervisorTurnPolicy,
    build_default_agent_registry,
)
from app.runtime.ai_adapter import (
    AdapterRequest,
    AdapterResponse,
    StoryAIAdapter,
    generate_with_timeout,
    normalize_token_usage,
)
from app.runtime.ai_decision import ParsedAIDecision, process_adapter_response
from app.runtime.orchestration_cache import OrchestrationTurnCache
from app.runtime.tool_loop import (
    HostToolContext,
    ToolCallTranscriptEntry,
    ToolCallStatus,
    ToolLoopPolicy,
    detect_tool_request_payload,
    execute_tool_request,
)
from app.runtime.runtime_models import (
    AgentInvocationRecord,
    AgentResultRecord,
    MergeFinalizationRecord,
    SupervisorPlan,
    TokenUsageRecord,
)


DEFAULT_EXECUTION_ORDER = [
    "scene_reader",
    "trigger_analyst",
    "delta_planner",
    "dialogue_planner",
]


@dataclass
class SupervisorExecutionResult:
    """Bounded output of supervisor orchestration."""

    final_response: AdapterResponse
    plan: SupervisorPlan
    invocations: list[AgentInvocationRecord]
    results: list[AgentResultRecord]
    merge_finalization: MergeFinalizationRecord
    agent_tool_transcript: list[dict[str, Any]]
    policy_violations: list[str]
    budget_summary: dict[str, Any]
    failover_events: list[dict[str, Any]]
    cache_summary: dict[str, Any]
    tool_audit: list[dict[str, Any]]


class SupervisorOrchestrator:
    """Sequential C1 orchestration: plan -> execute -> merge -> finalize."""

    def __init__(self, *, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or build_default_agent_registry()

    def plan_agents(self, *, operator_input: str | None = None) -> SupervisorPlan:
        selected: list[str] = []
        required: list[str] = []
        optional: list[str] = []
        for agent_id in DEFAULT_EXECUTION_ORDER:
            agent = self.registry.get(agent_id)
            if agent and agent.is_enabled():
                selected.append(agent_id)
                if agent.participation == "optional":
                    optional.append(agent_id)
                else:
                    required.append(agent_id)
        finalizer = self.registry.require_enabled("finalizer")
        selected.append(finalizer.agent_id)
        required.append(finalizer.agent_id)
        return SupervisorPlan(
            selected_agents=selected,
            execution_order=selected,
            selection_reason=(
                "Deterministic C1 planning based on the canonical default execution order."
            ),
            required_agents=required,
            optional_agents=optional,
            finalize_strategy="finalizer_subagent",
            merge_strategy="deterministic_merge_payload_with_finalizer_primary",
            operator_input_summary=(operator_input or "")[:220],
        )

    def orchestrate(
        self,
        *,
        base_request: AdapterRequest,
        adapter: StoryAIAdapter,
        session: Any,
        module: Any,
        current_turn: int,
        recent_events: list[dict[str, Any]] | None,
        tool_registry: dict[str, Any] | None = None,
    ) -> SupervisorExecutionResult:
        policy = self.registry.supervisor_policy
        plan = self.plan_agents(operator_input=base_request.operator_input)
        invocations: list[AgentInvocationRecord] = []
        results: list[AgentResultRecord] = []
        tool_transcript: list[dict[str, Any]] = []
        policy_violations: list[str] = []
        parsed_decisions: dict[str, ParsedAIDecision] = {}
        failover_events: list[dict[str, Any]] = []
        tool_audit: list[dict[str, Any]] = []
        turn_cache = OrchestrationTurnCache(max_entries=24)
        started = perf_counter()
        consumed_agent_calls = 0
        consumed_tool_calls = 0
        failed_agent_calls = 0
        degraded_steps = 0
        consumed_token_proxy = 0
        consumed_total_tokens = 0
        exact_usage_count = 0
        proxy_fallback_count = 0
        shared_preview_feedback: list[dict[str, Any]] = []

        for agent_id in plan.execution_order:
            if agent_id == "finalizer":
                continue
            agent = self.registry.require_enabled(agent_id)
            sequence_index = len(invocations) + 1
            elapsed_ms = int((perf_counter() - started) * 1000)
            budget_block_reason = self._get_budget_block_reason(
                policy=policy,
                consumed_agent_calls=consumed_agent_calls,
                consumed_tool_calls=consumed_tool_calls,
                consumed_total_tokens=consumed_total_tokens,
                elapsed_ms=elapsed_ms,
            )
            if budget_block_reason:
                if agent.participation == "optional" and policy.skip_optional_agents_under_pressure:
                    degraded_steps += 1
                    failover_events.append(
                        {
                            "reason": "optional_agent_skipped_budget",
                            "agent_id": agent.agent_id,
                            "detail": budget_block_reason,
                        }
                    )
                    invocations.append(
                        self._build_skipped_invocation(
                            agent=agent,
                            sequence_index=sequence_index,
                            base_request=base_request,
                            reason="optional_agent_skipped_budget",
                        )
                    )
                    continue
                failover_events.append(
                    {
                        "reason": "turn_budget_exhausted",
                        "agent_id": agent.agent_id,
                        "detail": budget_block_reason,
                    }
                )
                break

            invocation, result, parsed = self._invoke_agent(
                agent=agent,
                sequence_index=sequence_index,
                base_request=base_request,
                adapter=adapter,
                session=session,
                module=module,
                current_turn=current_turn,
                recent_events=recent_events or [],
                tool_registry=tool_registry,
                turn_cache=turn_cache,
                shared_preview_feedback=shared_preview_feedback,
            )
            invocations.append(invocation)
            results.append(result)
            tool_transcript.extend(invocation.tool_call_transcript)
            policy_violations.extend(invocation.policy_violations)
            consumed_agent_calls += 1
            counted_tool_calls = 0
            for entry in invocation.tool_call_transcript:
                tool_status = str(entry.get("status", "unknown"))
                counted = tool_status == ToolCallStatus.SUCCESS or policy.consume_budget_on_failed_tool_call
                if counted:
                    counted_tool_calls += 1
                tool_audit.append(
                    {
                        "agent_id": agent.agent_id,
                        "tool_name": entry.get("tool_name"),
                        "duration_ms": int(entry.get("duration_ms", 0)),
                        "status": tool_status,
                        "counted_against_hard_limits": counted,
                        "cache_hit": bool(entry.get("cache_hit", False)),
                    }
                )
                if entry.get("tool_name") == "wos.guard.preview_delta":
                    preview_summary = entry.get("preview_result_summary")
                    if isinstance(preview_summary, dict):
                        shared_preview_feedback.append(
                            {
                                "request_id": entry.get("preview_request_id"),
                                "requesting_agent_id": entry.get("agent_id", agent.agent_id),
                                "sequence_index": entry.get("sequence_index"),
                                "result_summary": preview_summary,
                            }
                        )
            consumed_tool_calls += counted_tool_calls
            consumed_token_proxy += int(invocation.budget_consumed.get("token_proxy_units", 0))
            consumed_total_tokens += int(invocation.budget_consumed.get("consumed_total_tokens", 0))
            if invocation.budget_consumed.get("token_usage_mode") == "exact":
                exact_usage_count += 1
            else:
                proxy_fallback_count += 1
            failed = invocation.execution_status != "success"
            if failed:
                failed_agent_calls += 1
            if parsed is not None:
                parsed_decisions[agent.agent_id] = parsed
            if failed:
                if agent.participation == "optional" and policy.continue_after_optional_failure:
                    degraded_steps += 1
                    failover_events.append(
                        {
                            "reason": "optional_agent_failed_continue",
                            "agent_id": agent.agent_id,
                            "detail": invocation.error_summary or "agent_execution_failed",
                        }
                    )
                    continue
                failover_events.append(
                    {
                        "reason": "required_agent_failed_abort",
                        "agent_id": agent.agent_id,
                        "detail": invocation.error_summary or "agent_execution_failed",
                    }
                )
                break
            if failed_agent_calls > policy.max_failed_agent_calls:
                failover_events.append(
                    {
                        "reason": "failed_agent_call_budget_exhausted",
                        "agent_id": agent.agent_id,
                        "detail": f"failed_agent_calls={failed_agent_calls}",
                    }
                )
                break
            if degraded_steps > policy.max_degraded_steps:
                failover_events.append(
                    {
                        "reason": "degraded_steps_exhausted",
                        "agent_id": agent.agent_id,
                        "detail": f"degraded_steps={degraded_steps}",
                    }
                )
                break

        merged_decision, merge_record = self.merge_agent_results(parsed_decisions)
        finalizer_error: str | None = None
        try:
            finalizer_agent = self.registry.require_enabled("finalizer")
            elapsed_ms = int((perf_counter() - started) * 1000)
            finalizer_block_reason = self._get_budget_block_reason(
                policy=policy,
                consumed_agent_calls=consumed_agent_calls,
                consumed_tool_calls=consumed_tool_calls,
                consumed_total_tokens=consumed_total_tokens,
                elapsed_ms=elapsed_ms,
            )
            if finalizer_block_reason:
                failover_events.append(
                    {
                        "reason": "turn_budget_exhausted",
                        "agent_id": "finalizer",
                        "detail": finalizer_block_reason,
                    }
                )
                raise RuntimeError(finalizer_block_reason)
            finalizer_sequence = len(invocations) + 1
            (
                finalizer_invocation,
                finalizer_result,
                final_response,
                finalizer_fallback_used,
                finalizer_fallback_reason,
            ) = self.finalize_with_agent(
                finalizer_agent=finalizer_agent,
                sequence_index=finalizer_sequence,
                base_request=base_request,
                adapter=adapter,
                merged_decision=merged_decision,
                all_results=results,
                allow_fallback=policy.allow_finalizer_fallback,
            )
            invocations.append(finalizer_invocation)
            results.append(finalizer_result)
            consumed_agent_calls += 1
            consumed_token_proxy += int(
                finalizer_invocation.budget_consumed.get("token_proxy_units", 0)
            )
            consumed_total_tokens += int(
                finalizer_invocation.budget_consumed.get("consumed_total_tokens", 0)
            )
            if finalizer_invocation.budget_consumed.get("token_usage_mode") == "exact":
                exact_usage_count += 1
            else:
                proxy_fallback_count += 1
            merge_record.finalizer_agent_id = finalizer_agent.agent_id
            merge_record.finalizer_status = "fallback" if finalizer_fallback_used else "success"
            merge_record.fallback_used = finalizer_fallback_used
            merge_record.fallback_reason = finalizer_fallback_reason
            merge_record.final_output_source = (
                "deterministic_merge_fallback"
                if finalizer_fallback_used
                else finalizer_result.agent_id
            )
        except Exception as exc:  # pragma: no cover - defensive path
            finalizer_error = f"finalizer_unavailable_or_invalid: {exc}"
            merged_payload = self._build_merged_payload(merged_decision)
            final_response = AdapterResponse(
                raw_output="[supervisor finalizer unavailable fallback] using deterministic merged payload",
                structured_payload=merged_payload,
                backend_metadata={
                    "adapter": adapter.adapter_name,
                    "supervisor_finalizer_fallback": True,
                    "supervisor_finalizer_fallback_reason": finalizer_error,
                },
                error=None,
            )
            invocations.append(
                AgentInvocationRecord(
                    agent_id="finalizer",
                    role="finalizer",
                    invocation_sequence=len(invocations) + 1,
                    input_summary=(base_request.operator_input or "")[:200],
                    tool_policy_snapshot={
                        "allowed_tools": [],
                        "max_tool_calls": 0,
                        "per_tool_timeout_ms": 0,
                    },
                    model_profile="default",
                    adapter_name=adapter.adapter_name,
                    execution_status="error",
                    duration_ms=0,
                    budget_consumed={
                        "tool_calls": 0,
                        "token_proxy_units": 0,
                        "consumed_total_tokens": 0,
                        "token_usage_mode": "proxy",
                    },
                    token_usage=TokenUsageRecord(total_tokens=0, usage_mode="proxy"),
                    error_summary=finalizer_error,
                    tool_call_transcript=[],
                    policy_violations=[],
                )
            )
            results.append(
                AgentResultRecord(
                    agent_id="finalizer",
                    payload=merged_payload,
                    confidence="low",
                    bounded_summary="Deterministic merge payload used because finalizer could not run.",
                    result_shape="finalizer_fallback_payload",
                )
            )
            merge_record.finalizer_agent_id = "finalizer"
            merge_record.finalizer_status = "fallback"
            merge_record.fallback_used = True
            merge_record.fallback_reason = finalizer_error
            merge_record.final_output_source = "deterministic_merge_fallback"
            failover_events.append(
                {
                    "reason": "finalizer_failed_deterministic_merge_fallback",
                    "agent_id": "finalizer",
                    "detail": finalizer_error,
                }
            )

        if merge_record.fallback_used and not merge_record.fallback_reason and finalizer_error:
            merge_record.fallback_reason = finalizer_error
        merge_record.policy_violations = policy_violations
        elapsed_total_ms = int((perf_counter() - started) * 1000)
        budget_summary = {
            "configured": {
                "max_turn_duration_ms": policy.max_turn_duration_ms,
                "max_total_agent_calls": policy.max_total_agent_calls,
                "max_total_tool_calls": policy.max_total_tool_calls,
                "max_total_tokens": policy.max_total_tokens,
                "max_failed_agent_calls": policy.max_failed_agent_calls,
                "max_degraded_steps": policy.max_degraded_steps,
            },
            "consumed": {
                "turn_duration_ms": elapsed_total_ms,
                "total_agent_calls": consumed_agent_calls,
                "total_tool_calls": consumed_tool_calls,
                "token_proxy_units": consumed_token_proxy,
                "consumed_total_tokens": consumed_total_tokens,
                "token_usage_mode": self._aggregate_usage_mode(
                    exact_usage_count=exact_usage_count,
                    proxy_fallback_count=proxy_fallback_count,
                ),
                "proxy_fallback_count": proxy_fallback_count,
                "failed_agent_calls": failed_agent_calls,
                "degraded_steps": degraded_steps,
            },
            "limit_hit": bool(failover_events),
        }
        return SupervisorExecutionResult(
            final_response=final_response,
            plan=plan,
            invocations=invocations,
            results=results,
            merge_finalization=merge_record,
            agent_tool_transcript=tool_transcript,
            policy_violations=policy_violations,
            budget_summary=budget_summary,
            failover_events=failover_events,
            cache_summary=turn_cache.summary(),
            tool_audit=tool_audit,
        )

    def _invoke_agent(
        self,
        *,
        agent: AgentConfig,
        sequence_index: int,
        base_request: AdapterRequest,
        adapter: StoryAIAdapter,
        session: Any,
        module: Any,
        current_turn: int,
        recent_events: list[dict[str, Any]],
        tool_registry: dict[str, Any] | None,
        turn_cache: OrchestrationTurnCache,
        shared_preview_feedback: list[dict[str, Any]],
    ) -> tuple[AgentInvocationRecord, AgentResultRecord, ParsedAIDecision | None]:
        request = self._build_agent_request(
            base_request=base_request,
            agent=agent,
            sequence_index=sequence_index,
            tool_results=[],
            cross_agent_preview_feedback=shared_preview_feedback,
        )
        started = perf_counter()
        response = generate_with_timeout(
            adapter=adapter,
            request=request,
            timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
        )
        retry_count = 0
        tool_call_transcript: list[dict[str, Any]] = []
        policy_violations: list[str] = []
        tool_results: list[dict[str, Any]] = []
        max_tool_calls = max(agent.budget_profile.max_tool_calls, 0)

        tool_context = HostToolContext(
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events,
        )
        tool_policy = ToolLoopPolicy(
            enabled=max_tool_calls > 0,
            allowed_tools=list(agent.allowed_tools),
            max_tool_calls_per_turn=max_tool_calls,
            per_tool_timeout_ms=agent.budget_profile.per_tool_timeout_ms,
            max_retries_per_tool_call=agent.budget_profile.max_retries_per_tool_call,
        )
        tool_calls = 0
        while tool_policy.enabled and tool_calls < tool_policy.max_tool_calls_per_turn:
            tool_request = detect_tool_request_payload(
                response.structured_payload,
                sequence_index=tool_calls + 1,
            )
            if tool_request is None:
                break
            cache_key: str | None = None
            if self._is_cacheable_tool(tool_request.tool_name):
                cache_key = OrchestrationTurnCache.make_tool_key(
                    tool_request.tool_name,
                    tool_request.arguments,
                )
                cached = turn_cache.get(cache_key)
                if cached is not None:
                    entry = ToolCallTranscriptEntry(
                        sequence_index=tool_request.sequence_index,
                        tool_name=tool_request.tool_name,
                        sanitized_arguments={},
                        status=ToolCallStatus.SUCCESS,
                        attempts=1,
                        duration_ms=0,
                        result_summary="cache_hit",
                    )
                    tool_result = {
                        "request_id": tool_request.request_id,
                        "sequence_index": tool_request.sequence_index,
                        "tool_name": tool_request.tool_name,
                        "status": ToolCallStatus.SUCCESS,
                        "result": cached.get("result"),
                        "cache_hit": True,
                    }
                else:
                    entry, tool_result = execute_tool_request(
                        tool_request,
                        policy=tool_policy,
                        context=tool_context,
                        registry=tool_registry,
                    )
                    if (
                        entry.status == ToolCallStatus.SUCCESS
                        and isinstance(tool_result.get("result"), dict)
                    ):
                        turn_cache.put(cache_key, {"result": tool_result.get("result")})
            else:
                turn_cache.mark_bypass()
                entry, tool_result = execute_tool_request(
                    tool_request,
                    policy=tool_policy,
                    context=tool_context,
                    registry=tool_registry,
                )
            entry_dict = entry.model_dump()
            entry_dict["agent_id"] = agent.agent_id
            if tool_result.get("cache_hit"):
                entry_dict["cache_hit"] = True
            if tool_request.tool_name == "wos.guard.preview_delta":
                entry_dict["preview_request_id"] = tool_result.get("request_id")
                result_payload = tool_result.get("result")
                if isinstance(result_payload, dict):
                    entry_dict["preview_result_summary"] = {
                        "preview_allowed": bool(result_payload.get("preview_allowed", False)),
                        "guard_outcome": result_payload.get("guard_outcome"),
                        "accepted_delta_count": int(
                            result_payload.get("accepted_delta_count", 0)
                        ),
                        "rejected_delta_count": int(
                            result_payload.get("rejected_delta_count", 0)
                        ),
                        "partial_acceptance": bool(
                            result_payload.get("partial_acceptance", False)
                        ),
                        "rejection_reasons": list(
                            (result_payload.get("rejection_reasons") or [])[:5]
                        ),
                        "suggested_corrections": list(
                            (result_payload.get("suggested_corrections") or [])[:5]
                        ),
                        "input_targets": list((result_payload.get("input_targets") or [])[:20]),
                        "summary": result_payload.get("summary"),
                        "preview_safe_no_write": bool(
                            result_payload.get("preview_safe_no_write", True)
                        ),
                    }
            tool_call_transcript.append(entry_dict)
            tool_results.append(tool_result)
            if entry.status == ToolCallStatus.REJECTED:
                policy_violations.append(
                    f"{agent.agent_id}:{tool_result.get('error', 'tool_rejected')}"
                )
                break
            if entry.status != ToolCallStatus.SUCCESS:
                break
            tool_calls += 1
            request = self._build_agent_request(
                base_request=base_request,
                agent=agent,
                sequence_index=sequence_index,
                tool_results=tool_results,
                cross_agent_preview_feedback=shared_preview_feedback,
            )
            response = generate_with_timeout(
                adapter=adapter,
                request=request,
                timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
            )

        duration_ms = int((perf_counter() - started) * 1000)
        parse_result = process_adapter_response(response)
        while (
            not parse_result.success
            and retry_count < max(agent.budget_profile.max_attempts - 1, 0)
        ):
            retry_count += 1
            response = generate_with_timeout(
                adapter=adapter,
                request=request,
                timeout_ms=max(agent.budget_profile.max_agent_duration_ms, 1),
            )
            parse_result = process_adapter_response(response)
        status = "success" if parse_result.success else "error"
        error_summary = "; ".join(parse_result.errors) if parse_result.errors else None
        result_payload = response.structured_payload if isinstance(response.structured_payload, dict) else {}
        token_consumed, token_usage = self._build_token_consumption(response)
        if duration_ms > agent.budget_profile.max_agent_duration_ms:
            status = "error"
            extra = (
                f"agent_duration_budget_exhausted:{duration_ms}>{agent.budget_profile.max_agent_duration_ms}"
            )
            error_summary = f"{error_summary}; {extra}" if error_summary else extra
        max_agent_tokens = max(agent.budget_profile.max_agent_tokens, 0)
        if max_agent_tokens > 0 and int(token_consumed.get("consumed_total_tokens", 0)) > max_agent_tokens:
            status = "error"
            extra = (
                "agent_token_budget_exhausted:"
                f"{int(token_consumed.get('consumed_total_tokens', 0))}>{max_agent_tokens}"
            )
            error_summary = f"{error_summary}; {extra}" if error_summary else extra
            policy_violations.append(f"{agent.agent_id}:{extra}")
        bounded_summary = (
            parse_result.decision.scene_interpretation[:200]
            if parse_result.success and parse_result.decision
            else (response.raw_output or "")[:200]
        )
        invocation = AgentInvocationRecord(
            agent_id=agent.agent_id,
            role=agent.role,
            invocation_sequence=sequence_index,
            input_summary=(request.operator_input or "")[:200],
            tool_policy_snapshot={
                "allowed_tools": list(agent.allowed_tools),
                "max_tool_calls": agent.budget_profile.max_tool_calls,
                "per_tool_timeout_ms": agent.budget_profile.per_tool_timeout_ms,
            },
            model_profile=agent.model_selection.model_profile,
            adapter_name=(agent.model_selection.adapter_name or adapter.adapter_name),
            execution_status=status,
            duration_ms=duration_ms,
            retry_count=retry_count,
            budget_snapshot={
                "max_attempts": agent.budget_profile.max_attempts,
                "max_tool_calls": agent.budget_profile.max_tool_calls,
                "max_agent_duration_ms": agent.budget_profile.max_agent_duration_ms,
                "max_agent_tokens": agent.budget_profile.max_agent_tokens,
            },
            budget_consumed={
                "tool_calls": len(tool_call_transcript),
                **token_consumed,
            },
            token_usage=token_usage,
            error_summary=error_summary,
            tool_call_transcript=tool_call_transcript,
            policy_violations=policy_violations,
        )
        result = AgentResultRecord(
            agent_id=agent.agent_id,
            payload=result_payload,
            confidence="high" if parse_result.success else "low",
            bounded_summary=bounded_summary,
            result_shape="parsed_decision" if parse_result.success else "unparsed_payload",
        )
        return invocation, result, parse_result.decision if parse_result.success else None

    def merge_agent_results(
        self,
        parsed_decisions: dict[str, ParsedAIDecision],
    ) -> tuple[ParsedAIDecision, MergeFinalizationRecord]:
        preferred_order = ["delta_planner", "trigger_analyst", "scene_reader", "dialogue_planner"]
        used_sources: list[str] = []
        ignored_sources: list[str] = []
        chosen: ParsedAIDecision | None = None
        for agent_id in preferred_order:
            decision = parsed_decisions.get(agent_id)
            if decision is None:
                continue
            if chosen is None and decision.proposed_deltas:
                chosen = decision
                used_sources.append(agent_id)
            else:
                ignored_sources.append(agent_id)
        if chosen is None:
            for agent_id in preferred_order:
                decision = parsed_decisions.get(agent_id)
                if decision is None:
                    continue
                chosen = decision
                used_sources.append(agent_id)
                break
        if chosen is None:
            chosen = ParsedAIDecision(
                scene_interpretation="",
                detected_triggers=[],
                proposed_deltas=[],
                proposed_scene_id=None,
                rationale="No valid subagent decision available.",
                raw_output="",
                parsed_source="supervisor_merge_fallback",
            )
        conflict_notes: list[str] = []
        if len(parsed_decisions) > 1:
            conflict_notes.append(
                "Deterministic merge preferred delta_planner, then trigger_analyst, scene_reader, dialogue_planner."
            )
        merge_record = MergeFinalizationRecord(
            used_agent_outputs=used_sources,
            ignored_agent_outputs=ignored_sources,
            downgraded_agent_outputs=[],
            conflict_notes=conflict_notes,
            selection_reason=(
                "Prepared deterministic merge payload for finalizer context. "
                "This payload is not the canonical finalization path unless finalizer fallback is required."
            ),
            final_output_source="pending_finalizer",
            finalizer_agent_id=None,
            finalizer_status="success",
            fallback_used=False,
            fallback_reason=None,
            policy_violations=[],
        )
        return chosen, merge_record

    def finalize_with_agent(
        self,
        *,
        finalizer_agent: AgentConfig,
        sequence_index: int,
        base_request: AdapterRequest,
        adapter: StoryAIAdapter,
        merged_decision: ParsedAIDecision,
        all_results: list[AgentResultRecord],
        allow_fallback: bool,
    ) -> tuple[AgentInvocationRecord, AgentResultRecord, AdapterResponse, bool, str | None]:
        merged_payload = self._build_merged_payload(merged_decision)
        finalizer_request = self._build_agent_request(
            base_request=base_request,
            agent=finalizer_agent,
            sequence_index=sequence_index,
            tool_results=[],
        )
        finalizer_request.metadata["supervisor_merge_payload"] = merged_payload
        finalizer_request.metadata["supervisor_subagent_result_summaries"] = [
            {"agent_id": item.agent_id, "summary": item.bounded_summary}
            for item in all_results
        ]

        started = perf_counter()
        final_response = generate_with_timeout(
            adapter=adapter,
            request=finalizer_request,
            timeout_ms=max(finalizer_agent.budget_profile.max_agent_duration_ms, 1),
        )
        parse_result = process_adapter_response(final_response)
        duration_ms = int((perf_counter() - started) * 1000)
        finalizer_fallback_used = False
        finalizer_fallback_reason: str | None = None
        if not parse_result.success:
            if not allow_fallback:
                raise RuntimeError("finalizer_failed_no_fallback")
            finalizer_fallback_used = True
            reason = "; ".join(parse_result.errors) if parse_result.errors else "finalizer_parse_failed"
            finalizer_fallback_reason = f"finalizer_unavailable_or_invalid: {reason}"
            fallback_raw = "[supervisor finalizer fallback] using deterministic merged payload"
            final_response = AdapterResponse(
                raw_output=fallback_raw,
                structured_payload=merged_payload,
                backend_metadata={
                    "adapter": adapter.adapter_name,
                    "supervisor_finalizer_fallback": True,
                    "supervisor_finalizer_fallback_reason": finalizer_fallback_reason,
                },
                error=None,
            )
            parse_result = process_adapter_response(final_response)

        token_consumed, token_usage = self._build_token_consumption(final_response)
        max_agent_tokens = max(finalizer_agent.budget_profile.max_agent_tokens, 0)
        if max_agent_tokens > 0 and int(token_consumed.get("consumed_total_tokens", 0)) > max_agent_tokens:
            reason = (
                "agent_token_budget_exhausted:"
                f"{int(token_consumed.get('consumed_total_tokens', 0))}>{max_agent_tokens}"
            )
            if not allow_fallback:
                raise RuntimeError(reason)
            finalizer_fallback_used = True
            finalizer_fallback_reason = f"finalizer_unavailable_or_invalid: {reason}"
            final_response = AdapterResponse(
                raw_output="[supervisor finalizer fallback] using deterministic merged payload",
                structured_payload=merged_payload,
                backend_metadata={
                    "adapter": adapter.adapter_name,
                    "supervisor_finalizer_fallback": True,
                    "supervisor_finalizer_fallback_reason": finalizer_fallback_reason,
                },
                error=None,
            )
            parse_result = process_adapter_response(final_response)
            token_consumed, token_usage = self._build_token_consumption(final_response)
        invocation = AgentInvocationRecord(
            agent_id=finalizer_agent.agent_id,
            role=finalizer_agent.role,
            invocation_sequence=sequence_index,
            input_summary=(finalizer_request.operator_input or "")[:200],
            tool_policy_snapshot={
                "allowed_tools": [],
                "max_tool_calls": 0,
                "per_tool_timeout_ms": finalizer_agent.budget_profile.per_tool_timeout_ms,
            },
            model_profile=finalizer_agent.model_selection.model_profile,
            adapter_name=(finalizer_agent.model_selection.adapter_name or adapter.adapter_name),
            execution_status="success" if parse_result.success else "error",
            duration_ms=duration_ms,
            retry_count=0,
            budget_snapshot={
                "max_attempts": finalizer_agent.budget_profile.max_attempts,
                "max_tool_calls": 0,
                "max_agent_duration_ms": finalizer_agent.budget_profile.max_agent_duration_ms,
                "max_agent_tokens": finalizer_agent.budget_profile.max_agent_tokens,
            },
            budget_consumed={"tool_calls": 0, **token_consumed},
            token_usage=token_usage,
            error_summary="; ".join(parse_result.errors) if parse_result.errors else None,
            tool_call_transcript=[],
            policy_violations=[],
        )
        if finalizer_fallback_reason:
            invocation.error_summary = finalizer_fallback_reason
        result = AgentResultRecord(
            agent_id=finalizer_agent.agent_id,
            payload=final_response.structured_payload or {},
            confidence="low" if finalizer_fallback_used else ("high" if parse_result.success else "low"),
            bounded_summary=(
                "Deterministic merge payload used because finalizer produced no valid decision."
                if finalizer_fallback_used
                else (
                    parse_result.decision.rationale[:220]
                    if parse_result.success and parse_result.decision
                    else final_response.raw_output[:220]
                )
            ),
            result_shape=(
                "finalizer_fallback_payload"
                if finalizer_fallback_used
                else "finalized_decision"
            ),
        )
        return (
            invocation,
            result,
            final_response,
            finalizer_fallback_used,
            finalizer_fallback_reason,
        )

    def _build_merged_payload(self, merged_decision: ParsedAIDecision) -> dict[str, Any]:
        return {
            "scene_interpretation": merged_decision.scene_interpretation,
            "detected_triggers": list(merged_decision.detected_triggers or []),
            "proposed_state_deltas": [
                delta.model_dump(mode="json")
                for delta in (merged_decision.proposed_deltas or [])
            ],
            "proposed_scene_id": merged_decision.proposed_scene_id,
            "rationale": merged_decision.rationale,
        }

    def _get_budget_block_reason(
        self,
        *,
        policy: SupervisorTurnPolicy,
        consumed_agent_calls: int,
        consumed_tool_calls: int,
        consumed_total_tokens: int,
        elapsed_ms: int,
    ) -> str | None:
        if elapsed_ms >= policy.max_turn_duration_ms:
            return f"turn_duration_limit:{elapsed_ms}>={policy.max_turn_duration_ms}"
        if consumed_agent_calls >= policy.max_total_agent_calls:
            return f"agent_call_limit:{consumed_agent_calls}>={policy.max_total_agent_calls}"
        if consumed_tool_calls >= policy.max_total_tool_calls:
            return f"tool_call_limit:{consumed_tool_calls}>={policy.max_total_tool_calls}"
        if policy.max_total_tokens > 0 and consumed_total_tokens >= policy.max_total_tokens:
            return f"token_limit:{consumed_total_tokens}>={policy.max_total_tokens}"
        return None

    def _build_skipped_invocation(
        self,
        *,
        agent: AgentConfig,
        sequence_index: int,
        base_request: AdapterRequest,
        reason: str,
    ) -> AgentInvocationRecord:
        return AgentInvocationRecord(
            agent_id=agent.agent_id,
            role=agent.role,
            invocation_sequence=sequence_index,
            input_summary=(base_request.operator_input or "")[:200],
            tool_policy_snapshot={
                "allowed_tools": list(agent.allowed_tools),
                "max_tool_calls": agent.budget_profile.max_tool_calls,
                "per_tool_timeout_ms": agent.budget_profile.per_tool_timeout_ms,
            },
            model_profile=agent.model_selection.model_profile,
            adapter_name=agent.model_selection.adapter_name or "default",
            execution_status="skipped",
            duration_ms=0,
            retry_count=0,
            budget_snapshot={
                "max_attempts": agent.budget_profile.max_attempts,
                "max_tool_calls": agent.budget_profile.max_tool_calls,
                "max_agent_duration_ms": agent.budget_profile.max_agent_duration_ms,
                "max_agent_tokens": agent.budget_profile.max_agent_tokens,
            },
            budget_consumed={
                "tool_calls": 0,
                "token_proxy_units": 0,
                "consumed_total_tokens": 0,
                "token_usage_mode": "proxy",
            },
            token_usage=TokenUsageRecord(total_tokens=0, usage_mode="proxy"),
            failover_reason=reason,
            tool_call_transcript=[],
            policy_violations=[],
        )

    def _is_cacheable_tool(self, tool_name: str) -> bool:
        return tool_name.startswith("wos.read.")

    def _token_proxy_units(self, response: AdapterResponse) -> int:
        payload = response.raw_output or ""
        if not payload:
            return 0
        return len(payload.split())

    def _build_token_consumption(
        self,
        response: AdapterResponse,
    ) -> tuple[dict[str, Any], TokenUsageRecord]:
        proxy_units = self._token_proxy_units(response)
        normalized_usage = normalize_token_usage(response)
        if normalized_usage is not None:
            consumed_total_tokens = int(normalized_usage.total_tokens)
            mode = "exact"
            token_usage = normalized_usage
        else:
            consumed_total_tokens = proxy_units
            mode = "proxy"
            metadata = response.backend_metadata if isinstance(response.backend_metadata, dict) else {}
            token_usage = TokenUsageRecord(
                total_tokens=proxy_units,
                provider_name=metadata.get("provider_name", metadata.get("provider")),
                model_name=metadata.get("model_name", metadata.get("model")),
                usage_mode="proxy",
            )

        return (
            {
                "token_proxy_units": proxy_units,
                "consumed_total_tokens": consumed_total_tokens,
                "token_usage_mode": mode,
            },
            token_usage,
        )

    def _aggregate_usage_mode(self, *, exact_usage_count: int, proxy_fallback_count: int) -> str:
        if exact_usage_count > 0 and proxy_fallback_count > 0:
            return "mixed"
        if exact_usage_count > 0:
            return "exact"
        return "proxy"

    def _build_agent_request(
        self,
        *,
        base_request: AdapterRequest,
        agent: AgentConfig,
        sequence_index: int,
        tool_results: list[dict[str, Any]],
        cross_agent_preview_feedback: list[dict[str, Any]] | None = None,
    ) -> AdapterRequest:
        metadata = dict(base_request.metadata)
        metadata["agent_invocation"] = {
            "agent_id": agent.agent_id,
            "role": agent.role,
            "sequence_index": sequence_index,
            "model_profile": agent.model_selection.model_profile,
            "execution_mode": agent.execution_mode,
        }
        metadata["tool_loop"] = {
            "enabled": agent.budget_profile.max_tool_calls > 0,
            "allowed_tools": list(agent.allowed_tools),
            "max_tool_calls_per_turn": agent.budget_profile.max_tool_calls,
            "per_tool_timeout_ms": agent.budget_profile.per_tool_timeout_ms,
            "max_retries_per_tool_call": agent.budget_profile.max_retries_per_tool_call,
            "tool_results": tool_results[-agent.budget_profile.max_tool_calls :],
        }
        if cross_agent_preview_feedback:
            metadata["cross_agent_preview_feedback"] = list(cross_agent_preview_feedback[-5:])
        return AdapterRequest(
            session_id=base_request.session_id,
            turn_number=base_request.turn_number,
            current_scene_id=base_request.current_scene_id,
            canonical_state=base_request.canonical_state,
            recent_events=list(base_request.recent_events),
            operator_input=base_request.operator_input,
            input_interpretation=base_request.input_interpretation,
            request_role_structured_output=base_request.request_role_structured_output,
            metadata=metadata,
        )
