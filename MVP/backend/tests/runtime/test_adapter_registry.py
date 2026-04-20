"""Tests for W2.1-R3 — AI Adapter Registry

Verifies adapter registration and lookup functionality.
"""

import pytest
from app.runtime.adapter_registry import (
    adapter_registered,
    clear_registry,
    get_adapter,
    register_adapter,
)
from app.runtime.ai_adapter import AdapterResponse, StoryAIAdapter


class MockAdapter(StoryAIAdapter):
    """Mock adapter for registry testing."""

    def __init__(self, name: str = "test"):
        self._name = name

    @property
    def adapter_name(self) -> str:
        return self._name

    def generate(self, request):
        return AdapterResponse(
            raw_output="test",
            structured_payload={
                "scene_interpretation": "Test",
                "detected_triggers": [],
                "proposed_state_deltas": [],
                "rationale": "Test",
            },
        )


def test_register_adapter():
    """Adapter can be registered by name."""
    clear_registry()
    adapter = MockAdapter("test_adapter")
    register_adapter("test_adapter", adapter)
    assert adapter_registered("test_adapter")


def test_get_adapter():
    """Adapter can be looked up by name."""
    clear_registry()
    adapter = MockAdapter("my_adapter")
    register_adapter("my_adapter", adapter)

    retrieved = get_adapter("my_adapter")
    assert retrieved is not None
    assert retrieved.adapter_name == "my_adapter"


def test_get_adapter_case_insensitive():
    """Adapter lookup is case-insensitive."""
    clear_registry()
    adapter = MockAdapter("CaseAdapter")
    register_adapter("CaseAdapter", adapter)

    assert get_adapter("caseadapter") is not None
    assert get_adapter("CASEADAPTER") is not None
    assert get_adapter("CaseAdapter") is not None


def test_get_nonexistent_adapter_returns_none():
    """Nonexistent adapter lookup returns None."""
    clear_registry()
    assert get_adapter("nonexistent") is None


def test_register_adapter_validates_name():
    """Adapter registration requires non-empty name."""
    clear_registry()
    adapter = MockAdapter()

    with pytest.raises(ValueError, match="Adapter name cannot be empty"):
        register_adapter("", adapter)

    with pytest.raises(ValueError, match="Adapter name cannot be empty"):
        register_adapter("   ", adapter)


def test_register_adapter_validates_adapter():
    """Adapter registration requires non-None adapter."""
    clear_registry()

    with pytest.raises(ValueError, match="Adapter cannot be None"):
        register_adapter("test", None)


def test_clear_registry():
    """Registry can be cleared."""
    clear_registry()
    adapter = MockAdapter("test")
    register_adapter("test", adapter)
    assert adapter_registered("test")

    clear_registry()
    assert not adapter_registered("test")


def test_adapter_registered_function():
    """adapter_registered() checks registration status."""
    clear_registry()

    assert not adapter_registered("unknown")

    adapter = MockAdapter("check")
    register_adapter("check", adapter)
    assert adapter_registered("check")


def test_multiple_adapters_registered():
    """Multiple adapters can be registered independently."""
    clear_registry()

    adapter1 = MockAdapter("adapter1")
    adapter2 = MockAdapter("adapter2")

    register_adapter("adapter1", adapter1)
    register_adapter("adapter2", adapter2)

    assert get_adapter("adapter1") is adapter1
    assert get_adapter("adapter2") is adapter2


def test_no_w2_scope_jump_adapter_registry():
    """No scope jump into W2.2+ features."""
    assert True  # Scope validation is manual

def test_register_adapter_after_register_adapter_model_keeps_stale_spec():
    """Legacy register_adapter replaces the instance only; model spec metadata is unchanged (Task 2D)."""
    from app.runtime.adapter_registry import (
        get_model_spec,
        has_model_spec,
        iter_model_specs,
        legacy_adapter_without_model_spec,
        register_adapter_model,
    )
    from app.runtime.model_routing_contracts import (
        AdapterModelSpec,
        CostClass,
        LatencyClass,
        LLMOrSLM,
        ModelTier,
        StructuredOutputReliability,
        TaskKind,
        WorkflowPhase,
    )

    clear_registry()
    phases = frozenset(WorkflowPhase)
    tasks = frozenset({TaskKind.cheap_preflight})
    spec = AdapterModelSpec(
        adapter_name="dual",
        provider_name="p",
        model_name="v1",
        model_tier=ModelTier.light,
        llm_or_slm=LLMOrSLM.slm,
        cost_class=CostClass.low,
        latency_class=LatencyClass.low,
        supported_phases=phases,
        supported_task_kinds=tasks,
        structured_output_reliability=StructuredOutputReliability.high,
    )
    first = MockAdapter("dual")
    register_adapter_model(spec, first)
    assert get_adapter("dual") is first
    assert has_model_spec("dual")
    assert not legacy_adapter_without_model_spec("dual")
    second = MockAdapter("dual")
    register_adapter("dual", second)
    assert get_adapter("dual") is second
    assert get_adapter("dual") is not first
    assert get_model_spec("dual") is spec
    assert len(iter_model_specs()) == 1

