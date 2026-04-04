"""Tests for C1 supervisor orchestrator."""

from __future__ import annotations

import time
from typing import Any

from app.runtime.agent_registry import (
    AgentBudgetProfile,
    AgentConfig,
    AgentRegistry,
    SupervisorTurnPolicy,
    build_default_agent_registry,
)
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.supervisor_orchestrator import SupervisorOrchestrator


class RecordingSupervisorAdapter(StoryAIAdapter):
    """Deterministic adapter that records every subagent invocation."""

    def __init__(self, *, force_forbidden_scene_tool: bool = False) -> None:
        self.calls: list[str] = []
        self.force_forbidden_scene_tool = force_forbidden_scene_tool
        self.force_invalid_finalizer_payload = False

    @property
    def adapter_name(self) -> str:
        return "recording-supervisor"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        invocation = request.metadata.get("agent_invocation") or {}
        agent_id = invocation.get("agent_id", "unknown")
        self.calls.append(agent_id)
        tool_loop_meta = request.metadata.get("tool_loop") or {}
        tool_results = tool_loop_meta.get("tool_results") or []

        if agent_id == "scene_reader":
            if self.force_forbidden_scene_tool:
                return AdapterResponse(
                    raw_output="[scene_reader forbidden tool request]",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.guard.preview_delta",
                        "arguments": {},
                    },
                )
            if not tool_results:
                return AdapterResponse(
                    raw_output="[scene_reader request context tool]",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.read.current_scene",
                        "arguments": {},
                    },
                )
            return AdapterResponse(
                raw_output="[scene_reader final]",
                structured_payload={
                    "scene_interpretation": "Scene reader summary",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": "Scene context available",
                },
            )

        if agent_id == "trigger_analyst":
            return AdapterResponse(
                raw_output="[trigger_analyst]",
                structured_payload={
                    "scene_interpretation": "Trigger analyst summary",
                    "detected_triggers": ["trigger_a"],
                    "proposed_state_deltas": [],
                    "rationale": "Trigger pressure detected",
                },
            )

        if agent_id == "delta_planner":
            return AdapterResponse(
                raw_output="[delta_planner]",
                structured_payload={
                    "scene_interpretation": "Delta planner summary",
                    "detected_triggers": ["trigger_a"],
                    "proposed_state_deltas": [
                        {
                            "target_path": "characters.veronique.emotional_state",
                            "next_value": 71,
                            "delta_type": "state_update",
                            "rationale": "Escalating tension",
                        }
                    ],
                    "rationale": "Proposes one bounded state update",
                },
            )

        if agent_id == "dialogue_planner":
            return AdapterResponse(
                raw_output="[dialogue_planner]",
                structured_payload={
                    "scene_interpretation": "Dialogue planning hints",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": "Supports final response wording",
                },
            )

        if agent_id == "finalizer":
            if self.force_invalid_finalizer_payload:
                return AdapterResponse(
                    raw_output="[finalizer invalid]",
                    structured_payload={"not": "a_valid_decision_payload"},
                )
            merge_payload = request.metadata.get("supervisor_merge_payload") or {}
            merged = dict(merge_payload)
            merged["rationale"] = "Finalizer merged subagent outputs."
            return AdapterResponse(
                raw_output="[finalizer]",
                structured_payload=merged,
            )

        return AdapterResponse(raw_output="[unknown]", structured_payload={})


class UsageAwareSupervisorAdapter(StoryAIAdapter):
    """Adapter that emits exact usage for selected agents."""

    def __init__(self, exact_agents: set[str] | None = None) -> None:
        self.exact_agents = exact_agents or set()

    @property
    def adapter_name(self) -> str:
        return "usage-aware-supervisor"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
        payload = {
            "scene_interpretation": f"{agent_id} summary",
            "detected_triggers": [],
            "proposed_state_deltas": [],
            "rationale": f"{agent_id} rationale",
        }
        if agent_id == "finalizer":
            merged = dict(request.metadata.get("supervisor_merge_payload") or {})
            merged["rationale"] = "finalized"
            payload = merged

        backend_metadata: dict[str, Any] = {}
        if agent_id in self.exact_agents:
            backend_metadata = {
                "provider": "test-provider",
                "model": "test-model",
                "usage": {
                    "input_tokens": 20,
                    "output_tokens": 10,
                    "total_tokens": 30,
                },
            }
        return AdapterResponse(
            raw_output=f"[{agent_id}]",
            structured_payload=payload,
            backend_metadata=backend_metadata,
        )


