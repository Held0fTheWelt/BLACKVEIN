"""Task 2B: runtime routes before adapter execution; trace on AIDecisionLog."""

import asyncio
import pytest

from app.content.module_models import ContentModule, ModuleMetadata
from app.runtime.adapter_registry import clear_registry, register_adapter_model
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.ai_turn_executor import execute_turn_with_ai
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    CostClass,
    LLMOrSLM,
    LatencyClass,
    ModelTier,
    StructuredOutputReliability,
    TaskKind,
    WorkflowPhase,
)
from app.runtime.runtime_models import SessionState


class RecordingAdapter(StoryAIAdapter):
    def __init__(self, name: str):
        self._name = name
        self.calls = 0

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request):
        self.calls += 1
        return AdapterResponse(raw_output='{"scene_interpretation":"","detected_triggers":[],"rationale":"","proposed_deltas":[]}')


ALL_PHASES = frozenset(WorkflowPhase)
NARR_TASKS = frozenset(
    {
        TaskKind.narrative_formulation,
        TaskKind.scene_direction,
        TaskKind.classification,
    }
)


def _llm_spec(name: str) -> AdapterModelSpec:
    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="m",
        model_tier=ModelTier.premium,
        llm_or_slm=LLMOrSLM.llm,
        cost_class=CostClass.medium,
        latency_class=LatencyClass.medium,
        supported_phases=ALL_PHASES,
        supported_task_kinds=NARR_TASKS,
        structured_output_reliability=StructuredOutputReliability.high,
    )


def _slm_spec(name: str) -> AdapterModelSpec:
    return AdapterModelSpec(
        adapter_name=name,
        provider_name="p",
        model_name="m",
        model_tier=ModelTier.light,
        llm_or_slm=LLMOrSLM.slm,
        cost_class=CostClass.low,
        latency_class=LatencyClass.low,
        supported_phases=ALL_PHASES,
        supported_task_kinds=NARR_TASKS,
        structured_output_reliability=StructuredOutputReliability.high,
    )


@pytest.fixture
def minimal_module() -> ContentModule:
    meta = ModuleMetadata(
        module_id="m1",
        title="T",
        version="1",
        contract_version="1.0.0",
    )
    return ContentModule(metadata=meta, scenes={}, characters={})


@pytest.mark.asyncio
async def test_execute_turn_with_ai_uses_routed_llm_adapter_when_specs_registered(
    minimal_module: ContentModule,
):
    clear_registry()
    passed = RecordingAdapter("passed_slm")
    routed = RecordingAdapter("routed_llm")
    register_adapter_model(_slm_spec("passed_slm"), passed)
    register_adapter_model(_llm_spec("routed_llm"), routed)

    session = SessionState(
        session_id="s1",
        execution_mode="ai",
        adapter_name="passed_slm",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, passed, minimal_module)

    assert routed.calls == 1
    assert passed.calls == 0
    logs = session.metadata.get("ai_decision_logs") or []
    assert logs
    trace = logs[-1].model_routing_trace
    assert trace is not None
    assert trace["routing_invoked"] is True
    assert trace["executed_adapter_name"] == "routed_llm"
    assert trace["fallback_to_passed_adapter"] is False
    req = trace["request"]
    assert req["workflow_phase"] == "generation"
    assert req["task_kind"] == "narrative_formulation"
    ev = trace.get("routing_evidence") or {}
    assert ev.get("requested_workflow_phase") == "generation"
    assert ev.get("requested_task_kind") == "narrative_formulation"
    assert ev.get("executed_adapter_name") == "routed_llm"
    assert ev.get("passed_adapter_name") == "passed_slm"
    assert ev.get("fallback_to_passed_adapter") is False
    assert ev.get("no_eligible_spec_selection") is False
    assert "diagnostics_overview" in ev
    assert "diagnostics_flags" in ev


@pytest.mark.asyncio
async def test_execute_turn_with_ai_falls_back_when_no_model_specs(minimal_module: ContentModule):
    clear_registry()
    ad = RecordingAdapter("only_adapter")

    session = SessionState(
        session_id="s2",
        execution_mode="ai",
        adapter_name="only_adapter",
        module_id="m1",
        module_version="1",
        current_scene_id="scene1",
    )
    session.canonical_state = {}

    await execute_turn_with_ai(session, 1, ad, minimal_module)

    assert ad.calls >= 1
    trace = session.metadata["last_model_routing_trace"]
    assert trace["fallback_to_passed_adapter"] is True
    assert trace["decision"]["route_reason_code"] == "no_eligible_adapter"
    ev = trace.get("routing_evidence") or {}
    assert ev.get("no_eligible_spec_selection") is True
    assert ev.get("fallback_to_passed_adapter") is True
    assert ev.get("route_reason_code") == "no_eligible_adapter"
    assert "diagnostics_overview" in ev
    assert ev["diagnostics_flags"].get("no_eligible_spec_selection") is True
