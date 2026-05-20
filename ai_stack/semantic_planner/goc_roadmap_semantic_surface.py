"""
Roadmap §4.2 / G1 shared semantic surface — canonical label bundles for
GoC.

Maps roadmap mandatory vocabulary families to concrete frozen string
sets implemented in this repository. Consumers should import labels from
here or from the underlying modules referenced in
``ROADMAP_SEMANTIC_REGISTRY`` — do not introduce parallel productive
enums for the same roadmap family.

Parity with backend routing enums is enforced by
``backend/tests/test_goc_semantic_parity.py``.
"""

from __future__ import annotations

from typing import Final

from ai_stack.goc_frozen_vocab import (
    CONTINUITY_CLASSES,
    FAILURE_CLASSES,
    GATE_FAMILIES,
    PACING_MODES,
    SCENE_FUNCTIONS,
    SILENCE_BREVITY_MODES,
    TRANSITION_PATTERNS,
    VISIBILITY_CLASSES,
)

# --- Roadmap ``scene_direction_subdecision_labels`` (director + pacing + silence axes) ---
SCENE_DIRECTION_SUBDECISION_LABELS: Final[frozenset[str]] = frozenset(
    SCENE_FUNCTIONS
    | PACING_MODES
    | SILENCE_BREVITY_MODES
    | CONTINUITY_CLASSES
    | VISIBILITY_CLASSES
    | TRANSITION_PATTERNS
)

# --- Roadmap ``fallback_classes`` — vertical-slice failure / degradation taxonomy (frozen vocab) ---
FALLBACK_CLASSES: Final[frozenset[str]] = FAILURE_CLASSES

# --- Roadmap ``runtime_profile_labels`` — gate families + pacing modes (operator/runtime hints) ---
RUNTIME_PROFILE_LABELS: Final[frozenset[str]] = frozenset(GATE_FAMILIES | PACING_MODES)

# --- task_types — MUST match ``app.runtime.model_routing_contracts.TaskKind`` (backend parity test) ---
TASK_TYPES: Final[frozenset[str]] = frozenset(
    {
        "classification",
        "trigger_signal_extraction",
        "repetition_consistency_check",
        "ranking",
        "cheap_preflight",
        "scene_direction",
        "conflict_synthesis",
        "narrative_formulation",
        "social_narrative_tradeoff",
        "revision_synthesis",
        "ambiguity_resolution",
        "continuity_judgment",
        "high_stakes_narrative_tradeoff",
    }
)

# --- model_roles — coarse adapter class labels (``LLMOrSLM``) ---
MODEL_ROLES: Final[frozenset[str]] = frozenset({"llm", "slm"})

# --- decision_classes — AI action taxonomy (``app.runtime.decision_policy.AIActionType``) ---
DECISION_CLASSES: Final[frozenset[str]] = frozenset(
    {
        "state_update",
        "relationship_shift",
        "scene_transition",
        "trigger_assertion",
        "dialogue_impulse",
        "conflict_signal",
    }
)

# --- routing_labels — primary route reason codes (``RouteReasonCode``, including legacy) ---
ROUTING_LABELS: Final[frozenset[str]] = frozenset(
    {
        "role_matrix_primary",
        "latency_constraint",
        "cost_constraint",
        "no_eligible_adapter",
        "fallback_only",
        "escalation_due_to_complexity",
        "escalation_due_to_high_stakes_task",
        "escalation_due_to_structured_output_gap",
        "escalation_due_to_explicit_hint",
        "structured_output_required",
        "escalation_applied",
    }
)

# --- controlled_reason_codes — alias of routing_labels for roadmap §4.2 naming ---
CONTROLLED_REASON_CODES: Final[frozenset[str]] = ROUTING_LABELS

ROADMAP_SEMANTIC_REGISTRY: Final[dict[str, frozenset[str]]] = {
    "task_types": TASK_TYPES,
    "model_roles": MODEL_ROLES,
    "fallback_classes": FALLBACK_CLASSES,
    "decision_classes": DECISION_CLASSES,
    "routing_labels": ROUTING_LABELS,
    "scene_direction_subdecision_labels": SCENE_DIRECTION_SUBDECISION_LABELS,
    "runtime_profile_labels": RUNTIME_PROFILE_LABELS,
    "controlled_reason_codes": CONTROLLED_REASON_CODES,
}
