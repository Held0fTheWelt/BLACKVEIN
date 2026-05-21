"""Game routes implementation concern: story window scene block helpers.

Loaded by game_routes.py so route monkeypatches keep their public module namespace.
"""

SOURCE = r'''
def _scene_blocks_from_turn(turn: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(turn, dict):
        return []
    bundle = turn.get("visible_output_bundle") if isinstance(turn.get("visible_output_bundle"), dict) else {}
    scene_blocks = bundle.get("scene_blocks")
    if isinstance(scene_blocks, list):
        return [dict(block) for block in scene_blocks if isinstance(block, dict)]
    visible_scene_output = (

        turn.get("visible_scene_output")
        if isinstance(turn.get("visible_scene_output"), dict)
        else {}
    )
    blocks = visible_scene_output.get("blocks")
    if isinstance(blocks, list):
        return [dict(block) for block in blocks if isinstance(block, dict)]
    return []


def _scene_blocks_from_story_window(story_window: dict[str, Any]) -> list[dict[str, Any]]:
    latest_entry = story_window.get("latest_entry") if isinstance(story_window.get("latest_entry"), dict) else {}
    scene_blocks = latest_entry.get("scene_blocks")
    if isinstance(scene_blocks, list):
        return [dict(block) for block in scene_blocks if isinstance(block, dict)]
    entries = story_window.get("entries") if isinstance(story_window.get("entries"), list) else []
    for entry in reversed(entries):
        if not isinstance(entry, dict):
            continue
        scene_blocks = entry.get("scene_blocks")
        if isinstance(scene_blocks, list) and scene_blocks:
            return [dict(block) for block in scene_blocks if isinstance(block, dict)]
    return []


def _cumulative_scene_blocks_from_story_window(story_window: dict[str, Any]) -> list[dict[str, Any]]:
    """Collect scene blocks from every story_window entry in chronological order.

    MVP5 ``BlocksOrchestrator.loadTurn`` clears ``#turn-transcript`` and replays only
    ``visible_scene_output.blocks``. Player-turn HTTP responses must therefore carry the
    **full** committed block stream, not a single-turn slice (otherwise the shell appears
    to reset to the opening or latest slice only).
    """
    entries = story_window.get("entries") if isinstance(story_window.get("entries"), list) else []
    out: list[dict[str, Any]] = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        blocks = entry.get("scene_blocks")
        if not isinstance(blocks, list):
            continue
        for block in blocks:
            if isinstance(block, dict):
                out.append(dict(block))
    return out
def _scene_blocks_count_prior_story_entries(story_window: dict[str, Any]) -> int:
    """Count scene_blocks dicts in all story_window entries except the last (ADR-0034 §7)."""
    entries = story_window.get("entries") if isinstance(story_window.get("entries"), list) else []
    if len(entries) <= 1:
        return 0
    n = 0
    for entry in entries[:-1]:
        if not isinstance(entry, dict):
            continue
        blocks = entry.get("scene_blocks")
        if isinstance(blocks, list):
            n += sum(1 for b in blocks if isinstance(b, dict))
    return n


def _typewriter_slice_start_index_for_bundle(
    *,
    story_window: dict[str, Any],
    scene_blocks: list[dict[str, Any]],
    used_cumulative_story_blocks: bool,
) -> int | None:
    """First index in scene_blocks that belongs to the latest commit for typewriter sequencing.

    When ``used_cumulative_story_blocks`` is True, transcript-stable blocks from earlier
    entries render immediately; blocks from the latest entry(s) animate in order.


    When the bundle uses non-cumulative fallback (single-turn slice), every block animates
    from index 0.
    """
    if not scene_blocks:
        return None
    if not used_cumulative_story_blocks:
        return 0
    prior = _scene_blocks_count_prior_story_entries(story_window)
    return min(prior, len(scene_blocks))
'''
