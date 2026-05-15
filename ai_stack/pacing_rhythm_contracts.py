"""Pacing-rhythm contracts for the runtime-intelligence aspect.

The contract is structural: policy, planner state, and typed realization
counts are the oracle. Generated prose wording is not.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


PACING_RHYTHM_SCHEMA_VERSION = "pacing_rhythm.v1"
PACING_RHYTHM_POLICY_VERSION = "pacing_rhythm_policy.v1"

PacingRhythmCadence = Literal["breathe", "hold", "press", "release", "pivot", "interrupt"]
PacingRhythmTempoArc = Literal["still", "compressed", "standard", "accelerating", "releasing"]
PacingRhythmResponseShape = Literal["pause", "single_beat", "exchange", "multi_reaction"]
PacingRhythmTurnChangePolicy = Literal[
    "allow_hold",
    "prefer_actor_turn_change",
    "require_actor_turn_change",
    "silence_or_action_only",
]
PacingRhythmValidationStatus = Literal["approved", "degraded", "rejected", "not_applicable"]

PACING_RHYTHM_CADENCES: frozenset[str] = frozenset(
    {"breathe", "hold", "press", "release", "pivot", "interrupt"}
)
PACING_RHYTHM_TEMPO_ARCS: frozenset[str] = frozenset(
    {"still", "compressed", "standard", "accelerating", "releasing"}
)
PACING_RHYTHM_RESPONSE_SHAPES: frozenset[str] = frozenset(
    {"pause", "single_beat", "exchange", "multi_reaction"}
)
PACING_RHYTHM_TURN_CHANGE_POLICIES: frozenset[str] = frozenset(
    {
        "allow_hold",
        "prefer_actor_turn_change",
        "require_actor_turn_change",
        "silence_or_action_only",
    }
)
PACING_RHYTHM_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

PACING_RHYTHM_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "pacing_rhythm_underrealized_cadence",
        "pacing_rhythm_visible_density_exceeded",
        "pacing_rhythm_required_turn_change_missing",
        "pacing_rhythm_pause_obligation_lost",
        "pacing_rhythm_forced_speech_violation",
        "pacing_rhythm_flat_repetition",
        "pacing_rhythm_target_mismatch",
    }
)


class PacingRhythmEvidenceRef(BaseModel):
    """Pointer to a declared field, not a prose excerpt."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PacingRhythmState(BaseModel):
    """Bounded prior/current rhythm state carried across turns."""

    model_config = {"extra": "forbid"}

    schema_version: str = PACING_RHYTHM_SCHEMA_VERSION
    current_cadence: PacingRhythmCadence | None = None
    prior_cadence: PacingRhythmCadence | None = None
    recent_cadences: list[PacingRhythmCadence] = Field(default_factory=list, max_length=6)
    repeated_cadence_count: int = Field(default=0, ge=0, le=6)
    pressure_streak: int = Field(default=0, ge=0, le=12)
    release_due: bool = False
    pause_obligation_active: bool = False
    last_pacing_mode: str | None = None
    last_scene_function: str | None = None
    last_beat_id: str | None = None
    source_evidence: list[PacingRhythmEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PacingRhythmTarget(BaseModel):
    """Planner-selected rhythm target for the next visible realization."""

    model_config = {"extra": "forbid"}

    schema_version: str = PACING_RHYTHM_SCHEMA_VERSION
    cadence: PacingRhythmCadence
    tempo_arc: PacingRhythmTempoArc
    response_shape: PacingRhythmResponseShape
    turn_change_policy: PacingRhythmTurnChangePolicy
    min_visible_blocks: int = Field(default=1, ge=0, le=8)
    max_visible_blocks: int = Field(default=6, ge=1, le=12)
    min_actor_turns: int = Field(default=0, ge=0, le=4)
    max_actor_turns: int = Field(default=4, ge=0, le=4)
    requires_pause: bool = False
    blocks_forced_speech: bool = False
    release_due_after_turn: bool = False
    source_evidence: list[PacingRhythmEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class PacingRhythmValidation(BaseModel):
    """Validation result over structured realization evidence."""

    model_config = {"extra": "forbid"}

    schema_version: str = PACING_RHYTHM_SCHEMA_VERSION
    status: PacingRhythmValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[PacingRhythmEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def normalize_pacing_rhythm_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe policy envelope with contract-known keys."""

    raw = policy if isinstance(policy, dict) else {}
    cadence_profiles = (
        raw.get("cadence_profiles")
        if isinstance(raw.get("cadence_profiles"), dict)
        else {}
    )
    pacing_mode_profiles = (
        raw.get("pacing_mode_profiles")
        if isinstance(raw.get("pacing_mode_profiles"), dict)
        else {}
    )
    scene_function_profiles = (
        raw.get("scene_function_profiles")
        if isinstance(raw.get("scene_function_profiles"), dict)
        else {}
    )
    return {
        "schema_version": PACING_RHYTHM_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "cadence_profiles": cadence_profiles,
        "pacing_mode_profiles": pacing_mode_profiles,
        "scene_function_profiles": scene_function_profiles,
        "max_repeated_cadence_count": _bounded_int(
            raw.get("max_repeated_cadence_count"), 2, minimum=1, maximum=6
        ),
        "default_max_visible_blocks": _bounded_int(
            raw.get("default_max_visible_blocks"), 6, minimum=1, maximum=12
        ),
        "source": "module_runtime_policy.pacing_rhythm",
    }
