"""Genre-awareness contracts for bounded module-neutral runtime guidance.

The contract treats genre as authored policy and structured realization
evidence. It does not judge generated prose and it never uses legacy Pi labels
as runtime identifiers.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


GENRE_AWARENESS_SCHEMA_VERSION = "genre_awareness.v1"
GENRE_AWARENESS_POLICY_VERSION = "genre_awareness_policy.v1"

GENRE_AWARENESS_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)
GENRE_AWARENESS_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

GENRE_AWARENESS_FAILURE_TARGET_MISMATCH = "genre_awareness_target_mismatch"
GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_EVENT = (
    "genre_awareness_missing_required_event"
)
GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED = (
    "genre_awareness_event_budget_exceeded"
)
GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE = "genre_awareness_unselected_profile"
GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED = (
    "genre_awareness_register_not_allowed"
)
GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION = (
    "genre_awareness_missing_required_convention"
)
GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER = "genre_awareness_forbidden_marker"

GENRE_AWARENESS_FAILURE_CODES: frozenset[str] = frozenset(
    {
        GENRE_AWARENESS_FAILURE_TARGET_MISMATCH,
        GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_EVENT,
        GENRE_AWARENESS_FAILURE_EVENT_BUDGET_EXCEEDED,
        GENRE_AWARENESS_FAILURE_UNSELECTED_PROFILE,
        GENRE_AWARENESS_FAILURE_REGISTER_NOT_ALLOWED,
        GENRE_AWARENESS_FAILURE_MISSING_REQUIRED_CONVENTION,
        GENRE_AWARENESS_FAILURE_FORBIDDEN_MARKER,
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


def _clean_str_list(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if text and text not in out:
            out.append(text)
    return out


def _bounded_int(value: Any, default: int, *, minimum: int, maximum: int) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        parsed = default
    return max(minimum, min(maximum, parsed))


def _marker_ids(value: Any) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        marker_id = ""
        if isinstance(item, dict):
            marker_id = _text(
                item.get("id")
                or item.get("marker_id")
                or item.get("code")
                or item.get("label")
            )
        else:
            marker_id = _text(item)
        if marker_id and marker_id not in out:
            out.append(marker_id)
    return out


@dataclass(frozen=True)
class GenreAwarenessState:
    schema_version: str = GENRE_AWARENESS_SCHEMA_VERSION
    current_genre_profile_id: str | None = None
    prior_genre_profile_id: str | None = None
    selected_registers: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class GenreAwarenessTarget:
    schema_version: str = GENRE_AWARENESS_SCHEMA_VERSION
    policy_version: str = GENRE_AWARENESS_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    genre_profile_id: str | None = None
    selected_registers: list[str] = field(default_factory=list)
    required_conventions: list[str] = field(default_factory=list)
    forbidden_marker_ids: list[str] = field(default_factory=list)
    require_structured_events: bool = False
    max_genre_signals_per_turn: int = 1
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    rationale_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class GenreAwarenessValidation:
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


def default_genre_awareness_policy() -> dict[str, Any]:
    """Return neutral defaults; content modules opt in explicitly."""
    return {
        "schema_version": GENRE_AWARENESS_POLICY_VERSION,
        "enabled": False,
        "genre_profile_id": "",
        "allowed_registers": [],
        "required_conventions": [],
        "forbidden_genre_markers": [],
        "require_structured_events": False,
        "max_genre_signals_per_turn": 1,
        "default_commit_impact": "diagnostic",
        "model_context_visibility": "bounded_genre_profile",
    }


def normalize_genre_awareness_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module policy into a stable JSON-safe genre envelope."""
    raw = policy if isinstance(policy, dict) else {}
    default = default_genre_awareness_policy()
    commit_impact = _text(
        raw.get("default_commit_impact") or default["default_commit_impact"]
    )
    if commit_impact not in GENRE_AWARENESS_COMMIT_IMPACTS:
        commit_impact = default["default_commit_impact"]
    return {
        "schema_version": _text(raw.get("schema_version"))
        or GENRE_AWARENESS_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "genre_profile_id": _text(raw.get("genre_profile_id")),
        "allowed_registers": _clean_str_list(raw.get("allowed_registers")),
        "required_conventions": _clean_str_list(raw.get("required_conventions")),
        "forbidden_marker_ids": _marker_ids(raw.get("forbidden_genre_markers")),
        "require_structured_events": bool(
            raw.get(
                "require_structured_events",
                default["require_structured_events"],
            )
        ),
        "max_genre_signals_per_turn": _bounded_int(
            raw.get("max_genre_signals_per_turn"),
            int(default["max_genre_signals_per_turn"]),
            minimum=0,
            maximum=6,
        ),
        "default_commit_impact": commit_impact,
        "model_context_visibility": _text(raw.get("model_context_visibility"))
        or default["model_context_visibility"],
        "source": "module_runtime_policy.genre_awareness",
    }
