"""Improvisational-coherence contracts for bounded yes-and behavior.

The contract is structural: runtime policy selects how a player contribution
should be accepted, bounded, or redirected, and validation checks structured
event evidence rather than generated prose.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION = "improvisational_coherence.v1"
IMPROVISATIONAL_COHERENCE_POLICY_VERSION = "improvisational_coherence_policy.v1"

IMPROV_ACCEPT = "accept"
IMPROV_ACCEPT_WITH_BOUNDARY = "accept_with_boundary"
IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT = "redirect_with_acknowledgement"
IMPROV_REJECT_WITH_PLAYABLE_REASON = "reject_with_playable_reason"

IMPROV_ACCEPTANCE_MODES: frozenset[str] = frozenset(
    {
        IMPROV_ACCEPT,
        IMPROV_ACCEPT_WITH_BOUNDARY,
        IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT,
        IMPROV_REJECT_WITH_PLAYABLE_REASON,
    }
)

IMPROV_ADVANCE_CLASSES: frozenset[str] = frozenset(
    {
        "pressure_raise",
        "relationship_shift",
        "scene_reframe",
        "continuity_carry",
        "boundary_containment",
        "beat_deepen",
    }
)

IMPROV_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)

IMPROV_VALIDATION_STATUSES: frozenset[str] = frozenset(
    {"approved", "degraded", "rejected", "not_applicable"}
)

IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED = "improv_player_contribution_dropped"
IMPROV_FAILURE_SCENE_ANCHOR_MISSING = "improv_scene_anchor_missing"
IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION = "improv_unbounded_world_expansion"
IMPROV_FAILURE_CONTRADICTS_COMMITTED_TRUTH = "improv_contradicts_committed_truth"
IMPROV_FAILURE_FORCED_PLAYER_REVISION = "improv_forced_player_revision"
IMPROV_FAILURE_NO_PLAYABLE_BOUNDARY_REASON = "improv_no_playable_boundary_reason"

IMPROV_FAILURE_CODES: frozenset[str] = frozenset(
    {
        IMPROV_FAILURE_PLAYER_CONTRIBUTION_DROPPED,
        IMPROV_FAILURE_SCENE_ANCHOR_MISSING,
        IMPROV_FAILURE_UNBOUNDED_WORLD_EXPANSION,
        IMPROV_FAILURE_CONTRADICTS_COMMITTED_TRUTH,
        IMPROV_FAILURE_FORCED_PLAYER_REVISION,
        IMPROV_FAILURE_NO_PLAYABLE_BOUNDARY_REASON,
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
class ImprovisationalCoherenceTarget:
    schema_version: str = IMPROVISATIONAL_COHERENCE_SCHEMA_VERSION
    policy_version: str = IMPROVISATIONAL_COHERENCE_POLICY_VERSION
    policy_enabled: bool = False
    commit_impact: str = "diagnostic"
    require_structured_events: bool = False
    min_anchor_refs: int = 1
    contribution_id: str | None = None
    contribution_kind: str | None = None
    acceptance_mode: str = IMPROV_ACCEPT
    allowed_acceptance_modes: list[str] = field(default_factory=list)
    allowed_advance_classes: list[str] = field(default_factory=list)
    required_anchor_refs: list[dict[str, Any]] = field(default_factory=list)
    selected_scene_function: str | None = None
    visible_actor_ids: list[str] = field(default_factory=list)
    requires_playable_boundary_reason: bool = False
    boundary_reason_code: str | None = None
    rationale_codes: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class ImprovisationalCoherenceValidation:
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


def default_improvisational_coherence_policy() -> dict[str, Any]:
    """Return neutral defaults; modules opt in explicitly."""
    return {
        "schema_version": IMPROVISATIONAL_COHERENCE_POLICY_VERSION,
        "enabled": False,
        "allowed_acceptance_modes": [
            IMPROV_ACCEPT,
            IMPROV_ACCEPT_WITH_BOUNDARY,
            IMPROV_REDIRECT_WITH_ACKNOWLEDGEMENT,
            IMPROV_REJECT_WITH_PLAYABLE_REASON,
        ],
        "allowed_advance_classes": [
            "pressure_raise",
            "relationship_shift",
            "scene_reframe",
            "continuity_carry",
            "boundary_containment",
            "beat_deepen",
        ],
        "require_structured_events": False,
        "min_anchor_refs": 1,
        "max_anchor_refs": 6,
        "default_commit_impact": "recover",
        "model_context_visibility": "bounded_structured_only",
        "boundary_reason_required": True,
    }


def normalize_improvisational_coherence_policy(policy: dict[str, Any] | None) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe envelope."""
    raw = policy if isinstance(policy, dict) else {}
    default = default_improvisational_coherence_policy()
    acceptance_modes = _clean_str_list(
        raw.get("allowed_acceptance_modes"),
        allowed=IMPROV_ACCEPTANCE_MODES,
    ) or list(default["allowed_acceptance_modes"])
    advance_classes = _clean_str_list(
        raw.get("allowed_advance_classes"),
        allowed=IMPROV_ADVANCE_CLASSES,
    ) or list(default["allowed_advance_classes"])
    commit_impact = _text(raw.get("default_commit_impact") or default["default_commit_impact"])
    if commit_impact not in IMPROV_COMMIT_IMPACTS:
        commit_impact = default["default_commit_impact"]
    return {
        "schema_version": _text(raw.get("schema_version"))
        or IMPROVISATIONAL_COHERENCE_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "allowed_acceptance_modes": acceptance_modes,
        "allowed_advance_classes": advance_classes,
        "require_structured_events": bool(
            raw.get("require_structured_events", default["require_structured_events"])
        ),
        "min_anchor_refs": _bounded_int(
            raw.get("min_anchor_refs"),
            int(default["min_anchor_refs"]),
            minimum=0,
            maximum=8,
        ),
        "max_anchor_refs": _bounded_int(
            raw.get("max_anchor_refs"),
            int(default["max_anchor_refs"]),
            minimum=1,
            maximum=12,
        ),
        "default_commit_impact": commit_impact,
        "model_context_visibility": _text(raw.get("model_context_visibility"))
        or default["model_context_visibility"],
        "boundary_reason_required": bool(
            raw.get("boundary_reason_required", default["boundary_reason_required"])
        ),
        "source": "module_runtime_policy.improvisational_coherence",
    }
