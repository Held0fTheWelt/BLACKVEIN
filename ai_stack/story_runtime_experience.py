"""Canonical Story Runtime Experience settings model.

Shared between the backend (resolving / validating operator settings) and the
world-engine (consuming the resolved view). Keeping this in ``ai_stack``
ensures a single source of truth for experience-mode semantics rather than two
parallel definitions drifting between backend and play-service.

The settings live inside the resolved runtime config under the key
``story_runtime_experience`` so they ride the same propagation path as the
rest of the governed runtime surface.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


# -- Canonical enums -------------------------------------------------------

EXPERIENCE_MODES: tuple[str, ...] = (
    "turn_based_narrative_recap",
    "dramatic_turn",
    "live_dramatic_scene_simulator",
)

DELIVERY_PROFILES: tuple[str, ...] = (
    "classic_recap",
    "lean_dramatic",
    "cinematic_live",
    "npc_forward",
    "operator_custom",
)

_LOW_MED_HIGH: tuple[str, ...] = ("low", "medium", "high")
_MOTIF_MODES: tuple[str, ...] = (
    "strict_suppression",
    "controlled_reuse",
    "thematic_reinforcement",
)
_NPC_VERBOSITY: tuple[str, ...] = ("terse", "balanced", "expressive")
_NPC_INITIATIVE: tuple[str, ...] = ("passive", "reactive", "assertive")
_EXCHANGE_INTENSITY: tuple[str, ...] = ("off", "light", "medium", "strong")
_PULSE_LENGTH: tuple[str, ...] = ("short", "medium", "long")
_BEAT_SPEED: tuple[str, ...] = ("slow", "normal", "fast")


# -- Contract / packaging versioning --------------------------------------

STORY_RUNTIME_EXPERIENCE_CONFIG_VERSION: str = "1.0"
STORY_RUNTIME_EXPERIENCE_PACKAGING_CONTRACT_VERSION: str = "1.0"


# -- Degradation markers --------------------------------------------------

DEGRADATION_LIVE_NOT_FULLY_HONORED = "live_simulator_partial_foundation"
DEGRADATION_PULSE_CAP_APPLIED = "pulse_count_capped"
DEGRADATION_INTER_NPC_EXCHANGE_FORCED_OFF = "inter_npc_exchange_unavailable_in_recap"
DEGRADATION_AUTO_PROGRESS_GATED = "auto_scene_progress_requires_dramatic_or_live"


def canonical_defaults() -> dict[str, Any]:
    """Return the fresh-bootstrap default Story Runtime Experience settings.

    The default is the safest and most truthful baseline: turn-based recap
    with one pulse and no autonomous scene motion. Operators can widen it via
    the Administration Tool.
    """
    return {
        "experience_mode": "turn_based_narrative_recap",
        "delivery_profile": "classic_recap",
        "prose_density": "medium",
        "explanation_level": "medium",
        "narrator_presence": "medium",
        "dialogue_priority": "medium",
        "action_visibility": "medium",
        "repetition_guard": "medium",
        "motif_handling": "controlled_reuse",
        "npc_verbosity": "balanced",
        "npc_initiative": "reactive",
        "inter_npc_exchange_intensity": "light",
        "pulse_length": "medium",
        "max_scene_pulses_per_response": 1,
        "allow_scene_progress_without_player_action": False,
        "beat_progression_speed": "normal",
    }


_DELIVERY_PROFILE_OVERRIDES: dict[str, dict[str, Any]] = {
    "classic_recap": {
        "prose_density": "medium",
        "narrator_presence": "high",
        "dialogue_priority": "low",
        "action_visibility": "medium",
    },
    "lean_dramatic": {
        "prose_density": "medium",
        "narrator_presence": "medium",
        "dialogue_priority": "high",
        "action_visibility": "high",
    },
    "cinematic_live": {
        "prose_density": "medium",
        "narrator_presence": "low",
        "dialogue_priority": "high",
        "action_visibility": "high",
        "inter_npc_exchange_intensity": "medium",
    },
    "npc_forward": {
        "narrator_presence": "low",
        "dialogue_priority": "high",
        "npc_initiative": "assertive",
        "inter_npc_exchange_intensity": "medium",
    },
    "operator_custom": {},
}


def _coerce_choice(raw: Any, choices: tuple[str, ...], fallback: str) -> str:
    if isinstance(raw, str) and raw.strip():
        value = raw.strip().lower()
        if value in choices:
            return value
    return fallback


def _coerce_int(raw: Any, lo: int, hi: int, fallback: int) -> int:
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return fallback
    return max(lo, min(hi, value))


def _coerce_bool(raw: Any, fallback: bool) -> bool:
    if isinstance(raw, bool):
        return raw
    if isinstance(raw, str):
        lo = raw.strip().lower()
        if lo in {"true", "1", "yes", "on"}:
            return True
        if lo in {"false", "0", "no", "off"}:
            return False
    return fallback


def normalize_story_runtime_experience(payload: Any) -> dict[str, Any]:
    """Coerce a raw operator payload into a canonical settings dict.

    Unknown keys are dropped. Bad values fall back to defaults. Preset
    overrides are applied *before* advanced overrides so operators can still
    fine-tune on top of a picked profile.
    """
    defaults = canonical_defaults()
    if not isinstance(payload, dict):
        return defaults

    profile = _coerce_choice(
        payload.get("delivery_profile"), DELIVERY_PROFILES, defaults["delivery_profile"]
    )
    base: dict[str, Any] = dict(defaults)
    base["delivery_profile"] = profile
    base.update(_DELIVERY_PROFILE_OVERRIDES.get(profile, {}))

    def pick_choice(key: str, choices: tuple[str, ...]) -> str:
        return _coerce_choice(payload.get(key), choices, base[key])

    base["experience_mode"] = pick_choice("experience_mode", EXPERIENCE_MODES)
    base["prose_density"] = pick_choice("prose_density", _LOW_MED_HIGH)
    base["explanation_level"] = pick_choice("explanation_level", _LOW_MED_HIGH)
    base["narrator_presence"] = pick_choice("narrator_presence", _LOW_MED_HIGH)
    base["dialogue_priority"] = pick_choice("dialogue_priority", _LOW_MED_HIGH)
    base["action_visibility"] = pick_choice("action_visibility", _LOW_MED_HIGH)
    base["repetition_guard"] = pick_choice("repetition_guard", _LOW_MED_HIGH)
    base["motif_handling"] = pick_choice("motif_handling", _MOTIF_MODES)
    base["npc_verbosity"] = pick_choice("npc_verbosity", _NPC_VERBOSITY)
    base["npc_initiative"] = pick_choice("npc_initiative", _NPC_INITIATIVE)
    base["inter_npc_exchange_intensity"] = pick_choice(
        "inter_npc_exchange_intensity", _EXCHANGE_INTENSITY
    )
    base["pulse_length"] = pick_choice("pulse_length", _PULSE_LENGTH)
    base["beat_progression_speed"] = pick_choice("beat_progression_speed", _BEAT_SPEED)

    base["max_scene_pulses_per_response"] = _coerce_int(
        payload.get("max_scene_pulses_per_response"),
        1,
        3,
        base["max_scene_pulses_per_response"],
    )
    base["allow_scene_progress_without_player_action"] = _coerce_bool(
        payload.get("allow_scene_progress_without_player_action"),
        base["allow_scene_progress_without_player_action"],
    )
    return base


def validate_story_runtime_experience(settings: dict[str, Any]) -> list[str]:
    """Return operator-visible validation warnings for a normalized settings dict.

    Validation rejects misleading combinations by surfacing warnings rather
    than silently mutating values — the operator must either fix them or
    acknowledge the degraded state visible in diagnostics.
    """
    warnings: list[str] = []
    mode = settings.get("experience_mode")
    pulses = int(settings.get("max_scene_pulses_per_response") or 1)
    exchange = settings.get("inter_npc_exchange_intensity")
    allow_auto = bool(settings.get("allow_scene_progress_without_player_action"))

    if mode == "live_dramatic_scene_simulator":
        if pulses <= 1 and exchange == "off":
            warnings.append(
                "live_dramatic_scene_simulator requires either max_scene_pulses_per_response >= 2 "
                "or inter_npc_exchange_intensity != off; otherwise the mode runs in degraded "
                "recap-like form."
            )
    if mode == "turn_based_narrative_recap":
        if pulses > 1:
            warnings.append(
                "turn_based_narrative_recap caps max_scene_pulses_per_response to 1; the extra "
                "pulses will be ignored at runtime."
            )
        if allow_auto:
            warnings.append(
                "turn_based_narrative_recap does not honor allow_scene_progress_without_player_action."
            )
    if allow_auto and mode not in ("dramatic_turn", "live_dramatic_scene_simulator"):
        warnings.append(
            "allow_scene_progress_without_player_action requires dramatic_turn or "
            "live_dramatic_scene_simulator."
        )
    if settings.get("delivery_profile") == "operator_custom":
        # Nothing to assert — operator is explicitly on custom. Present for
        # symmetry so diagnostics surfaces can still pick this up.
        pass
    return warnings


# -- Effective policy (what the runtime actually honors) ------------------


@dataclass(frozen=True)
class StoryRuntimeExperiencePolicy:
    """Runtime-effective view of Story Runtime Experience.

    ``configured`` is exactly what the operator asked for (post-normalization).
    ``effective`` is what the runtime actually honors after it applies safety
    caps. ``degradation_markers`` explains any gap between the two — this is
    what diagnostics and admin truth-surfaces must read, not ``configured``.
    """

    configured: dict[str, Any]
    effective: dict[str, Any]
    degradation_markers: list[dict[str, str]] = field(default_factory=list)
    packaging_contract_version: str = STORY_RUNTIME_EXPERIENCE_PACKAGING_CONTRACT_VERSION
    config_version: str = STORY_RUNTIME_EXPERIENCE_CONFIG_VERSION

    @property
    def experience_mode(self) -> str:
        return str(self.effective.get("experience_mode") or "turn_based_narrative_recap")

    @property
    def delivery_profile(self) -> str:
        return str(self.effective.get("delivery_profile") or "classic_recap")

    @property
    def max_scene_pulses_per_response(self) -> int:
        try:
            return int(self.effective.get("max_scene_pulses_per_response") or 1)
        except (TypeError, ValueError):
            return 1

    @property
    def allow_scene_progress_without_player_action(self) -> bool:
        return bool(self.effective.get("allow_scene_progress_without_player_action"))

    @property
    def is_live_mode(self) -> bool:
        return self.experience_mode == "live_dramatic_scene_simulator"

    @property
    def is_dramatic_turn(self) -> bool:
        return self.experience_mode == "dramatic_turn"

    def to_truth_surface(self) -> dict[str, Any]:
        return {
            "configured": dict(self.configured),
            "effective": dict(self.effective),
            "degradation_markers": [dict(m) for m in self.degradation_markers],
            "packaging_contract_version": self.packaging_contract_version,
            "config_version": self.config_version,
        }


def resolve_story_runtime_experience_policy(
    raw: Any,
) -> StoryRuntimeExperiencePolicy:
    """Produce a policy from a raw resolved-runtime-config section.

    Applies safety caps and records the reason when values are downgraded so
    the admin UI can show the truth rather than an aspirational claim. This
    is the single place where runtime caps live — the admin form validates
    but does not cap; the runtime caps and reports it.
    """
    configured = normalize_story_runtime_experience(raw)
    effective = dict(configured)
    markers: list[dict[str, str]] = []

    mode = effective["experience_mode"]
    if mode == "turn_based_narrative_recap":
        if effective.get("max_scene_pulses_per_response", 1) > 1:
            markers.append(
                {
                    "marker": DEGRADATION_PULSE_CAP_APPLIED,
                    "reason": "recap_mode_caps_pulses_to_one",
                }
            )
            effective["max_scene_pulses_per_response"] = 1
        if effective.get("inter_npc_exchange_intensity") not in (None, "off"):
            markers.append(
                {
                    "marker": DEGRADATION_INTER_NPC_EXCHANGE_FORCED_OFF,
                    "reason": "recap_mode_disables_inter_npc_exchange",
                }
            )
            effective["inter_npc_exchange_intensity"] = "off"
        if effective.get("allow_scene_progress_without_player_action"):
            markers.append(
                {
                    "marker": DEGRADATION_AUTO_PROGRESS_GATED,
                    "reason": "recap_mode_disables_auto_scene_progress",
                }
            )
            effective["allow_scene_progress_without_player_action"] = False
    elif mode == "dramatic_turn":
        if effective.get("max_scene_pulses_per_response", 1) > 2:
            markers.append(
                {
                    "marker": DEGRADATION_PULSE_CAP_APPLIED,
                    "reason": "dramatic_turn_caps_pulses_to_two",
                }
            )
            effective["max_scene_pulses_per_response"] = 2
    elif mode == "live_dramatic_scene_simulator":
        markers.append(
            {
                "marker": DEGRADATION_LIVE_NOT_FULLY_HONORED,
                "reason": (
                    "live_simulator_runs_on_partial_pulse_foundation; packaging honors "
                    "pulse_count and stronger dialogue/action beats but scene motion "
                    "without player action is bounded and declared partial."
                ),
            }
        )

    return StoryRuntimeExperiencePolicy(
        configured=configured,
        effective=effective,
        degradation_markers=markers,
    )


def extract_policy_from_resolved_config(resolved: Any) -> StoryRuntimeExperiencePolicy:
    """Pull the ``story_runtime_experience`` section from a resolved runtime config."""
    if isinstance(resolved, dict):
        section = resolved.get("story_runtime_experience")
    else:
        section = None
    return resolve_story_runtime_experience_policy(section)


__all__ = [
    "EXPERIENCE_MODES",
    "DELIVERY_PROFILES",
    "STORY_RUNTIME_EXPERIENCE_CONFIG_VERSION",
    "STORY_RUNTIME_EXPERIENCE_PACKAGING_CONTRACT_VERSION",
    "DEGRADATION_LIVE_NOT_FULLY_HONORED",
    "DEGRADATION_PULSE_CAP_APPLIED",
    "DEGRADATION_INTER_NPC_EXCHANGE_FORCED_OFF",
    "DEGRADATION_AUTO_PROGRESS_GATED",
    "canonical_defaults",
    "normalize_story_runtime_experience",
    "validate_story_runtime_experience",
    "StoryRuntimeExperiencePolicy",
    "resolve_story_runtime_experience_policy",
    "extract_policy_from_resolved_config",
]
