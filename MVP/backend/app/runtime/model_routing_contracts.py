"""Task 2A — Canonical model routing contracts (bounded enums + Pydantic models).

Cross-model LLM/SLM routing metadata and routing decisions. This is separate from
``role_contract.py``, which describes interpreter/director/responder sections inside
a single adapter call.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class WorkflowPhase(str, Enum):
    """Bounded workflow phases for adapter capability matching."""

    preflight = "preflight"
    interpretation = "interpretation"
    generation = "generation"
    revision = "revision"
    qa = "qa"


class TaskKind(str, Enum):
    """Task kinds used by the role matrix and routing policy."""

    # SLM-first
    classification = "classification"
    trigger_signal_extraction = "trigger_signal_extraction"
    repetition_consistency_check = "repetition_consistency_check"
    ranking = "ranking"
    cheap_preflight = "cheap_preflight"

    # LLM-first
    scene_direction = "scene_direction"
    conflict_synthesis = "conflict_synthesis"
    narrative_formulation = "narrative_formulation"
    social_narrative_tradeoff = "social_narrative_tradeoff"
    revision_synthesis = "revision_synthesis"

    # Escalation-sensitive
    ambiguity_resolution = "ambiguity_resolution"
    continuity_judgment = "continuity_judgment"
    high_stakes_narrative_tradeoff = "high_stakes_narrative_tradeoff"


class TaskRoutingMode(str, Enum):
    """How the role matrix biases primary model class selection."""

    slm_first = "slm_first"
    llm_first = "llm_first"
    escalation_sensitive = "escalation_sensitive"


class Complexity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LatencyBudget(str, Enum):
    strict = "strict"
    normal = "normal"
    relaxed = "relaxed"


class CostSensitivity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LLMOrSLM(str, Enum):
    llm = "llm"
    slm = "slm"


class ModelTier(str, Enum):
    """Coarse model strength for deterministic escalation ordering."""

    light = "light"
    standard = "standard"
    premium = "premium"


class CostClass(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class LatencyClass(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"


class StructuredOutputReliability(str, Enum):
    high = "high"
    medium = "medium"
    low = "low"


class EscalationHint(str, Enum):
    """Bounded hints that influence escalation-sensitive routing (Task 2E+)."""

    prefer_llm = "prefer_llm"
    high_stakes = "high_stakes"
    continuity_risk = "continuity_risk"
    ambiguity_high = "ambiguity_high"
    conflict_dense = "conflict_dense"
    social_tradeoff_high = "social_tradeoff_high"
    unreliable_low_cost_candidate = "unreliable_low_cost_candidate"


class RouteReasonCode(str, Enum):
    """Stable, inspectable reason for the primary route selection.

    Task 2E replaces generic escalation codes with specific primary reasons.
    Legacy enum members remain for backward compatibility when ingesting older
    persisted traces; ``route_model`` emits only the Task 2E set.
    """

    role_matrix_primary = "role_matrix_primary"
    latency_constraint = "latency_constraint"
    cost_constraint = "cost_constraint"
    no_eligible_adapter = "no_eligible_adapter"
    fallback_only = "fallback_only"
    escalation_due_to_complexity = "escalation_due_to_complexity"
    escalation_due_to_high_stakes_task = "escalation_due_to_high_stakes_task"
    escalation_due_to_structured_output_gap = "escalation_due_to_structured_output_gap"
    escalation_due_to_explicit_hint = "escalation_due_to_explicit_hint"
    # Legacy — not emitted by route_model after Task 2E
    structured_output_required = "structured_output_required"
    escalation_applied = "escalation_applied"


def model_tier_rank(tier: ModelTier) -> int:
    """Numeric rank for deterministic tier ordering (higher = stronger)."""

    return {ModelTier.light: 0, ModelTier.standard: 1, ModelTier.premium: 2}[tier]


class AdapterModelSpec(BaseModel):
    """Structured registration metadata for a registered story adapter/model route."""

    adapter_name: str
    provider_name: str
    model_name: str
    model_tier: ModelTier
    llm_or_slm: LLMOrSLM
    cost_class: CostClass
    latency_class: LatencyClass
    supported_phases: frozenset[WorkflowPhase]
    supported_task_kinds: frozenset[TaskKind]
    structured_output_reliability: StructuredOutputReliability
    fallback_priority: int = 0
    degrade_targets: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"frozen": True}


class RoutingRequest(BaseModel):
    """Input to deterministic model routing (Task 2A)."""

    workflow_phase: WorkflowPhase
    task_kind: TaskKind
    complexity: Complexity = Complexity.medium
    latency_budget: LatencyBudget = LatencyBudget.normal
    cost_sensitivity: CostSensitivity = CostSensitivity.medium
    requires_structured_output: bool = False
    allow_fallback: bool = True
    escalation_hints: list[EscalationHint] = Field(default_factory=list)

    model_config = {"frozen": True}


class RoutingDecision(BaseModel):
    """Inspectable routing outcome; execution still uses ``get_adapter(name)`` (Task 2B+)."""

    selected_adapter_name: str
    selected_provider: str
    selected_model: str
    phase: WorkflowPhase
    task_kind: TaskKind
    route_reason_code: RouteReasonCode
    decision_factors: dict[str, Any] = Field(default_factory=dict)
    fallback_chain: list[str] = Field(default_factory=list)
    escalation_applied: bool = False
    degradation_applied: bool = False

    model_config = {"frozen": True}


# --- Roadmap G2 names (docs/ROADMAP_MVP_GoC.md §6.2): aliases only, no parallel schema ---
ModelCapabilityRecord = AdapterModelSpec
RoutingPolicyRecord = RoutingRequest
# Observation dicts are assembled by ``app.runtime.model_routing_evidence.build_routing_evidence``.
RoutingObservationRecord = dict[str, Any]