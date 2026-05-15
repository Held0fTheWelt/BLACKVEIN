"""Expectation-variation contracts for bounded turn-level variation.

The contract governs when a turn may introduce a structured variation from
already selected runtime evidence. It validates event IDs, variation types,
budget, setup references, and cooldown evidence rather than judging prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


EXPECTATION_VARIATION_SCHEMA_VERSION = "expectation_variation.v1"
EXPECTATION_VARIATION_POLICY_VERSION = "expectation_variation_policy.v1"

EXPECTATION_VARIATION_SOCIAL_ALIGNMENT_SHIFT = "social_alignment_shift"
EXPECTATION_VARIATION_RESPONDER_HANDOFF = "responder_handoff"
EXPECTATION_VARIATION_PRESSURE_REVERSAL = "pressure_reversal"
EXPECTATION_VARIATION_CONSEQUENCE_RETURN = "consequence_return"
EXPECTATION_VARIATION_BOUNDED_REVEAL = "bounded_reveal"
EXPECTATION_VARIATION_IRONIC_MISREAD = "ironic_misread"
EXPECTATION_VARIATION_SENSORY_REFRAME = "sensory_reframe"
EXPECTATION_VARIATION_SILENCE_PIVOT = "silence_pivot"

EXPECTATION_VARIATION_TYPES: frozenset[str] = frozenset(
    {
        EXPECTATION_VARIATION_SOCIAL_ALIGNMENT_SHIFT,
        EXPECTATION_VARIATION_RESPONDER_HANDOFF,
        EXPECTATION_VARIATION_PRESSURE_REVERSAL,
        EXPECTATION_VARIATION_CONSEQUENCE_RETURN,
        EXPECTATION_VARIATION_BOUNDED_REVEAL,
        EXPECTATION_VARIATION_IRONIC_MISREAD,
        EXPECTATION_VARIATION_SENSORY_REFRAME,
        EXPECTATION_VARIATION_SILENCE_PIVOT,
    }
)

EXPECTATION_VARIATION_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)

EXPECTATION_VARIATION_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

EXPECTATION_VARIATION_FAILURE_OVER_BUDGET = "expectation_variation_over_budget"
EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT = "expectation_variation_unselected_event"
EXPECTATION_VARIATION_FAILURE_MISSING_REQUIRED_EVENT = (
    "expectation_variation_missing_required_event"
)
EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT = "expectation_variation_unearned_event"
EXPECTATION_VARIATION_FAILURE_COOLDOWN_VIOLATION = (
    "expectation_variation_cooldown_violation"
)
EXPECTATION_VARIATION_FAILURE_TARGET_MISMATCH = "expectation_variation_target_mismatch"

EXPECTATION_VARIATION_FAILURE_CODES: frozenset[str] = frozenset(
    {
        EXPECTATION_VARIATION_FAILURE_OVER_BUDGET,
        EXPECTATION_VARIATION_FAILURE_UNSELECTED_EVENT,
        EXPECTATION_VARIATION_FAILURE_MISSING_REQUIRED_EVENT,
        EXPECTATION_VARIATION_FAILURE_UNEARNED_EVENT,
        EXPECTATION_VARIATION_FAILURE_COOLDOWN_VIOLATION,
        EXPECTATION_VARIATION_FAILURE_TARGET_MISMATCH,
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
class ExpectationVariationTarget:
    schema_version: str = EXPECTATION_VARIATION_SCHEMA_VERSION
    policy_version: str = EXPECTATION_VARIATION_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    require_structured_events: bool = False
    max_variation_units_per_turn: int = 1
    cooldown_turns: int = 1
    allowed_variation_types: list[str] = field(default_factory=list)
    selected_variation_ids: list[str] = field(default_factory=list)
    selected_variation_types: list[str] = field(default_factory=list)
    withheld_variation_ids: list[str] = field(default_factory=list)
    required_setup_refs: list[dict[str, Any]] = field(default_factory=list)
    rationale_codes: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ExpectationVariationState:
    schema_version: str = EXPECTATION_VARIATION_SCHEMA_VERSION
    recent_variation_ids: list[str] = field(default_factory=list)
    cooldown_blocked_ids: list[str] = field(default_factory=list)
    selected_variation_ids: list[str] = field(default_factory=list)
    budget_remaining: int = 0
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ExpectationVariationValidation:
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


def default_expectation_variation_policy() -> dict[str, Any]:
    """Return neutral defaults; modules opt in explicitly."""
    return {
        "schema_version": EXPECTATION_VARIATION_POLICY_VERSION,
        "enabled": False,
        "allowed_variation_types": [
            EXPECTATION_VARIATION_SOCIAL_ALIGNMENT_SHIFT,
            EXPECTATION_VARIATION_RESPONDER_HANDOFF,
            EXPECTATION_VARIATION_PRESSURE_REVERSAL,
            EXPECTATION_VARIATION_CONSEQUENCE_RETURN,
            EXPECTATION_VARIATION_BOUNDED_REVEAL,
            EXPECTATION_VARIATION_IRONIC_MISREAD,
            EXPECTATION_VARIATION_SENSORY_REFRAME,
            EXPECTATION_VARIATION_SILENCE_PIVOT,
        ],
        "require_structured_events": False,
        "max_variation_units_per_turn": 1,
        "cooldown_turns": 1,
        "min_setup_refs": 1,
        "max_setup_refs": 6,
        "default_commit_impact": "recover",
        "model_context_visibility": "bounded_structured_only",
    }


def normalize_expectation_variation_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe envelope."""
    raw = policy if isinstance(policy, dict) else {}
    default = default_expectation_variation_policy()
    variation_types = _clean_str_list(
        raw.get("allowed_variation_types"),
        allowed=EXPECTATION_VARIATION_TYPES,
    ) or list(default["allowed_variation_types"])
    commit_impact = _text(raw.get("default_commit_impact") or default["default_commit_impact"])
    if commit_impact not in EXPECTATION_VARIATION_COMMIT_IMPACTS:
        commit_impact = default["default_commit_impact"]
    return {
        "schema_version": _text(raw.get("schema_version"))
        or EXPECTATION_VARIATION_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "allowed_variation_types": variation_types,
        "require_structured_events": bool(
            raw.get("require_structured_events", default["require_structured_events"])
        ),
        "max_variation_units_per_turn": _bounded_int(
            raw.get("max_variation_units_per_turn"),
            int(default["max_variation_units_per_turn"]),
            minimum=0,
            maximum=4,
        ),
        "cooldown_turns": _bounded_int(
            raw.get("cooldown_turns"),
            int(default["cooldown_turns"]),
            minimum=0,
            maximum=8,
        ),
        "min_setup_refs": _bounded_int(
            raw.get("min_setup_refs"),
            int(default["min_setup_refs"]),
            minimum=0,
            maximum=8,
        ),
        "max_setup_refs": _bounded_int(
            raw.get("max_setup_refs"),
            int(default["max_setup_refs"]),
            minimum=1,
            maximum=12,
        ),
        "default_commit_impact": commit_impact,
        "model_context_visibility": _text(raw.get("model_context_visibility"))
        or default["model_context_visibility"],
        "source": "module_runtime_policy.expectation_variation",
    }
