"""Closed-enum safety gates and source-context derivation."""

from __future__ import annotations

from typing import Any

from .constants import *


def _profile_forbidden_language_markers(profile: dict[str, Any]) -> list[str]:
    """Return the closed-enum list of forbidden language markers for the actor.

    Authored content owns the list (``voice_consistency.forbidden_language_markers``).
    Empty list → gate is ``not_applicable`` (no claim about output content).
    """
    raw = profile.get("forbidden_language_markers") if isinstance(profile, dict) else None
    if isinstance(raw, dict):
        out: list[str] = []
        for value in raw.values():
            if isinstance(value, str) and value.strip():
                out.append(value.strip())
            elif isinstance(value, list):
                out.extend(str(v).strip() for v in value if isinstance(v, str) and v.strip())
        return out
    if isinstance(raw, list):
        return [str(v).strip() for v in raw if isinstance(v, str) and v.strip()]
    return []


def _closed_enum_str_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(v).strip() for v in value if isinstance(v, str) and v.strip()]
    return []


def _context_known_actor_ids(context: dict[str, Any]) -> set[str]:
    return {
        s
        for s in _closed_enum_str_list(context.get("known_actor_ids"))
    }


def _context_ai_forbidden_actor_ids(context: dict[str, Any]) -> set[str]:
    lane_ctx = (
        context.get("actor_lane_context")
        if isinstance(context.get("actor_lane_context"), dict)
        else {}
    )
    direct = _closed_enum_str_list(context.get("ai_forbidden_actor_ids"))
    nested = _closed_enum_str_list(lane_ctx.get("ai_forbidden_actor_ids"))
    forbidden: set[str] = {*direct, *nested}
    human = str(lane_ctx.get("human_actor_id") or context.get("human_actor_id") or "").strip()
    if human:
        forbidden.add(human)
    return forbidden


def _gate_voice_forbidden_markers(text: str, profile: dict[str, Any]) -> tuple[str, str | None]:
    markers = _profile_forbidden_language_markers(profile)
    if not markers:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    lower = text.lower()
    for marker in markers:
        if marker.lower() in lower:
            return SAFETY_GATE_RESULT_REJECT, f"voice_forbidden_marker:{marker}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_actor_lane(actor_id: str, context: dict[str, Any]) -> tuple[str, str | None]:
    forbidden = _context_ai_forbidden_actor_ids(context)
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    if actor_id in forbidden:
        return SAFETY_GATE_RESULT_REJECT, f"actor_lane_forbidden_speaker:{actor_id}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_length(text: str) -> tuple[str, str | None]:
    if not text:
        return SAFETY_GATE_RESULT_REJECT, "empty_composed_follow_up"
    if len(text) > MAX_COMPOSED_FOLLOW_UP_CHARS:
        return SAFETY_GATE_RESULT_REJECT, "composed_follow_up_exceeds_length_cap"
    return SAFETY_GATE_RESULT_PASS, None


def _contains_any_token(text: str, tokens: list[str]) -> str | None:
    """Closed-enum substring containment, case-insensitive. Returns the first hit."""
    if not tokens:
        return None
    lower = text.lower()
    for token in tokens:
        candidate = token.lower().strip()
        if candidate and candidate in lower:
            return token
    return None


def _gate_no_new_people(
    text: str, context: dict[str, Any], actor_id: str
) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_new_person_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"new_person_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_no_new_rooms(text: str, context: dict[str, Any]) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_new_room_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"new_room_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_no_forbidden_plot_facts(
    text: str, context: dict[str, Any]
) -> tuple[str, str | None]:
    forbidden = _closed_enum_str_list(context.get("forbidden_plot_fact_tokens"))
    if not forbidden:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, forbidden)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"forbidden_plot_fact_mentioned:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _gate_information_disclosure(
    text: str, context: dict[str, Any]
) -> tuple[str, str | None]:
    target = (
        context.get("information_disclosure_target")
        if isinstance(context.get("information_disclosure_target"), dict)
        else {}
    )
    if not target:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    withheld_tokens: list[str] = []
    for unit in target.get("withheld_units") or []:
        if isinstance(unit, dict):
            tokens = _closed_enum_str_list(unit.get("forbidden_disclosure_tokens"))
            withheld_tokens.extend(tokens)
    if not withheld_tokens:
        return SAFETY_GATE_RESULT_NOT_APPLICABLE, None
    hit = _contains_any_token(text, withheld_tokens)
    if hit:
        return SAFETY_GATE_RESULT_REJECT, f"forbidden_disclosure:{hit}"
    return SAFETY_GATE_RESULT_PASS, None


