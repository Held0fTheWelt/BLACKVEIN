"""Voice-profile lookup and deterministic follow-up template rendering."""

from __future__ import annotations

from typing import Any

from .constants import (
    MAX_COMPOSED_FOLLOW_UP_CHARS,
    _FOLLOW_UP_ALLOWED_PLACEHOLDERS,
    _FOLLOW_UP_PROFILE_TEMPLATE_KEYS,
    _PLACEHOLDER_RE,
)
from .player_input import _compact_one_line


def _profile_actor_ids(profile: dict[str, Any]) -> set[str]:
    ids: set[str] = set()
    for key in ("runtime_actor_id", "actor_id", "character_key", "character_id"):
        value = str(profile.get(key) or "").strip()
        if value:
            ids.add(value)
    return ids


def _voice_profiles_by_actor(context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_profiles: Any = None
    for key in ("actor_voice_profiles", "character_voice_profiles", "voice_profiles"):
        candidate = context.get(key)
        if candidate:
            raw_profiles = candidate
            break

    indexed: dict[str, dict[str, Any]] = {}
    if isinstance(raw_profiles, dict):
        for actor_id, profile in raw_profiles.items():
            if not isinstance(profile, dict):
                continue
            profile_copy = dict(profile)
            profile_copy.setdefault("runtime_actor_id", str(actor_id))
            for pid in _profile_actor_ids(profile_copy) or {str(actor_id)}:
                indexed[pid] = profile_copy
    elif isinstance(raw_profiles, list):
        for profile in raw_profiles:
            if not isinstance(profile, dict):
                continue
            for pid in _profile_actor_ids(profile):
                indexed[pid] = dict(profile)
    return indexed


def _string_from_profile_container(
    container: dict[str, Any],
    *,
    prefix: str,
) -> tuple[str, str] | None:
    for key in _FOLLOW_UP_PROFILE_TEMPLATE_KEYS:
        value = container.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip(), f"{prefix}.{key}"
    return None


def _follow_up_template_from_profile(profile: dict[str, Any]) -> tuple[str, str] | None:
    profile_composition = (
        profile.get("follow_up_composition")
        if isinstance(profile.get("follow_up_composition"), dict)
        else {}
    )
    selected = _string_from_profile_container(
        profile_composition,
        prefix="follow_up_composition",
    )
    if selected:
        return selected
    speech_patterns = (
        profile.get("speech_patterns")
        if isinstance(profile.get("speech_patterns"), dict)
        else {}
    )
    selected = _string_from_profile_container(
        speech_patterns,
        prefix="speech_patterns",
    )
    if selected:
        return selected
    return _string_from_profile_container(profile, prefix="voice_profile")


def _motivation_score_for_actor(
    *,
    context: dict[str, Any],
    actor_id: str,
) -> float | None:
    raw_scores = context.get("motivation_scores")
    if not isinstance(raw_scores, dict):
        return None
    raw_score = raw_scores.get(actor_id)
    if isinstance(raw_score, (int, float)):
        return float(raw_score)
    if isinstance(raw_score, dict):
        score = raw_score.get("score")
        if isinstance(score, (int, float)):
            return float(score)
    return None


def _render_follow_up_template(
    *,
    template: str,
    replanning: dict[str, Any],
    profile: dict[str, Any],
    actor_id: str,
    motivation_score: float | None,
) -> tuple[str, list[str], str | None]:
    placeholders = _PLACEHOLDER_RE.findall(template)
    unknown = sorted({
        name for name in placeholders if name not in _FOLLOW_UP_ALLOWED_PLACEHOLDERS
    })
    if unknown:
        return "", [], "unsupported_follow_up_template_placeholder"
    if "{" in _PLACEHOLDER_RE.sub("", template) or "}" in _PLACEHOLDER_RE.sub("", template):
        return "", [], "malformed_follow_up_template"

    promoted_input = (
        replanning.get("promoted_input")
        if isinstance(replanning.get("promoted_input"), dict)
        else {}
    )
    promoted_text = str(promoted_input.get("text_excerpt") or "").strip()
    values = {
        "actor_id": actor_id,
        "baseline_tone": str(profile.get("baseline_tone") or "").strip(),
        "current_phase_voice_hint": str(
            profile.get("current_phase_voice_hint") or ""
        ).strip(),
        "interrupted_block_id": str(replanning.get("interrupted_block_id") or "").strip(),
        "interrupted_block_type": str(
            replanning.get("interrupted_block_type") or ""
        ).strip(),
        "motivation_score": (
            f"{motivation_score:.2f}" if motivation_score is not None else ""
        ),
        "player_input": promoted_text,
        "promoted_player_input": promoted_text,
        "promoted_player_input_id": str(
            promoted_input.get("promoted_player_input_id")
            or replanning.get("promoted_player_input_id")
            or ""
        ).strip(),
        "voice_hint": str(profile.get("current_phase_voice_hint") or "").strip(),
    }
    rendered = template
    for name in sorted(set(placeholders), key=len, reverse=True):
        rendered = rendered.replace("{" + name + "}", values.get(name, ""))
    rendered = _compact_one_line(rendered, limit=MAX_COMPOSED_FOLLOW_UP_CHARS)
    if not rendered:
        return "", sorted(set(placeholders)), "empty_composed_follow_up"
    return rendered, sorted(set(placeholders)), None


def _voice_profile_actor_id(profile: dict[str, Any]) -> str | None:
    return (
        profile.get("runtime_actor_id")
        or profile.get("actor_id")
        or profile.get("character_key")
    )
