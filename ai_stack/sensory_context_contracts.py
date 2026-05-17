"""Sensory-context contracts for bounded runtime sensory layering.

The contract is structural: module policy, authored sensory sources, selected
layer ids, and structured realization events are the oracle. Generated prose is
not.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SENSORY_CONTEXT_SCHEMA_VERSION = "sensory_context.v1"
SENSORY_CONTEXT_POLICY_VERSION = "sensory_context_policy.v1"

SensoryContextLayerKind = Literal["mood", "room_ambient", "location_entry", "object_perception"]
SensoryContextIntensity = Literal["low", "medium", "high"]
SensoryContextValidationStatus = Literal["approved", "degraded", "rejected", "not_applicable"]

SENSORY_CONTEXT_LAYER_KINDS: frozenset[str] = frozenset(
    {"mood", "room_ambient", "location_entry", "object_perception"}
)
SENSORY_CONTEXT_INTENSITIES: frozenset[str] = frozenset({"low", "medium", "high"})
SENSORY_CONTEXT_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

SENSORY_CONTEXT_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "sensory_context_target_mismatch",
        "sensory_context_missing_required_layer",
        "sensory_context_unselected_layer",
        "sensory_context_source_ref_mismatch",
        "sensory_context_layer_budget_exceeded",
        "sensory_context_structured_event_missing",
    }
)


class SensoryContextEvidenceRef(BaseModel):
    """Pointer to declared source data, not a prose oracle."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SensoryContextLayer(BaseModel):
    """One selected authored sensory layer available to generation."""

    model_config = {"extra": "forbid"}

    layer_id: str
    layer_kind: SensoryContextLayerKind
    source: str
    source_field: str
    source_ref: str
    language: str | None = None
    text: str | None = None
    required: bool = True

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SensoryContextState(BaseModel):
    """Bounded prior/current sensory state carried across turns."""

    model_config = {"extra": "forbid"}

    schema_version: str = SENSORY_CONTEXT_SCHEMA_VERSION
    current_layer_ids: list[str] = Field(default_factory=list, max_length=8)
    prior_layer_ids: list[str] = Field(default_factory=list, max_length=8)
    repeated_layer_count: int = Field(default=0, ge=0, le=8)
    location_id: str | None = None
    object_id: str | None = None
    mood_key: str | None = None
    intensity: SensoryContextIntensity = "medium"
    source_evidence: list[SensoryContextEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SensoryContextTarget(BaseModel):
    """Planner-selected sensory context for the next visible realization."""

    model_config = {"extra": "forbid"}

    schema_version: str = SENSORY_CONTEXT_SCHEMA_VERSION
    intensity: SensoryContextIntensity = "medium"
    location_id: str | None = None
    object_id: str | None = None
    mood_key: str | None = None
    selected_layers: list[SensoryContextLayer] = Field(default_factory=list, max_length=8)
    required_layer_ids: list[str] = Field(default_factory=list, max_length=8)
    min_layers_per_turn: int = Field(default=1, ge=0, le=8)
    max_layers_per_turn: int = Field(default=3, ge=1, le=8)
    require_structured_events: bool = True
    source_evidence: list[SensoryContextEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SensoryContextValidation(BaseModel):
    """Validation result over structured sensory realization evidence."""

    model_config = {"extra": "forbid"}

    schema_version: str = SENSORY_CONTEXT_SCHEMA_VERSION
    status: SensoryContextValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[SensoryContextEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_sensory_context_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe policy envelope with contract-known keys."""

    raw = policy if isinstance(policy, dict) else {}
    return {
        "schema_version": SENSORY_CONTEXT_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "min_layers_per_turn": _bounded_int(raw.get("min_layers_per_turn"), 1, minimum=0, maximum=8),
        "max_layers_per_turn": _bounded_int(raw.get("max_layers_per_turn"), 3, minimum=1, maximum=8),
        "require_structured_events": bool(raw.get("require_structured_events", True)),
        "model_context_visibility": str(
            raw.get("model_context_visibility") or "bounded_authored_layers"
        ).strip()
        or "bounded_authored_layers",
        "intensity_by_pressure_band": (
            raw.get("intensity_by_pressure_band")
            if isinstance(raw.get("intensity_by_pressure_band"), dict)
            else {}
        ),
        "mood_by_scene_energy": (
            raw.get("mood_by_scene_energy")
            if isinstance(raw.get("mood_by_scene_energy"), dict)
            else {}
        ),
        "mood_by_scene_function": (
            raw.get("mood_by_scene_function")
            if isinstance(raw.get("mood_by_scene_function"), dict)
            else {}
        ),
        "source": "module_runtime_policy.sensory_context",
    }
