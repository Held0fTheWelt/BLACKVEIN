"""C1 supervisor orchestrator with real bounded subagent invocations."""

from __future__ import annotations

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
from app.runtime.supervisor_execution_types import SupervisorExecutionResult
from app.runtime.supervisor_invoke_agent import invoke_supervisor_agent
from app.runtime.supervisor_orchestrate_execute import execute_supervisor_orchestration
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
        return execute_supervisor_orchestration(
            self,
            base_request=base_request,
            adapter=adapter,
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events,
            tool_registry=tool_registry,
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
        return invoke_supervisor_agent(
            self,
            agent=agent,
            sequence_index=sequence_index,
            base_request=base_request,
            adapter=adapter,
            session=session,
            module=module,
            current_turn=current_turn,
            recent_events=recent_events,
            tool_registry=tool_registry,
            turn_cache=turn_cache,
            shared_preview_feedback=shared_preview_feedback,
        )

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
