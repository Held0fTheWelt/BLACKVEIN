from story_runtime_core.model_registry import build_default_registry, RoutingPolicy


def test_routing_policy_prefers_slm_for_classification():
    registry = build_default_registry()
    decision = RoutingPolicy(registry).choose(task_type="classification")
    assert decision.selected_provider in {"ollama", "mock"}


def test_routing_policy_prefers_llm_for_narrative():
    registry = build_default_registry()
    decision = RoutingPolicy(registry).choose(task_type="narrative_generation")
    assert decision.selected_provider == "openai"
    assert decision.fallback_model is not None
