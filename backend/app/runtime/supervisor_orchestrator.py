"""C1 supervisor orchestrator with real bounded subagent invocations."""

from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Any

from app.runtime.agent_registry import (
    AgentConfig,
    AgentRegistry,
    build_default_agent_registry,
)
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.ai_decision import ParsedAIDecision, process_adapter_response
from app.runtime.tool_loop import (
    HostToolContext,
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


class SupervisorOrchestrator:
    """Sequential C1 orchestration: plan -> execute -> merge -> finalize."""

    def __init__(self, *, registry: AgentRegistry | None = None) -> None:
        self.registry = registry or build_default_agent_registry()

    def plan_agents(self, *, operator_input: str | None = None) -> SupervisorPlan:
        selected: list[str] = []
        required: list[str] = []
        for agent_id in DEFAULT_EXECUTION_ORDER:
            agent = self.registry.get(agent_id)
            if agent and agent.is_enabled():
                selected.append(agent_id)
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
            optional_agents=[],
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
        plan = self.plan_agents(operator_input=base_request.operator_input)
        invocations: list[AgentInvocationRecord] = []
        results: list[AgentResultRecord] = []
        tool_transcript: list[dict[str, Any]] = []
        policy_violations: list[str] = []
        parsed_decisions: dict[str, ParsedAIDecision] = {}

        for sequence_index, agent_id in enumerate(plan.execution_order, start=1):
            if agent_id == "finalizer":
                continue
            agent = self.registry.require_enabled(agent_id)
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
            )
            invocations.append(invocation)
            results.append(result)
            tool_transcript.extend(invocation.tool_call_transcript)
            policy_violations.extend(invocation.policy_violations)
            if parsed is not None:
                parsed_decisions[agent.agent_id] = parsed

        merged_decision, merge_record = self.merge_agent_results(parsed_decisions)
        finalizer_error: str | None = None
        try:
            finalizer_agent = self.registry.require_enabled("finalizer")
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
            )
            invocations.append(finalizer_invocation)
            results.append(finalizer_result)
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

        if merge_record.fallback_used and not merge_record.fallback_reason and finalizer_error:
            merge_record.fallback_reason = finalizer_error
        merge_record.policy_violations = policy_violations
        return SupervisorExecutionResult(
            final_response=final_response,
            plan=plan,
            invocations=invocations,
            results=results,
            merge_finalization=merge_record,
            agent_tool_transcript=tool_transcript,
            policy_violations=policy_violations,
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
    ) -> tuple[AgentInvocationRecord, AgentResultRecord, ParsedAIDecision | None]:
        request = self._build_agent_request(
            base_request=base_request,
            agent=agent,
            sequence_index=sequence_index,
            tool_results=[],
        )
        started = perf_counter()
        response = adapter.generate(request)
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
            entry, tool_result = execute_tool_request(
                tool_request,
                policy=tool_policy,
                context=tool_context,
                registry=tool_registry,
            )
            entry_dict = entry.model_dump()
            entry_dict["agent_id"] = agent.agent_id
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
            )
            response = adapter.generate(request)

        duration_ms = int((perf_counter() - started) * 1000)
        parse_result = process_adapter_response(response)
        status = "success" if parse_result.success else "error"
        error_summary = "; ".join(parse_result.errors) if parse_result.errors else None
        result_payload = response.structured_payload if isinstance(response.structured_payload, dict) else {}
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
        final_response = adapter.generate(finalizer_request)
        parse_result = process_adapter_response(final_response)
        duration_ms = int((perf_counter() - started) * 1000)
        finalizer_fallback_used = False
        finalizer_fallback_reason: str | None = None
        if not parse_result.success:
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
            error_summary="; ".join(parse_result.errors) if parse_result.errors else None,
            tool_call_transcript=[],
            policy_violations=[],
        )
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

    def _build_agent_request(
        self,
        *,
        base_request: AdapterRequest,
        agent: AgentConfig,
        sequence_index: int,
        tool_results: list[dict[str, Any]],
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
        return AdapterRequest(
            session_id=base_request.session_id,
            turn_number=base_request.turn_number,
            current_scene_id=base_request.current_scene_id,
            canonical_state=base_request.canonical_state,
            recent_events=list(base_request.recent_events),
            operator_input=base_request.operator_input,
            request_role_structured_output=base_request.request_role_structured_output,
            metadata=metadata,
        )
