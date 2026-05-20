"""Degradation and turn-block helpers.

Builds safe degraded turn blocks and diagnostics when runtime execution must remain playable after partial failure.
"""
from __future__ import annotations

from ._deps import *

def _build_degradation_chain(path_summary: dict[str, Any]) -> list[str]:
    """Build the operator-facing causation chain for score metadata.

    Order convention (cause -> action -> consequence):
    1. ``live_opening_failure_reason`` (root cause, e.g. ``dramatic_effect_reject_empty_fluency``)
    2. Whatever ``path_summary['degradation_signals']`` exposes, in original order
       (this typically holds the runtime decision marker
       ``ldss_fallback_after_live_opening_failure`` followed by the visibility
       consequence ``non_factual_staging``).

    Duplicates are collapsed; empty / non-string entries are dropped.
    """
    chain: list[str] = []
    live_reason = path_summary.get("live_opening_failure_reason")
    if isinstance(live_reason, str):
        token = live_reason.strip()
        if token:
            chain.append(token)
    raw_signals = path_summary.get("degradation_signals") or []
    if isinstance(raw_signals, list):
        for entry in raw_signals:
            token = str(entry).strip()
            if token and token not in chain:
                chain.append(token)
    return chain

def _build_degradation_prose_summary(path_summary: dict[str, Any]) -> str:
    """Compose a human-readable summary describing the operational degradation.

    The prose is operator-facing (alert / dashboard surface). It does not feed
    the live-gate booleans or any canonical contract; ``path_summary['degradation_summary']``
    keeps its existing raw-token semantics for the root span statusMessage.
    """
    live_reason = ""
    raw_reason = path_summary.get("live_opening_failure_reason")
    if isinstance(raw_reason, str):
        live_reason = raw_reason.strip()
    raw_signals = path_summary.get("degradation_signals") or []
    raw_signals = [str(s).strip() for s in raw_signals if str(s).strip()] if isinstance(raw_signals, list) else []
    if not live_reason and not raw_signals:
        return "none"

    has_ldss_fallback = "ldss_fallback_after_live_opening_failure" in raw_signals
    has_non_factual = "non_factual_staging" in raw_signals
    has_fallback_used = "fallback_used" in raw_signals

    parts: list[str] = []
    if "dramatic_effect_reject" in live_reason:
        parts.append("Live opening failed dramatic-effect validation")
    elif "actor_lane" in live_reason:
        parts.append(f"Live opening failed actor-lane validation ({live_reason})")
    elif live_reason:
        parts.append(f"Live opening failed validation ({live_reason})")

    if has_ldss_fallback:
        parts.append("and fell back to LDSS" if parts else "Live opening fell back to LDSS")
    elif has_fallback_used and not parts:
        parts.append("Operational degradation (fallback used)")

    if not parts:
        parts.append("Operational degradation observed")

    base = " ".join(parts)
    if has_ldss_fallback or has_non_factual:
        return f"{base}; visible output exists but is degraded/fallback."
    if raw_signals:
        return f"{base}; canonical signals: {', '.join(raw_signals)}."
    return f"{base}."

def _visible_lines_from_turn_event(event: dict[str, Any]) -> list[str]:
    bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
    lines = _coerce_visible_text_lines(bundle.get("gm_narration"))
    if lines:
        return lines

    generation = ((event.get("model_route") or {}).get("generation") or {}) if isinstance(event.get("model_route"), dict) else {}
    meta = generation.get("metadata") if isinstance(generation.get("metadata"), dict) else {}
    structured = meta.get("structured_output") if isinstance(meta.get("structured_output"), dict) else None
    if structured is None and isinstance(generation.get("structured_output"), dict):
        structured = generation["structured_output"]
    if isinstance(structured, dict):
        for key in (
            "narrative_response",
            "narration_summary",
            "opening_narration",
            "scene_description",
            "narrative_summary",
        ):
            lines = _coerce_visible_text_lines(structured.get(key))
            if lines:
                return lines
        for lane_key in ("spoken_lines", "action_lines"):
            lane = structured.get(lane_key)
            if not isinstance(lane, list):
                continue
            lane_lines: list[str] = []
            for row in lane:
                if isinstance(row, dict):
                    text = str(row.get("text") or row.get("line") or "").strip()
                    if text:
                        lane_lines.append(text)
                elif str(row).strip():
                    lane_lines.append(str(row).strip())
            if lane_lines:
                return lane_lines

    lines = _coerce_visible_text_lines(generation.get("content") or generation.get("model_raw_text"))
    if lines:
        return lines

    commit = event.get("narrative_commit") if isinstance(event.get("narrative_commit"), dict) else {}
    status = str(commit.get("situation_status") or "").strip()
    return [status] if status else []

