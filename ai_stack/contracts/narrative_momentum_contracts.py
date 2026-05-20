"""Narrative-momentum contracts for bounded turn-level pacing state.

The contract turns the Capability Matrix momentum row into a semantic runtime
aspect. Policy, state machine, structured events, and ledger fields are the
oracle; historical Pi labels and generated prose are not.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


NARRATIVE_MOMENTUM_SCHEMA_VERSION = "narrative_momentum.v1"
NARRATIVE_MOMENTUM_POLICY_VERSION = "narrative_momentum_policy.v1"

NARRATIVE_MOMENTUM_RESTING = "resting"
NARRATIVE_MOMENTUM_BUILDING = "building"
NARRATIVE_MOMENTUM_DRIVING = "driving"
NARRATIVE_MOMENTUM_CRESTING = "cresting"
NARRATIVE_MOMENTUM_RELEASING = "releasing"
NARRATIVE_MOMENTUM_STALLED = "stalled"

NARRATIVE_MOMENTUM_STATES: frozenset[str] = frozenset(
    {
        NARRATIVE_MOMENTUM_RESTING,
        NARRATIVE_MOMENTUM_BUILDING,
        NARRATIVE_MOMENTUM_DRIVING,
        NARRATIVE_MOMENTUM_CRESTING,
        NARRATIVE_MOMENTUM_RELEASING,
        NARRATIVE_MOMENTUM_STALLED,
    }
)

NARRATIVE_MOMENTUM_TRENDS: frozenset[str] = frozenset(
    {"falling", "stable", "rising"}
)

NARRATIVE_MOMENTUM_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)

NARRATIVE_MOMENTUM_FAILURE_TARGET_MISSING = "narrative_momentum_target_missing"
NARRATIVE_MOMENTUM_FAILURE_TRANSITION_FORBIDDEN = (
    "narrative_momentum_transition_forbidden"
)
NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING = "narrative_momentum_event_missing"
NARRATIVE_MOMENTUM_FAILURE_VELOCITY_EXCEEDED = (
    "narrative_momentum_velocity_exceeded"
)
NARRATIVE_MOMENTUM_FAILURE_STALL_BUDGET_EXCEEDED = (
    "narrative_momentum_stall_budget_exceeded"
)
NARRATIVE_MOMENTUM_FAILURE_SOURCE_REF_INVALID = (
    "narrative_momentum_source_ref_invalid"
)

NARRATIVE_MOMENTUM_FAILURE_CODES: frozenset[str] = frozenset(
    {
        NARRATIVE_MOMENTUM_FAILURE_TARGET_MISSING,
        NARRATIVE_MOMENTUM_FAILURE_TRANSITION_FORBIDDEN,
        NARRATIVE_MOMENTUM_FAILURE_EVENT_MISSING,
        NARRATIVE_MOMENTUM_FAILURE_VELOCITY_EXCEEDED,
        NARRATIVE_MOMENTUM_FAILURE_STALL_BUDGET_EXCEEDED,
        NARRATIVE_MOMENTUM_FAILURE_SOURCE_REF_INVALID,
    }
)

NARRATIVE_MOMENTUM_ALLOWED_SOURCE_REFS: frozenset[str] = frozenset(
    {
        "scene_energy",
        "scene_energy_target",
        "scene_energy_transition",
        "pacing_rhythm",
        "pacing_rhythm_target",
        "pacing_cadence",
        "social_pressure",
        "social_pressure_target",
        "social_pressure_band",
        "expectation_variation",
        "expectation_variation_target",
        "expectation_variation_signal",
        "semantic_move",
        "scene_plan_record",
        "prior_narrative_momentum_state",
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
        key = _text(raw_key)
        if not key:
            continue
        out[key] = _bounded_float(raw_score, 0.0, minimum=0.0, maximum=1.0)
    return out


def default_narrative_momentum_policy() -> dict[str, Any]:
    """Return neutral defaults; modules opt in explicitly."""

    return {
        "schema_version": NARRATIVE_MOMENTUM_POLICY_VERSION,
        "enabled": False,
        "default_score": 0.35,
        "state_thresholds": {
            "resting_max": 0.25,
            "driving_min": 0.55,
            "cresting_min": 0.82,
            "release_drop_min": 0.12,
            "trend_deadband": 0.05,
        },
        "allowed_transitions": {
            NARRATIVE_MOMENTUM_RESTING: [
                NARRATIVE_MOMENTUM_RESTING,
                NARRATIVE_MOMENTUM_BUILDING,
            ],
            NARRATIVE_MOMENTUM_BUILDING: [
                NARRATIVE_MOMENTUM_BUILDING,
                NARRATIVE_MOMENTUM_DRIVING,
                NARRATIVE_MOMENTUM_RELEASING,
                NARRATIVE_MOMENTUM_STALLED,
            ],
            NARRATIVE_MOMENTUM_DRIVING: [
                NARRATIVE_MOMENTUM_DRIVING,
                NARRATIVE_MOMENTUM_CRESTING,
                NARRATIVE_MOMENTUM_RELEASING,
                NARRATIVE_MOMENTUM_STALLED,
            ],
            NARRATIVE_MOMENTUM_CRESTING: [
                NARRATIVE_MOMENTUM_CRESTING,
                NARRATIVE_MOMENTUM_RELEASING,
                NARRATIVE_MOMENTUM_DRIVING,
            ],
            NARRATIVE_MOMENTUM_RELEASING: [
                NARRATIVE_MOMENTUM_RELEASING,
                NARRATIVE_MOMENTUM_RESTING,
                NARRATIVE_MOMENTUM_BUILDING,
            ],
            NARRATIVE_MOMENTUM_STALLED: [
                NARRATIVE_MOMENTUM_STALLED,
                NARRATIVE_MOMENTUM_BUILDING,
                NARRATIVE_MOMENTUM_RELEASING,
            ],
        },
        "source_weights": {
            "scene_energy_transition": {
                "release": 0.28,
                "deescalate": 0.32,
                "hold": 0.45,
                "pivot": 0.6,
                "rise": 0.74,
                "interrupt": 0.88,
            },
            "pacing_cadence": {
                "breathe": 0.26,
                "release": 0.34,
                "hold": 0.44,
                "pivot": 0.59,
                "press": 0.74,
                "interrupt": 0.86,
            },
            "social_pressure_band": {
                "low": 0.28,
                "moderate": 0.52,
                "high": 0.78,
            },
            "expectation_variation_signal": {
                "absent": 0.42,
                "selected": 0.66,
                "withheld": 0.5,
            },
            "semantic_move": {
                "observe": 0.34,
                "wait": 0.32,
                "question": 0.44,
                "challenge": 0.68,
                "escalate": 0.76,
                "deescalate": 0.36,
            },
        },
        "decay_per_turn": 0.05,
        "max_velocity_delta": 0.4,
        "stall_budget_turns": 2,
        "require_structured_events": False,
        "min_progress_event_count": 0,
        "default_commit_impact": "recover",
        "model_context_visibility": "bounded_momentum_state",
    }


def normalize_narrative_momentum_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe envelope."""

    raw = policy if isinstance(policy, dict) else {}
    default = default_narrative_momentum_policy()
    thresholds_raw = (
        raw.get("state_thresholds") if isinstance(raw.get("state_thresholds"), dict) else {}
    )
    resting_max = _bounded_float(
        thresholds_raw.get("resting_max"),
        default["state_thresholds"]["resting_max"],
        minimum=0.0,
        maximum=0.6,
    )
    driving_min = _bounded_float(
        thresholds_raw.get("driving_min"),
        default["state_thresholds"]["driving_min"],
        minimum=0.1,
        maximum=0.95,
    )
    cresting_min = _bounded_float(
        thresholds_raw.get("cresting_min"),
        default["state_thresholds"]["cresting_min"],
        minimum=0.2,
        maximum=1.0,
    )
    if not (resting_max < driving_min < cresting_min):
        resting_max = default["state_thresholds"]["resting_max"]
        driving_min = default["state_thresholds"]["driving_min"]
        cresting_min = default["state_thresholds"]["cresting_min"]

    allowed_raw = (
        raw.get("allowed_transitions")
        if isinstance(raw.get("allowed_transitions"), dict)
        else {}
    )
    transitions: dict[str, list[str]] = {}
    for state in sorted(NARRATIVE_MOMENTUM_STATES):
        default_next = default["allowed_transitions"].get(state, [state])
        configured = _clean_str_list(
            allowed_raw.get(state),
            allowed=NARRATIVE_MOMENTUM_STATES,
        )
        transitions[state] = configured or list(default_next)

    source_weights_raw = (
        raw.get("source_weights") if isinstance(raw.get("source_weights"), dict) else {}
    )
    source_weights: dict[str, dict[str, float]] = {}
    for source, default_map in default["source_weights"].items():
        values = dict(default_map)
        values.update(_score_map(source_weights_raw.get(source)))
        source_weights[source] = values

    commit_impact = _text(raw.get("default_commit_impact") or default["default_commit_impact"])
    if commit_impact not in NARRATIVE_MOMENTUM_COMMIT_IMPACTS:
        commit_impact = default["default_commit_impact"]

    return {
        "schema_version": _text(raw.get("schema_version"))
        or NARRATIVE_MOMENTUM_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "default_score": _bounded_float(
            raw.get("default_score"),
            default["default_score"],
            minimum=0.0,
            maximum=1.0,
        ),
        "state_thresholds": {
            "resting_max": resting_max,
            "driving_min": driving_min,
            "cresting_min": cresting_min,
            "release_drop_min": _bounded_float(
                thresholds_raw.get("release_drop_min"),
                default["state_thresholds"]["release_drop_min"],
                minimum=0.0,
                maximum=0.5,
            ),
            "trend_deadband": _bounded_float(
                thresholds_raw.get("trend_deadband"),
                default["state_thresholds"]["trend_deadband"],
                minimum=0.0,
                maximum=0.4,
            ),
        },
        "allowed_transitions": transitions,
        "source_weights": source_weights,
        "decay_per_turn": _bounded_float(
            raw.get("decay_per_turn"),
            default["decay_per_turn"],
            minimum=0.0,
            maximum=0.5,
        ),
        "max_velocity_delta": _bounded_float(
            raw.get("max_velocity_delta"),
            default["max_velocity_delta"],
            minimum=0.05,
            maximum=1.0,
        ),
        "stall_budget_turns": _bounded_int(
            raw.get("stall_budget_turns"),
            default["stall_budget_turns"],
            minimum=0,
            maximum=8,
        ),
        "require_structured_events": bool(
            raw.get("require_structured_events", default["require_structured_events"])
        ),
        "min_progress_event_count": _bounded_int(
            raw.get("min_progress_event_count"),
            default["min_progress_event_count"],
            minimum=0,
            maximum=4,
        ),
        "default_commit_impact": commit_impact,
        "model_context_visibility": _text(raw.get("model_context_visibility"))
        or default["model_context_visibility"],
        "source": "module_runtime_policy.narrative_momentum",
    }


@dataclass(frozen=True)
class NarrativeMomentumState:
    schema_version: str = NARRATIVE_MOMENTUM_SCHEMA_VERSION
    current_state: str = NARRATIVE_MOMENTUM_RESTING
    current_score: float = 0.0
    prior_state: str | None = None
    prior_score: float | None = None
    trend: str = "stable"
    velocity: float = 0.0
    stall_turn_count: int = 0
    active_source_count: int = 0
    source_evidence: list[dict[str, Any]] = field(default_factory=list)
    rationale_codes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeMomentumTarget:
    schema_version: str = NARRATIVE_MOMENTUM_SCHEMA_VERSION
    policy_version: str = NARRATIVE_MOMENTUM_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    target_state: str = NARRATIVE_MOMENTUM_RESTING
    target_score: float = 0.0
    allowed_next_states: list[str] = field(default_factory=list)
    requires_forward_motion: bool = False
    release_allowed: bool = False
    min_progress_event_count: int = 0
    selected_driver_refs: list[dict[str, Any]] = field(default_factory=list)
    rationale_codes: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class NarrativeMomentumValidation:
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
