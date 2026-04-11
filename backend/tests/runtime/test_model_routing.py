"""Tests for Task 2A model routing core and registry-backed specs."""

import pytest

from app.runtime.adapter_registry import (
    clear_registry,
    get_adapter,
    get_model_spec,
    iter_model_specs,
    register_adapter,
    register_adapter_model,
)
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter
from app.runtime.model_routing import TASK_ROUTING_MODE, route_model
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    Complexity,
    CostClass,
    CostSensitivity,
    LatencyBudget,
    EscalationHint,
    LLMOrSLM,
    LatencyClass,
    ModelTier,
    RoutingRequest,
    StructuredOutputReliability,
    TaskKind,
    TaskRoutingMode,
    WorkflowPhase,
)


class NamedAdapter(StoryAIAdapter):
    def __init__(self, name: str):
        self._name = name

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request):
        return AdapterResponse(raw_output="ok")


ALL_PHASES = frozenset(WorkflowPhase)


def _spec(
    *,
    name: str,
    provider: str,
    model: str,
    role: LLMOrSLM,
    tier: ModelTier,
    tasks: frozenset[TaskKind],
    structured: StructuredOutputReliability = StructuredOutputReliability.high,
    degrade: list[str] | None = None,
    cost: CostClass = CostClass.low,
    latency: LatencyClass = LatencyClass.low,
    priority: int = 0,
) -> AdapterModelSpec:
    return AdapterModelSpec(
        adapter_name=name,
        provider_name=provider,
        model_name=model,
        model_tier=tier,
        llm_or_slm=role,
        cost_class=cost,
        latency_class=latency,
        supported_phases=ALL_PHASES,
        supported_task_kinds=tasks,
        structured_output_reliability=structured,
        fallback_priority=priority,
        degrade_targets=degrade or [],
    )


def test_task_routing_mode_covers_all_task_kinds():
    assert set(TaskKind) == set(TASK_ROUTING_MODE.keys())


def test_multiple_specs_same_provider_different_models():
    clear_registry()
    slm = _spec(
        name="acme_small",
        provider="acme",
        model="small-v1",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
    )
    llm = _spec(
        name="acme_large",
        provider="acme",
        model="large-v2",
        role=LLMOrSLM.llm,
        tier=ModelTier.premium,
        tasks=frozenset({TaskKind.classification}),
    )
    register_adapter_model(slm, NamedAdapter("acme_small"))
    register_adapter_model(llm, NamedAdapter("acme_large"))
    assert len(iter_model_specs()) == 2
    assert get_model_spec("acme_small").model_name == "small-v1"
    assert get_model_spec("acme_large").model_name == "large-v2"


def test_slm_first_selects_slm_when_available():
    clear_registry()
    slm = _spec(
        name="slm_a",
        provider="p",
        model="m1",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        priority=1,
    )
    llm = _spec(
        name="llm_a",
        provider="p",
        model="m2",
        role=LLMOrSLM.llm,
        tier=ModelTier.premium,
        tasks=frozenset({TaskKind.classification}),
        priority=99,
    )
    register_adapter_model(slm, NamedAdapter("slm_a"))
    register_adapter_model(llm, NamedAdapter("llm_a"))
    req = RoutingRequest(
        workflow_phase=WorkflowPhase.preflight,
        task_kind=TaskKind.classification,
    )
    d = route_model(req)
    assert d.selected_adapter_name == "slm_a"
    assert d.decision_factors["task_routing_mode"] == TaskRoutingMode.slm_first.value
    assert TASK_ROUTING_MODE[TaskKind.classification] == TaskRoutingMode.slm_first


def test_llm_first_selects_llm_when_available():
    clear_registry()
    slm = _spec(
        name="slm_b",
        provider="p",
        model="m1",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.scene_direction}),
    )
    llm = _spec(
        name="llm_b",
        provider="p",
        model="m2",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.scene_direction}),
    )
    register_adapter_model(slm, NamedAdapter("slm_b"))
    register_adapter_model(llm, NamedAdapter("llm_b"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.scene_direction,
        )
    )
    assert d.selected_adapter_name == "llm_b"


def test_escalation_sensitive_with_hints_prefers_llm():
    clear_registry()
    slm = _spec(
        name="slm_c",
        provider="p",
        model="fast",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ambiguity_resolution}),
    )
    llm = _spec(
        name="llm_c",
        provider="p",
        model="smart",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.ambiguity_resolution}),
    )
    register_adapter_model(slm, NamedAdapter("slm_c"))
    register_adapter_model(llm, NamedAdapter("llm_c"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.interpretation,
            task_kind=TaskKind.ambiguity_resolution,
            escalation_hints=[EscalationHint.prefer_llm],
        )
    )
    assert d.selected_adapter_name == "llm_c"
    assert d.escalation_applied is True
    assert d.route_reason_code.value == "escalation_due_to_explicit_hint"
    assert d.decision_factors.get("escalation_trigger") == "explicit_hint"


