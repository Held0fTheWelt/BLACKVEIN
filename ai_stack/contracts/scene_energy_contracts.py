"""Scene-energy contracts for the Scene Energy runtime-intelligence aspect.

The contract is intentionally structural.  It describes target energy,
transition intent, and validation evidence without treating generated prose as
an oracle.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SCENE_ENERGY_SCHEMA_VERSION = "scene_energy.v1"
SCENE_ENERGY_POLICY_VERSION = "scene_energy_policy.v1"

SceneEnergyLevel = Literal["low", "contained", "rising", "volatile", "collapsed"]
SceneEnergyPressureVector = Literal["social", "moral", "evasive", "exposure", "repair", "rupture"]
SceneEnergyTempo = Literal["still", "compressed", "standard", "accelerating", "fragmented"]
SceneEnergyDensity = Literal["sparse", "focused", "layered", "overloaded"]
SceneEnergyVolatility = Literal["stable", "unstable", "breaking"]
SceneEnergyTransitionIntent = Literal["hold", "rise", "release", "pivot", "interrupt", "deescalate"]
SceneEnergyValidationStatus = Literal["approved", "degraded", "rejected", "not_applicable"]

SCENE_ENERGY_LEVELS: frozenset[str] = frozenset(
    {"low", "contained", "rising", "volatile", "collapsed"}
)
SCENE_ENERGY_PRESSURE_VECTORS: frozenset[str] = frozenset(
    {"social", "moral", "evasive", "exposure", "repair", "rupture"}
)
SCENE_ENERGY_TEMPOS: frozenset[str] = frozenset(
    {"still", "compressed", "standard", "accelerating", "fragmented"}
)
SCENE_ENERGY_DENSITIES: frozenset[str] = frozenset(
    {"sparse", "focused", "layered", "overloaded"}
)
SCENE_ENERGY_VOLATILITIES: frozenset[str] = frozenset(
    {"stable", "unstable", "breaking"}
)
SCENE_ENERGY_TRANSITIONS: frozenset[str] = frozenset(
    {"hold", "rise", "release", "pivot", "interrupt", "deescalate"}
)
SCENE_ENERGY_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

SCENE_ENERGY_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "scene_energy_missing_required_pressure",
        "scene_energy_forbidden_escalation",
        "scene_energy_overloaded_output",
        "scene_energy_empty_fluency",
        "scene_energy_transition_mismatch",
    }
)


class SceneEnergyEvidenceRef(BaseModel):
    """Pointer to a declared source field, never a prose excerpt oracle."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SceneEnergyTarget(BaseModel):
    """Planner-selected target for the next visible realization."""

    model_config = {"extra": "forbid"}

    schema_version: str = SCENE_ENERGY_SCHEMA_VERSION
    energy_level: SceneEnergyLevel
    pressure_vector: SceneEnergyPressureVector
    tempo: SceneEnergyTempo
    density: SceneEnergyDensity
    volatility: SceneEnergyVolatility
    target_transition: SceneEnergyTransitionIntent
    minimum_actor_response_count: int = Field(default=0, ge=0, le=4)
    maximum_visible_density_count: int = Field(default=8, ge=1, le=12)
    forbidden_transitions: list[SceneEnergyTransitionIntent] = Field(default_factory=list)
    source_evidence: list[SceneEnergyEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SceneEnergyTransition(BaseModel):
    """Transition selected from current/prior state into the target."""

    model_config = {"extra": "forbid"}

    schema_version: str = SCENE_ENERGY_SCHEMA_VERSION
    from_energy_level: SceneEnergyLevel | None = None
    to_energy_level: SceneEnergyLevel
    transition_intent: SceneEnergyTransitionIntent
    allowed: bool = True
    reason_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SceneEnergyValidation(BaseModel):
    """Validation result for structured realization evidence."""

    model_config = {"extra": "forbid"}

    schema_version: str = SCENE_ENERGY_SCHEMA_VERSION
    status: SceneEnergyValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[SceneEnergyEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def normalize_scene_energy_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe policy envelope with contract-known keys.

    Tests and runtime code should load this policy rather than duplicating
    module-specific expectations in assertions.
    """

    raw = policy if isinstance(policy, dict) else {}
    enabled = bool(raw.get("enabled", False))
    scene_function_profiles = (
        raw.get("scene_function_profiles")
        if isinstance(raw.get("scene_function_profiles"), dict)
        else {}
    )
    pacing_profiles = raw.get("pacing_profiles") if isinstance(raw.get("pacing_profiles"), dict) else {}
    phase_limits = raw.get("phase_limits") if isinstance(raw.get("phase_limits"), dict) else {}
    return {
        "schema_version": SCENE_ENERGY_POLICY_VERSION,
        "enabled": enabled,
        "scene_function_profiles": scene_function_profiles,
        "pacing_profiles": pacing_profiles,
        "phase_limits": phase_limits,
        "default_maximum_visible_density_count": int(
            raw.get("default_maximum_visible_density_count") or 8
        ),
        "source": "module_runtime_policy.scene_energy",
    }