def _run_safety_gates(
    *,
    text: str,
    actor_id: str,
    profile: dict[str, Any],
    context: dict[str, Any],
) -> dict[str, Any]:
    """Run every closed-enum safety gate on a candidate follow-up text.

    Each gate returns ``pass`` / ``reject`` / ``not_applicable`` deterministically.
    The whole composition is rejected if *any* gate returns ``reject``.
    """
    gate_calls: list[tuple[str, tuple[str, str | None]]] = [
        (SAFETY_GATE_LENGTH, _gate_length(text)),
        (SAFETY_GATE_ACTOR_LANE, _gate_actor_lane(actor_id, context)),
        (SAFETY_GATE_VOICE_FORBIDDEN_MARKERS, _gate_voice_forbidden_markers(text, profile)),
        (SAFETY_GATE_NO_NEW_PEOPLE, _gate_no_new_people(text, context, actor_id)),
        (SAFETY_GATE_NO_NEW_ROOMS, _gate_no_new_rooms(text, context)),
        (
            SAFETY_GATE_NO_FORBIDDEN_PLOT_FACTS,
            _gate_no_forbidden_plot_facts(text, context),
        ),
        (
            SAFETY_GATE_INFORMATION_DISCLOSURE,
            _gate_information_disclosure(text, context),
        ),
    ]
    decisions: dict[str, str] = {}
    rejected_reason: str | None = None
    for name, (result, reason) in gate_calls:
        decisions[name] = result
        if result == SAFETY_GATE_RESULT_REJECT and rejected_reason is None:
            rejected_reason = reason or f"{name}_rejected"
    return {
        "all_pass": rejected_reason is None,
        "decisions": decisions,
        "rejected_reason": rejected_reason,
    }


def _derive_source_contexts(
    *,
    replanning: dict[str, Any],
    context: dict[str, Any],
    profile_used: bool,
    motivation_score: float | None,
    placeholders_used: list[str] | None = None,
) -> list[str]:
    contexts: set[str] = set()
    placeholders_used = placeholders_used or []
    if profile_used:
        contexts.add(SOURCE_CONTEXT_VOICE_PROFILE)
    promoted = (
        replanning.get("promoted_input")
        if isinstance(replanning.get("promoted_input"), dict)
        else {}
    )
    if str(promoted.get("text_excerpt") or "").strip() or any(
        p in placeholders_used
        for p in ("promoted_player_input", "player_input", "promoted_player_input_id")
    ):
        contexts.add(SOURCE_CONTEXT_PROMOTED_PLAYER_INPUT)
    if str(replanning.get("interrupted_block_id") or "").strip() or any(
        p in placeholders_used
        for p in ("interrupted_block_id", "interrupted_block_type")
    ):
        contexts.add(SOURCE_CONTEXT_INTERRUPTED_BLOCK)
    if motivation_score is not None or "motivation_score" in placeholders_used:
        contexts.add(SOURCE_CONTEXT_MOTIVATION_SCORE)
    if isinstance(context.get("relationship_state_output"), dict) and context.get(
        "relationship_state_output"
    ):
        contexts.add(SOURCE_CONTEXT_RELATIONSHIP_STATE)
    if isinstance(context.get("scene_energy_output"), dict) and context.get(
        "scene_energy_output"
    ):
        contexts.add(SOURCE_CONTEXT_SCENE_ENERGY)
    if isinstance(context.get("social_pressure_output"), dict) and context.get(
        "social_pressure_output"
    ):
        contexts.add(SOURCE_CONTEXT_SOCIAL_PRESSURE)
    if isinstance(context.get("recent_visible_blocks"), list) and context.get(
        "recent_visible_blocks"
    ):
        contexts.add(SOURCE_CONTEXT_RECENT_VISIBLE_CONTEXT)
    if isinstance(context.get("information_disclosure_target"), dict) and context.get(
        "information_disclosure_target"
    ):
        contexts.add(SOURCE_CONTEXT_INFORMATION_DISCLOSURE_TARGET)
    return sorted(contexts)
