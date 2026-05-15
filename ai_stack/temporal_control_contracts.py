"""Temporal-control contracts for bounded turn-level time handling.

The contract is structural: module policy, committed-turn references, selected
operation, and typed realization events are the oracle. Generated prose wording
is not.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


TEMPORAL_CONTROL_SCHEMA_VERSION = "temporal_control.v1"
TEMPORAL_CONTROL_POLICY_VERSION = "temporal_control_policy.v1"

TemporalControlOperation = Literal[
    "hold_current_moment",
    "advance_elapsed_time",
    "recall_committed_past",
    "summarize_gap",
    "resume_present",
]
TemporalControlValidationStatus = Literal[
    "approved",
    "degraded",
    "rejected",
    "not_applicable",
]

TEMPORAL_CONTROL_OPERATIONS: frozenset[str] = frozenset(
    {
        "hold_current_moment",
        "advance_elapsed_time",
        "recall_committed_past",
        "summarize_gap",
        "resume_present",
    }
)
TEMPORAL_CONTROL_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)
TEMPORAL_CONTROL_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

TEMPORAL_CONTROL_FAILURE_TARGET_MISMATCH = "temporal_control_target_mismatch"
TEMPORAL_CONTROL_FAILURE_OPERATION_NOT_ALLOWED = (
    "temporal_control_operation_not_allowed"
)
TEMPORAL_CONTROL_FAILURE_MISSING_REQUIRED_EVENT = (
    "temporal_control_missing_required_event"
)
TEMPORAL_CONTROL_FAILURE_UNSELECTED_EVENT = "temporal_control_unselected_event"
TEMPORAL_CONTROL_FAILURE_UNCOMMITTED_SOURCE = (
    "temporal_control_uncommitted_source"
)
TEMPORAL_CONTROL_FAILURE_HISTORY_REWRITE_ATTEMPT = (
    "temporal_control_history_rewrite_attempt"
)
TEMPORAL_CONTROL_FAILURE_BRANCH_STATE_ADOPTION = (
    "temporal_control_branch_state_adoption"
)
TEMPORAL_CONTROL_FAILURE_UNBOUNDED_JUMP = "temporal_control_unbounded_jump"

TEMPORAL_CONTROL_FAILURE_CODES: frozenset[str] = frozenset(
    {
        TEMPORAL_CONTROL_FAILURE_TARGET_MISMATCH,
        TEMPORAL_CONTROL_FAILURE_OPERATION_NOT_ALLOWED,
        TEMPORAL_CONTROL_FAILURE_MISSING_REQUIRED_EVENT,
        TEMPORAL_CONTROL_FAILURE_UNSELECTED_EVENT,
        TEMPORAL_CONTROL_FAILURE_UNCOMMITTED_SOURCE,
        TEMPORAL_CONTROL_FAILURE_HISTORY_REWRITE_ATTEMPT,
        TEMPORAL_CONTROL_FAILURE_BRANCH_STATE_ADOPTION,
        TEMPORAL_CONTROL_FAILURE_UNBOUNDED_JUMP,
    }
)


class TemporalControlEvidenceRef(BaseModel):
    """Pointer to a declared structured field, not a prose excerpt."""

    model_config = {"extra": "forbid"}

    source: str
    field: str
    value: Any = None

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TemporalControlState(BaseModel):
    """Bounded temporal state carried through committed planner truth."""

    model_config = {"extra": "forbid"}

    schema_version: str = TEMPORAL_CONTROL_SCHEMA_VERSION
    current_operation: TemporalControlOperation | None = None
    prior_operation: TemporalControlOperation | None = None
    anchor_turn_id: str | None = None
    anchor_turn_number: int | None = Field(default=None, ge=0)
    elapsed_turns: int = Field(default=0, ge=0, le=24)
    recalled_turn_ids: list[str] = Field(default_factory=list, max_length=12)
    recalled_consequence_ids: list[str] = Field(default_factory=list, max_length=12)
    source_evidence: list[TemporalControlEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TemporalControlTarget(BaseModel):
    """Planner-selected time operation for the next visible realization."""

    model_config = {"extra": "forbid"}

    schema_version: str = TEMPORAL_CONTROL_SCHEMA_VERSION
    policy_version: str = TEMPORAL_CONTROL_POLICY_VERSION
    policy_enabled: bool = False
    operation: TemporalControlOperation = "resume_present"
    allowed_operations: list[TemporalControlOperation] = Field(default_factory=list)
    commit_impact: str = "recover"
    require_structured_events: bool = False
    max_recalled_turns: int = Field(default=3, ge=0, le=12)
    max_elapsed_turns: int = Field(default=4, ge=0, le=24)
    anchor_turn_id: str | None = None
    anchor_turn_number: int | None = Field(default=None, ge=0)
    recalled_turn_ids: list[str] = Field(default_factory=list, max_length=12)
    recalled_consequence_ids: list[str] = Field(default_factory=list, max_length=12)
    source_evidence: list[TemporalControlEvidenceRef] = Field(default_factory=list)
    rationale_codes: list[str] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


class TemporalControlValidation(BaseModel):
    """Validation result over structured temporal-control events."""

    model_config = {"extra": "forbid"}

    schema_version: str = TEMPORAL_CONTROL_SCHEMA_VERSION
    status: TemporalControlValidationStatus
    contract_pass: bool
    failure_codes: list[str] = Field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = Field(default_factory=dict)
    actual: dict[str, Any] = Field(default_factory=dict)
    source_evidence: list[TemporalControlEvidenceRef] = Field(default_factory=list)

    def to_runtime_dict(self) -> dict[str, Any]:
        return self.model_dump(mode="json")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    if value is None:
        return []
    return [value]


def _clean_str_list(value: Any, *, allowed: frozenset[str] | None = None) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _clean_text(item)
        if not text:
            continue
        if allowed is not None and text not in allowed:
            continue
        if text not in out:
            out.append(text)
    return out


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def default_temporal_control_policy() -> dict[str, Any]:
    """Return neutral defaults; modules opt in explicitly."""

    return {
        "schema_version": TEMPORAL_CONTROL_POLICY_VERSION,
        "enabled": False,
        "allowed_operations": [
            "hold_current_moment",
            "advance_elapsed_time",
            "recall_committed_past",
            "summarize_gap",
            "resume_present",
        ],
        "require_structured_events": False,
        "max_recalled_turns": 3,
        "max_elapsed_turns": 4,
        "default_commit_impact": "recover",
        "model_context_visibility": "bounded_committed_time_refs",
    }


def normalize_temporal_control_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe envelope."""

    raw = policy if isinstance(policy, dict) else {}
    default = default_temporal_control_policy()
    allowed_operations = _clean_str_list(
        raw.get("allowed_operations"),
        allowed=TEMPORAL_CONTROL_OPERATIONS,
    ) or list(default["allowed_operations"])
    commit_impact = _clean_text(
        raw.get("default_commit_impact") or default["default_commit_impact"]
    )
    if commit_impact not in TEMPORAL_CONTROL_COMMIT_IMPACTS:
        commit_impact = str(default["default_commit_impact"])
    return {
        "schema_version": _clean_text(raw.get("schema_version"))
        or TEMPORAL_CONTROL_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "allowed_operations": allowed_operations,
        "require_structured_events": bool(
            raw.get("require_structured_events", default["require_structured_events"])
        ),
        "max_recalled_turns": _bounded_int(
            raw.get("max_recalled_turns"),
            int(default["max_recalled_turns"]),
            minimum=0,
            maximum=12,
        ),
        "max_elapsed_turns": _bounded_int(
            raw.get("max_elapsed_turns"),
            int(default["max_elapsed_turns"]),
            minimum=0,
            maximum=24,
        ),
        "default_commit_impact": commit_impact,
        "model_context_visibility": _clean_text(
            raw.get("model_context_visibility")
            or default["model_context_visibility"]
        ),
        "source": "module_runtime_policy.temporal_control",
    }


def temporal_control_policy_from_module_runtime(
    module_runtime_policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Read the temporal-control policy from the neutral module-runtime shape."""

    raw = module_runtime_policy if isinstance(module_runtime_policy, dict) else {}
    direct = raw.get("temporal_control_policy")
    if isinstance(direct, dict):
        return normalize_temporal_control_policy(direct)
    governance = (
        raw.get("runtime_governance_policy")
        if isinstance(raw.get("runtime_governance_policy"), dict)
        else {}
    )
    nested = governance.get("temporal_control")
    return normalize_temporal_control_policy(nested if isinstance(nested, dict) else {})