def _build_base_request(session: Any) -> AdapterRequest:
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter + 1,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=[],
        operator_input="operator test input",
        request_role_structured_output=True,
        metadata={},
    )


def test_supervisor_plan_is_deterministic(god_of_carnage_module_with_state):
    orchestrator = SupervisorOrchestrator()

    plan = orchestrator.plan_agents(operator_input="test")

    assert plan.execution_order[-1] == "finalizer"
    assert plan.selected_agents == plan.execution_order
    assert len(plan.selected_agents) >= 3


def test_orchestrator_executes_multiple_real_subagent_invocations(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = RecordingSupervisorAdapter()
    orchestrator = SupervisorOrchestrator()
    base_request = _build_base_request(session)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert len(adapter.calls) >= 3
    assert "scene_reader" in adapter.calls
    assert "trigger_analyst" in adapter.calls
    assert "finalizer" in adapter.calls
    assert outcome.plan.execution_order[-1] == "finalizer"
    assert len(outcome.invocations) >= 3
    assert outcome.results[-1].agent_id == "finalizer"
    assert outcome.final_response.structured_payload is not None
    assert "rationale" in outcome.final_response.structured_payload


def test_orchestrator_logs_policy_violations_for_forbidden_tools(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = RecordingSupervisorAdapter(force_forbidden_scene_tool=True)
    base_request = _build_base_request(session)
    registry = build_default_agent_registry()

    scene_reader = registry.require_enabled("scene_reader").model_copy(deep=True)
    scene_reader.allowed_tools = []
    custom_registry = AgentRegistry(
        agents=[
            scene_reader,
            registry.require_enabled("trigger_analyst"),
            registry.require_enabled("delta_planner"),
            registry.require_enabled("dialogue_planner"),
            registry.require_enabled("finalizer"),
        ]
    )
    orchestrator = SupervisorOrchestrator(registry=custom_registry)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert outcome.policy_violations
    assert any("scene_reader" in item for item in outcome.policy_violations)
    assert outcome.invocations[0].policy_violations


def test_orchestrator_marks_deterministic_fallback_when_finalizer_output_is_invalid(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = RecordingSupervisorAdapter()
    adapter.force_invalid_finalizer_payload = True
    orchestrator = SupervisorOrchestrator()
    base_request = _build_base_request(session)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert outcome.plan.execution_order[-1] == "finalizer"
    assert outcome.results[-1].agent_id == "finalizer"
    assert outcome.merge_finalization.fallback_used is True
    assert outcome.merge_finalization.finalizer_status == "fallback"
    assert outcome.merge_finalization.final_output_source == "deterministic_merge_fallback"
    assert outcome.merge_finalization.fallback_reason is not None


def test_orchestrator_skips_optional_agent_under_budget_pressure(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = RecordingSupervisorAdapter()
    base_request = _build_base_request(session)

    custom_registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                allowed_tools=["wos.read.current_scene"],
                budget_profile=AgentBudgetProfile(max_tool_calls=1),
                participation="required",
            ),
            AgentConfig(
                agent_id="dialogue_planner",
                role="dialogue_planner",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
                participation="optional",
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
                participation="required",
            ),
        ],
        supervisor_policy=SupervisorTurnPolicy(
            max_total_agent_calls=1,
            skip_optional_agents_under_pressure=True,
            continue_after_optional_failure=True,
        ),
    )
    orchestrator = SupervisorOrchestrator(registry=custom_registry)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    skipped = [item for item in outcome.invocations if item.execution_status == "skipped"]
    assert skipped
    assert any(item.agent_id == "dialogue_planner" for item in skipped)
    assert outcome.budget_summary["limit_hit"] is True
    assert any(reason["reason"] == "optional_agent_skipped_budget" for reason in outcome.failover_events)


def test_orchestrator_uses_per_turn_cache_for_repeated_read_tools(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)

    class RepeatedReadAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "repeated-read"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            invocation = request.metadata.get("agent_invocation") or {}
            agent_id = invocation.get("agent_id", "unknown")
            tool_loop_meta = request.metadata.get("tool_loop") or {}
            tool_results = tool_loop_meta.get("tool_results") or []

            if agent_id in {"scene_reader", "trigger_analyst"} and not tool_results:
                return AdapterResponse(
                    raw_output="request read tool",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.read.current_scene",
                        "arguments": {},
                    },
                )
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized"
                return AdapterResponse(raw_output="final", structured_payload=payload)
            return AdapterResponse(
                raw_output=f"{agent_id} done",
                structured_payload={
                    "scene_interpretation": f"{agent_id} summary",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": "ok",
                },
            )

    custom_registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                allowed_tools=["wos.read.current_scene"],
                budget_profile=AgentBudgetProfile(max_tool_calls=1),
            ),
            AgentConfig(
                agent_id="trigger_analyst",
                role="trigger_analyst",
                allowed_tools=["wos.read.current_scene"],
                budget_profile=AgentBudgetProfile(max_tool_calls=1),
            ),
            AgentConfig(agent_id="finalizer", role="finalizer", allowed_tools=[]),
        ],
        supervisor_policy=SupervisorTurnPolicy(max_total_agent_calls=4, max_total_tool_calls=4),
    )
    orchestrator = SupervisorOrchestrator(registry=custom_registry)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=RepeatedReadAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert outcome.cache_summary["hits"] >= 1
    assert outcome.cache_summary["misses"] >= 1
    assert outcome.cache_summary["scope"] == "turn"


