"""Durable relationship-state-machine contracts for Pi27.

The contract is bounded and structural. It carries committed relationship
feedback across turns without using generated narration as an oracle.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RELATIONSHIP_STATE_SCHEMA_VERSION = "relationship_state_machine.v1"
RELATIONSHIP_STATE_POLICY_VERSION = "relationship_state_policy.v1"

RelationshipStabilityBand = Literal["stable", "strained", "fractured"]
RelationshipTrend = Literal["falling", "stable", "rising"]
RelationshipValidationStatus = Literal["approved", "degraded", "rejected", "not_applicable"]

RELATIONSHIP_STABILITY_BANDS: frozenset[str] = frozenset({"stable", "strained", "fractured"})
RELATIONSHIP_TRENDS: frozenset[str] = frozenset({"falling", "stable", "rising"})
RELATIONSHIP_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

RELATIONSHIP_TRANSITION_CODES: frozenset[str] = frozenset(
    {
        "blame_pressure",
        "repair_attempt",
        "alliance_shift",
        "social_state_shifted",
        "high_social_pressure",
        "npc_initiative_pressure",
        "relationship_axis_pressure",
    }
)

RELATIONSHIP_STATE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "relationship_state_missing",
        "relationship_target_missing",
        "relationship_pair_score_out_of_bounds",
        "relationship_axis_score_out_of_bounds",
        "relationship_unknown_target_relationship",
        "relationship_unknown_target_axis",
        "relationship_unknown_transition_code",
        "relationship_event_actor_lane_violation",
    }
)


class RelationshipStateEvidenceRef(BaseModel):
    """Pointer to a structured runtime field, not prose evidence."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RelationshipPairState(BaseModel):
    """Durable bounded state for one canonical relationship pair."""

    model_config = {"extra": "forbid"}

    relationship_id: str
    character_ids: list[str] = Field(default_factory=list, max_length=2)
    axis_ids: list[str] = Field(default_factory=list, max_length=8)
    tension_score: float = Field(default=0.0, ge=0.0, le=1.0)
    trust_score: float = Field(default=0.5, ge=0.0, le=1.0)
    alliance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    dominance_score: float = Field(default=0.5, ge=0.0, le=1.0)
    stability_band: RelationshipStabilityBand = "stable"
    trend: RelationshipTrend = "stable"
    last_transition_codes: list[str] = Field(default_factory=list, max_length=8)
    last_updated_turn: int = Field(default=0, ge=0)


class RelationshipAxisState(BaseModel):
    """Aggregate durable state for a canonical relationship axis."""

    model_config = {"extra": "forbid"}

    axis_id: str
    relationship_ids: list[str] = Field(default_factory=list, max_length=16)
    tension_score: float = Field(default=0.0, ge=0.0, le=1.0)
    stability_band: RelationshipStabilityBand = "stable"
    trend: RelationshipTrend = "stable"
    active: bool = False
    last_transition_codes: list[str] = Field(default_factory=list, max_length=8)


class RelationshipTransitionEvent(BaseModel):
    """Committed relationship-state transition emitted by the deterministic engine."""

    model_config = {"extra": "forbid"}

    transition_id: str
    turn_number: int = Field(default=0, ge=0)
    relationship_id: str
    axis_ids: list[str] = Field(default_factory=list, max_length=8)
    transition_code: str
    tension_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    trust_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    alliance_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    dominance_delta: float = Field(default=0.0, ge=-1.0, le=1.0)
    source_evidence: list[RelationshipStateEvidenceRef] = Field(default_factory=list, max_length=8)


class RelationshipStateRecord(BaseModel):
    """Durable relationship-state snapshot committed through planner truth."""

    model_config = {"extra": "forbid"}

    schema_version: str = RELATIONSHIP_STATE_SCHEMA_VERSION
    turn_number: int = Field(default=0, ge=0)
    prior_record_fingerprint: str | None = None
    pair_states: list[RelationshipPairState] = Field(default_factory=list, max_length=64)
    axis_states: list[RelationshipAxisState] = Field(default_factory=list, max_length=32)
    transition_events: list[RelationshipTransitionEvent] = Field(default_factory=list, max_length=64)
    active_relationship_axis_ids: list[str] = Field(default_factory=list, max_length=16)
    dominant_relationship_axis_id: str | None = None
    source_evidence: list[RelationshipStateEvidenceRef] = Field(default_factory=list, max_length=24)
    rationale_codes: list[str] = Field(default_factory=list, max_length=24)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RelationshipDynamicsTarget(BaseModel):
    """Generation-facing target selected from the durable state."""

    model_config = {"extra": "forbid"}

    schema_version: str = RELATIONSHIP_STATE_SCHEMA_VERSION
    target_axis_ids: list[str] = Field(default_factory=list, max_length=8)
    target_relationship_ids: list[str] = Field(default_factory=list, max_length=8)
    required_transition_codes: list[str] = Field(default_factory=list, max_length=8)
    pressure_band: RelationshipStabilityBand = "stable"
    requires_visible_relationship_beat: bool = False
    source_evidence: list[RelationshipStateEvidenceRef] = Field(default_factory=list, max_length=12)
    rationale_codes: list[str] = Field(default_factory=list, max_length=16)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class RelationshipStateValidation(BaseModel):
    """Validation result over schema bounds and structured event compatibility."""

    model_config = {"extra": "forbid"}

    schema_version: str = RELATIONSHIP_STATE_SCHEMA_VERSION
    status: RelationshipValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[RelationshipStateEvidenceRef] = Field(default_factory=list)

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