def _scene_blocks_from_turn_event(event: dict[str, Any]) -> list[dict[str, Any]]:
    bundle = event.get("visible_output_bundle") if isinstance(event.get("visible_output_bundle"), dict) else {}
    scene_blocks = bundle.get("scene_blocks")
    if isinstance(scene_blocks, list):
        return [dict(block) for block in scene_blocks if isinstance(block, dict)]

    scene_turn_envelope = (
        event.get("scene_turn_envelope")
        if isinstance(event.get("scene_turn_envelope"), dict)
        else {}
    )
    visible_scene_output = (
        scene_turn_envelope.get("visible_scene_output")
        if isinstance(scene_turn_envelope.get("visible_scene_output"), dict)
        else {}
    )
    blocks = visible_scene_output.get("blocks")
    if isinstance(blocks, list):
        return [dict(block) for block in blocks if isinstance(block, dict)]
    return []

def _opening_block_contract_satisfied(scene_blocks: list[dict[str, Any]]) -> bool:
    """OPEN-GATE-01: Turn 0 must start with 3 narrator blocks before any actor_line/action."""
    if len(scene_blocks) < 4:
        return False

    def _bt(b: dict) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    if _bt(scene_blocks[0]) != "narrator":
        return False
    if _bt(scene_blocks[1]) != "narrator":
        return False
    if _bt(scene_blocks[2]) != "narrator":
        return False
    first_actor = next(
        (i for i, b in enumerate(scene_blocks) if _bt(b) in {"actor_line", "actor_action"}),
        None,
    )
    return first_actor is not None and first_actor >= 3

def _compute_opening_shape_subgates(
    scene_blocks: list[dict[str, Any]],
) -> tuple[dict[str, bool], list[str]]:
    """OPEN-SHAPE-EVIDENCE-01: Decompose ``_opening_block_contract_satisfied`` into
    auditable per-subgate truth values + ordered failure-reason tokens.

    The aggregate truth of the returned subgates is functionally equivalent to
    ``_opening_block_contract_satisfied(scene_blocks)`` — the helper exists only
    to surface *why* the contract failed for Langfuse score metadata. It must
    not introduce any new gate semantics.

    Subgates (all booleans):
        block_count_ok           — at least 4 visible blocks
        narrator_intro_present   — block[0].block_type == "narrator"
        role_anchor_present      — block[1].block_type == "narrator"
        scene_setup_present      — block[2].block_type == "narrator"
        first_three_are_narrator — narrator_intro AND role_anchor AND scene_setup
        first_actor_after_intro  — first actor_line/actor_action appears at idx >= 3

    Failure reasons (ordered, lowercase tokens) match the operator vocabulary
    captured during the 2026-05-08 audit so dashboards can correlate score rows
    with the audit narrative without bespoke joins.
    """

    def _bt(b: dict) -> str:
        return str(b.get("block_type") or b.get("type") or "").strip().lower()

    block_count = len(scene_blocks)
    types = [_bt(b) for b in scene_blocks]
    first_actor_idx = next(
        (i for i, t in enumerate(types) if t in {"actor_line", "actor_action"}),
        None,
    )

    narrator_intro_present = block_count >= 1 and types[0] == "narrator"
    role_anchor_present = block_count >= 2 and types[1] == "narrator"
    scene_setup_present = block_count >= 3 and types[2] == "narrator"
    first_three_are_narrator = (
        narrator_intro_present and role_anchor_present and scene_setup_present
    )
    first_actor_after_intro = first_actor_idx is not None and first_actor_idx >= 3
    block_count_ok = block_count >= 4

    subgates = {
        "block_count_ok": block_count_ok,
        "narrator_intro_present": narrator_intro_present,
        "role_anchor_present": role_anchor_present,
        "scene_setup_present": scene_setup_present,
        "first_three_are_narrator": first_three_are_narrator,
        "first_actor_after_intro": first_actor_after_intro,
    }

    failure_reasons: list[str] = []
    if block_count == 0:
        failure_reasons.append("no_visible_scene_blocks")
    if not block_count_ok:
        failure_reasons.append("block_count_lt_4")
    if not narrator_intro_present:
        failure_reasons.append("narrator_intro_missing")
    if not role_anchor_present:
        failure_reasons.append("role_anchor_missing")
    if not scene_setup_present:
        failure_reasons.append("scene_setup_missing")
    if first_actor_idx is None:
        failure_reasons.append("no_actor_block_present")
    elif not first_actor_after_intro:
        failure_reasons.append("actor_block_before_intro")

    return subgates, failure_reasons

__all__ = [
    name
    for name in globals()
    if not name.startswith("__") and name != "annotations"
]