def test_orchestrator_uses_exact_token_usage_when_available(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)
    adapter = UsageAwareSupervisorAdapter(
        exact_agents={"scene_reader", "trigger_analyst", "delta_planner", "dialogue_planner", "finalizer"}
    )
    orchestrator = SupervisorOrchestrator()

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["consumed_total_tokens"] == 150
    assert consumed["token_usage_mode"] == "exact"
    assert consumed["proxy_fallback_count"] == 0
    assert all(
        item.budget_consumed.get("token_usage_mode") == "exact"
        for item in outcome.invocations
    )


def test_orchestrator_falls_back_to_proxy_when_exact_usage_missing(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)
    adapter = UsageAwareSupervisorAdapter(exact_agents=set())
    orchestrator = SupervisorOrchestrator()

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["consumed_total_tokens"] == consumed["token_proxy_units"]
    assert consumed["token_usage_mode"] == "proxy"
    assert consumed["proxy_fallback_count"] == len(outcome.invocations)
    assert all(
        item.budget_consumed.get("token_usage_mode") == "proxy"
        for item in outcome.invocations
    )


def test_orchestrator_marks_mixed_mode_when_some_agents_have_exact_usage(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)
    adapter = UsageAwareSupervisorAdapter(exact_agents={"scene_reader", "finalizer"})
    orchestrator = SupervisorOrchestrator()

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["token_usage_mode"] == "mixed"
    assert consumed["proxy_fallback_count"] > 0


