"""Social-pressure contracts for the runtime-intelligence aspect.

The contract is structural: policy, bounded state, and selected metric fields
are the oracle. Generated narration is not.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


SOCIAL_PRESSURE_SCHEMA_VERSION = "social_pressure.v1"
SOCIAL_PRESSURE_POLICY_VERSION = "social_pressure_policy.v1"

SocialPressureBand = Literal["low", "moderate", "high"]
SocialPressureTrend = Literal["falling", "stable", "rising"]
SocialPressureValidationStatus = Literal["approved", "degraded", "rejected", "not_applicable"]

SOCIAL_PRESSURE_BANDS: frozenset[str] = frozenset({"low", "moderate", "high"})
SOCIAL_PRESSURE_TRENDS: frozenset[str] = frozenset({"falling", "stable", "rising"})
SOCIAL_PRESSURE_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

SOCIAL_PRESSURE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "social_pressure_target_missing",
        "social_pressure_score_out_of_bounds",
        "social_pressure_band_mismatch",
        "social_pressure_target_mismatch",
    }
)


class SocialPressureEvidenceRef(BaseModel):
    """Pointer to a declared runtime field, not a prose excerpt."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SocialPressureState(BaseModel):
    """Bounded current/prior social-pressure metric carried across turns."""

    model_config = {"extra": "forbid"}

    schema_version: str = SOCIAL_PRESSURE_SCHEMA_VERSION
    current_score: float = Field(ge=0.0, le=1.0)
    current_band: SocialPressureBand
    prior_score: float | None = Field(default=None, ge=0.0, le=1.0)
    prior_band: SocialPressureBand | None = None
    trend: SocialPressureTrend = "stable"
    velocity: float = Field(default=0.0, ge=-1.0, le=1.0)
    active_source_count: int = Field(default=0, ge=0, le=32)
    source_evidence: list[SocialPressureEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SocialPressureTarget(BaseModel):
    """Planner-selected continuous pressure target for the next turn."""

    model_config = {"extra": "forbid"}

    schema_version: str = SOCIAL_PRESSURE_SCHEMA_VERSION
    target_score: float = Field(ge=0.0, le=1.0)
    target_band: SocialPressureBand
    trend: SocialPressureTrend = "stable"
    pressure_floor: float = Field(default=0.0, ge=0.0, le=1.0)
    requires_visible_pressure: bool = False
    release_allowed: bool = False
    source_evidence: list[SocialPressureEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class SocialPressureValidation(BaseModel):
    """Validation result over metric schema and threshold consistency."""

    model_config = {"extra": "forbid"}

    schema_version: str = SOCIAL_PRESSURE_SCHEMA_VERSION
    status: SocialPressureValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[SocialPressureEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _bounded_float(value: Any, default: float, *, minimum: float, maximum: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _score_map(value: Any) -> dict[str, float]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, float] = {}
    for raw_key, raw_score in value.items():
        key = str(raw_key or "").strip()
        if not key:
            continue
        out[key] = _bounded_float(raw_score, 0.0, minimum=0.0, maximum=1.0)
    return out


def normalize_social_pressure_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe policy envelope with contract-known keys."""

    raw = policy if isinstance(policy, dict) else {}
    thresholds = raw.get("band_thresholds") if isinstance(raw.get("band_thresholds"), dict) else {}
    low_max = _bounded_float(thresholds.get("low_max"), 0.33, minimum=0.05, maximum=0.95)
    high_min = _bounded_float(thresholds.get("high_min"), 0.67, minimum=0.05, maximum=0.95)
    if low_max >= high_min:
        low_max, high_min = 0.33, 0.67
    source_scores = raw.get("source_scores") if isinstance(raw.get("source_scores"), dict) else {}
    increments = raw.get("increments") if isinstance(raw.get("increments"), dict) else {}
    return {
        "schema_version": SOCIAL_PRESSURE_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "default_score": _bounded_float(raw.get("default_score"), 0.4, minimum=0.0, maximum=1.0),
        "band_thresholds": {
            "low_max": low_max,
            "high_min": high_min,
        },
        "trend_deadband": _bounded_float(raw.get("trend_deadband"), 0.05, minimum=0.0, maximum=0.5),
        "smoothing_alpha": _bounded_float(raw.get("smoothing_alpha"), 0.7, minimum=0.0, maximum=1.0),
        "max_evidence_refs": _bounded_int(raw.get("max_evidence_refs"), 8, minimum=1, maximum=24),
        "source_scores": {
            "social_risk_band": _score_map(source_scores.get("social_risk_band")),
            "scene_pressure_state": _score_map(source_scores.get("scene_pressure_state")),
            "thread_pressure_state": _score_map(source_scores.get("thread_pressure_state")),
            "scene_energy_transition": _score_map(source_scores.get("scene_energy_transition")),
            "scene_energy_pressure_vector": _score_map(
                source_scores.get("scene_energy_pressure_vector")
            ),
            "pacing_cadence": _score_map(source_scores.get("pacing_cadence")),
            "pressure_shift": _score_map(source_scores.get("pressure_shift")),
        },
        "increments": {
            "per_active_thread": _bounded_float(
                increments.get("per_active_thread"), 0.04, minimum=0.0, maximum=0.25
            ),
            "prior_high_band": _bounded_float(
                increments.get("prior_high_band"), 0.08, minimum=0.0, maximum=0.25
            ),
            "thread_pressure_level": _bounded_float(
                increments.get("thread_pressure_level"), 0.04, minimum=0.0, maximum=0.25
            ),
        },
        "source": "module_runtime_policy.social_pressure",
    }