def test_requires_structured_output_drops_low_reliability():
    clear_registry()
    low = _spec(
        name="cheap_slm",
        provider="p",
        model="x",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ranking}),
        structured=StructuredOutputReliability.low,
        priority=100,
    )
    high = _spec(
        name="good_slm",
        provider="p",
        model="y",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ranking}),
        structured=StructuredOutputReliability.high,
        priority=1,
    )
    register_adapter_model(low, NamedAdapter("cheap_slm"))
    register_adapter_model(high, NamedAdapter("good_slm"))
    d_loose = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.ranking,
            requires_structured_output=False,
        )
    )
    d_strict = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.ranking,
            requires_structured_output=True,
        )
    )
    assert d_loose.selected_adapter_name == "cheap_slm"
    assert d_strict.selected_adapter_name == "good_slm"
    assert d_strict.route_reason_code.value == "escalation_due_to_structured_output_gap"
    assert d_strict.degradation_applied is True
    assert d_strict.decision_factors.get("structured_output_gap") is True


def test_structured_filter_removes_only_losing_slm_no_primary_gap():
    """Low-reliability SLM loses the SLM-first pick; dropping it does not change the winner."""
    clear_registry()
    loser = _spec(
        name="slm_low_lose",
        provider="p",
        model="x",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ranking}),
        structured=StructuredOutputReliability.low,
        priority=0,
    )
    winner = _spec(
        name="slm_high_win",
        provider="p",
        model="y",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ranking}),
        structured=StructuredOutputReliability.high,
        priority=100,
    )
    register_adapter_model(loser, NamedAdapter("slm_low_lose"))
    register_adapter_model(winner, NamedAdapter("slm_high_win"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.ranking,
            requires_structured_output=True,
        )
    )
    assert d.selected_adapter_name == "slm_high_win"
    assert d.route_reason_code.value != "escalation_due_to_structured_output_gap"
    assert d.route_reason_code.value == "role_matrix_primary"
    assert d.decision_factors.get("structured_output_gap") is False
    assert d.degradation_applied is False
    assert d.decision_factors.get("preferred_pool_widened") is False


def test_structured_filter_changes_llm_first_winner_emits_gap():
    """When the LLM-first winner is low structured reliability, strict filtering moves the primary."""
    clear_registry()
    premium_low = _spec(
        name="llm_premium_low",
        provider="p",
        model="a",
        role=LLMOrSLM.llm,
        tier=ModelTier.premium,
        tasks=frozenset({TaskKind.scene_direction}),
        structured=StructuredOutputReliability.low,
        priority=0,
    )
    standard_high = _spec(
        name="llm_standard_high",
        provider="p",
        model="b",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.scene_direction}),
        structured=StructuredOutputReliability.high,
        priority=0,
    )
    register_adapter_model(premium_low, NamedAdapter("llm_premium_low"))
    register_adapter_model(standard_high, NamedAdapter("llm_standard_high"))
    d_loose = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.scene_direction,
            requires_structured_output=False,
        )
    )
    d_strict = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.scene_direction,
            requires_structured_output=True,
        )
    )
    assert d_loose.selected_adapter_name == "llm_premium_low"
    assert d_strict.selected_adapter_name == "llm_standard_high"
    assert d_strict.route_reason_code.value == "escalation_due_to_structured_output_gap"
    assert d_strict.escalation_applied is True
    assert d_strict.degradation_applied is True
    assert d_strict.decision_factors.get("structured_output_gap") is True


def test_fallback_chain_filters_missing_and_phase_task():
    clear_registry()
    primary = _spec(
        name="primary_route",
        provider="p",
        model="a",
        role=LLMOrSLM.llm,
        tier=ModelTier.premium,
        tasks=frozenset({TaskKind.narrative_formulation}),
        degrade=["missing", "fallback_ok", "wrong_task"],
        priority=5,
    )
    fb = _spec(
        name="fallback_ok",
        provider="p",
        model="b",
        role=LLMOrSLM.llm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.narrative_formulation}),
        priority=0,
    )
    wrong = _spec(
        name="wrong_task",
        provider="p",
        model="c",
        role=LLMOrSLM.llm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        priority=0,
    )
    register_adapter_model(primary, NamedAdapter("primary_route"))
    register_adapter_model(fb, NamedAdapter("fallback_ok"))
    register_adapter_model(wrong, NamedAdapter("wrong_task"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.narrative_formulation,
        )
    )
    assert d.fallback_chain == ["fallback_ok"]