def test_orchestrator_allows_delta_planner_preview_and_logs_requesting_agent(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    base_request = _build_base_request(session)

    class PreviewAwareAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "preview-aware-supervisor"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
            tool_results = ((request.metadata.get("tool_loop") or {}).get("tool_results") or [])

            if agent_id == "delta_planner" and not tool_results:
                return AdapterResponse(
                    raw_output="[delta_planner preview]",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.guard.preview_delta",
                        "arguments": {
                            "proposed_state_deltas": [
                                {
                                    "target_path": "characters.veronique.emotional_state",
                                    "next_value": 63,
                                    "delta_type": "state_update",
                                }
                            ]
                        },
                    },
                )

            payload = {
                "scene_interpretation": f"{agent_id} summary",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": f"{agent_id} rationale",
            }
            if agent_id == "delta_planner":
                payload["proposed_state_deltas"] = [
                    {
                        "target_path": "characters.veronique.emotional_state",
                        "next_value": 63,
                        "delta_type": "state_update",
                    }
                ]
            if agent_id == "finalizer":
                merged = dict(request.metadata.get("supervisor_merge_payload") or {})
                merged["rationale"] = "finalized"
                payload = merged
            return AdapterResponse(raw_output=f"[{agent_id}]", structured_payload=payload)

    orchestrator = SupervisorOrchestrator()
    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=PreviewAwareAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    preview_entries = [
        entry
        for entry in outcome.agent_tool_transcript
        if entry.get("tool_name") == "wos.guard.preview_delta"
    ]
    assert preview_entries
    assert preview_entries[0]["agent_id"] == "delta_planner"
    assert preview_entries[0]["preview_result_summary"]["preview_safe_no_write"] is True


def test_orchestrator_enforces_max_agent_tokens_per_invocation(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)

    class HighTokenAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "high-token-adapter"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
            payload = {
                "scene_interpretation": f"{agent_id} summary",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": f"{agent_id} rationale",
            }
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized"
            return AdapterResponse(
                raw_output=f"[{agent_id}]",
                structured_payload=payload,
                backend_metadata={
                    "usage": {
                        "input_tokens": 120,
                        "output_tokens": 30,
                        "total_tokens": 150,
                    }
                },
            )

    registry = build_default_agent_registry()
    constrained_agents = []
    for agent in registry.all_agents():
        updated = agent.model_copy(deep=True)
        updated.budget_profile.max_agent_tokens = 40
        constrained_agents.append(updated)
    constrained_registry = AgentRegistry(
        agents=constrained_agents,
        supervisor_policy=registry.supervisor_policy.model_copy(deep=True),
    )

    orchestrator = SupervisorOrchestrator(registry=constrained_registry)
    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=HighTokenAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    non_skipped = [inv for inv in outcome.invocations if inv.execution_status != "skipped"]
    assert non_skipped
    assert any(inv.execution_status == "error" for inv in non_skipped)
    assert any(
        inv.error_summary and "agent_token_budget_exhausted" in inv.error_summary
        for inv in non_skipped
    )


def test_failed_tool_calls_do_not_consume_budget_when_policy_disabled(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)

    class RejectedToolAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "rejected-tool-adapter"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
            if agent_id == "scene_reader":
                return AdapterResponse(
                    raw_output="[request disallowed tool]",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.guard.preview_delta",
                        "arguments": {},
                    },
                )
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized"
                return AdapterResponse(raw_output="[finalizer]", structured_payload=payload)
            return AdapterResponse(
                raw_output=f"[{agent_id}]",
                structured_payload={
                    "scene_interpretation": f"{agent_id} summary",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": f"{agent_id} rationale",
                },
            )

    registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=1),
                participation="required",
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
                participation="required",
            ),
        ],
        supervisor_policy=SupervisorTurnPolicy(
            consume_budget_on_failed_tool_call=False,
            max_total_agent_calls=4,
            max_total_tool_calls=4,
        ),
    )
    orchestrator = SupervisorOrchestrator(registry=registry)
    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=RejectedToolAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    consumed = outcome.budget_summary["consumed"]
    assert consumed["total_tool_calls"] == 0
    assert outcome.tool_audit
    assert outcome.tool_audit[0]["status"] == "rejected"
    assert outcome.tool_audit[0]["counted_against_hard_limits"] is False


