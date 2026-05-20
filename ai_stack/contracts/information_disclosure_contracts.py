"""Information-disclosure contracts for bounded reveal control.

The contract is intentionally structural: content policy declares what may be
surfaced, the runtime selects eligible units, and validation checks structured
events rather than generated prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


INFORMATION_DISCLOSURE_SCHEMA_VERSION = "information_disclosure.v1"
INFORMATION_DISCLOSURE_POLICY_VERSION = "information_disclosure_policy.v1"

DISCLOSURE_STAGES: frozenset[str] = frozenset(
    {"seed", "hint", "complicate", "confirm", "payoff", "withhold"}
)
DISCLOSURE_MODES: frozenset[str] = frozenset(
    {
        "visible_hint",
        "implication",
        "redirection",
        "withheld",
        "confirmation",
        "payoff",
    }
)
DISCLOSURE_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)
DISCLOSURE_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

DISCLOSURE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        "information_disclosure_missing_required_event",
        "information_disclosure_over_budget",
        "information_disclosure_forbidden_unit",
        "information_disclosure_forbidden_stage",
        "information_disclosure_forbidden_mode",
    }
)


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _text(value: Any) -> str:
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
        text = _text(item)
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


@dataclass(frozen=True)
class InformationDisclosureUnit:
    id: str
    stage: str = "hint"
    allowed_modes: list[str] = field(default_factory=lambda: ["visible_hint"])
    forbidden_before: list[str] = field(default_factory=list)
    unlock_conditions: dict[str, Any] = field(default_factory=dict)
    semantic_profile: dict[str, Any] = field(default_factory=dict)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class InformationDisclosureTarget:
    schema_version: str = INFORMATION_DISCLOSURE_SCHEMA_VERSION
    policy_version: str = INFORMATION_DISCLOSURE_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    require_structured_events: bool = False
    max_visible_units_per_turn: int = 0
    selected_unit_ids: list[str] = field(default_factory=list)
    allowed_unit_ids: list[str] = field(default_factory=list)
    withheld_unit_ids: list[str] = field(default_factory=list)
    forbidden_unit_ids: list[str] = field(default_factory=list)
    selected_units: list[dict[str, Any]] = field(default_factory=list)
    disclosure_mode: str | None = None
    rationale_codes: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class InformationDisclosureValidation:
    schema_version: str
    status: str
    contract_pass: bool
    failure_codes: list[str] = field(default_factory=list)
    feedback_code: str | None = None
    target: dict[str, Any] = field(default_factory=dict)
    actual: dict[str, Any] = field(default_factory=dict)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def normalize_information_disclosure_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Return a JSON-safe disclosure-control policy envelope."""
    raw = policy if isinstance(policy, dict) else {}
    raw_units = raw.get("units") if isinstance(raw.get("units"), list) else []
    units: list[dict[str, Any]] = []
    for row in raw_units:
        if not isinstance(row, dict):
            continue
        unit_id = _text(row.get("id") or row.get("unit_id"))
        if not unit_id:
            continue
        stage = _text(row.get("stage")) or "hint"
        if stage not in DISCLOSURE_STAGES:
            stage = "hint"
        allowed_modes = _clean_str_list(row.get("allowed_modes"), allowed=DISCLOSURE_MODES)
        if not allowed_modes:
            allowed_modes = ["withheld"] if stage == "withhold" else ["visible_hint"]
        units.append(
            InformationDisclosureUnit(
                id=unit_id,
                stage=stage,
                allowed_modes=allowed_modes,
                forbidden_before=_clean_str_list(row.get("forbidden_before")),
                unlock_conditions=row.get("unlock_conditions")
                if isinstance(row.get("unlock_conditions"), dict)
                else {},
                semantic_profile=row.get("semantic_profile")
                if isinstance(row.get("semantic_profile"), dict)
                else {},
                source_evidence=[
                    _json_safe(item)
                    for item in _as_list(row.get("source_evidence"))
                    if isinstance(item, dict)
                ],
                metadata=row.get("metadata") if isinstance(row.get("metadata"), dict) else {},
            ).to_dict()
        )
    commit_impact = _text(raw.get("default_commit_impact") or "diagnostic")
    if commit_impact not in DISCLOSURE_COMMIT_IMPACTS:
        commit_impact = "diagnostic"
    return {
        "schema_version": _text(raw.get("schema_version"))
        or INFORMATION_DISCLOSURE_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", bool(units))),
        "default_commit_impact": commit_impact,
        "require_structured_events": bool(raw.get("require_structured_events", False)),
        "max_visible_units_per_turn": _bounded_int(
            raw.get("max_visible_units_per_turn"),
            1 if units else 0,
            minimum=0,
            maximum=6,
        ),
        "units": units,
        "source": "module_runtime_policy.information_disclosure",
    }