def test_allow_fallback_false_clears_chain():
    clear_registry()
    p = _spec(
        name="p_only",
        provider="p",
        model="a",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.revision_synthesis}),
        degrade=["fb"],
    )
    register_adapter_model(
        _spec(
            name="fb",
            provider="p",
            model="b",
            role=LLMOrSLM.slm,
            tier=ModelTier.light,
            tasks=frozenset({TaskKind.revision_synthesis}),
        ),
        NamedAdapter("fb"),
    )
    register_adapter_model(p, NamedAdapter("p_only"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.revision,
            task_kind=TaskKind.revision_synthesis,
            allow_fallback=False,
        )
    )
    assert d.fallback_chain == []


def test_legacy_get_adapter_after_register_adapter_model():
    clear_registry()
    spec = _spec(
        name="legacy_check",
        provider="x",
        model="m",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.cheap_preflight}),
    )
    ad = NamedAdapter("legacy_check")
    register_adapter_model(spec, ad)
    assert get_adapter("legacy_check") is ad


def test_register_adapter_without_spec_not_in_iter_model_specs():
    clear_registry()
    register_adapter("bare", NamedAdapter("bare"))
    assert get_adapter("bare") is not None
    assert iter_model_specs() == []


def test_clear_registry_clears_specs_and_adapters():
    clear_registry()
    spec = _spec(
        name="tmp",
        provider="p",
        model="m",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.cheap_preflight}),
    )
    register_adapter_model(spec, NamedAdapter("tmp"))
    register_adapter("other", NamedAdapter("other"))
    clear_registry()
    assert get_adapter("tmp") is None
    assert get_model_spec("tmp") is None
    assert get_adapter("other") is None


def test_register_adapter_model_rejects_name_mismatch():
    clear_registry()
    spec = _spec(
        name="right",
        provider="p",
        model="m",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.cheap_preflight}),
    )
    with pytest.raises(ValueError, match="adapter.adapter_name must match"):
        register_adapter_model(spec, NamedAdapter("wrong"))


def test_no_eligible_adapter_empty_decision():
    clear_registry()
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.qa,
            task_kind=TaskKind.scene_direction,
        )
    )
    assert d.selected_adapter_name == ""
    assert d.route_reason_code.value == "no_eligible_adapter"

def test_fallback_only_when_llm_first_pool_widens_to_slm_only():
    clear_registry()
    slm = _spec(
        name="only_slm",
        provider="p",
        model="m",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.scene_direction}),
    )
    register_adapter_model(slm, NamedAdapter("only_slm"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.scene_direction,
        )
    )
    assert d.selected_adapter_name == "only_slm"
    assert d.route_reason_code.value == "fallback_only"
    assert d.decision_factors["preferred_pool_widened"] is True


def test_latency_constraint_only_when_normal_budget_counterfactual_differs():
    clear_registry()
    s1 = _spec(
        name="s1",
        provider="p",
        model="a",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.high,
        latency=LatencyClass.low,
    )
    s2 = _spec(
        name="s2",
        provider="p",
        model="b",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.low,
        latency=LatencyClass.high,
    )
    register_adapter_model(s1, NamedAdapter("s1"))
    register_adapter_model(s2, NamedAdapter("s2"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            latency_budget=LatencyBudget.relaxed,
            cost_sensitivity=CostSensitivity.high,
        )
    )
    assert d.selected_adapter_name == "s2"
    assert d.route_reason_code.value == "latency_constraint"
    assert d.decision_factors["counterfactual_latency_changed"] is True
    d_norm = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            latency_budget=LatencyBudget.normal,
            cost_sensitivity=CostSensitivity.high,
        )
    )
    assert d_norm.selected_adapter_name == "s1"
    assert d_norm.route_reason_code.value == "role_matrix_primary"


def test_cost_constraint_only_when_medium_sensitivity_counterfactual_differs():
    clear_registry()
    cheap = _spec(
        name="cheap",
        provider="p",
        model="a",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.low,
        latency=LatencyClass.medium,
    )
    expensive = _spec(
        name="expensive",
        provider="p",
        model="b",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.high,
        latency=LatencyClass.medium,
    )
    register_adapter_model(cheap, NamedAdapter("cheap"))
    register_adapter_model(expensive, NamedAdapter("expensive"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            cost_sensitivity=CostSensitivity.low,
        )
    )
    assert d.selected_adapter_name == "expensive"
    assert d.route_reason_code.value == "cost_constraint"
    assert d.decision_factors["counterfactual_cost_changed"] is True
    d_med = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            cost_sensitivity=CostSensitivity.medium,
        )
    )
    assert d_med.selected_adapter_name == "cheap"
    assert d_med.route_reason_code.value == "role_matrix_primary"


