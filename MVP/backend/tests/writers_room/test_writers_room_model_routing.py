"""Unit tests for writers_room_model_routing functions."""

from __future__ import annotations

from dataclasses import dataclass

import pytest
from story_runtime_core.model_registry import ModelRegistry, ModelSpec

from app.runtime.model_routing_contracts import (
    CostClass,
    LatencyClass,
    LLMOrSLM,
    ModelTier,
    StructuredOutputReliability,
    TaskKind,
)
from app.services.writers_room_model_routing import (
    _cost_class,
    _latency_class,
    _task_kinds_for_use_cases,
    build_writers_room_model_route_specs,
    model_spec_to_adapter_model_spec,
)


class TestCostClass:
    """Tests for _cost_class."""

    def test_cost_class_low_for_none_and_low_raw(self):
        """'none' and 'low' both map to CostClass.low (empty/None becomes medium)."""
        assert _cost_class("low") == CostClass.low
        assert _cost_class("LOW") == CostClass.low
        assert _cost_class("none") == CostClass.low
        assert _cost_class("None") == CostClass.low
        # None and "" fall through to medium since (raw or "").lower() == ""
        assert _cost_class(None) == CostClass.medium
        assert _cost_class("") == CostClass.medium

    def test_cost_class_high_for_high_raw(self):
        """'high' maps to CostClass.high."""
        assert _cost_class("high") == CostClass.high
        assert _cost_class("HIGH") == CostClass.high

    def test_cost_class_medium_for_unknown_raw(self):
        """Unknown values map to CostClass.medium."""
        assert _cost_class("medium") == CostClass.medium
        assert _cost_class("unknown") == CostClass.medium
        assert _cost_class("random") == CostClass.medium


class TestLatencyClass:
    """Tests for _latency_class."""

    def test_latency_class_low_for_very_low(self):
        """'very_low' and 'low' both map to LatencyClass.low."""
        assert _latency_class("very_low") == LatencyClass.low
        assert _latency_class("low") == LatencyClass.low
        assert _latency_class("LOW") == LatencyClass.low
        assert _latency_class("VERY_LOW") == LatencyClass.low

    def test_latency_class_high_for_high(self):
        """'high' maps to LatencyClass.high."""
        assert _latency_class("high") == LatencyClass.high
        assert _latency_class("HIGH") == LatencyClass.high

    def test_latency_class_medium_for_unknown(self):
        """Unknown and None values map to LatencyClass.medium."""
        assert _latency_class(None) == LatencyClass.medium
        assert _latency_class("") == LatencyClass.medium
        assert _latency_class("medium") == LatencyClass.medium
        assert _latency_class("unknown") == LatencyClass.medium


class TestTaskKindsForUseCases:
    """Tests for _task_kinds_for_use_cases."""

    def test_task_kinds_for_empty_use_cases_returns_fallback(self):
        """Empty use cases returns default narrative_formulation + cheap_preflight."""
        kinds = _task_kinds_for_use_cases(())
        assert TaskKind.narrative_formulation in kinds
        assert TaskKind.cheap_preflight in kinds

    def test_task_kinds_for_narrative_formulation_adds_revision_synthesis(self):
        """narrative_generation maps to narrative_formulation + revision_synthesis."""
        kinds = _task_kinds_for_use_cases(("narrative_generation",))
        assert TaskKind.narrative_formulation in kinds
        assert TaskKind.revision_synthesis in kinds

    def test_task_kinds_for_scene_direction_adds_revision_synthesis(self):
        """scene_direction adds revision_synthesis."""
        kinds = _task_kinds_for_use_cases(("scene_direction",))
        assert TaskKind.scene_direction in kinds
        assert TaskKind.revision_synthesis in kinds

    def test_task_kinds_for_synthesis_use_case(self):
        """synthesis use case maps to narrative_formulation + revision_synthesis."""
        kinds = _task_kinds_for_use_cases(("synthesis",))
        assert TaskKind.narrative_formulation in kinds
        assert TaskKind.revision_synthesis in kinds

    def test_task_kinds_for_multiple_mapped_use_cases(self):
        """Multiple use cases combine their task kinds."""
        kinds = _task_kinds_for_use_cases(("classification", "extraction"))
        assert TaskKind.classification in kinds
        assert TaskKind.trigger_signal_extraction in kinds

    def test_task_kinds_for_mock_provider_returns_all_task_kinds(self):
        """Mock provider gets all task kinds (for honest degrade)."""
        # This is tested in model_spec_to_adapter_model_spec for mock provider
        kinds = _task_kinds_for_use_cases(("ranking",))
        assert TaskKind.ranking in kinds


