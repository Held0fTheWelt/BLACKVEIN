"""Bounded, deterministic text formatters for retrieval corpus entity chunks."""

from __future__ import annotations

from typing import Any

MAX_CHUNK_CHARS = 1600
_SCALAR_MAX = 400
_LIST_MAX_ITEMS = 12
_LIST_ITEM_MAX = 120


def cap_text(text: str, *, max_chars: int = MAX_CHUNK_CHARS) -> str:
    cleaned = "\n".join(line.rstrip() for line in text.strip().splitlines()).strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 3].rstrip() + "..."


def _scalar_line(key: str, value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return f"{key}: {str(value).lower()}"
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    text = str(value).strip()
    if not text:
        return None
    if len(text) > _SCALAR_MAX:
        text = text[: _SCALAR_MAX - 3].rstrip() + "..."
    return f"{key}: {text}"


def _list_line(key: str, value: Any) -> str | None:
    if not isinstance(value, list) or not value:
        return None
    items: list[str] = []
    for item in value[:_LIST_MAX_ITEMS]:
        if isinstance(item, dict):
            item_id = str(item.get("id") or item.get("action") or "").strip()
            if item_id:
                items.append(item_id)
            else:
                items.append(str(item)[:_LIST_ITEM_MAX])
        else:
            text = str(item).strip()
            if text:
                items.append(text[:_LIST_ITEM_MAX])
    if not items:
        return None
    suffix = " ..." if len(value) > _LIST_MAX_ITEMS else ""
    return f"{key}: {', '.join(items)}{suffix}"


def _compact_exits(exits: Any) -> str | None:
    if not isinstance(exits, list) or not exits:
        return None
    parts: list[str] = []
    for row in exits[:_LIST_MAX_ITEMS]:
        if not isinstance(row, dict):
            continue
        exit_id = str(row.get("id") or "").strip()
        to_room = str(row.get("to_room_id") or row.get("to_place_id") or "").strip()
        kind = str(row.get("kind") or "").strip()
        label = exit_id or to_room or kind
        if not label:
            continue
        if to_room and exit_id:
            parts.append(f"{exit_id}->{to_room}")
        else:
            parts.append(label)
    if not parts:
        return None
    return _list_line("exits", parts)


def format_location(place: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("id", "name", "category", "playable_access", "description"):
        line = _scalar_line(key, place.get(key))
        if line:
            lines.append(line)
    for key in ("sensory_tags", "plausible_actions", "forbidden_actions"):
        line = _list_line(key, place.get(key))
        if line:
            lines.append(line)
    prevented = place.get("prevented_actions")
    if isinstance(prevented, list) and prevented:
        ids = [
            str(row.get("id") or row.get("action") or "").strip()
            for row in prevented[:_LIST_MAX_ITEMS]
            if isinstance(row, dict)
        ]
        ids = [item for item in ids if item]
        if ids:
            lines.append(_list_line("prevented_actions", ids) or "")
    return cap_text("\n".join(line for line in lines if line))


def format_location_topology(room: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("id", "dramatic_role", "privacy", "access_pattern"):
        line = _scalar_line(key, room.get(key))
        if line:
            lines.append(line)
    for key in ("adjacent_room_ids", "plausible_actions", "forbidden_actions"):
        line = _list_line(key, room.get(key))
        if line:
            lines.append(line)
    exit_line = _compact_exits(room.get("exits"))
    if exit_line:
        lines.append(exit_line)
    prevented_exit_line = _compact_exits(room.get("prevented_exits"))
    if prevented_exit_line:
        lines.append(prevented_exit_line.replace("exits:", "prevented_exits:", 1))
    policy = _scalar_line("inventory_policy", room.get("inventory_policy"))
    if policy:
        lines.append(policy)
    return cap_text("\n".join(line for line in lines if line))


def format_object(obj: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("id", "name", "category", "placement_location_id", "playable_access", "description"):
        line = _scalar_line(key, obj.get(key))
        if line:
            lines.append(line)
    notes = obj.get("interaction_notes")
    if isinstance(notes, dict):
        for note_key, note_val in list(notes.items())[:6]:
            line = _scalar_line(f"interaction_notes.{note_key}", note_val)
            if line:
                lines.append(line)
    for key in ("sensory_tags", "plausible_actions", "forbidden_actions", "symbolic_roles"):
        line = _list_line(key, obj.get(key))
        if line:
            lines.append(line)
    return cap_text("\n".join(line for line in lines if line))


def format_character(doc: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("id", "canonical_id", "name", "role", "playable_status", "public_identity", "baseline_attitude"):
        line = _scalar_line(key, doc.get(key))
        if line:
            lines.append(line)
    opening = doc.get("opening_canon")
    if isinstance(opening, dict):
        footing = opening.get("location_footing")
        if isinstance(footing, dict):
            line = _scalar_line("opening_canon.primary_location_id", footing.get("primary_location_id"))
            if line:
                lines.append(line)
        initial = opening.get("initial_function") or opening.get("statement_pressure")
        line = _scalar_line("opening_canon.pressure", initial)
        if line:
            lines.append(line)
    return cap_text("\n".join(line for line in lines if line))


def format_canonical_step(step: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("id", "sequence", "path_id", "name", "mode"):
        line = _scalar_line(key, step.get(key))
        if line:
            lines.append(line)
    anchor = step.get("scene_anchor")
    if isinstance(anchor, dict):
        line = _scalar_line("scene_anchor.summary", anchor.get("summary"))
        if line:
            lines.append(line)
    path_point = step.get("path_point")
    if isinstance(path_point, dict):
        beats = path_point.get("action_beats")
        line = _list_line("action_beats", beats)
        if line:
            lines.append(line)
        present = path_point.get("present")
        if isinstance(present, dict):
            line = _list_line("present.named_characters", present.get("named_characters"))
            if line:
                lines.append(line)
    line = _list_line("theme_threads", step.get("theme_threads"))
    if line:
        lines.append(line)
    mandatory = step.get("mandatory_beats")
    if isinstance(mandatory, list) and mandatory:
        beat_ids = [
            str(row.get("id") or "").strip()
            for row in mandatory[:_LIST_MAX_ITEMS]
            if isinstance(row, dict)
        ]
        beat_ids = [item for item in beat_ids if item]
        line = _list_line("mandatory_beats", beat_ids)
        if line:
            lines.append(line)
    return cap_text("\n".join(line for line in lines if line))


def format_director_hint(record: dict[str, Any]) -> str:
    lines: list[str] = []
    for key in ("hint_id", "hint_type", "text"):
        line = _scalar_line(key, record.get(key))
        if line:
            lines.append(line)
    applies = record.get("_applies_when") or record.get("applies_when")
    if isinstance(applies, dict):
        for key in ("guidance_phase_keys", "scene_ids", "pacing_modes"):
            line = _list_line(f"applies_when.{key}", applies.get(key))
            if line:
                lines.append(line)
    return cap_text("\n".join(line for line in lines if line))
