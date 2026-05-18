"""Narrator-path realization for the God of Carnage canonical opening.

This module is intentionally a renderer, not a second content database. It
loads the numbered canonical path and referenced location/object authority, then
projects the first narrator-only transition into visible blocks.
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_yaml_authority import (
    load_goc_canonical_module_yaml,
    load_goc_canonical_path_yaml,
    load_goc_locations_yaml,
    load_goc_objects_yaml,
)
from ai_stack.visible_narrative_contract import sanitize_gm_narration_beat_line

NARRATOR_PATH_CONTRACT = "goc_narrator_path.opening.v1"
NARRATOR_PATH_ADAPTER = "goc_narrator_path_direct"
NARRATOR_PATH_INVOCATION_MODE = "narrator_path_direct"


def _opening_steps() -> list[dict[str, Any]]:
    data = load_goc_canonical_path_yaml()
    steps = data.get("steps") if isinstance(data, dict) else []
    path = data.get("paths") if isinstance(data.get("paths"), dict) else {}
    opening = path.get("opening") if isinstance(path.get("opening"), dict) else {}
    first_step_id = str(opening.get("first_step_id") or "").strip()
    first_playable_step_id = str(opening.get("first_playable_step_id") or "").strip()
    step_order = [
        str(step_id).strip()
        for step_id in (data.get("step_order") if isinstance(data.get("step_order"), list) else [])
        if str(step_id).strip()
    ]
    by_id = {
        str(row.get("id") or "").strip(): row
        for row in (steps if isinstance(steps, list) else [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }

    if first_step_id and first_playable_step_id and step_order:
        try:
            start = step_order.index(first_step_id)
            end = step_order.index(first_playable_step_id)
        except ValueError:
            start = end = -1
        if 0 <= start <= end:
            selected = [by_id[step_id] for step_id in step_order[start : end + 1] if step_id in by_id]
            if selected:
                return selected

    selected: list[dict[str, Any]] = []
    for row in steps if isinstance(steps, list) else []:
        mode = str(row.get("mode") or "").strip()
        if not mode.startswith("narrator_"):
            if selected:
                return selected
            continue
        selected.append(row)
    return selected


def _source_ref_for_step(step: dict[str, Any]) -> str:
    sequence = int(step.get("sequence") or 0)
    step_id = str(step.get("id") or "").strip()
    if sequence > 0 and step_id:
        suffix = step_id.removeprefix(f"opening_{sequence:03d}_")
        return f"canonical_path/{sequence:03d}_{suffix}.yaml"
    return f"canonical_path#{step_id or 'unknown'}"


def _delivery() -> dict[str, Any]:
    return {
        "mode": "typewriter",
        "characters_per_second": 44,
        "pause_before_ms": 150,
        "pause_after_ms": 650,
        "skippable": True,
    }


def _locations_by_id() -> dict[str, dict[str, Any]]:
    data = load_goc_locations_yaml()
    rows = data.get("places") if isinstance(data, dict) else []
    return {
        str(row.get("id") or "").strip(): row
        for row in (rows if isinstance(rows, list) else [])
        if isinstance(row, dict) and str(row.get("id") or "").strip()
    }


def _objects_by_id() -> dict[str, dict[str, Any]]:
    data = load_goc_objects_yaml()
    rows = data.get("object_documents") if isinstance(data, dict) else {}
    return {
        str(obj_id or row.get("id") or "").strip(): row
        for obj_id, row in (rows.items() if isinstance(rows, dict) else [])
        if isinstance(row, dict) and str(obj_id or row.get("id") or "").strip()
    }


def _compact_location(doc: dict[str, Any] | None, *, use_fields: list[str] | None = None) -> dict[str, Any]:
    loc = doc if isinstance(doc, dict) else {}
    fields = set(use_fields or [])
    out: dict[str, Any] = {
        "id": str(loc.get("id") or "").strip(),
        "name": str(loc.get("name") or "").strip(),
    }
    for key in ("description", "sensory_tags", "plausible_actions", "forbidden_actions"):
        if not fields or key in fields:
            value = loc.get(key)
            if value:
                out[key] = value
    if not fields or "entrances_exits" in fields:
        exits = loc.get("entrances_exits")
        if exits:
            out["entrances_exits"] = exits
    context = loc.get("real_world_context")
    if isinstance(context, dict) and context.get("usable_texture"):
        out["real_world_texture"] = context.get("usable_texture")
    return {key: value for key, value in out.items() if value not in ("", [], {}, None)}


def _compact_object(doc: dict[str, Any] | None, *, use_fields: list[str] | None = None) -> dict[str, Any]:
    obj = doc if isinstance(doc, dict) else {}
    fields = set(use_fields or [])
    out: dict[str, Any] = {
        "id": str(obj.get("id") or "").strip(),
        "name": str(obj.get("name") or "").strip(),
        "placement_location_id": str(obj.get("placement_location_id") or "").strip(),
    }
    for key in ("description", "sensory_tags", "interaction_notes", "symbolic_roles"):
        if not fields or key in fields:
            value = obj.get(key)
            if value:
                out[key] = value
    return {key: value for key, value in out.items() if value not in ("", [], {}, None)}


def _module_context() -> dict[str, Any]:
    module = load_goc_canonical_module_yaml()
    content = module.get("content") if isinstance(module.get("content"), dict) else {}
    return {
        "module_id": str(module.get("module_id") or "").strip(),
        "title": str(module.get("title") or "").strip(),
        "setting": str(content.get("setting") or "").strip(),
        "narrative_scope": str(content.get("narrative_scope") or "").strip(),
    }


def _content_refs(step: dict[str, Any], beat: dict[str, Any] | None = None) -> list[str]:
    refs: list[str] = [_source_ref_for_step(step)]
    loc = step.get("location_ref") if isinstance(step.get("location_ref"), dict) else {}
    if loc.get("source"):
        refs.append(str(loc["source"]))
    for key in ("support_refs", "object_refs"):
        rows = step.get(key)
        if isinstance(rows, list):
            for row in rows:
                if isinstance(row, dict) and row.get("source"):
                    refs.append(str(row["source"]))
    obj = step.get("object_focus_ref") if isinstance(step.get("object_focus_ref"), dict) else {}
    if obj.get("source"):
        refs.append(str(obj["source"]))
    topo = step.get("topology_ref") if isinstance(step.get("topology_ref"), dict) else {}
    if topo.get("source"):
        refs.append(str(topo["source"]))
    if isinstance(beat, dict):
        params = beat.get("beat_pattern_params") if isinstance(beat.get("beat_pattern_params"), dict) else {}
        for ref in params.get("sensory_anchors") if isinstance(params.get("sensory_anchors"), list) else []:
            if str(ref).strip():
                refs.append(str(ref).strip())
    seen: set[str] = set()
    return [ref for ref in refs if not (ref in seen or seen.add(ref))]


def _ref_use_fields(row: dict[str, Any]) -> list[str] | None:
    fields = row.get("use_fields") if isinstance(row, dict) else None
    return [str(item).strip() for item in fields if str(item).strip()] if isinstance(fields, list) else None


def _beat_source_facts(step: dict[str, Any], beat: dict[str, Any]) -> dict[str, Any]:
    locations = _locations_by_id()
    objects = _objects_by_id()
    loc_ref = step.get("location_ref") if isinstance(step.get("location_ref"), dict) else {}
    support_refs = step.get("support_refs") if isinstance(step.get("support_refs"), list) else []
    object_refs = step.get("object_refs") if isinstance(step.get("object_refs"), list) else []
    params = beat.get("beat_pattern_params") if isinstance(beat.get("beat_pattern_params"), dict) else {}
    instruction = beat.get("director_instruction") if isinstance(beat.get("director_instruction"), dict) else {}
    perception_cues = _perception_lines(beat)
    return {
        "semantic_input_language": "en",
        "module_context": _module_context(),
        "step": {
            "id": str(step.get("id") or "").strip(),
            "sequence": int(step.get("sequence") or 0),
            "name": str(step.get("name") or "").strip(),
            "mode": str(step.get("mode") or "").strip(),
            "summary": str((step.get("scene_anchor") or {}).get("summary") or "").strip()
            if isinstance(step.get("scene_anchor"), dict)
            else "",
            "duration_target_seconds": int(step.get("duration_target_seconds") or 0),
        },
        "location": _compact_location(
            locations.get(str(loc_ref.get("location_id") or "").strip()),
            use_fields=_ref_use_fields(loc_ref),
        ),
        "support_locations": [
            _compact_location(
                locations.get(str(row.get("location_id") or "").strip()),
                use_fields=_ref_use_fields(row),
            )
            for row in support_refs
            if isinstance(row, dict)
        ],
        "objects": [
            _compact_object(
                objects.get(str(row.get("object_id") or "").strip()),
                use_fields=_ref_use_fields(row),
            )
            for row in object_refs
            if isinstance(row, dict)
        ],
        "presence": step.get("present") if isinstance(step.get("present"), dict) else {},
        "mandatory_beat": {
            "id": str(beat.get("id") or "").strip(),
            "order": int(beat.get("order") or 0),
            "duration_target_seconds": int(beat.get("duration_target_seconds") or 0),
            "coverage_cues": perception_cues,
            "sensory_anchors": [
                str(item).strip()
                for item in params.get("sensory_anchors")
                if str(item).strip()
            ]
            if isinstance(params.get("sensory_anchors"), list)
            else [],
            "player_status": str(
                beat.get("player_status")
                or instruction.get("player_status")
                or ""
            ).strip(),
        },
        "next_point": step.get("next_point") if isinstance(step.get("next_point"), dict) else {},
        "state_changes_committed": step.get("state_changes_committed")
        if isinstance(step.get("state_changes_committed"), list)
        else [],
    }


def _location_ref_id(step: dict[str, Any] | None) -> str:
    row = step if isinstance(step, dict) else {}
    loc_ref = row.get("location_ref") if isinstance(row.get("location_ref"), dict) else {}
    return str(loc_ref.get("location_id") or "").strip()


def _scene_anchor_scene(step: dict[str, Any] | None) -> str:
    row = step if isinstance(step, dict) else {}
    anchor = row.get("scene_anchor") if isinstance(row.get("scene_anchor"), dict) else {}
    return str(anchor.get("scene") or "").strip()


def _transition_facts(
    *,
    previous_step: dict[str, Any] | None,
    current_step: dict[str, Any],
) -> dict[str, Any]:
    prev_loc_id = _location_ref_id(previous_step)
    curr_loc_id = _location_ref_id(current_step)
    prev_scene = _scene_anchor_scene(previous_step)
    curr_scene = _scene_anchor_scene(current_step)
    if not previous_step:
        return {"kind": "opening_start", "location_changed": False, "scene_changed": False}
    if prev_loc_id == curr_loc_id and prev_scene == curr_scene:
        return {"kind": "continuous", "location_changed": False, "scene_changed": False}
    locations = _locations_by_id()
    previous_next = (
        previous_step.get("next_point")
        if isinstance(previous_step, dict) and isinstance(previous_step.get("next_point"), dict)
        else {}
    )
    return {
        "kind": "location_or_scene_shift",
        "location_changed": prev_loc_id != curr_loc_id,
        "scene_changed": bool(prev_scene and curr_scene and prev_scene != curr_scene),
        "previous_location": _compact_location(locations.get(prev_loc_id)),
        "current_location": _compact_location(locations.get(curr_loc_id)),
        "previous_scene": prev_scene,
        "current_scene": curr_scene,
        "handoff": str(previous_next.get("handoff") or "").strip(),
        "module_context": _module_context(),
    }


def _visual_emphasis(beat: dict[str, Any]) -> dict[str, Any] | None:
    raw = beat.get("visual_emphasis") or beat.get("dramatic_marker")
    if not isinstance(raw, dict):
        return None
    kind = str(raw.get("kind") or raw.get("marker_kind") or "").strip()
    if not kind:
        return None
    out = {
        "kind": kind,
        "intensity": str(raw.get("intensity") or "medium").strip() or "medium",
        "reason": str(raw.get("reason") or "").strip(),
    }
    return {key: value for key, value in out.items() if value}


def _block(
    *,
    index: int,
    text: str,
    beat: str,
    step: dict[str, Any],
    mandatory_beat: dict[str, Any],
    previous_step: dict[str, Any] | None = None,
) -> dict[str, Any]:
    source_facts = _beat_source_facts(step, mandatory_beat)
    source_facts["transition_from_previous"] = _transition_facts(
        previous_step=previous_step,
        current_step=step,
    )
    block = {
        "id": f"opening-narrator-path-{index}",
        "block_type": "narrator",
        "speaker_label": "Narrator",
        "actor_id": None,
        "target_actor_id": None,
        "text": text.strip(),
        "delivery": _delivery(),
        "source": "narrator_path_canonical_content",
        "narration_beat": beat,
        "canonical_step_id": str(step.get("id") or "").strip(),
        "canonical_step_sequence": int(step.get("sequence") or index),
        "canonical_mandatory_beat_id": str(mandatory_beat.get("id") or "").strip(),
        "source_refs": _content_refs(step, mandatory_beat),
        "source_facts": source_facts,
    }
    emphasis = _visual_emphasis(mandatory_beat)
    if emphasis:
        block["visual_emphasis"] = emphasis
    return block


def _string_list(value: Any) -> list[str]:
    return [str(item).strip() for item in value if str(item).strip()] if isinstance(value, list) else []


def _perception_lines(beat: dict[str, Any]) -> list[str]:
    params = beat.get("beat_pattern_params") if isinstance(beat.get("beat_pattern_params"), dict) else {}
    lines = _string_list(params.get("perception_lines"))
    if lines:
        return lines
    instruction = beat.get("director_instruction") if isinstance(beat.get("director_instruction"), dict) else {}
    return _string_list(instruction.get("narrator_perception_only"))


def _mandatory_beats(step: dict[str, Any]) -> list[dict[str, Any]]:
    beats = [beat for beat in step.get("mandatory_beats") or [] if isinstance(beat, dict)]
    return sorted(beats, key=lambda beat: int(beat.get("order") or 0))


def _render_from_canonical_steps(
    steps: list[dict[str, Any]],
) -> list[tuple[str, str, int, dict[str, Any]]]:
    rendered: list[tuple[str, str, int, dict[str, Any]]] = []
    for step_index, step in enumerate(steps):
        for beat in _mandatory_beats(step):
            lines = _perception_lines(beat)
            if not lines:
                continue
            text = sanitize_gm_narration_beat_line(" ".join(lines))
            if text:
                rendered.append((text, str(beat.get("id") or "").strip(), step_index, beat))
    return rendered


def build_goc_narrator_path_opening(*, session_output_language: str = "de") -> dict[str, Any]:
    """Return a narrator-only visible opening grounded in canonical path refs."""
    canonical_path = load_goc_canonical_path_yaml()
    steps = _opening_steps()
    if not steps:
        raise RuntimeError("God of Carnage canonical narrator path has no opening steps.")
    authoring_language = str(canonical_path.get("authoring_language") or "en").strip().lower()[:2] or "en"
    render_items = _render_from_canonical_steps(steps)
    if not render_items:
        raise RuntimeError("God of Carnage canonical narrator path has no renderable mandatory beats.")
    blocks = [
        _block(
            index=i + 1,
            text=text,
            beat=beat,
            step=steps[min(max(step_index, 0), len(steps) - 1)],
            mandatory_beat=mandatory_beat,
            previous_step=steps[step_index - 1] if step_index > 0 else None,
        )
        for i, (text, beat, step_index, mandatory_beat) in enumerate(render_items)
    ]
    step_ids = [str(step.get("id") or "").strip() for step in steps if str(step.get("id") or "").strip()]
    source_refs: list[str] = []
    for block in blocks:
        source_refs.extend(str(ref) for ref in block.get("source_refs") or [])
    source_refs = list(dict.fromkeys(source_refs))
    source_frames = [
        {
            "id": str(step.get("id") or "").strip(),
            "sequence": int(step.get("sequence") or 0),
            "mode": str(step.get("mode") or "").strip(),
            "scene_anchor": step.get("scene_anchor") if isinstance(step.get("scene_anchor"), dict) else {},
            "location_ref": step.get("location_ref") if isinstance(step.get("location_ref"), dict) else {},
            "support_refs": step.get("support_refs") if isinstance(step.get("support_refs"), list) else [],
            "object_refs": step.get("object_refs") if isinstance(step.get("object_refs"), list) else [],
            "present": step.get("present") if isinstance(step.get("present"), dict) else {},
            "mandatory_beat_ids": [
                str(beat.get("id") or "").strip()
                for beat in _mandatory_beats(step)
                if str(beat.get("id") or "").strip()
            ],
            "next_point": step.get("next_point") if isinstance(step.get("next_point"), dict) else {},
        }
        for step in steps
    ]
    return {
        "contract": NARRATOR_PATH_CONTRACT,
        "path_mode": "narrator_path",
        "adapter": NARRATOR_PATH_ADAPTER,
        "adapter_invocation_mode": NARRATOR_PATH_INVOCATION_MODE,
        "path_id": "goc_opening_canonical_path",
        "authoring_language": authoring_language,
        "session_output_language": str(session_output_language or "").strip().lower()[:2] or None,
        "requires_output_realization": (
            bool(str(session_output_language or "").strip())
            and (str(session_output_language or "").strip().lower()[:2] != authoring_language)
        ),
        "canonical_step_ids": step_ids,
        "source_refs": source_refs,
        "source_input_mode": "semantic_frames_with_fallback_blocks",
        "narrative_source_frames": source_frames,
        "scene_blocks": blocks,
        "gm_narration": [str(block["text"]) for block in blocks],
        "director_plan": {
            "contract": "director_narrator_path_plan.v1",
            "path_mode": "narrator_path",
            "speech_allowed": False,
            "npc_agency_required": False,
            "player_action_resolution_required": False,
            "selected_capabilities": ["narrator.opening_event.realize"],
            "skipped_capability_groups": [
                "player_action_resolution",
                "affordance_evaluation",
                "npc_agency",
                "npc_authority",
                "voice_classification",
                "dramatic_irony",
                "branch_forecast",
            ],
            "canonical_step_ids": step_ids,
            "content_source_refs": source_refs,
        },
    }
