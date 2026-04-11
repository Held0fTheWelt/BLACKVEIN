"""Deterministic model routing policy (Task 2A core, Task 2E escalation stages).

Selects a registered adapter name from ``AdapterModelSpec`` metadata only (no
provider-only shortcuts). One policy evaluation per ``route_model`` call — no
multi-stage Runtime orchestration.
"""

from __future__ import annotations

from collections.abc import Sequence

from app.runtime import adapter_registry
from app.runtime.model_routing_contracts import (
    AdapterModelSpec,
    Complexity,
    CostClass,
    CostSensitivity,
    LatencyBudget,
    LatencyClass,
    LLMOrSLM,
    ModelTier,
    RouteReasonCode,
    RoutingDecision,
    RoutingRequest,
    StructuredOutputReliability,
    TaskKind,
    TaskRoutingMode,
    WorkflowPhase,
    model_tier_rank,
)

TASK_ROUTING_MODE: dict[TaskKind, TaskRoutingMode] = {
    TaskKind.classification: TaskRoutingMode.slm_first,
    TaskKind.trigger_signal_extraction: TaskRoutingMode.slm_first,
    TaskKind.repetition_consistency_check: TaskRoutingMode.slm_first,
    TaskKind.ranking: TaskRoutingMode.slm_first,
    TaskKind.cheap_preflight: TaskRoutingMode.slm_first,
    TaskKind.scene_direction: TaskRoutingMode.llm_first,
    TaskKind.conflict_synthesis: TaskRoutingMode.llm_first,
    TaskKind.narrative_formulation: TaskRoutingMode.llm_first,
    TaskKind.social_narrative_tradeoff: TaskRoutingMode.llm_first,
    TaskKind.revision_synthesis: TaskRoutingMode.llm_first,
    TaskKind.ambiguity_resolution: TaskRoutingMode.escalation_sensitive,
    TaskKind.continuity_judgment: TaskRoutingMode.escalation_sensitive,
    TaskKind.high_stakes_narrative_tradeoff: TaskRoutingMode.escalation_sensitive,
}

HIGH_STAKES_TASK_KINDS: frozenset[TaskKind] = frozenset(
    {
        TaskKind.ambiguity_resolution,
        TaskKind.continuity_judgment,
        TaskKind.high_stakes_narrative_tradeoff,
    }
)

# Task kinds where high complexity can trigger mandatory LLM emphasis on generation/revision.
# Includes ``ranking`` so SLM-first work can deterministically move to LLMs under complexity.
_SYNTHESIS_HEAVY_CORE: frozenset[TaskKind] = frozenset(
    {
        TaskKind.revision_synthesis,
        TaskKind.conflict_synthesis,
        TaskKind.narrative_formulation,
        TaskKind.social_narrative_tradeoff,
    }
)


def _synthesis_heavy_for_complexity(request: RoutingRequest) -> bool:
    if request.task_kind in _SYNTHESIS_HEAVY_CORE:
        return request.workflow_phase in (WorkflowPhase.generation, WorkflowPhase.revision)
    if request.task_kind == TaskKind.ranking:
        return request.workflow_phase in (WorkflowPhase.generation, WorkflowPhase.revision)
    return False


def _reliability_rank(rel: StructuredOutputReliability) -> int:
    return {
        StructuredOutputReliability.high: 2,
        StructuredOutputReliability.medium: 1,
        StructuredOutputReliability.low: 0,
    }[rel]


def _latency_rank(spec: AdapterModelSpec) -> int:
    return {LatencyClass.low: 0, LatencyClass.medium: 1, LatencyClass.high: 2}[spec.latency_class]


def _cost_rank(spec: AdapterModelSpec) -> int:
    return {CostClass.low: 0, CostClass.medium: 1, CostClass.high: 2}[spec.cost_class]


def _latency_alignment(spec: AdapterModelSpec, budget: LatencyBudget) -> int:
    r = _latency_rank(spec)
    if budget == LatencyBudget.strict:
        return 10 - r
    if budget == LatencyBudget.relaxed:
        return r + 4
    return 7 - r // 2


def _cost_alignment(spec: AdapterModelSpec, sens: CostSensitivity) -> int:
    r = _cost_rank(spec)
    if sens == CostSensitivity.high:
        return 10 - r
    if sens == CostSensitivity.low:
        return r + 4
    return 7 - r // 2


def _filter_eligible(
    specs: Sequence[AdapterModelSpec],
    request: RoutingRequest,
    *,
    require_structured: bool,
) -> list[AdapterModelSpec]:
    out: list[AdapterModelSpec] = []
    for spec in specs:
        if request.workflow_phase not in spec.supported_phases:
            continue
        if request.task_kind not in spec.supported_task_kinds:
            continue
        if require_structured and spec.structured_output_reliability == StructuredOutputReliability.low:
            continue
        out.append(spec)
    return out