def _score_delta_map(value: Any) -> dict[str, dict[str, float]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict[str, float]] = {}
    for raw_code, raw_deltas in value.items():
        code = str(raw_code or "").strip()
        if not code or not isinstance(raw_deltas, dict):
            continue
        out[code] = {
            "tension_delta": _bounded_float(raw_deltas.get("tension_delta"), 0.0, minimum=-1.0, maximum=1.0),
            "trust_delta": _bounded_float(raw_deltas.get("trust_delta"), 0.0, minimum=-1.0, maximum=1.0),
            "alliance_delta": _bounded_float(raw_deltas.get("alliance_delta"), 0.0, minimum=-1.0, maximum=1.0),
            "dominance_delta": _bounded_float(raw_deltas.get("dominance_delta"), 0.0, minimum=-1.0, maximum=1.0),
        }
    return out


def normalize_relationship_state_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return normalized relationship-state-machine policy."""

    raw = policy if isinstance(policy, dict) else {}
    thresholds = raw.get("stability_thresholds") if isinstance(raw.get("stability_thresholds"), dict) else {}
    strained_min = _bounded_float(thresholds.get("strained_min"), 0.45, minimum=0.0, maximum=1.0)
    fractured_min = _bounded_float(thresholds.get("fractured_min"), 0.72, minimum=0.0, maximum=1.0)
    if strained_min >= fractured_min:
        strained_min, fractured_min = 0.45, 0.72
    transition_weights = _score_delta_map(raw.get("transition_weights"))
    return {
        "schema_version": RELATIONSHIP_STATE_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "default_tension_score": _bounded_float(raw.get("default_tension_score"), 0.35, minimum=0.0, maximum=1.0),
        "default_trust_score": _bounded_float(raw.get("default_trust_score"), 0.65, minimum=0.0, maximum=1.0),
        "default_alliance_score": _bounded_float(raw.get("default_alliance_score"), 0.2, minimum=0.0, maximum=1.0),
        "default_dominance_score": _bounded_float(raw.get("default_dominance_score"), 0.5, minimum=0.0, maximum=1.0),
        "trend_deadband": _bounded_float(raw.get("trend_deadband"), 0.04, minimum=0.0, maximum=0.5),
        "max_tracked_pairs": _bounded_int(raw.get("max_tracked_pairs"), 24, minimum=1, maximum=64),
        "max_tracked_axes": _bounded_int(raw.get("max_tracked_axes"), 12, minimum=1, maximum=32),
        "max_transition_events": _bounded_int(raw.get("max_transition_events"), 24, minimum=1, maximum=64),
        "stability_thresholds": {
            "strained_min": strained_min,
            "fractured_min": fractured_min,
        },
        "transition_weights": {
            "blame_pressure": {
                "tension_delta": 0.18,
                "trust_delta": -0.08,
                "alliance_delta": 0.0,
                "dominance_delta": 0.03,
            },
            "repair_attempt": {
                "tension_delta": -0.12,
                "trust_delta": 0.08,
                "alliance_delta": 0.02,
                "dominance_delta": -0.01,
            },
            "alliance_shift": {
                "tension_delta": 0.05,
                "trust_delta": -0.02,
                "alliance_delta": 0.14,
                "dominance_delta": 0.02,
            },
            "social_state_shifted": {
                "tension_delta": 0.05,
                "trust_delta": -0.02,
                "alliance_delta": 0.0,
                "dominance_delta": 0.0,
            },
            "high_social_pressure": {
                "tension_delta": 0.08,
                "trust_delta": -0.03,
                "alliance_delta": 0.0,
                "dominance_delta": 0.0,
            },
            "npc_initiative_pressure": {
                "tension_delta": 0.06,
                "trust_delta": -0.02,
                "alliance_delta": 0.0,
                "dominance_delta": 0.04,
            },
            "relationship_axis_pressure": {
                "tension_delta": 0.04,
                "trust_delta": 0.0,
                "alliance_delta": 0.0,
                "dominance_delta": 0.0,
            },
            **transition_weights,
        },
        "allowed_transition_codes": sorted(RELATIONSHIP_TRANSITION_CODES),
        "source": "module_runtime_policy.relationship_state_machine",
    }
