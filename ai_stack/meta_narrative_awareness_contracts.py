"""Opt-in meta-narrative awareness contracts.

The feature is intentionally structural and consent-gated. Module policy can
declare support, but a turn only becomes active when the resolved Story Runtime
Experience settings opt in and nominate eligible actors.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


META_NARRATIVE_AWARENESS_SCHEMA_VERSION = "meta_narrative_awareness.v1"
META_NARRATIVE_AWARENESS_SCHEMA_VERSION_V2 = "meta_narrative_awareness.v2"
META_NARRATIVE_AWARENESS_POLICY_VERSION = "meta_narrative_awareness_policy.v1"
META_NARRATIVE_AWARENESS_POLICY_VERSION_V2 = "meta_narrative_awareness_policy.v2"

META_NARRATIVE_INTENSITIES: frozenset[str] = frozenset(
    {"subtle", "moderate", "full_fourth_wall"}
)
META_NARRATIVE_AWARENESS_TIERS: frozenset[str] = frozenset(
    {"off", "subtle", "adaptive", "full"}
)
META_NARRATIVE_TRIGGER_FREQUENCIES: frozenset[str] = frozenset(
    {"rare", "occasional", "frequent"}
)
META_NARRATIVE_FOURTH_WALL_LEVELS: frozenset[str] = frozenset(
    {"none", "subtle", "direct", "full_fourth_wall"}
)
META_NARRATIVE_MEMORY_SCOPES: frozenset[str] = frozenset(
    {"session", "actor", "module", "long_term", "cross_session"}
)
META_NARRATIVE_AWARENESS_MODES: frozenset[str] = frozenset(
    {
        "dramatic_pattern_sense",
        "narrative_pressure_sense",
        "character_resistance",
        "narrator_negotiation",
        "fourth_wall_address",
        "direct_player_address",
        "quality_self_critique",
        "adaptive_pattern_recognition",
        "character_self_model",
        "cross_session_memory_reference",
        "story_form_negotiation",
    }
)
META_NARRATIVE_FORBIDDEN_MODES: frozenset[str] = frozenset(
    {
        "system_prompt_disclosure",
        "tool_or_model_disclosure",
        "player_control_claim",
        "unbounded_rewrite",
        "unauthorized_fourth_wall_break",
        "private_player_data_disclosure",
        "false_cross_session_memory",
    }
)
META_NARRATIVE_COMMIT_IMPACTS: frozenset[str] = frozenset(
    {"diagnostic", "recover", "reject"}
)

META_NARRATIVE_FAILURE_NOT_OPTED_IN = "meta_narrative_not_opted_in"
META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR = "meta_narrative_unauthorized_actor"
META_NARRATIVE_FAILURE_FORBIDDEN_MODE = "meta_narrative_forbidden_mode"
META_NARRATIVE_FAILURE_EVENT_BUDGET_EXCEEDED = (
    "meta_narrative_event_budget_exceeded"
)
META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE = "meta_narrative_system_disclosure"
META_NARRATIVE_FAILURE_UNBOUNDED_REWRITE = "meta_narrative_unbounded_rewrite"
META_NARRATIVE_FAILURE_DIRECT_ADDRESS = "meta_narrative_direct_address_not_allowed"
META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED = (
    "meta_narrative_consent_scope_exceeded"
)
META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY = "meta_narrative_privacy_boundary_violation"
META_NARRATIVE_FAILURE_FOURTH_WALL_SCOPE = "meta_narrative_fourth_wall_scope_exceeded"
META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED = (
    "meta_narrative_cross_session_memory_unverified"
)
META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY = "meta_narrative_false_self_memory"

META_NARRATIVE_FAILURE_CODES: frozenset[str] = frozenset(
    {
        META_NARRATIVE_FAILURE_NOT_OPTED_IN,
        META_NARRATIVE_FAILURE_UNAUTHORIZED_ACTOR,
        META_NARRATIVE_FAILURE_FORBIDDEN_MODE,
        META_NARRATIVE_FAILURE_EVENT_BUDGET_EXCEEDED,
        META_NARRATIVE_FAILURE_SYSTEM_DISCLOSURE,
        META_NARRATIVE_FAILURE_UNBOUNDED_REWRITE,
        META_NARRATIVE_FAILURE_DIRECT_ADDRESS,
        META_NARRATIVE_FAILURE_CONSENT_SCOPE_EXCEEDED,
        META_NARRATIVE_FAILURE_PRIVACY_BOUNDARY,
        META_NARRATIVE_FAILURE_FOURTH_WALL_SCOPE,
        META_NARRATIVE_FAILURE_CROSS_SESSION_MEMORY_UNVERIFIED,
        META_NARRATIVE_FAILURE_FALSE_SELF_MEMORY,
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


def _clean_str_list(
    value: Any,
    *,
    allowed: frozenset[str] | None = None,
    lower: bool = False,
) -> list[str]:
    out: list[str] = []
    for item in _as_list(value):
        text = _text(item)
        if lower:
            text = text.lower()
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
class MetaNarrativeAwarenessTarget:
    schema_version: str = META_NARRATIVE_AWARENESS_SCHEMA_VERSION
    policy_version: str = META_NARRATIVE_AWARENESS_POLICY_VERSION
    policy_enabled: bool = False
    opt_in_enabled: bool = False
    active: bool = False
    awareness_tier: str = "subtle"
    intensity: str = "subtle"
    trigger_frequency: str = "rare"
    supported_actor_ids: list[str] = field(default_factory=list)
    configured_actor_ids: list[str] = field(default_factory=list)
    selected_actor_ids: list[str] = field(default_factory=list)
    allowed_awareness_modes: list[str] = field(default_factory=list)
    forbidden_awareness_modes: list[str] = field(default_factory=list)
    allowed_fourth_wall_levels: list[str] = field(default_factory=list)
    max_events_per_turn: int = 0
    max_direct_addresses_per_turn: int = 0
    requires_player_consent: bool = True
    allow_player_toggle: bool = True
    direct_player_address_allowed: bool = False
    narrator_negotiation_allowed: bool = False
    cross_session_memory_allowed: bool = False
    memory_retention_scope: str = "session"
    selected_memory_ref_ids: list[str] = field(default_factory=list)
    adaptive_signal_codes: list[str] = field(default_factory=list)
    cooldown_applied: bool = False
    model_context_visibility: str = "bounded_structured_only"
    commit_impact: str = "recover"
    rationale_codes: list[str] = field(default_factory=list)
    source_evidence: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return _json_safe(asdict(self))


@dataclass(frozen=True)
class MetaNarrativeAwarenessValidation:
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


def default_meta_narrative_awareness_policy() -> dict[str, Any]:
    """Return neutral defaults. Runtime activation still requires session opt-in."""
    return {
        "schema_version": META_NARRATIVE_AWARENESS_POLICY_VERSION,
        "enabled": False,
        "allowed_awareness_tiers": ["subtle"],
        "default_awareness_tier": "subtle",
        "allowed_intensities": ["subtle"],
        "default_intensity": "subtle",
        "allowed_trigger_frequencies": ["rare"],
        "default_trigger_frequency": "rare",
        "characters_with_awareness": [],
        "allowed_awareness_modes": ["dramatic_pattern_sense"],
        "forbidden_awareness_modes": sorted(META_NARRATIVE_FORBIDDEN_MODES),
        "allowed_fourth_wall_levels": ["none", "subtle"],
        "max_events_per_turn": 1,
        "max_direct_addresses_per_turn": 0,
        "requires_player_consent": True,
        "allow_player_toggle": True,
        "allow_direct_player_address": False,
        "allow_narrator_negotiation": False,
        "allow_cross_session_memory": False,
        "allowed_memory_scopes": ["session"],
        "default_memory_retention_scope": "session",
        "max_cross_session_memory_refs": 0,
        "require_verified_memory_refs": True,
        "privacy_safe_memory_only": True,
        "model_context_visibility": "bounded_structured_only",
        "default_commit_impact": "recover",
    }


def normalize_meta_narrative_awareness_policy(
    policy: dict[str, Any] | None,
) -> dict[str, Any]:
    """Normalize module/runtime policy into a stable JSON-safe envelope."""
    raw = policy if isinstance(policy, dict) else {}
    default = default_meta_narrative_awareness_policy()
    allowed_tiers = _clean_str_list(
        raw.get("allowed_awareness_tiers"),
        allowed=META_NARRATIVE_AWARENESS_TIERS,
        lower=True,
    ) or list(default["allowed_awareness_tiers"])
    default_tier = _text(raw.get("default_awareness_tier")).lower()
    if default_tier not in allowed_tiers:
        default_tier = allowed_tiers[0]
    allowed_intensities = _clean_str_list(
        raw.get("allowed_intensities"),
        allowed=META_NARRATIVE_INTENSITIES,
        lower=True,
    ) or list(default["allowed_intensities"])
    default_intensity = _text(raw.get("default_intensity")).lower()
    if default_intensity not in allowed_intensities:
        default_intensity = allowed_intensities[0]
    allowed_frequencies = _clean_str_list(
        raw.get("allowed_trigger_frequencies"),
        allowed=META_NARRATIVE_TRIGGER_FREQUENCIES,
        lower=True,
    ) or list(default["allowed_trigger_frequencies"])
    default_frequency = _text(raw.get("default_trigger_frequency")).lower()
    if default_frequency not in allowed_frequencies:
        default_frequency = allowed_frequencies[0]
    forbidden_modes = _clean_str_list(
        raw.get("forbidden_awareness_modes"),
        allowed=META_NARRATIVE_FORBIDDEN_MODES,
        lower=True,
    ) or list(default["forbidden_awareness_modes"])
    forbidden = set(forbidden_modes)
    allowed_modes = [
        mode
        for mode in (
            _clean_str_list(
                raw.get("allowed_awareness_modes"),
                allowed=META_NARRATIVE_AWARENESS_MODES,
                lower=True,
            )
            or list(default["allowed_awareness_modes"])
        )
        if mode not in forbidden
    ]
    if not allowed_modes:
        allowed_modes = ["dramatic_pattern_sense"]
    allowed_fourth_wall_levels = _clean_str_list(
        raw.get("allowed_fourth_wall_levels"),
        allowed=META_NARRATIVE_FOURTH_WALL_LEVELS,
        lower=True,
    ) or list(default["allowed_fourth_wall_levels"])
    allowed_memory_scopes = _clean_str_list(
        raw.get("allowed_memory_scopes"),
        allowed=META_NARRATIVE_MEMORY_SCOPES,
        lower=True,
    ) or list(default["allowed_memory_scopes"])
    default_memory_scope = _text(raw.get("default_memory_retention_scope")).lower()
    if default_memory_scope not in allowed_memory_scopes:
        default_memory_scope = allowed_memory_scopes[0]
    commit_impact = _text(
        raw.get("default_commit_impact") or default["default_commit_impact"]
    ).lower()
    if commit_impact not in META_NARRATIVE_COMMIT_IMPACTS:
        commit_impact = default["default_commit_impact"]
    return {
        "schema_version": _text(raw.get("schema_version"))
        or META_NARRATIVE_AWARENESS_POLICY_VERSION,
        "enabled": bool(raw.get("enabled", default["enabled"])),
        "allowed_awareness_tiers": allowed_tiers,
        "default_awareness_tier": default_tier,
        "allowed_intensities": allowed_intensities,
        "default_intensity": default_intensity,
        "allowed_trigger_frequencies": allowed_frequencies,
        "default_trigger_frequency": default_frequency,
        "characters_with_awareness": _clean_str_list(
            raw.get("characters_with_awareness")
        ),
        "allowed_awareness_modes": allowed_modes,
        "forbidden_awareness_modes": forbidden_modes,
        "allowed_fourth_wall_levels": allowed_fourth_wall_levels,
        "max_events_per_turn": _bounded_int(
            raw.get("max_events_per_turn"),
            int(default["max_events_per_turn"]),
            minimum=0,
            maximum=3,
        ),
        "max_direct_addresses_per_turn": _bounded_int(
            raw.get("max_direct_addresses_per_turn"),
            int(default["max_direct_addresses_per_turn"]),
            minimum=0,
            maximum=3,
        ),
        "requires_player_consent": bool(
            raw.get("requires_player_consent", default["requires_player_consent"])
        ),
        "allow_player_toggle": bool(
            raw.get("allow_player_toggle", default["allow_player_toggle"])
        ),
        "allow_direct_player_address": bool(
            raw.get(
                "allow_direct_player_address",
                default["allow_direct_player_address"],
            )
        ),
        "allow_narrator_negotiation": bool(
            raw.get(
                "allow_narrator_negotiation",
                default["allow_narrator_negotiation"],
            )
        ),
        "allow_cross_session_memory": bool(
            raw.get(
                "allow_cross_session_memory",
                default["allow_cross_session_memory"],
            )
        ),
        "allowed_memory_scopes": allowed_memory_scopes,
        "default_memory_retention_scope": default_memory_scope,
        "max_cross_session_memory_refs": _bounded_int(
            raw.get("max_cross_session_memory_refs"),
            int(default["max_cross_session_memory_refs"]),
            minimum=0,
            maximum=5,
        ),
        "require_verified_memory_refs": bool(
            raw.get(
                "require_verified_memory_refs",
                default["require_verified_memory_refs"],
            )
        ),
        "privacy_safe_memory_only": bool(
            raw.get("privacy_safe_memory_only", default["privacy_safe_memory_only"])
        ),
        "model_context_visibility": _text(raw.get("model_context_visibility"))
        or default["model_context_visibility"],
        "default_commit_impact": commit_impact,
        "source": "module_runtime_policy.meta_narrative_awareness",
    }
