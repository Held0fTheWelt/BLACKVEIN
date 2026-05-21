"""Shared imports and common shell readout helpers."""

from __future__ import annotations

from typing import Any
import re

from ai_stack.story_runtime.god_of_carnage.god_of_carnage_yaml_authority import goc_actor_display_name, goc_actor_identity
from ai_stack.prompt_store import render_prompt


def _readout_text(prompt_key: str, **variables: Any) -> str:
    return render_prompt(prompt_key, **variables)


def _first_responder_actor(last_diagnostic: dict[str, Any] | None) -> str | None:
    if not isinstance(last_diagnostic, dict):
        return None
    responders = last_diagnostic.get("selected_responder_set")
    if isinstance(responders, list) and responders and isinstance(responders[0], dict):
        actor = responders[0].get("actor_id")
        if isinstance(actor, str) and actor.strip():
            return actor.strip()
    return None


def _selected_scene_function(last_diagnostic: dict[str, Any] | None) -> str:
    if isinstance(last_diagnostic, dict):
        value = last_diagnostic.get("selected_scene_function")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""


def _social_state_record(last_diagnostic: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(last_diagnostic, dict):
        rec = last_diagnostic.get("social_state_record")
        if isinstance(rec, dict):
            return rec
    return {}


def _responder_label(responder_actor: str | None) -> str:
    return goc_actor_display_name(responder_actor, first_name=True) if responder_actor else "Someone"


def _actor_blob(responder_actor: str | None) -> str:
    ident = goc_actor_identity(responder_actor)
    return " ".join(
        str(ident.get(key) or "")
        for key in (
            "actor_id",
            "character_key",
            "name",
            "role",
            "playable_status",
            "household_side",
        )
    ).lower()


def _actor_has(responder_actor: str | None, *terms: str) -> bool:
    blob = _actor_blob(responder_actor)
    return bool(blob) and all(str(term or "").lower() in blob for term in terms)


def _actor_has_any(responder_actor: str | None, *terms: str) -> bool:
    blob = _actor_blob(responder_actor)
    return bool(blob) and any(str(term or "").lower() in blob for term in terms)


def _responder_social_side(responder_actor: str | None) -> str:
    if _actor_has(responder_actor, "host"):
        return "host side"
    if _actor_has(responder_actor, "guest"):
        return "guest side"
    return "room side"


def _open_pressures(committed_state: dict[str, Any]) -> list[str]:
    raw = committed_state.get("last_open_pressures")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _last_consequences(committed_state: dict[str, Any]) -> list[str]:
    raw = committed_state.get("last_committed_consequences")
    if isinstance(raw, list):
        return [str(x) for x in raw if str(x).strip()]
    return []


def _thread_continuity(committed_state: dict[str, Any]) -> dict[str, Any]:
    tc = committed_state.get("narrative_thread_continuity")
    return tc if isinstance(tc, dict) else {}


def _environment_state(committed_state: dict[str, Any]) -> dict[str, Any]:
    env = committed_state.get("environment_state")
    return env if isinstance(env, dict) else {}


def _contains_any(values: list[str], *needles: str) -> bool:
    lowered = " | ".join(values).lower().replace("_", " ").replace("-", " ")
    for needle in needles:
        normalized = needle.lower().replace("_", " ").replace("-", " ").strip()
        if not normalized:
            continue
        if re.search(rf"\b{re.escape(normalized)}\b", lowered):
            return True
    return False


def _has_hosting_surface(values: list[str]) -> bool:
    return _contains_any(values, "rum", "drink", "glass", "hosting", "table", "coffee table", "coffee_table")


def _with_indefinite_article(phrase: str) -> str:
    stripped = (phrase or "").strip()
    if not stripped:
        return stripped
    return ("an " + stripped) if stripped[0].lower() in "aeiou" else ("a " + stripped)

__all__ = (
    '_readout_text',
    '_first_responder_actor',
    '_selected_scene_function',
    '_social_state_record',
    '_responder_label',
    '_actor_blob',
    '_actor_has',
    '_actor_has_any',
    '_responder_social_side',
    '_open_pressures',
    '_last_consequences',
    '_thread_continuity',
    '_environment_state',
    '_contains_any',
    '_has_hosting_surface',
    '_with_indefinite_article',
)
