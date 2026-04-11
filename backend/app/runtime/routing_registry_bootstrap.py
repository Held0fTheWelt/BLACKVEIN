"""Explicit bootstrap for routing-sensitive registry state (Task 2).

Registers the in-repo :class:`MockStoryAIAdapter` with a single :class:`AdapterModelSpec`
that covers Runtime staged tuples and typical session routing overrides. Does not register
fictional provider adapters.
"""

from __future__ import annotations

from flask import Flask

from app.runtime.adapter_registry import register_adapter_model
from app.runtime.ai_adapter import MockStoryAIAdapter
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

# Mock adapter serves every bounded task kind for in-process test/dev routing.
_MOCK_SUPPORTED_PHASES: frozenset[WorkflowPhase] = frozenset(WorkflowPhase)
_MOCK_SUPPORTED_TASK_KINDS: frozenset[TaskKind] = frozenset(TaskKind)


def build_default_mock_story_adapter_model_spec() -> AdapterModelSpec:
    """Return the canonical Task 2A spec for :class:`MockStoryAIAdapter`.

    Declared as LLM-class so synthesis-heavy task kinds resolve without relying on
    pool widening alone; preflight/signal (SLM-first) still select this spec when it is
    the only eligible candidate after widening.
    """

    return AdapterModelSpec(
        adapter_name="mock",
        provider_name="mock",
        model_name="mock-story-adapter",
        model_tier=ModelTier.standard,
        llm_or_slm=LLMOrSLM.llm,
        cost_class=CostClass.low,
        latency_class=LatencyClass.low,
        supported_phases=_MOCK_SUPPORTED_PHASES,
        supported_task_kinds=_MOCK_SUPPORTED_TASK_KINDS,
        structured_output_reliability=StructuredOutputReliability.high,
        fallback_priority=0,
        degrade_targets=[],
        metadata={"bootstrap": "routing_registry_bootstrap.MockStoryAIAdapter"},
    )


def bootstrap_routing_registry_from_config(app: Flask | None = None) -> bool:
    """Register mock story adapter + spec when enabled by config.

    Returns True if bootstrap ran (registration performed), False if skipped.
    """

    if app is not None:
        enabled = app.config.get("ROUTING_REGISTRY_BOOTSTRAP", True)
    else:
        enabled = True
    if not enabled:
        return False

    spec = build_default_mock_story_adapter_model_spec()
    register_adapter_model(spec, MockStoryAIAdapter())
    return True


def init_routing_registry_bootstrap(app: Flask) -> None:
    """Flask hook: run bootstrap once during application factory."""

    bootstrap_routing_registry_from_config(app)
