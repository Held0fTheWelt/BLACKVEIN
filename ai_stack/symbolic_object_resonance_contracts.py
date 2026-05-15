"""Symbolic-object-resonance contracts.

The contract is structural: canonical object ids, selected symbolic roles,
source references, and structured realization events are the oracle. Generated
prose is not.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION = "symbolic_object_resonance.v1"
SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION = "symbolic_object_resonance_policy.v1"

SymbolicObjectResonanceRole = Literal[
    "attention_diversion",
    "departure_surface",
    "exposure_surface",
    "hospitality_surface",
    "status_surface",
    "territorial_anchor",
]
SymbolicObjectResonanceValidationStatus = Literal[
    "approved",
    "degraded",
    "rejected",
    "not_applicable",
]

SYMBOLIC_OBJECT_RESONANCE_ROLES: frozenset[str] = frozenset(
    {
        "attention_diversion",
        "departure_surface",
        "exposure_surface",
        "hospitality_surface",
        "status_surface",
        "territorial_anchor",
    }
)

SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH = (
    "symbolic_object_resonance_target_mismatch"
)
SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT = (
    "symbolic_object_resonance_unselected_object"
)
SYMBOLIC_OBJECT_RESONANCE_FAILURE_ROLE_MISMATCH = (
    "symbolic_object_resonance_role_mismatch"
)
SYMBOLIC_OBJECT_RESONANCE_FAILURE_MISSING_REQUIRED_EVENT = (
    "symbolic_object_resonance_missing_required_event"
)
SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH = (
    "symbolic_object_resonance_source_ref_mismatch"
)
SYMBOLIC_OBJECT_RESONANCE_FAILURE_BUDGET_EXCEEDED = (
    "symbolic_object_resonance_budget_exceeded"
)

SYMBOLIC_OBJECT_RESONANCE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_TARGET_MISMATCH,
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_UNSELECTED_OBJECT,
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_ROLE_MISMATCH,
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_MISSING_REQUIRED_EVENT,
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_SOURCE_REF_MISMATCH,
        SYMBOLIC_OBJECT_RESONANCE_FAILURE_BUDGET_EXCEEDED,
    }
)


class SymbolicObjectResonanceEvidenceRef(BaseModel):
    """Pointer to structured runtime or canonical content, not prose."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SymbolicObjectResonanceSignal(BaseModel):
    """One selected object-role signal available to generation."""

    model_config = {"extra": "forbid"}

    symbol_id: str
    object_id: str
    resonance_role: SymbolicObjectResonanceRole
    priority: int = Field(default=0, ge=0, le=100)
    source_refs: list[SymbolicObjectResonanceEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SymbolicObjectResonanceState(BaseModel):
    """Bounded object-symbol feedback carried across committed turns."""

    model_config = {"extra": "forbid"}

    schema_version: str = SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION
    recent_symbol_ids: list[str] = Field(default_factory=list, max_length=12)
    active_object_ids: list[str] = Field(default_factory=list, max_length=8)
    resonance_counts: dict[str, int] = Field(default_factory=dict)
    prior_state_fingerprint: str | None = None
    source_evidence: list[SymbolicObjectResonanceEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SymbolicObjectResonanceTarget(BaseModel):
    """Planner-selected symbolic-object resonance for this turn."""

    model_config = {"extra": "forbid"}

    schema_version: str = SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION
    policy_version: str = SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    require_structured_events: bool = False
    max_symbols_per_turn: int = Field(default=2, ge=0, le=8)
    allowed_resonance_roles: list[SymbolicObjectResonanceRole] = Field(default_factory=list)
    selected_symbol_ids: list[str] = Field(default_factory=list, max_length=8)
    selected_object_ids: list[str] = Field(default_factory=list, max_length=8)
    selected_resonance_roles: list[SymbolicObjectResonanceRole] = Field(default_factory=list)
    selected_signals: list[SymbolicObjectResonanceSignal] = Field(default_factory=list)
    required_source_refs: list[SymbolicObjectResonanceEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)
    source_evidence: list[SymbolicObjectResonanceEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SymbolicObjectResonanceValidation(BaseModel):
    """Validation result over structured symbolic-object realization events."""

    model_config = {"extra": "forbid"}

    schema_version: str = SYMBOLIC_OBJECT_RESONANCE_SCHEMA_VERSION
    status: SymbolicObjectResonanceValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[SymbolicObjectResonanceEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clean_str_list(value: Any) -> list[str]:
    if isinstance(value, tuple):
        value = list(value)
    rows = value if isinstance(value, list) else ([] if value is None else [value])
    out: list[str] = []
    for item in rows:
        text = str(item or "").strip()
        if text and text not in out:
            out.append(text)
    return out


def normalize_symbolic_object_resonance_policy(
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Return a JSON-safe symbolic-object-resonance policy envelope."""

    raw = policy if isinstance(policy, dict) else {}
    allowed_roles = [
        role
        for role in _clean_str_list(raw.get("allowed_resonance_roles"))
        if role in SYMBOLIC_OBJECT_RESONANCE_ROLES
    ]
    if not allowed_roles:
        allowed_roles = sorted(SYMBOLIC_OBJECT_RESONANCE_ROLES)
    role_weights = raw.get("role_weights") if isinstance(raw.get("role_weights"), dict) else {}
    normalized_weights: dict[str, int] = {}
    for role in allowed_roles:
        normalized_weights[role] = _bounded_int(
            role_weights.get(role),
            50,
            minimum=0,
            maximum=100,
        )
    return {
        "schema_version": SYMBOLIC_OBJECT_RESONANCE_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "max_symbols_per_turn": _bounded_int(
            raw.get("max_symbols_per_turn"),
            2,
            minimum=0,
            maximum=8,
        ),
        "max_source_refs": _bounded_int(raw.get("max_source_refs"), 6, minimum=0, maximum=16),
        "require_structured_events": bool(raw.get("require_structured_events", False)),
        "default_commit_impact": str(raw.get("default_commit_impact") or "diagnostic").strip()
        or "diagnostic",
        "model_context_visibility": str(
            raw.get("model_context_visibility") or "bounded_structured_only"
        ).strip()
        or "bounded_structured_only",
        "allowed_resonance_roles": allowed_roles,
        "role_weights": normalized_weights,
        "source_priority": _clean_str_list(raw.get("source_priority"))
        or [
            "player_action_frame",
            "environment_state",
            "sensory_context_target",
            "social_pressure_target",
            "relationship_state_record",
            "prior_callback_web_state",
            "prior_consequence_cascade_state",
        ],
        "source": "module_runtime_policy.symbolic_object_resonance",
    }
