"""Souffleuse projection for God of Carnage.

The Souffleuse is a Director-selected player guidance lane. It is not a
location, not a narrator, not an NPC, and not a second content database: timing
comes from canonical_path ``souffleuse_cues``; source facts and source wording
stay in English. Non-English player-visible text is produced by the story
output module.
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_yaml_authority import (
    goc_actor_identity,
    goc_character_key_for_actor_id,
    load_goc_canonical_path_yaml,
    load_goc_character_documents_yaml,
    load_goc_locations_yaml,
)
from ai_stack.prompt_store import render_prompt


SOUFFLEUSE_BLOCK_TYPE = "souffleuse"
SOUFFLEUSE_CONTRACT = "goc_souffleuse_projection.v1"
SOUFFLEUSE_ADAPTER = "goc_souffleuse_prompt_store"
SOUFFLEUSE_INVOCATION_MODE = "content_cue_prompt_store_render"
SOUFFLEUSE_INTERNAL_LANGUAGE = "en"
SOUFFLEUSE_OPENING_ROLE_ORIENTATION = "souffleuse.role_orientation"
SOUFFLEUSE_ROLE_PRESSURE = "souffleuse.role_pressure"


def _clean(value: Any) -> str:
    return str(value or "").strip()


def _lang(value: str | None) -> str:
    code = _clean(value).lower()[:2]
    return code or "de"


def _indexed_steps() -> dict[str, dict[str, Any]]:
    data = load_goc_canonical_path_yaml()
    steps = data.get("steps") if isinstance(data, dict) else []
    return {
        _clean(step.get("id")): step
        for step in (steps if isinstance(steps, list) else [])
        if isinstance(step, dict) and _clean(step.get("id"))
    }


def _indexed_locations() -> dict[str, dict[str, Any]]:
    data = load_goc_locations_yaml()
    rows = data.get("places") if isinstance(data, dict) else []
    return {
        _clean(row.get("id")): row
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and _clean(row.get("id"))
    }


def _display_location_name(location: dict[str, Any] | None, *, lang: str) -> str:
    _ = lang
    loc = location if isinstance(location, dict) else {}
    name = _clean(loc.get("name") or loc.get("id"))
    if name.lower().endswith(" edge"):
        name = name[:-5].strip()
    return name or "current location"


def _human_actor_id(runtime_projection: dict[str, Any] | None) -> str:
    proj = runtime_projection if isinstance(runtime_projection, dict) else {}
    raw = _clean(proj.get("human_actor_id") or proj.get("selected_player_role"))
    ident = goc_actor_identity(raw)
    return _clean(ident.get("actor_id")) or raw


def _character_doc_for_actor(actor_id: str) -> tuple[str, dict[str, Any]]:
    docs = load_goc_character_documents_yaml()
    key = _clean(goc_character_key_for_actor_id(actor_id))
    if key and isinstance(docs.get(key), dict):
        return key, docs[key]
    for doc_key, doc in docs.items():
        if not isinstance(doc, dict):
            continue
        if actor_id in {
            _clean(doc.get("actor_id")),
            _clean(doc.get("runtime_actor_id")),
            _clean(doc.get("id")),
            _clean(doc.get("canonical_id")),
        }:
            return _clean(doc_key), doc
    return key or actor_id, {}


def _side_label(character_doc: dict[str, Any], *, lang: str) -> str:
    _ = lang
    side = _clean(character_doc.get("household_side"))
    if side:
        label = side.replace("_", " ").title()
        return f"{label} side"
    return "your side"


def _source_refs_for_cue(
    cue: dict[str, Any],
    *,
    character_key: str,
    step: dict[str, Any],
) -> list[str]:
    refs: list[str] = []
    for ref in cue.get("source_refs") if isinstance(cue.get("source_refs"), list) else []:
        text = _clean(ref).replace("{current_human_actor}", character_key)
        if text:
            refs.append(text)
    loc = step.get("location_ref") if isinstance(step.get("location_ref"), dict) else {}
    if loc.get("source"):
        refs.append(_clean(loc.get("source")))
    refs.append(f"characters/definitions/{character_key}.yaml#character_document")
    seen: set[str] = set()
    return [ref for ref in refs if ref and not (ref in seen or seen.add(ref))]


def _last_narrator_beat(scene_blocks: list[dict[str, Any]]) -> str:
    for block in reversed(scene_blocks):
        if not isinstance(block, dict):
            continue
        if _clean(block.get("block_type")).lower() != "narrator":
            continue
        return _clean(block.get("canonical_mandatory_beat_id") or block.get("narration_beat"))
    return ""


def _last_step_id(scene_blocks: list[dict[str, Any]]) -> str:
    for block in reversed(scene_blocks):
        if not isinstance(block, dict):
            continue
        step_id = _clean(block.get("canonical_step_id"))
        if step_id:
            return step_id
    return ""


def _matching_cues(
    *,
    narrator_path: dict[str, Any],
    scene_blocks: list[dict[str, Any]],
) -> list[tuple[dict[str, Any], dict[str, Any]]]:
    del narrator_path
    beat_id = _last_narrator_beat(scene_blocks)
    step_id = _last_step_id(scene_blocks)
    if not beat_id or not step_id:
        return []
    step = _indexed_steps().get(step_id) or {}
    matches: list[tuple[dict[str, Any], dict[str, Any]]] = []
    for cue in step.get("souffleuse_cues") if isinstance(step.get("souffleuse_cues"), list) else []:
        if not isinstance(cue, dict):
            continue
        trigger = cue.get("trigger") if isinstance(cue.get("trigger"), dict) else {}
        if _clean(trigger.get("after_mandatory_beat")) == beat_id:
            matches.append((cue, step))
    return matches


def _prompt_key(cue: dict[str, Any], *, lang: str) -> str:
    raw = cue.get("prompt_key")
    if isinstance(raw, dict):
        return _clean(raw.get(lang) or raw.get("en") or raw.get("de"))
    return _clean(raw)


def _cue_is_suppressed(
    cue: dict[str, Any],
    *,
    scene_blocks: list[dict[str, Any]],
    player_name: str,
) -> bool:
    raw_suppress = cue.get("suppress_if") if isinstance(cue.get("suppress_if"), list) else []
    suppress = {
        _clean(item)
        for item in raw_suppress
    }
    if "narrator_already_established_player_role_and_playable_options" not in suppress:
        return False
    joined = "\n".join(_clean(block.get("text")) for block in scene_blocks if isinstance(block, dict))
    folded = joined.casefold()
    return bool(player_name and player_name.casefold() in folded and ("you " in folded or "du " in folded))


def _projection_variables(
    *,
    lang: str,
    character_doc: dict[str, Any],
    current_step: dict[str, Any],
) -> dict[str, str]:
    locations = _indexed_locations()
    current_loc_ref = current_step.get("location_ref") if isinstance(current_step.get("location_ref"), dict) else {}
    current_location = locations.get(_clean(current_loc_ref.get("location_id"))) or {}
    canonical = load_goc_canonical_path_yaml()
    first_step_id = ""
    paths = canonical.get("paths") if isinstance(canonical.get("paths"), dict) else {}
    opening = paths.get("opening") if isinstance(paths.get("opening"), dict) else {}
    first_step_id = _clean(opening.get("first_step_id"))
    first_step = _indexed_steps().get(first_step_id) or {}
    incident_ref = first_step.get("location_ref") if isinstance(first_step.get("location_ref"), dict) else {}
    incident_location = locations.get(_clean(incident_ref.get("location_id"))) or {}
    opening_canon = character_doc.get("opening_canon") if isinstance(character_doc.get("opening_canon"), dict) else {}
    return {
        "player_name": _clean(character_doc.get("name")) or "Player",
        "player_side_label": _side_label(character_doc, lang=lang),
        "location_name": _display_location_name(current_location, lang=lang),
        "incident_location_name": _display_location_name(incident_location, lang=lang),
        "role_pressure": (
            _clean(opening_canon.get("statement_pressure"))
            or _clean(character_doc.get("baseline_attitude"))
            or _clean(character_doc.get("public_identity"))
        ),
    }


def _block_delivery() -> dict[str, Any]:
    return {
        "mode": "typewriter",
        "characters_per_second": 48,
        "pause_before_ms": 120,
        "pause_after_ms": 520,
        "skippable": True,
    }


def build_goc_opening_souffleuse_projection(
    *,
    session_output_language: str = "de",
    runtime_projection: dict[str, Any] | None = None,
    narrator_path: dict[str, Any] | None = None,
    scene_blocks: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Return Souffleuse scene blocks selected by canonical content cues."""
    lang = _lang(session_output_language)
    path = narrator_path if isinstance(narrator_path, dict) else {}
    blocks = [dict(block) for block in (scene_blocks or []) if isinstance(block, dict)]
    diagnostics: dict[str, Any] = {
        "contract": SOUFFLEUSE_CONTRACT,
        "adapter": SOUFFLEUSE_ADAPTER,
        "adapter_invocation_mode": SOUFFLEUSE_INVOCATION_MODE,
        "internal_resolution_language": SOUFFLEUSE_INTERNAL_LANGUAGE,
        "source_language": SOUFFLEUSE_INTERNAL_LANGUAGE,
        "session_output_language": lang,
        "requires_output_realization": lang != SOUFFLEUSE_INTERNAL_LANGUAGE,
        "selected": False,
        "errors": [],
    }
    actor_id = _human_actor_id(runtime_projection)
    character_key, character_doc = _character_doc_for_actor(actor_id)
    if not actor_id or not character_doc:
        diagnostics["errors"].append("missing_human_actor_character_document")
        return {"blocks": [], "diagnostics": diagnostics}

    player_name = _clean(character_doc.get("name")) or actor_id
    matches = _matching_cues(narrator_path=path, scene_blocks=blocks)
    if not matches:
        diagnostics["reason"] = "no_matching_content_cue"
        return {"blocks": [], "diagnostics": diagnostics}

    out_blocks: list[dict[str, Any]] = []
    for cue, step in matches[:1]:
        if _cue_is_suppressed(cue, scene_blocks=blocks, player_name=player_name):
            diagnostics["reason"] = "content_cue_suppressed"
            continue
        key = _prompt_key(cue, lang=SOUFFLEUSE_INTERNAL_LANGUAGE)
        if not key:
            diagnostics["errors"].append("missing_prompt_key")
            continue
        variables = _projection_variables(
            lang=SOUFFLEUSE_INTERNAL_LANGUAGE,
            character_doc=character_doc,
            current_step=step,
        )
        try:
            text = render_prompt(key, **variables).strip()
        except Exception as exc:  # noqa: BLE001 - opening should survive prompt-store drift.
            diagnostics["errors"].append(f"prompt_render_failed:{type(exc).__name__}")
            diagnostics["prompt_key"] = key
            continue
        if not text:
            diagnostics["errors"].append("empty_prompt_render")
            continue
        cue_id = _clean(cue.get("id")) or "souffleuse_cue"
        capability = _clean(cue.get("capability")) or SOUFFLEUSE_OPENING_ROLE_ORIENTATION
        block = {
            "id": f"opening-souffleuse-{cue_id}",
            "block_type": SOUFFLEUSE_BLOCK_TYPE,
            "speaker_label": "Souffleuse",
            "actor_id": None,
            "target_actor_id": actor_id,
            "text": text,
            "player_display_text": text,
            "visible_lane": "player_hint",
            "card_style": "director_notice",
            "delivery": _block_delivery(),
            "source": "canonical_path_souffleuse_cue",
            "narration_beat": "souffleuse_orientation",
            "canonical_step_id": _clean(step.get("id")),
            "canonical_step_sequence": int(step.get("sequence") or 0),
            "souffleuse_cue_id": cue_id,
            "contract": SOUFFLEUSE_CONTRACT,
            "voice_mode": _clean(cue.get("voice_mode")) or "second_person_inner",
            "commit_impact": _clean(cue.get("commit_impact")) or "ui_guidance_only",
            "internal_resolution_language": SOUFFLEUSE_INTERNAL_LANGUAGE,
            "source_language": SOUFFLEUSE_INTERNAL_LANGUAGE,
            "session_output_language": lang,
            "visible_output_language": SOUFFLEUSE_INTERNAL_LANGUAGE,
            "requires_output_realization": lang != SOUFFLEUSE_INTERNAL_LANGUAGE,
            "prompt_key": key,
            "origin_aspect": "souffleuse",
            "origin_beat_id": cue_id,
            "origin_capability": capability,
            "authority_owner": "director",
            "expected_owner": "director",
            "actual_owner": "director",
            "evidence_role": "supporting",
            "source_refs": _source_refs_for_cue(cue, character_key=character_key, step=step),
            "source_facts": {
                "character_public_identity": _clean(character_doc.get("public_identity")),
                "character_baseline_attitude": _clean(character_doc.get("baseline_attitude")),
                "character_statement_pressure": _clean(
                    (character_doc.get("opening_canon") or {}).get("statement_pressure")
                    if isinstance(character_doc.get("opening_canon"), dict)
                    else ""
                ),
            },
        }
        out_blocks.append(block)
        diagnostics.update(
            {
                "selected": True,
                "cue_id": cue_id,
                "prompt_key": key,
                "capability": capability,
                "target_actor_id": actor_id,
                "canonical_step_id": _clean(step.get("id")),
            }
        )

    return {"blocks": out_blocks, "diagnostics": diagnostics}


__all__ = [
    "SOUFFLEUSE_ADAPTER",
    "SOUFFLEUSE_BLOCK_TYPE",
    "SOUFFLEUSE_CONTRACT",
    "SOUFFLEUSE_INTERNAL_LANGUAGE",
    "SOUFFLEUSE_INVOCATION_MODE",
    "SOUFFLEUSE_OPENING_ROLE_ORIENTATION",
    "SOUFFLEUSE_ROLE_PRESSURE",
    "build_goc_opening_souffleuse_projection",
]
