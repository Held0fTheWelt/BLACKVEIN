"""Task 2B: story_runtime_core ModelSpec -> Task 2A AdapterModelSpec for Writers-Room routing."""

from __future__ import annotations

from story_runtime_core.model_registry import ModelRegistry, ModelSpec, build_default_registry

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

ALL_PHASES = frozenset(WorkflowPhase)

_USE_CASE_TASK: dict[str, TaskKind] = {
    "narrative_generation": TaskKind.narrative_formulation,
    "scene_direction": TaskKind.scene_direction,
    "synthesis": TaskKind.narrative_formulation,
    "classification": TaskKind.classification,
    "extraction": TaskKind.trigger_signal_extraction,
    "ranking": TaskKind.ranking,
    "compression": TaskKind.cheap_preflight,
    "tests": TaskKind.cheap_preflight,
    "fallback": TaskKind.cheap_preflight,
}


def _cost_class(raw: str) -> CostClass:
    key = (raw or "").lower()
    if key in ("none", "low"):
        return CostClass.low
    if key == "high":
        return CostClass.high
    return CostClass.medium


def _latency_class(raw: str) -> LatencyClass:
    key = (raw or "").lower()
    if key in ("very_low", "low"):
        return LatencyClass.low
    if key == "high":
        return LatencyClass.high
    return LatencyClass.medium


def _task_kinds_for_use_cases(use_cases: tuple[str, ...]) -> frozenset[TaskKind]:
    kinds: set[TaskKind] = set()
    for uc in use_cases:
        mapped = _USE_CASE_TASK.get(uc)
        if mapped is not None:
            kinds.add(mapped)
    if not kinds:
        kinds = {TaskKind.narrative_formulation, TaskKind.cheap_preflight}
    # Improvement bounded calls use revision_synthesis + revision phase on the same provider pool.
    if TaskKind.narrative_formulation in kinds or TaskKind.scene_direction in kinds:
        kinds.add(TaskKind.revision_synthesis)
    return frozenset(kinds)


def model_spec_to_adapter_model_spec(ms: ModelSpec) -> AdapterModelSpec:
    role = LLMOrSLM.llm if ms.llm_or_slm == "llm" else LLMOrSLM.slm
    if role == LLMOrSLM.llm and ms.provider == "openai":
        tier = ModelTier.premium
    elif role == LLMOrSLM.slm:
        tier = ModelTier.light
    else:
        tier = ModelTier.standard
    rel = (
        StructuredOutputReliability.high
        if ms.structured_output_capable
        else StructuredOutputReliability.low
    )
    degrade: list[str] = []
    if ms.provider in ("openai", "ollama"):
        degrade = ["mock"]
    task_kinds = _task_kinds_for_use_cases(ms.use_cases)
    # Default mock provider participates in all bounded routing tasks for honest degrade targets.
    if ms.provider == "mock":
        task_kinds = frozenset(TaskKind)
    return AdapterModelSpec(
        adapter_name=ms.provider,
        provider_name=ms.provider,
        model_name=ms.model_name,
        model_tier=tier,
        llm_or_slm=role,
        cost_class=_cost_class(ms.cost_class),
        latency_class=_latency_class(ms.latency_class),
        supported_phases=ALL_PHASES,
        supported_task_kinds=task_kinds,
        structured_output_reliability=rel,
        fallback_priority=0,
        degrade_targets=degrade,
        metadata={"source": "story_runtime_core.ModelSpec", "degrade_policy": "provider_to_mock"},
    )


def build_writers_room_model_route_specs(registry: ModelRegistry | None = None) -> list[AdapterModelSpec]:
    reg = registry or build_default_registry()
    return [model_spec_to_adapter_model_spec(m) for m in reg.all().values()]
