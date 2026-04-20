from __future__ import annotations

from dataclasses import dataclass

# String values must match ``app.runtime.model_routing_contracts.RouteReasonCode`` (backend / G1 parity).
ROUTE_REASON_ROLE_MATRIX_PRIMARY = "role_matrix_primary"
ROUTE_REASON_FALLBACK_ONLY = "fallback_only"

# Canonical ``TaskKind``-style strings (see ``ai_stack.goc_roadmap_semantic_surface.TASK_TYPES``).
_SLM_FIRST_TASKS = frozenset(
    {
        "classification",
        "trigger_signal_extraction",
        "repetition_consistency_check",
        "ranking",
        "cheap_preflight",
        # Deprecated aliases — normalized internally; do not emit from new code paths.
        "extraction",
        "compression",
    }
)

_TASK_TYPE_ALIASES: dict[str, str] = {
    "narrative_generation": "narrative_formulation",
    "extraction": "trigger_signal_extraction",
    "compression": "cheap_preflight",
}


def _normalize_task_type(task_type: str) -> str:
    t = (task_type or "").strip().lower()
    return _TASK_TYPE_ALIASES.get(t, t)


@dataclass(slots=True)
class ModelSpec:
    model_name: str
    provider: str
    llm_or_slm: str
    timeout_seconds: float
    structured_output_capable: bool
    cost_class: str
    latency_class: str
    use_cases: tuple[str, ...]


@dataclass(slots=True)
class RoutingDecision:
    selected_model: str
    selected_provider: str
    route_reason: str
    fallback_model: str | None = None


class ModelRegistry:
    def __init__(self) -> None:
        self._models: dict[str, ModelSpec] = {}

    def register(self, spec: ModelSpec) -> None:
        self._models[spec.model_name] = spec

    def get(self, model_name: str) -> ModelSpec | None:
        return self._models.get(model_name)

    def all(self) -> dict[str, ModelSpec]:
        return dict(self._models)


class RoutingPolicy:
    def __init__(self, registry: ModelRegistry) -> None:
        self.registry = registry

    def choose(self, *, task_type: str) -> RoutingDecision:
        task = _normalize_task_type(task_type)
        if task in _SLM_FIRST_TASKS:
            for spec in self.registry.all().values():
                if spec.llm_or_slm == "slm":
                    return RoutingDecision(
                        selected_model=spec.model_name,
                        selected_provider=spec.provider,
                        route_reason=ROUTE_REASON_ROLE_MATRIX_PRIMARY,
                    )

        for spec in self.registry.all().values():
            if spec.llm_or_slm == "llm":
                fallback = next((m.model_name for m in self.registry.all().values() if m.llm_or_slm == "slm"), None)
                return RoutingDecision(
                    selected_model=spec.model_name,
                    selected_provider=spec.provider,
                    route_reason=ROUTE_REASON_ROLE_MATRIX_PRIMARY,
                    fallback_model=fallback,
                )

        for spec in self.registry.all().values():
            return RoutingDecision(
                selected_model=spec.model_name,
                selected_provider=spec.provider,
                route_reason=ROUTE_REASON_FALLBACK_ONLY,
            )
        raise ValueError("No models registered in ModelRegistry")


def build_default_registry() -> ModelRegistry:
    registry = ModelRegistry()
    registry.register(
        ModelSpec(
            model_name="openai:gpt-4o-mini",
            provider="openai",
            llm_or_slm="llm",
            timeout_seconds=20.0,
            structured_output_capable=True,
            cost_class="medium",
            latency_class="medium",
            use_cases=("narrative_generation", "scene_direction", "synthesis"),
        )
    )
    registry.register(
        ModelSpec(
            model_name="ollama:llama3.2",
            provider="ollama",
            llm_or_slm="slm",
            timeout_seconds=8.0,
            structured_output_capable=False,
            cost_class="low",
            latency_class="low",
            use_cases=("classification", "extraction", "ranking", "compression"),
        )
    )
    registry.register(
        ModelSpec(
            model_name="mock:deterministic",
            provider="mock",
            llm_or_slm="slm",
            timeout_seconds=1.0,
            structured_output_capable=True,
            cost_class="none",
            latency_class="very_low",
            use_cases=("tests", "fallback"),
        )
    )
    return registry