def _preferred_pool(
    eligible: list[AdapterModelSpec],
    request: RoutingRequest,
) -> tuple[list[AdapterModelSpec], bool]:
    """Return (pool, widened). widened=True when the preferred model class had no candidates."""
    mode = TASK_ROUTING_MODE[request.task_kind]
    hints = request.escalation_hints

    if mode == TaskRoutingMode.slm_first:
        slms = [s for s in eligible if s.llm_or_slm == LLMOrSLM.slm]
        if slms:
            return slms, False
        return eligible, True

    if mode == TaskRoutingMode.llm_first:
        llms = [s for s in eligible if s.llm_or_slm == LLMOrSLM.llm]
        if llms:
            return llms, False
        return eligible, True

    if hints:
        llms = [s for s in eligible if s.llm_or_slm == LLMOrSLM.llm]
        if llms:
            return llms, False
        return eligible, True

    llms = [s for s in eligible if s.llm_or_slm == LLMOrSLM.llm]
    if llms:
        return llms, False
    return eligible, True


def _pick_slm(request: RoutingRequest, pool: list[AdapterModelSpec]) -> AdapterModelSpec:
    return min(
        pool,
        key=lambda s: (
            model_tier_rank(s.model_tier),
            -_latency_alignment(s, request.latency_budget),
            -_cost_alignment(s, request.cost_sensitivity),
            -s.fallback_priority,
            s.adapter_name.lower(),
        ),
    )


def _pick_llm(request: RoutingRequest, pool: list[AdapterModelSpec]) -> AdapterModelSpec:
    return max(
        pool,
        key=lambda s: (
            model_tier_rank(s.model_tier),
            _latency_alignment(s, request.latency_budget),
            _cost_alignment(s, request.cost_sensitivity),
            s.fallback_priority,
            s.adapter_name.lower(),
        ),
    )


def _pick_primary(pool: list[AdapterModelSpec], request: RoutingRequest) -> AdapterModelSpec:
    mode = TASK_ROUTING_MODE[request.task_kind]
    has_slm = any(s.llm_or_slm == LLMOrSLM.slm for s in pool)
    if mode == TaskRoutingMode.slm_first and has_slm:
        return _pick_slm(request, pool)
    return _pick_llm(request, pool)


def _spec_by_name(specs: Sequence[AdapterModelSpec]) -> dict[str, AdapterModelSpec]:
    return {s.adapter_name.lower(): s for s in specs}


def _build_fallback_chain(
    primary: AdapterModelSpec,
    request: RoutingRequest,
    by_name: dict[str, AdapterModelSpec],
) -> list[str]:
    if not request.allow_fallback:
        return []
    out: list[str] = []
    for target in primary.degrade_targets:
        spec = by_name.get(target.lower())
        if spec is None:
            continue
        if request.workflow_phase not in spec.supported_phases:
            continue
        if request.task_kind not in spec.supported_task_kinds:
            continue
        if request.requires_structured_output and spec.structured_output_reliability == StructuredOutputReliability.low:
            continue
        out.append(spec.adapter_name)
    return out


def _slm_in_eligible(eligible: list[AdapterModelSpec]) -> bool:
    return any(s.llm_or_slm == LLMOrSLM.slm for s in eligible)


def _mandatory_llm_escalation(request: RoutingRequest, eligible: list[AdapterModelSpec]) -> bool:
    if request.task_kind in HIGH_STAKES_TASK_KINDS:
        return True
    if TASK_ROUTING_MODE[request.task_kind] == TaskRoutingMode.escalation_sensitive and bool(
        request.escalation_hints
    ):
        return True
    if (
        request.complexity == Complexity.high
        and _synthesis_heavy_for_complexity(request)
        and any(s.llm_or_slm == LLMOrSLM.llm for s in eligible)
    ):
        return True
    return False


def _apply_mandatory_llm_pool(
    eligible: list[AdapterModelSpec], request: RoutingRequest
) -> tuple[list[AdapterModelSpec], bool]:
    """Narrow to LLM-class specs when mandatory escalation requires it."""
    if not _mandatory_llm_escalation(request, eligible):
        return eligible, False
    llms = [s for s in eligible if s.llm_or_slm == LLMOrSLM.llm]
    if llms:
        return llms, True
    return eligible, False


def _apply_complexity_tier_floor(
    pool: list[AdapterModelSpec], request: RoutingRequest
) -> list[AdapterModelSpec]:
    """Prefer standard-or-better tiers when complexity is high on synthesis-heavy paths."""
    if request.complexity != Complexity.high:
        return pool
    if not _synthesis_heavy_for_complexity(request):
        return pool
    if request.workflow_phase not in (WorkflowPhase.generation, WorkflowPhase.revision):
        return pool
    floor = model_tier_rank(ModelTier.standard)
    strong = [s for s in pool if model_tier_rank(s.model_tier) >= floor]
    return strong if strong else pool


