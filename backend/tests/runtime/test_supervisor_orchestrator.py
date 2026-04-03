"""Tests for C1 supervisor orchestrator."""

from __future__ import annotations

from typing import Any

from app.runtime.agent_registry import AgentConfig, AgentRegistry, build_default_agent_registry
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