def test_cross_agent_preview_feedback_is_exposed_in_request_metadata(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    session.canonical_state.setdefault("characters", {}).setdefault(
        "veronique", {"emotional_state": 50}
    )
    base_request = _build_base_request(session)
    captured_feedback: list[dict[str, Any]] = []

    class CrossAgentPreviewAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "cross-agent-preview-adapter"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            invocation = request.metadata.get("agent_invocation") or {}
            agent_id = invocation.get("agent_id", "unknown")
            cross_feedback = request.metadata.get("cross_agent_preview_feedback") or []
            if cross_feedback:
                captured_feedback.extend(cross_feedback)

            tool_results = ((request.metadata.get("tool_loop") or {}).get("tool_results") or [])
            if agent_id == "delta_planner" and not tool_results:
                return AdapterResponse(
                    raw_output="[delta planner preview request]",
                    structured_payload={
                        "type": "tool_request",
                        "tool_name": "wos.guard.preview_delta",
                        "arguments": {
                            "proposed_state_deltas": [
                                {
                                    "target_path": "characters.veronique.emotional_state",
                                    "next_value": 63,
                                    "delta_type": "state_update",
                                }
                            ]
                        },
                    },
                )
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized"
                return AdapterResponse(raw_output="[finalizer]", structured_payload=payload)
            return AdapterResponse(
                raw_output=f"[{agent_id}]",
                structured_payload={
                    "scene_interpretation": f"{agent_id} summary",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": f"{agent_id} rationale",
                },
            )

    orchestrator = SupervisorOrchestrator()
    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=CrossAgentPreviewAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert outcome.tool_audit is not None
    assert captured_feedback
    assert any(item.get("requesting_agent_id") == "delta_planner" for item in captured_feedback)


def test_orchestrator_contains_slow_adapter_calls_with_timeout(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    base_request = _build_base_request(session)

    class SlowAdapter(StoryAIAdapter):
        @property
        def adapter_name(self) -> str:
            return "slow-supervisor-adapter"

        def generate(self, request: AdapterRequest) -> AdapterResponse:
            time.sleep(0.08)
            agent_id = (request.metadata.get("agent_invocation") or {}).get("agent_id", "unknown")
            if agent_id == "finalizer":
                payload = dict(request.metadata.get("supervisor_merge_payload") or {})
                payload["rationale"] = "finalized"
                return AdapterResponse(raw_output="[finalizer]", structured_payload=payload)
            return AdapterResponse(
                raw_output=f"[{agent_id}]",
                structured_payload={
                    "scene_interpretation": f"{agent_id} summary",
                    "detected_triggers": [],
                    "proposed_state_deltas": [],
                    "rationale": f"{agent_id} rationale",
                },
            )

    registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(
                    max_tool_calls=0,
                    max_agent_duration_ms=5,
                ),
                participation="required",
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0, max_agent_duration_ms=5),
                participation="required",
            ),
        ],
        supervisor_policy=SupervisorTurnPolicy(max_total_agent_calls=4),
    )
    orchestrator = SupervisorOrchestrator(registry=registry)

    started = time.perf_counter()
    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=SlowAdapter(),
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )
    elapsed_ms = (time.perf_counter() - started) * 1000

    assert elapsed_ms < 80
    assert any(
        inv.error_summary and "adapter_generate_timeout" in inv.error_summary
        for inv in outcome.invocations
    )


def test_build_agent_request_preserves_input_interpretation(god_of_carnage_module_with_state):
    """Task 1A: cloned subagent AdapterRequest keeps base input_interpretation."""
    from app.runtime.input_interpreter import interpret_operator_input

    session = god_of_carnage_module_with_state
    interp = interpret_operator_input("I say 'hello'")
    base = AdapterRequest(
        session_id=session.session_id,
        turn_number=1,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=[],
        operator_input="I say 'hello'",
        input_interpretation=interp,
        request_role_structured_output=True,
        metadata={},
    )
    orchestrator = SupervisorOrchestrator()
    registry = build_default_agent_registry()
    agent = registry.require_enabled("scene_reader")
    built = orchestrator._build_agent_request(
        base_request=base,
        agent=agent,
        sequence_index=1,
        tool_results=[],
    )
    assert built.input_interpretation is not None
    assert built.input_interpretation.primary_mode == interp.primary_mode
    assert built.input_interpretation.model_dump() == interp.model_dump()