def test_reason_precedence_structured_over_fallback_only_when_both_apply():
    clear_registry()
    low_slm = _spec(
        name="low_rel_slm",
        provider="p",
        model="x",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        structured=StructuredOutputReliability.low,
    )
    high_llm = _spec(
        name="high_rel_llm",
        provider="p",
        model="y",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.classification}),
        structured=StructuredOutputReliability.high,
    )
    register_adapter_model(low_slm, NamedAdapter("low_rel_slm"))
    register_adapter_model(high_llm, NamedAdapter("high_rel_llm"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            requires_structured_output=True,
        )
    )
    assert d.selected_adapter_name == "high_rel_llm"
    assert d.route_reason_code.value == "escalation_due_to_structured_output_gap"
    assert d.decision_factors["preferred_pool_widened"] is True


def test_reason_precedence_escalation_over_fallback_only():
    clear_registry()
    slm = _spec(
        name="slm_e",
        provider="p",
        model="s",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ambiguity_resolution}),
    )
    llm = _spec(
        name="llm_e",
        provider="p",
        model="l",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.ambiguity_resolution}),
    )
    register_adapter_model(slm, NamedAdapter("slm_e"))
    register_adapter_model(llm, NamedAdapter("llm_e"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.interpretation,
            task_kind=TaskKind.ambiguity_resolution,
            escalation_hints=[EscalationHint.prefer_llm],
        )
    )
    assert d.route_reason_code.value == "escalation_due_to_explicit_hint"
    assert d.decision_factors["preferred_pool_widened"] is False


def test_high_stakes_task_escalation_without_hints():
    clear_registry()
    slm = _spec(
        name="slm_hs",
        provider="p",
        model="s",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.continuity_judgment}),
    )
    llm = _spec(
        name="llm_hs",
        provider="p",
        model="l",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.continuity_judgment}),
    )
    register_adapter_model(slm, NamedAdapter("slm_hs"))
    register_adapter_model(llm, NamedAdapter("llm_hs"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.interpretation,
            task_kind=TaskKind.continuity_judgment,
            escalation_hints=[],
        )
    )
    assert d.selected_adapter_name == "llm_hs"
    assert d.route_reason_code.value == "escalation_due_to_high_stakes_task"
    assert d.decision_factors.get("escalation_trigger") == "high_stakes_task"


def test_escalation_due_to_complexity_ranking_generation():
    clear_registry()
    slm = _spec(
        name="slm_rank",
        provider="p",
        model="s",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.ranking}),
    )
    llm = _spec(
        name="llm_rank",
        provider="p",
        model="l",
        role=LLMOrSLM.llm,
        tier=ModelTier.standard,
        tasks=frozenset({TaskKind.ranking}),
    )
    register_adapter_model(slm, NamedAdapter("slm_rank"))
    register_adapter_model(llm, NamedAdapter("llm_rank"))
    d_high = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.ranking,
            complexity=Complexity.high,
        )
    )
    d_med = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.generation,
            task_kind=TaskKind.ranking,
            complexity=Complexity.medium,
        )
    )
    assert d_med.selected_adapter_name == "slm_rank"
    assert d_high.selected_adapter_name == "llm_rank"
    assert d_high.route_reason_code.value == "escalation_due_to_complexity"
    assert d_high.decision_factors.get("mandatory_llm_pool_applied") is True
    assert d_high.decision_factors.get("selected_outside_preferred_role_family") is True


def test_dual_counterfactual_prefers_latency_reason_code():
    clear_registry()
    s1 = _spec(
        name="s1",
        provider="p",
        model="a",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.high,
        latency=LatencyClass.low,
    )
    s2 = _spec(
        name="s2",
        provider="p",
        model="b",
        role=LLMOrSLM.slm,
        tier=ModelTier.light,
        tasks=frozenset({TaskKind.classification}),
        cost=CostClass.low,
        latency=LatencyClass.high,
    )
    register_adapter_model(s1, NamedAdapter("s1"))
    register_adapter_model(s2, NamedAdapter("s2"))
    d = route_model(
        RoutingRequest(
            workflow_phase=WorkflowPhase.preflight,
            task_kind=TaskKind.classification,
            latency_budget=LatencyBudget.relaxed,
            cost_sensitivity=CostSensitivity.high,
        )
    )
    assert d.decision_factors["counterfactual_latency_changed"] is True
    assert d.decision_factors["counterfactual_cost_changed"] is False
    assert d.route_reason_code.value == "latency_constraint"

