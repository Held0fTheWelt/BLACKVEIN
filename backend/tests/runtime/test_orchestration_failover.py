"""Focused failover/degradation tests for supervisor orchestration."""

from __future__ import annotations

from app.runtime.agent_registry import AgentBudgetProfile, AgentConfig, AgentRegistry, SupervisorTurnPolicy
from app.runtime.ai_adapter import AdapterRequest, AdapterResponse, StoryAIAdapter
from app.runtime.supervisor_orchestrator import SupervisorOrchestrator


class FailoverAdapter(StoryAIAdapter):
    @property
    def adapter_name(self) -> str:
        return "failover-adapter"

    def generate(self, request: AdapterRequest) -> AdapterResponse:
        invocation = request.metadata.get("agent_invocation") or {}
        agent_id = invocation.get("agent_id", "unknown")
        if agent_id == "scene_reader":
            return AdapterResponse(
                raw_output="scene reader failed payload",
                structured_payload={"invalid": True},
            )
        if agent_id == "finalizer":
            payload = dict(request.metadata.get("supervisor_merge_payload") or {})
            payload["rationale"] = "fallback-safe finalization"
            return AdapterResponse(raw_output="finalizer", structured_payload=payload)
        return AdapterResponse(
            raw_output="ok",
            structured_payload={
                "scene_interpretation": "ok",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "ok",
            },
        )


def _build_base_request(session) -> AdapterRequest:
    return AdapterRequest(
        session_id=session.session_id,
        turn_number=session.turn_counter + 1,
        current_scene_id=session.current_scene_id,
        canonical_state=session.canonical_state,
        recent_events=[],
        operator_input="operator input",
        request_role_structured_output=True,
        metadata={},
    )


def test_optional_agent_failure_is_logged_and_turn_continues(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = FailoverAdapter()
    base_request = _build_base_request(session)

    registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                participation="optional",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                participation="required",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
            ),
        ],
        supervisor_policy=SupervisorTurnPolicy(continue_after_optional_failure=True),
    )
    orchestrator = SupervisorOrchestrator(registry=registry)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert outcome.final_response.structured_payload is not None
    assert any(item["reason"] == "optional_agent_failed_continue" for item in outcome.failover_events)


def test_required_agent_failure_aborts_with_explicit_reason(
    god_of_carnage_module_with_state,
    god_of_carnage_module,
):
    session = god_of_carnage_module_with_state
    adapter = FailoverAdapter()
    base_request = _build_base_request(session)

    registry = AgentRegistry(
        agents=[
            AgentConfig(
                agent_id="scene_reader",
                role="scene_reader",
                participation="required",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
            ),
            AgentConfig(
                agent_id="finalizer",
                role="finalizer",
                participation="required",
                allowed_tools=[],
                budget_profile=AgentBudgetProfile(max_tool_calls=0),
            ),
        ],
        supervisor_policy=SupervisorTurnPolicy(continue_after_optional_failure=True),
    )
    orchestrator = SupervisorOrchestrator(registry=registry)

    outcome = orchestrator.orchestrate(
        base_request=base_request,
        adapter=adapter,
        session=session,
        module=god_of_carnage_module,
        current_turn=session.turn_counter + 1,
        recent_events=[],
        tool_registry=None,
    )

    assert any(item["reason"] == "required_agent_failed_abort" for item in outcome.failover_events)