def _select_primary_and_meta(
    request: RoutingRequest,
    spec_list: list[AdapterModelSpec],
    eligible: list[AdapterModelSpec],
    eligible_all: list[AdapterModelSpec],
) -> tuple[AdapterModelSpec, list[AdapterModelSpec], bool, bool, list[str]]:
    """Stages 2–6: mandatory LLM pool, tier floor, role pool, pick, fallback chain.

    ``eligible_all`` is reserved for callers that re-run this pipeline on the full
    pre-structured candidate set (``eligible_all``, ``eligible_all``) so length-based
    structured shaping stays inactive inside that counterfactual evaluation.

    Returns (primary, final_pool, widened, mandatory_llm_narrowed, fallback_chain).
    """
    by_name = _spec_by_name(spec_list)
    working, mandatory_narrowed = _apply_mandatory_llm_pool(eligible, request)
    pool, widened = _preferred_pool(working, request)
    final_pool = _apply_complexity_tier_floor(pool, request)
    primary = _pick_primary(final_pool, request)
    chain = _build_fallback_chain(primary, request, by_name)
    return primary, final_pool, widened, mandatory_narrowed, chain


def _compute_escalation_applied(*, route_reason_code: RouteReasonCode) -> bool:
    return route_reason_code in (
        RouteReasonCode.escalation_due_to_structured_output_gap,
        RouteReasonCode.escalation_due_to_explicit_hint,
        RouteReasonCode.escalation_due_to_high_stakes_task,
        RouteReasonCode.escalation_due_to_complexity,
    )


def _primary_route_reason_code(
    *,
    request: RoutingRequest,
    eligible: list[AdapterModelSpec],
    primary: AdapterModelSpec,
    widened: bool,
    mandatory_llm_narrowed: bool,
    pool_for_counterfactual: list[AdapterModelSpec],
    counterfactual_primary_name: str,
    material_structured_output_gap: bool,
) -> tuple[RouteReasonCode, dict[str, object]]:
    """Assign exactly one primary reason; escalation precedes fallback/latency/cost."""

    factors_extra: dict[str, object] = {}
    structured_gap = material_structured_output_gap
    explicit_hint_primary = (
        bool(request.escalation_hints)
        and TASK_ROUTING_MODE[request.task_kind] == TaskRoutingMode.escalation_sensitive
        and _slm_in_eligible(eligible)
        and primary.llm_or_slm == LLMOrSLM.llm
    )
    high_stakes_primary = (
        request.task_kind in HIGH_STAKES_TASK_KINDS
        and _slm_in_eligible(eligible)
        and primary.llm_or_slm == LLMOrSLM.llm
        and not explicit_hint_primary
    )
    complexity_primary = (
        request.complexity == Complexity.high
        and primary.adapter_name != counterfactual_primary_name
        and not structured_gap
        and not explicit_hint_primary
        and not high_stakes_primary
    )

    factors_extra["structured_output_gap"] = structured_gap
    factors_extra["explicit_hint_present"] = bool(request.escalation_hints)
    factors_extra["preferred_pool_empty"] = widened

    if structured_gap:
        factors_extra["escalation_trigger"] = "structured_output_gap"
        return RouteReasonCode.escalation_due_to_structured_output_gap, factors_extra
    if explicit_hint_primary:
        factors_extra["escalation_trigger"] = "explicit_hint"
        return RouteReasonCode.escalation_due_to_explicit_hint, factors_extra
    if high_stakes_primary:
        factors_extra["escalation_trigger"] = "high_stakes_task"
        return RouteReasonCode.escalation_due_to_high_stakes_task, factors_extra
    if complexity_primary:
        factors_extra["escalation_trigger"] = "complexity"
        return RouteReasonCode.escalation_due_to_complexity, factors_extra
    # True pool degradation: role-family had no candidates without mandatory LLM narrowing.
    if widened and not mandatory_llm_narrowed:
        factors_extra["escalation_trigger"] = "none"
        return RouteReasonCode.fallback_only, factors_extra

    lat_changed = False
    if request.latency_budget != LatencyBudget.normal:
        alt_lat = _pick_primary(
            pool_for_counterfactual,
            request.model_copy(update={"latency_budget": LatencyBudget.normal}),
        )
        lat_changed = alt_lat.adapter_name != primary.adapter_name
    cost_changed = False
    if request.cost_sensitivity != CostSensitivity.medium:
        alt_cost = _pick_primary(
            pool_for_counterfactual,
            request.model_copy(update={"cost_sensitivity": CostSensitivity.medium}),
        )
        cost_changed = alt_cost.adapter_name != primary.adapter_name
    factors_extra["counterfactual_latency_changed"] = lat_changed
    factors_extra["counterfactual_cost_changed"] = cost_changed
    factors_extra["escalation_trigger"] = "none"

    if lat_changed:
        return RouteReasonCode.latency_constraint, factors_extra
    if cost_changed:
        return RouteReasonCode.cost_constraint, factors_extra
    return RouteReasonCode.role_matrix_primary, factors_extra


