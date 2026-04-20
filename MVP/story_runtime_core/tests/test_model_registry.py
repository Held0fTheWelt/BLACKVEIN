from story_runtime_core.model_registry import (
    ROUTE_REASON_FALLBACK_ONLY,
    ROUTE_REASON_ROLE_MATRIX_PRIMARY,
    ModelRegistry,
    ModelSpec,
    build_default_registry,
    RoutingPolicy,
)


def test_routing_policy_prefers_slm_for_classification():
    registry = build_default_registry()
    decision = RoutingPolicy(registry).choose(task_type="classification")
    assert decision.selected_provider in {"ollama", "mock"}
    assert decision.route_reason == ROUTE_REASON_ROLE_MATRIX_PRIMARY


def test_routing_policy_prefers_llm_for_narrative_formulation():
    registry = build_default_registry()
    decision = RoutingPolicy(registry).choose(task_type="narrative_formulation")
    assert decision.selected_provider == "openai"
    assert decision.fallback_model is not None
    assert decision.route_reason == ROUTE_REASON_ROLE_MATRIX_PRIMARY


def test_routing_policy_narrative_generation_alias_maps_to_formulation():
    registry = build_default_registry()
    decision = RoutingPolicy(registry).choose(task_type="narrative_generation")
    assert decision.selected_provider == "openai"
    assert decision.route_reason == ROUTE_REASON_ROLE_MATRIX_PRIMARY


def test_routing_policy_fallback_only_when_no_llm_in_registry():
    registry = ModelRegistry()
    registry.register(
        ModelSpec(
            model_name="slm-only",
            provider="mock",
            llm_or_slm="slm",
            timeout_seconds=1.0,
            structured_output_capable=False,
            cost_class="low",
            latency_class="low",
            use_cases=("tests",),
        )
    )
    decision = RoutingPolicy(registry).choose(task_type="narrative_formulation")
    assert decision.route_reason == ROUTE_REASON_FALLBACK_ONLY
