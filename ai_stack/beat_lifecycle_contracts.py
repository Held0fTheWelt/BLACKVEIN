"""Generic beat lifecycle contracts for runtime intelligence.

The runtime core owns the lifecycle shape. Content modules own the concrete
phase ids, beat ids, and ranking hints supplied through ``ModuleRuntimePolicy``.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


BEAT_LIFECYCLE_SCHEMA_VERSION = "beat_lifecycle.v1"


def _json_safe(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


@dataclass(frozen=True)
class BeatState:
    schema_version: str = BEAT_LIFECYCLE_SCHEMA_VERSION
    phase_id: str | None = None
    prior_beat_id: str | None = None
    pressure_state: str | None = None
    policy_source: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class BeatCandidate:
    id: str
    phase_id: str | None = None
    source: str = "module_policy"
    expected_visible_functions: list[str] = field(default_factory=list)
    policy: dict[str, Any] = field(default_factory=dict)
    rank: int = 0

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class BeatSelection:
    selected_beat_id: str | None
    selection_source: str
    selection_reason: str | None = None
    candidate_count: int = 0
    expected_visible_functions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class BeatRealization:
    realized: bool
    visible: bool
    evidence_blocks: list[dict[str, Any]] = field(default_factory=list)
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class BeatValidation:
    status: str
    beat_selected: bool
    beat_realized: bool
    beat_realization_visible: bool
    transition_valid: bool
    failure_reason: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


def phase_beat_candidates(
    *,
    module_policy: dict[str, Any] | None,
    phase_id: str | None,
    fallback_candidate_ids: list[str] | None = None,
    expected_visible_functions: list[str] | None = None,
) -> list[BeatCandidate]:
    """Return beat candidates from generic phase policy data.

    The function recognizes common neutral keys while leaving all ids as data.
    It does not interpret module-specific phase or beat names.
    """
    policy = module_policy if isinstance(module_policy, dict) else {}
    phase_policy = policy.get("phase_policy") if isinstance(policy.get("phase_policy"), dict) else {}
    phases = phase_policy.get("phases") if isinstance(phase_policy.get("phases"), dict) else {}
    phase_key = str(phase_id or "").strip()
    phase = phases.get(phase_key) if phase_key else None
    if not isinstance(phase, dict):
        phase = {}

    raw_ids = (
        phase.get("allowed_beats")
        or phase.get("allowed_narrator_beats")
        or phase.get("beat_ids")
        or []
    )
    candidate_ids = [str(item).strip() for item in raw_ids if str(item).strip()]
    if not candidate_ids:
        candidate_ids = [str(item).strip() for item in (fallback_candidate_ids or []) if str(item).strip()]

    visible_functions = [
        str(item).strip()
        for item in (expected_visible_functions or [])
        if str(item).strip()
    ]
    out: list[BeatCandidate] = []
    for idx, beat_id in enumerate(candidate_ids):
        composite_id = f"{phase_key}:{beat_id}" if phase_key and ":" not in beat_id else beat_id
        out.append(
            BeatCandidate(
                id=composite_id,
                phase_id=phase_key or None,
                source="module_policy" if phase else "fallback",
                expected_visible_functions=list(visible_functions),
                policy={"phase": phase, "raw_beat_id": beat_id},
                rank=idx,
            )
        )
    return out


def select_beat_candidate(
    candidates: list[BeatCandidate],
    *,
    deterministic_fallback_id: str | None = None,
    selection_source: str = "module_policy",
    selection_reason: str | None = None,
) -> BeatSelection:
    """Select the first ranked candidate, falling back to deterministic data."""
    ranked = sorted(candidates, key=lambda item: (item.rank, item.id))
    if ranked:
        first = ranked[0]
        source = "module_policy" if first.source == "module_policy" else selection_source
        return BeatSelection(
            selected_beat_id=first.id,
            selection_source=source,
            selection_reason=selection_reason or "first_ranked_policy_candidate",
            candidate_count=len(ranked),
            expected_visible_functions=list(first.expected_visible_functions),
        )
    fallback = str(deterministic_fallback_id or "").strip() or None
    return BeatSelection(
        selected_beat_id=fallback,
        selection_source="deterministic" if fallback else "fallback",
        selection_reason=selection_reason or ("deterministic_fallback" if fallback else "no_candidate"),
        candidate_count=0,
        expected_visible_functions=[],
    )
