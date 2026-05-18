"""Narrator-path realization for the God of Carnage canonical opening.

This module is intentionally a renderer, not a second content database. It
loads the numbered canonical path and referenced location/object authority, then
projects the first narrator-only transition into visible blocks.
"""

from __future__ import annotations

from typing import Any

from ai_stack.goc_yaml_authority import (
    load_goc_canonical_path_yaml,
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


def _block(
    *,
    index: int,
    text: str,
    beat: str,
    step: dict[str, Any],
    mandatory_beat: dict[str, Any],
) -> dict[str, Any]:
    return {
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
    }


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
        )
        for i, (text, beat, step_index, mandatory_beat) in enumerate(render_items)
    ]
    step_ids = [str(step.get("id") or "").strip() for step in steps if str(step.get("id") or "").strip()]
    source_refs: list[str] = []
    for block in blocks:
        source_refs.extend(str(ref) for ref in block.get("source_refs") or [])
    source_refs = list(dict.fromkeys(source_refs))
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
