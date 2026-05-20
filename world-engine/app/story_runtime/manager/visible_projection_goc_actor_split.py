from __future__ import annotations

from ._deps import *

def _apply_goc_actor_block_colon_stutter_cleanup(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Normalize actor_line / actor_action visible text before split/prune."""
    out: list[dict[str, Any]] = []
    for b in blocks:
        if not isinstance(b, dict):
            out.append(b)
            continue
        bt = str(b.get("block_type") or "").strip().lower()
        if bt in {"actor_line", "actor_action"}:
            nb = dict(b)
            nb["text"] = dedupe_goc_speaker_colon_stutter_visible(
                str(b.get("text") or ""),
                speaker_label=str(b.get("speaker_label") or "") or None,
                actor_id=str(b.get("actor_id") or "").strip() or None,
            )
            out.append(nb)
        else:
            out.append(b)
    return out

def _goc_visible_text_fold(s: str) -> str:
    """Lowercase + light accent fold so prune substring checks survive accent drift."""
    return _goc_visible_lane_text_fold(s)

def _split_merged_goc_actor_line_segments(
    text: str,
    *,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[tuple[str, str, str]]:
    """Split one ``actor_line`` by roster speaker prefixes (``ai_stack.story_runtime.npc_agency.goc_npc_transcript_projection``)."""
    return split_merged_goc_actor_line_segments(
        text,
        runtime_projection=runtime_projection,
        story_runtime_experience=story_runtime_experience,
    )

def _expand_multi_speaker_actor_lines(
    blocks: list[dict[str, Any]],
    *,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Turn one model ``actor_line`` that jams multiple speakers into separate blocks."""
    out: list[dict[str, Any]] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        bt = str(b.get("block_type") or "").strip().lower()
        if bt != "actor_line":
            out.append(b)
            continue
        segs = _split_merged_goc_actor_line_segments(
            str(b.get("text") or ""),
            runtime_projection=runtime_projection,
            story_runtime_experience=story_runtime_experience,
        )
        if len(segs) < 2:
            out.append(b)
            continue
        base_id = str(b.get("id") or "live-block").strip() or "live-block"
        for idx, (aid, sh, body) in enumerate(segs):
            nb = dict(b)
            nb["id"] = base_id if idx == 0 else f"{base_id}-spk{idx}"
            nb["actor_id"] = aid
            nb["speaker_label"] = sh
            nb["text"] = f"{sh}: {body}"
            out.append(nb)
    return out

def _prune_actor_actions_subsumed_by_prior_actor_lines(blocks: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Delegate to shared ai_stack prune (also used by backend player bundle polish)."""
    return prune_goc_actor_actions_subsumed_by_prior_actor_lines(blocks)

def _finalize_visible_blocks_with_goc_actor_split(
    blocks: list[dict[str, Any]],
    *,
    expected_language: str,
    human_actor_id: str | None,
    selected_player_role: str | None,
    turn_number: int,
    player_input_echo_strings: list[str] | None,
    runtime_projection: dict[str, Any] | None = None,
    story_runtime_experience: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    blocks = _apply_goc_actor_block_colon_stutter_cleanup(blocks)
    blocks = _expand_multi_speaker_actor_lines(
        blocks,
        runtime_projection=runtime_projection,
        story_runtime_experience=story_runtime_experience,
    )
    out, diag = finalize_visible_scene_blocks(
        blocks,
        expected_language=expected_language,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        turn_number=turn_number,
        player_input_echo_strings=player_input_echo_strings,
    )
    return _prune_actor_actions_subsumed_by_prior_actor_lines(out), diag

def _actor_line_count(value: Any) -> int:
    if not isinstance(value, list):
        return 0
    count = 0
    for item in value:
        if isinstance(item, dict):
            text = str(item.get("text") or "").strip()
            if text:
                count += 1
            continue
        if str(item).strip():
            count += 1
    return count

def _structured_lane_dict_counts(structured: dict[str, Any] | None) -> tuple[int, int]:
    """Count dict-only rows with visible text (structured lanes used for actor projection)."""
    if not isinstance(structured, dict):
        return 0, 0

    def _dict_text_count(key: str) -> int:
        lane = structured.get(key)
        if not isinstance(lane, list):
            return 0
        return sum(
            1
            for item in lane
            if isinstance(item, dict) and str(item.get("text") or item.get("line") or "").strip()
        )

    return _dict_text_count("spoken_lines"), _dict_text_count("action_lines")

def _is_goc_human_lane_actor(
    actor_raw: str,
    *,
    human_actor_id: str,
    selected_player_role: str,
) -> bool:
    """True when this actor id/alias is the selected human role or human_actor_id."""
    actor_canon = canonicalize_goc_actor_id(str(actor_raw or "").strip())
    if not actor_canon:
        return False
    if human_actor_id:
        h = canonicalize_goc_actor_id(str(human_actor_id).strip())
        if h and actor_canon == h:
            return True
    if selected_player_role:
        r = canonicalize_goc_actor_id(str(selected_player_role).strip())
        if r and actor_canon == r:
            return True
    return False

def _opening_shape_requires_actor_backfill(blocks: list[dict[str, Any]]) -> bool:
    """OPEN-ACTOR-BLOCK-PROJECTION-01: first three blocks narrator but no actor at index >= 3."""
    if len(blocks) < 3:
        return False

    def _bt(b: dict[str, Any]) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    if not all(_bt(blocks[i]) == "narrator" for i in range(3)):
        return False
    first_actor = next(
        (i for i, b in enumerate(blocks) if _bt(b) in {"actor_line", "actor_action"}),
        None,
    )
    return first_actor is None

def _actor_block_projection_count(blocks: list[dict[str, Any]]) -> int:
    def _bt(b: dict[str, Any]) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    return sum(1 for b in blocks if isinstance(b, dict) and _bt(b) in {"actor_line", "actor_action"})

def _maybe_backfill_opening_actor_from_structured(
    blocks: list[dict[str, Any]],
    *,
    structured_output: dict[str, Any],
    runtime_projection: dict[str, Any] | None,
    turn_number: int,
    human_actor_id: str,
    selected_player_role: str,
    delivery_fn: Any,
    actor_label_fn: Any,
    story_runtime_experience: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], str, str | None]:
    """Append first safe NPC actor block from structured lanes. Returns (blocks, source, filter_reason)."""
    if turn_number != 0 or not _opening_shape_requires_actor_backfill(blocks):
        return blocks, "none", None

    inner_blocks: list[dict[str, Any]] = list(blocks)

    def _append(t: str, text: str, *, speaker_label: str, actor_id: str | None = None) -> None:
        clean = str(text or "").strip()
        if not clean:
            return
        inner_blocks.append(
            {
                "id": f"turn-{turn_number}-live-block-{len(inner_blocks) + 1}",
                "block_type": t,
                "speaker_label": speaker_label,
                "actor_id": actor_id,
                "target_actor_id": None,
                "text": clean,
                "delivery": delivery_fn(),
                "source": "live_runtime_graph",
            }
        )

    src = _try_spoken_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
    )
    if src:
        return inner_blocks, src, None
    _flags = goc_transcript_policy_flags(story_runtime_experience)
    _action_bt = "actor_line" if _flags["map_action_lines_to_actor_line_lane"] else "actor_action"
    src = _try_action_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
        action_block_type=_action_bt,
    )
    if src:
        return inner_blocks, src, None
    src = _try_initiative_with_blocks(
        append_fn=_append,
        actor_label_fn=actor_label_fn,
        runtime_projection=runtime_projection,
        human_actor_id=human_actor_id,
        selected_player_role=selected_player_role,
        structured_output=structured_output,
    )
    if src:
        return inner_blocks, src, None

    sl, al = _structured_lane_dict_counts(structured_output)
    initiative_ct = len([x for x in (structured_output.get("initiative_events") or []) if isinstance(x, dict)])
    if (sl or al or initiative_ct) and runtime_projection is not None:
        return inner_blocks, "none", "actor_block_missing_due_to_human_actor_filter"
    return inner_blocks, "none", None

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