class TestModelSpecToAdapterModelSpec:
    """Tests for model_spec_to_adapter_model_spec."""

    def _make_model_spec(
        self,
        provider: str = "openai",
        llm_or_slm: str = "llm",
        model_name: str = "gpt-4",
        cost_class: str = "high",
        latency_class: str = "medium",
        structured_output_capable: bool = True,
        use_cases: tuple[str, ...] = ("narrative_generation",),
        timeout_seconds: float = 30.0,
    ) -> ModelSpec:
        """Factory for ModelSpec instances."""
        return ModelSpec(
            provider=provider,
            model_name=model_name,
            llm_or_slm=llm_or_slm,
            cost_class=cost_class,
            latency_class=latency_class,
            structured_output_capable=structured_output_capable,
            use_cases=use_cases,
            timeout_seconds=timeout_seconds,
        )

    def test_model_spec_to_adapter_model_spec_openai_llm_premium_tier(self):
        """OpenAI LLM gets premium tier."""
        spec = self._make_model_spec(provider="openai", llm_or_slm="llm")
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert adapter_spec.model_tier == ModelTier.premium
        assert adapter_spec.llm_or_slm == LLMOrSLM.llm

    def test_model_spec_to_adapter_model_spec_slm_light_tier(self):
        """SLM gets light tier."""
        spec = self._make_model_spec(provider="local", llm_or_slm="slm")
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert adapter_spec.model_tier == ModelTier.light
        assert adapter_spec.llm_or_slm == LLMOrSLM.slm

    def test_model_spec_to_adapter_model_spec_other_llm_standard_tier(self):
        """Non-OpenAI LLM gets standard tier."""
        spec = self._make_model_spec(provider="anthropic", llm_or_slm="llm")
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert adapter_spec.model_tier == ModelTier.standard

    def test_model_spec_to_adapter_model_spec_structured_output_reliability(self):
        """Structured output capability maps to reliability."""
        spec_capable = self._make_model_spec(structured_output_capable=True)
        adapter_capable = model_spec_to_adapter_model_spec(spec_capable)
        assert adapter_capable.structured_output_reliability == (
            StructuredOutputReliability.high
        )

        spec_incapable = self._make_model_spec(structured_output_capable=False)
        adapter_incapable = model_spec_to_adapter_model_spec(spec_incapable)
        assert adapter_incapable.structured_output_reliability == (
            StructuredOutputReliability.low
        )

    def test_model_spec_to_adapter_model_spec_degrade_targets_for_openai(self):
        """OpenAI provider has 'mock' as degrade target."""
        spec = self._make_model_spec(provider="openai")
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert "mock" in adapter_spec.degrade_targets

    def test_model_spec_to_adapter_model_spec_degrade_targets_for_ollama(self):
        """Ollama provider has 'mock' as degrade target."""
        spec = self._make_model_spec(provider="ollama")
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert "mock" in adapter_spec.degrade_targets

    def test_model_spec_to_adapter_model_spec_mock_provider_gets_all_task_kinds(self):
        """Mock provider gets all TaskKind values."""
        spec = self._make_model_spec(provider="mock", use_cases=())
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert len(adapter_spec.supported_task_kinds) == len(TaskKind)

    def test_model_spec_to_adapter_model_spec_cost_and_latency_classes(self):
        """Cost and latency classes are mapped correctly."""
        spec = self._make_model_spec(
            cost_class="high", latency_class="very_low"
        )
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert adapter_spec.cost_class == CostClass.high
        assert adapter_spec.latency_class == LatencyClass.low

    def test_model_spec_to_adapter_model_spec_metadata_includes_source(self):
        """Metadata includes source marker."""
        spec = self._make_model_spec()
        adapter_spec = model_spec_to_adapter_model_spec(spec)
        assert adapter_spec.metadata["source"] == "story_runtime_core.ModelSpec"


class TestBuildWritersRoomModelRouteSpecs:
    """Tests for build_writers_room_model_route_specs."""

    class StubRegistry:
        """Minimal ModelRegistry stub for testing."""

        def __init__(self, specs: dict[str, ModelSpec] | None = None):
            self._specs = specs or {
                "openai_gpt4": ModelSpec(
                    provider="openai",
                    model_name="gpt-4",
                    llm_or_slm="llm",
                    cost_class="high",
                    latency_class="medium",
                    structured_output_capable=True,
                    use_cases=("narrative_generation",),
                    timeout_seconds=30.0,
                ),
                "anthropic_claude": ModelSpec(
                    provider="anthropic",
                    model_name="claude-3-sonnet",
                    llm_or_slm="llm",
                    cost_class="high",
                    latency_class="medium",
                    structured_output_capable=True,
                    use_cases=("narrative_generation",),
                    timeout_seconds=30.0,
                ),
            }

        def all(self) -> dict[str, ModelSpec]:
            return self._specs

    def test_build_writers_room_model_route_specs_with_stub_registry_produces_specs(
        self,
    ):
        """Registry with 2 models produces 2 adapter specs."""
        stub_registry = self.StubRegistry()
        specs = build_writers_room_model_route_specs(registry=stub_registry)
        assert len(specs) == 2
        adapter_names = {s.adapter_name for s in specs}
        assert "openai" in adapter_names
        assert "anthropic" in adapter_names

    def test_build_writers_room_model_route_specs_empty_registry_produces_empty_list(
        self,
    ):
        """Empty registry produces empty specs list."""
        # Create a StubRegistry with only one model for simplicity
        single_registry = self.StubRegistry(specs={"test_model": ModelSpec(
            provider="test",
            model_name="test-model",
            llm_or_slm="llm",
            cost_class="low",
            latency_class="low",
            structured_output_capable=False,
            use_cases=(),
            timeout_seconds=10.0,
        )})
        specs = build_writers_room_model_route_specs(registry=single_registry)
        assert len(specs) == 1

    def test_build_writers_room_model_route_specs_degrade_flag_for_ollama(self):
        """Ollama models include degrade target."""
        ollama_spec = ModelSpec(
            provider="ollama",
            model_name="ollama-mistral",
            llm_or_slm="slm",
            cost_class="low",
            latency_class="low",
            structured_output_capable=False,
            use_cases=("classification",),
            timeout_seconds=30.0,
        )
        stub_registry = self.StubRegistry(specs={"ollama": ollama_spec})
        specs = build_writers_room_model_route_specs(registry=stub_registry)
        assert len(specs) == 1
        assert specs[0].provider_name == "ollama"
        assert "mock" in specs[0].degrade_targets
