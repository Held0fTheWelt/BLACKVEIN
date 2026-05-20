from __future__ import annotations

from ._deps import *

def _compact_scene_block_summary(
    scene_blocks: list[dict[str, Any]],
    *,
    max_count: int = 6,
    text_excerpt_chars: int = 120,
) -> list[dict[str, Any]]:
    """OPEN-SHAPE-EVIDENCE-01: Build a small, score-metadata-safe scene_block excerpt list.

    Caps at ``max_count`` blocks and truncates each ``text`` field to
    ``text_excerpt_chars`` characters with an ellipsis. Keeps payload <= ~1KB
    so attaching it to every score row in ``score_metadata_base`` does not
    bloat Langfuse score storage.
    """
    out: list[dict[str, Any]] = []
    for idx, block in enumerate(scene_blocks[:max_count]):
        if not isinstance(block, dict):
            continue
        block_type = str(block.get("block_type") or block.get("type") or "").strip().lower() or None
        actor_id = block.get("actor_id") or block.get("speaker_id")
        actor_id_str = str(actor_id).strip() if actor_id else None
        raw_text = str(block.get("text") or "").strip().replace("\r", " ").replace("\n", " ")
        if len(raw_text) > text_excerpt_chars:
            text_excerpt = raw_text[: max(0, text_excerpt_chars - 1)] + "\u2026"
        else:
            text_excerpt = raw_text
        out.append(
            {
                "index": idx,
                "block_type": block_type,
                "actor_id": actor_id_str,
                "text_excerpt": text_excerpt,
            }
        )
    return out

def _actor_response_visible_in_scene_blocks(blocks: list[dict[str, Any]]) -> bool:
    for block in blocks:
        if not isinstance(block, dict):
            continue
        bt = str(block.get("block_type") or block.get("type") or "").strip()
        if bt in {"actor_line", "actor_action"}:
            return True
        spans = block.get("embedded_speech_spans")
        if isinstance(spans, list) and any(
            isinstance(span, dict)
            and str(span.get("actor_id") or "").strip()
            and str(span.get("speech_text") or "").strip()
            for span in spans
        ):
            return True
    return False

def _final_visible_actor_response_in_event(event: dict[str, Any]) -> bool:
    return _actor_response_visible_in_scene_blocks(_scene_blocks_from_turn_event(event))

def _reconcile_governance_passivity_with_final_projection(event: dict[str, Any]) -> None:
    """Drop ``no_visible_actor_response`` when final projected blocks show actor output."""
    if not _final_visible_actor_response_in_event(event):
        return

    def _without_no_visible(seq: Any) -> list[str]:
        if not isinstance(seq, list):
            return []
        return [str(x) for x in seq if str(x) != "no_visible_actor_response"]

    gov = event.get("runtime_governance_surface")
    if isinstance(gov, dict):
        gov["why_turn_felt_passive"] = _without_no_visible(gov.get("why_turn_felt_passive"))
        gov["primary_passivity_factors"] = _without_no_visible(gov.get("primary_passivity_factors"))
        pd = gov.get("passivity_diagnosis_v1")
        if isinstance(pd, dict):
            pd["why_turn_felt_passive"] = _without_no_visible(pd.get("why_turn_felt_passive"))
            pd["primary_passivity_factors"] = _without_no_visible(pd.get("primary_passivity_factors"))

    # Play shell / routes_play read passivity from actor_survival_telemetry, not gov alone.
    tel = event.get("actor_survival_telemetry")
    if isinstance(tel, dict):
        pd = tel.get("passivity_diagnosis_v1")
        if isinstance(pd, dict):
            pd["why_turn_felt_passive"] = _without_no_visible(pd.get("why_turn_felt_passive"))
            pd["primary_passivity_factors"] = _without_no_visible(pd.get("primary_passivity_factors"))
        vit = tel.get("vitality_telemetry_v1")
        if isinstance(vit, dict):
            vit["response_present"] = True

def _effective_story_runtime_experience_slice(
    graph_state: dict[str, Any] | None,
    explicit: dict[str, Any] | None,
) -> dict[str, Any]:
    """Resolve governed experience flags (effective slice) for GoC transcript policy."""
    if isinstance(explicit, dict) and explicit:
        return dict(explicit)
    if isinstance(graph_state, dict):
        sre = graph_state.get("story_runtime_experience")
        if isinstance(sre, dict):
            eff = sre.get("effective")
            if isinstance(eff, dict) and eff:
                return dict(eff)
            if any(
                k in sre
                for k in (
                    "experience_mode",
                    "goc_transcript_merge_consecutive_same_actor",
                    "goc_map_action_lines_to_actor_line_lane",
                )
            ):
                return dict(sre)
    return {}

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