def route_model(
    request: RoutingRequest,
    *,
    specs: Sequence[AdapterModelSpec] | None = None,
) -> RoutingDecision:
    """Return a deterministic routing decision for ``request``.

    If ``specs`` is None, uses ``adapter_registry.iter_model_specs()``.
    """
    spec_list = list(specs) if specs is not None else adapter_registry.iter_model_specs()

    # Stage 1 — hard exclusions
    eligible_all = _filter_eligible(spec_list, request, require_structured=False)
    eligible = _filter_eligible(spec_list, request, require_structured=request.requires_structured_output)

    factors: dict[str, object] = {
        "task_routing_mode": TASK_ROUTING_MODE[request.task_kind].value,
        "candidate_count_after_phase_task": len(eligible_all),
        "candidate_count_after_structured_filter": len(eligible),
        "requires_structured_output": request.requires_structured_output,
    }

    if not eligible:
        factors["failure"] = "no_eligible_adapter"
        factors["escalation_trigger"] = "none"
        return RoutingDecision(
            selected_adapter_name="",
            selected_provider="",
            selected_model="",
            phase=request.workflow_phase,
            task_kind=request.task_kind,
            route_reason_code=RouteReasonCode.no_eligible_adapter,
            decision_factors=factors,
            fallback_chain=[],
            escalation_applied=False,
            degradation_applied=bool(eligible_all),
        )

    primary, final_pool, widened, mandatory_narrowed, chain = _select_primary_and_meta(
        request, spec_list, eligible, eligible_all
    )

    material_structured_output_gap = False
    if request.requires_structured_output and len(eligible) < len(eligible_all):
        loose_primary, _, _, _, _ = _select_primary_and_meta(
            request, spec_list, eligible_all, eligible_all
        )
        material_structured_output_gap = primary.adapter_name != loose_primary.adapter_name

    degradation_applied = widened or material_structured_output_gap

    req_medium = request.model_copy(update={"complexity": Complexity.medium})
    _p_med, _, _, _, _ = _select_primary_and_meta(
        req_medium, spec_list, eligible, eligible_all
    )
    counterfactual_primary_name = _p_med.adapter_name

    code, reason_factors = _primary_route_reason_code(
        request=request,
        eligible=eligible,
        primary=primary,
        widened=widened,
        mandatory_llm_narrowed=mandatory_narrowed,
        pool_for_counterfactual=final_pool,
        counterfactual_primary_name=counterfactual_primary_name,
        material_structured_output_gap=material_structured_output_gap,
    )
    factors.update(reason_factors)
    factors["preferred_pool_widened"] = widened
    factors["mandatory_llm_pool_applied"] = mandatory_narrowed
    if mandatory_narrowed and TASK_ROUTING_MODE[request.task_kind] == TaskRoutingMode.slm_first:
        factors["selected_outside_preferred_role_family"] = True
    factors["selected_llm_or_slm"] = primary.llm_or_slm.value
    factors["escalation_hints"] = [h.value for h in request.escalation_hints]

    # Soft signals (informational; do not become primary codes)
    mode = TASK_ROUTING_MODE[request.task_kind]
    pref_pool, _ = _preferred_pool(eligible, request)
    if pref_pool:
        best_rel = max(_reliability_rank(s.structured_output_reliability) for s in pref_pool)
        factors["soft_preferred_max_reliability_rank"] = best_rel
        factors["soft_preferred_reliability_pressure"] = best_rel < _reliability_rank(
            StructuredOutputReliability.high
        )
    factors["soft_synthesis_heavy_context"] = _synthesis_heavy_for_complexity(request)
    factors["soft_widened_or_degraded_pool"] = widened or material_structured_output_gap

    esc = _compute_escalation_applied(route_reason_code=code)

    return RoutingDecision(
        selected_adapter_name=primary.adapter_name,
        selected_provider=primary.provider_name,
        selected_model=primary.model_name,
        phase=request.workflow_phase,
        task_kind=request.task_kind,
        route_reason_code=code,
        decision_factors=factors,
        fallback_chain=chain,
        escalation_applied=esc,
        degradation_applied=degradation_applied,
    )
