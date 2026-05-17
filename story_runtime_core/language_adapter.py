"""Thin semantic language adapter.

This module deliberately contains no verb ontology, locale table, action map,
or alias dictionary. It exposes the content that already exists in module files
as an AI-readable semantic catalog and defines the shape of the model-produced
resolution. Meaning is inferred from the player's utterance against that
catalog by the AI layer, not by code-level word maps.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

from story_runtime_core.player_input_intent_contract import (
    default_commit_flags_for_player_input_kind,
    is_non_story_control_player_input_kind,
    is_speech_like_player_input_kind,
)

__all__ = [
    "build_interaction_surface",
    "build_player_attributed_visible_line",
    "build_semantic_resolution_contract",
    "classify_player_input_from_rules",
    "clear_language_adapter_caches",
    "default_player_intent_commit_flags",
    "greeting_imperative_addressee_fragment",
    "greeting_imperative_visible_pair",
    "infer_verb_and_action_kind",
    "load_session_language_model_directive",
    "resolve_content_modules_root",
    "resolve_string",
]


def resolve_content_modules_root(explicit: Path | None = None) -> Path:
    """Return the ``content/modules`` directory."""
    if explicit is not None:
        p = explicit.expanduser().resolve()
        if not p.is_dir():
            raise FileNotFoundError(f"content_modules_root is not a directory: {p}")
        return p
    env = (os.environ.get("WOS_REPO_ROOT") or "").strip()
    if env:
        p = Path(env).expanduser().resolve() / "content" / "modules"
        if p.is_dir():
            return p
    cur = Path(__file__).resolve().parent
    for _ in range(24):
        cand = cur / "content" / "modules"
        if cand.is_dir():
            return cand.resolve()
        if cur.parent == cur:
            break
        cur = cur.parent
    raise RuntimeError(
        "Cannot resolve content/modules: set WOS_REPO_ROOT to the checkout or container root "
        "that contains content/modules/, or run from a monorepo tree that includes content/modules/."
    )


def clear_language_adapter_caches() -> None:
    _interaction_surface_cached.cache_clear()


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _relative(module_dir: Path, path: Path) -> str:
    try:
        return path.relative_to(module_dir).as_posix()
    except ValueError:
        return path.as_posix()


def _clean_list(values: Any) -> list[Any]:
    return list(values) if isinstance(values, list) else []


def _content_terms(identifier: str, row: dict[str, Any]) -> list[str]:
    terms: list[str] = []
    for value in (identifier, row.get("name"), row.get("display_name")):
        text = str(value or "").strip()
        if text and text not in terms:
            terms.append(text)
    return terms


def _source_ref(module_dir: Path, path: Path, field: str) -> str:
    return f"{_relative(module_dir, path)}#{field}"


def _read_location_documents(module_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    loc_dir = module_dir / "locations"
    if not loc_dir.is_dir():
        return out
    for path in sorted(loc_dir.rglob("*.yaml")):
        if path.name in {"index.yaml", "locations.yaml", "apartment_layout.yaml"}:
            continue
        payload = _read_yaml(path)
        row = payload.get("location") or payload.get("place")
        if not isinstance(row, dict):
            continue
        rid = str(row.get("id") or path.stem).strip()
        if rid:
            out[rid] = {**row, "_source_path": path}
    return out


def _read_layout_rooms(module_dir: Path) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    for path in (
        module_dir / "locations" / "appartment_vallon" / "apartment_layout.yaml",
        module_dir / "locations" / "appartment" / "apartment_layout.yaml",
        module_dir / "locations" / "apartment" / "apartment_layout.yaml",
        module_dir / "locations" / "apartment_layout.yaml",
        module_dir / "apartment_layout.yaml",
    ):
        payload = _read_yaml(path)
        layout = payload.get("apartment_layout") if isinstance(payload.get("apartment_layout"), dict) else {}
        if not layout:
            continue
        rooms: dict[str, dict[str, Any]] = {}
        for row in layout.get("rooms") if isinstance(layout.get("rooms"), list) else []:
            if not isinstance(row, dict):
                continue
            rid = str(row.get("id") or "").strip()
            if rid:
                rooms[rid] = {**row, "_source_path": path}
        return layout, rooms
    return {}, {}


def _read_object_documents(module_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    obj_dir = module_dir / "objects"
    if not obj_dir.is_dir():
        return out
    for path in sorted(obj_dir.rglob("*.yaml")):
        if path.name in {"index.yaml", "objects.yaml"}:
            continue
        payload = _read_yaml(path)
        row = payload.get("object") or payload.get("object_document")
        if not isinstance(row, dict):
            continue
        oid = str(row.get("id") or path.stem).strip()
        if oid:
            out[oid] = {**row, "_source_path": path}
    return out


def _read_character_documents(module_dir: Path) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    char_dir = module_dir / "characters"
    if not char_dir.is_dir():
        return out
    for path in sorted(char_dir.rglob("*.yaml")):
        payload = _read_yaml(path)
        row = payload.get("character_document") or payload.get("character")
        if not isinstance(row, dict):
            continue
        cid = str(row.get("id") or row.get("canonical_id") or path.stem).strip()
        if cid:
            out[cid] = {**row, "_source_path": path}
    return out


def _location_surface(module_dir: Path, rid: str, row: dict[str, Any]) -> dict[str, Any]:
    path = row.get("_source_path") if isinstance(row.get("_source_path"), Path) else module_dir
    source = _relative(module_dir, path) if path != module_dir else None
    return {
        "id": rid,
        "source": source,
        "content_terms": _content_terms(rid, row),
        "name": row.get("name"),
        "category": row.get("category"),
        "playable_access": row.get("playable_access") or row.get("access_pattern"),
        "description": row.get("description"),
        "description_source_ref": _source_ref(module_dir, path, "location.description") if source else None,
        "connected_place_ids": (row.get("room_profile") or {}).get("connected_place_ids")
        if isinstance(row.get("room_profile"), dict)
        else row.get("adjacent_room_ids"),
        "inventory_object_ids": _clean_list(row.get("inventory_object_ids")),
        "plausible_actions": _clean_list(row.get("plausible_actions")),
        "prevented_actions": _clean_list(row.get("prevented_actions")),
        "forbidden_actions": _clean_list(row.get("forbidden_actions")),
        "sensory_tags": _clean_list(row.get("sensory_tags")),
    }


def _object_surface(module_dir: Path, oid: str, row: dict[str, Any]) -> dict[str, Any]:
    path = row.get("_source_path") if isinstance(row.get("_source_path"), Path) else module_dir
    source = _relative(module_dir, path) if path != module_dir else None
    return {
        "id": oid,
        "source": source,
        "content_terms": _content_terms(oid, row),
        "name": row.get("name"),
        "category": row.get("category"),
        "placement_location_id": row.get("placement_location_id") or row.get("placement_room_id"),
        "playable_access": row.get("playable_access"),
        "portable": row.get("portable"),
        "description": row.get("description"),
        "description_source_ref": _source_ref(module_dir, path, "object.description") if source else None,
        "interaction_notes": row.get("interaction_notes") if isinstance(row.get("interaction_notes"), dict) else {},
        "plausible_actions": _clean_list(row.get("plausible_actions")),
        "prevented_actions": _clean_list(row.get("prevented_actions")),
        "forbidden_actions": _clean_list(row.get("forbidden_actions")),
        "sensory_tags": _clean_list(row.get("sensory_tags")),
        "symbolic_roles": _clean_list(row.get("symbolic_roles")),
    }


def _character_surface(module_dir: Path, cid: str, row: dict[str, Any]) -> dict[str, Any]:
    path = row.get("_source_path") if isinstance(row.get("_source_path"), Path) else module_dir
    source = _relative(module_dir, path) if path != module_dir else None
    return {
        "id": cid,
        "source": source,
        "content_terms": _content_terms(cid, row),
        "name": row.get("name"),
        "role": row.get("role"),
        "runtime_actor_id": row.get("runtime_actor_id") or row.get("actor_id"),
    }


def build_semantic_resolution_contract(*, raw_text: str | None = None, lang: str | None = None) -> dict[str, Any]:
    """Return the AI contract for turning player language into grounded intent."""
    return {
        "schema_version": "semantic_language_adapter.player_action_resolution.v1",
        "policy": {
            "no_hardcoded_language_maps": True,
            "infer_meaning_from_player_utterance_and_content_catalog": True,
            "do_not_translate_by_lookup_table": True,
            "ground_targets_in_content_ids_when_possible": True,
            "preserve_unknowns_as_clarification_requests": True,
        },
        "input": {
            "raw_player_text": str(raw_text or ""),
            "session_output_language": str(lang or "").strip() or None,
        },
        "expected_ai_output": {
            "player_input_kind": "speech|question|action|perception|mixed|object_interaction|social_nonverbal_action|physical_action|wait_or_observe|ambiguous|unclear",
            "action_kind": "free semantic label chosen by the model, grounded in utterance and catalog",
            "verb": "free semantic label chosen by the model, not restricted by engine maps",
            "target_query": "text span or null",
            "resolved_target_id": "location/object/character id or null",
            "resolved_target_type": "location|object|actor|null",
            "source_query": "optional source/container text span or null",
            "resolved_source_id": "optional content id or null",
            "commit_policy": "commit_action|commit_speech|no_commit|needs_clarification|recover_or_reject",
            "confidence": "high|medium|low",
            "reasoning_summary": "short grounding explanation citing content ids/fields",
        },
    }


@lru_cache(maxsize=64)
def _interaction_surface_cached(module_dir_s: str) -> dict[str, Any]:
    module_dir = Path(module_dir_s)
    module_id = module_dir.name
    layout, layout_rooms = _read_layout_rooms(module_dir)
    doc_locations = _read_location_documents(module_dir)
    merged_locations: dict[str, dict[str, Any]] = {}
    for rid, row in layout_rooms.items():
        merged_locations[rid] = dict(row)
    for rid, row in doc_locations.items():
        base = dict(merged_locations.get(rid) or {})
        base.update(row)
        merged_locations[rid] = base
    current_area = (
        layout.get("narrative_anchor_area_id")
        or (layout.get("location_assignment") or {}).get("live_play_default_location_id")
    )
    return {
        "id": f"{module_id}_semantic_interaction_surface",
        "schema_version": "semantic_language_adapter.interaction_surface.v1",
        "authority": "derived_from_content_files",
        "current_area": current_area,
        "setting_id": layout.get("setting_id"),
        "adapter_policy": {
            "module_locale_files_required": False,
            "engine_maps_allowed": False,
            "meaning_source": "ai_semantic_resolution_against_content_catalog",
        },
        "semantic_resolution_contract": build_semantic_resolution_contract(),
        "locations": [
            _location_surface(module_dir, rid, row)
            for rid, row in sorted(merged_locations.items())
        ],
        "objects": [
            _object_surface(module_dir, oid, row)
            for oid, row in sorted(_read_object_documents(module_dir).items())
        ],
        "characters": [
            _character_surface(module_dir, cid, row)
            for cid, row in sorted(_read_character_documents(module_dir).items())
        ],
    }


def build_interaction_surface(
    module_id: str,
    *,
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    root = resolve_content_modules_root(content_modules_root)
    mid = str(module_id or "").strip()
    if not mid:
        return {}
    module_dir = root / mid
    if not module_dir.is_dir():
        return {}
    return _interaction_surface_cached(str(module_dir.resolve()))


def classify_player_input_from_rules(
    raw_text: str,
    *,
    module_id: str,
    lang_hint: str = "de",
    content_modules_root: Path | None = None,
) -> dict[str, Any]:
    """Return an AI-required classification shell; no rule table is consulted."""
    surface = build_interaction_surface(module_id, content_modules_root=content_modules_root)
    flags = default_commit_flags_for_player_input_kind("ambiguous")
    return {
        "player_input_kind": "ambiguous",
        "semantic_category": "semantic_resolution_required",
        "speech_projection_allowed": False,
        "deterministic_intent_rule": None,
        "projection_key": None,
        "captures": {},
        "semantic_resolution_required": True,
        "semantic_resolution_contract": build_semantic_resolution_contract(
            raw_text=raw_text,
            lang=lang_hint,
        ),
        "semantic_catalog_available": bool(surface),
        **flags,
    }


def infer_verb_and_action_kind(
    raw_text: str,
    *,
    module_id: str,
    player_input_kind: str,
    content_modules_root: Path | None = None,
) -> tuple[str, str]:
    """Return only a sentinel unless upstream AI has already resolved semantics."""
    del raw_text, module_id, content_modules_root
    pik = str(player_input_kind or "").strip().lower()
    if is_non_story_control_player_input_kind(pik):
        return "meta", "control"
    if is_speech_like_player_input_kind(pik):
        return "utterance", "speech"
    return "semantic_resolution_required", "semantic_action"


def resolve_string(
    module_id: str,
    key: str,
    lang: str,
    *,
    content_modules_root: Path | None = None,
    fallback_module_id: str | None = None,
    **placeholders: Any,
) -> str:
    """Render a neutral technical fallback without content or locale lookup."""
    del module_id, key, lang, content_modules_root, fallback_module_id
    if "raw" in placeholders and "name" in placeholders:
        return f"{placeholders['name']}: {placeholders['raw']}"
    if "role" in placeholders:
        return str(placeholders["role"])
    return ""


def build_player_attributed_visible_line(
    *,
    name: str,
    raw: str,
    input_kind: str,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
    projection_key: str | None = None,
    projection_captures: dict[str, Any] | None = None,
) -> str:
    del input_kind, lang, module_id, content_modules_root, projection_key, projection_captures
    return f"{str(name or '').strip()}: {str(raw or '').strip()}".strip()


def greeting_imperative_addressee_fragment(
    raw: str,
    *,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
) -> str | None:
    del raw, lang, module_id, content_modules_root
    return None


def greeting_imperative_visible_pair(
    raw: str,
    *,
    addressee: str,
    player_shell_name: str,
    lang: str,
    module_id: str,
    content_modules_root: Path | None = None,
) -> tuple[str, str] | None:
    del raw, addressee, player_shell_name, lang, module_id, content_modules_root
    return None


def load_session_language_model_directive(
    *,
    module_id: str,
    lang: str,
    content_modules_root: Path | None = None,
) -> str:
    del module_id, content_modules_root
    language = str(lang or "").strip() or "the session output language"
    return (
        "Resolve player-visible narration semantically and write it in "
        f"session_output_language={language}. Do not use module locale files or engine "
        "lookup maps for meaning; infer intent from the utterance and grounded content catalog."
    )


def default_player_intent_commit_flags(player_input_kind: str) -> dict[str, bool]:
    d = default_commit_flags_for_player_input_kind(player_input_kind)
    return {k: bool(d[k]) for k in d}
