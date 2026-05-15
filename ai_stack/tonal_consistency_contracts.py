"""Tonal-consistency contracts for bounded runtime style drift evidence.

The contract is structural: normalized module policy, selected tone dimensions,
structured classification, and policy-declared marker classes are the oracle.
Generated prose and judge labels are not pass/fail oracles.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TONAL_CONSISTENCY_SCHEMA_VERSION = "tonal_consistency.v1"
TONAL_CONSISTENCY_POLICY_VERSION = "tonal_consistency_policy.v1"

TonalConsistencyDriftBehavior = Literal["diagnostic", "recover", "reject"]
TonalConsistencyValidationStatus = Literal[
    "approved",
    "degraded",
    "rejected",
    "not_applicable",
]

TONAL_CONSISTENCY_DRIFT_BEHAVIORS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)
TONAL_CONSISTENCY_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

TONAL_CONSISTENCY_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "tonal_consistency_target_mismatch",
        "tonal_consistency_classification_missing",
        "tonal_consistency_required_dimension_missing",
        "tonal_consistency_forbidden_marker_detected",
        "tonal_consistency_register_mismatch",
        "tonal_consistency_wrong_genre",
    }
)


class TonalConsistencyEvidenceRef(BaseModel):
    """Pointer to declared source data, not a prose excerpt."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TonalConsistencyTarget(BaseModel):
    """Planner-selected tone target for one visible realization."""

    model_config = {"extra": "forbid"}

    schema_version: str = TONAL_CONSISTENCY_SCHEMA_VERSION
    policy_version: str = TONAL_CONSISTENCY_POLICY_VERSION
    policy_enabled: bool = False
    profile_id: str | None = None
    target_dimension_ids: list[str] = Field(default_factory=list, max_length=16)
    required_dimension_ids: list[str] = Field(default_factory=list, max_length=16)
    allowed_registers: list[str] = Field(default_factory=list, max_length=12)
    forbidden_genre_labels: list[str] = Field(default_factory=list, max_length=12)
    forbidden_marker_map: dict[str, list[str]] = Field(default_factory=dict)
    require_structured_classification: bool = True
    min_required_dimensions_present: int = Field(default=1, ge=0, le=16)
    max_forbidden_marker_hits: int = Field(default=0, ge=0, le=20)
    drift_behavior: TonalConsistencyDriftBehavior = "diagnostic"
    scene_function: str | None = None
    pressure_band: str | None = None
    source_evidence: list[TonalConsistencyEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TonalConsistencyClassification(BaseModel):
    """Structured tone classification evidence consumed by validation."""

    model_config = {"extra": "forbid"}

    schema_version: str = TONAL_CONSISTENCY_SCHEMA_VERSION
    structured_classification_present: bool = False
    realized_dimension_ids: list[str] = Field(default_factory=list, max_length=16)
    register_label: str | None = None
    genre_label: str | None = None
    forbidden_marker_hits: dict[str, int] = Field(default_factory=dict)
    marker_hit_count: int = Field(default=0, ge=0)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    source_evidence: list[TonalConsistencyEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TonalConsistencyValidation(BaseModel):
    """Validation result over structured tonal consistency evidence."""

    model_config = {"extra": "forbid"}

    schema_version: str = TONAL_CONSISTENCY_SCHEMA_VERSION
    status: TonalConsistencyValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[TonalConsistencyEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _clean_str_list(value: Any) -> list[str]:
    items = value if isinstance(value, (list, tuple, set)) else []
    out: list[str] = []
    for item in items:
        text = _clean_text(item)
        if text and text not in out:
            out.append(text)
    return out


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _clean_marker_map(value: Any) -> dict[str, list[str]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, list[str]] = {}
    for key, markers in value.items():
        label = _clean_text(key)
        cleaned = _clean_str_list(markers)
        if label and cleaned:
            out[label] = cleaned
    return out


def _clean_profile_map(value: Any) -> dict[str, dict[str, Any]]:
    if not isinstance(value, dict):
        return {}
    out: dict[str, dict[str, Any]] = {}
    for key, profile in value.items():
        label = _clean_text(key)
        if label and isinstance(profile, dict):
            out[label] = _json_safe(profile)
    return out


def normalize_tonal_consistency_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe policy envelope with contract-known keys."""

    raw = policy if isinstance(policy, dict) else {}
    behavior = _clean_text(raw.get("default_drift_behavior") or "diagnostic")
    if behavior not in TONAL_CONSISTENCY_DRIFT_BEHAVIORS:
        behavior = "diagnostic"
    return {
        "schema_version": TONAL_CONSISTENCY_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", False)),
        "tone_profiles": _clean_profile_map(raw.get("tone_profiles")),
        "default_profile_id": _clean_text(raw.get("default_profile_id")) or None,
        "profile_by_scene_function": {
            str(key): _clean_text(value)
            for key, value in (
                raw.get("profile_by_scene_function")
                if isinstance(raw.get("profile_by_scene_function"), dict)
                else {}
            ).items()
            if _clean_text(key) and _clean_text(value)
        },
        "allowed_registers": _clean_str_list(raw.get("allowed_registers")),
        "forbidden_genre_labels": _clean_str_list(raw.get("forbidden_genre_labels")),
        "forbidden_marker_map": _clean_marker_map(raw.get("forbidden_marker_map")),
        "require_structured_classification": bool(
            raw.get("require_structured_classification", True)
        ),
        "min_required_dimensions_present": _bounded_int(
            raw.get("min_required_dimensions_present"), 1, minimum=0, maximum=16
        ),
        "max_forbidden_marker_hits": _bounded_int(
            raw.get("max_forbidden_marker_hits"), 0, minimum=0, maximum=20
        ),
        "default_drift_behavior": behavior,
        "model_context_visibility": _clean_text(
            raw.get("model_context_visibility") or "bounded_tone_target"
        )
        or "bounded_tone_target",
        "source": "module_runtime_policy.tonal_consistency",
    }
