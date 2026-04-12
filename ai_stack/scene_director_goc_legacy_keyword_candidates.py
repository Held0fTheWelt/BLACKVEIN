"""Pre-semantic keyword / pacing heuristic for GoC scene candidates (legacy fallback path)."""

from __future__ import annotations

from typing import Any

from ai_stack.scene_director_goc_legacy_keyword_constants import (
    ALLIANCE_REPOSITION_PHRASES,
    BLAME_PHRASES,
    ESCALATION_PHRASES,
    EVASION_PHRASES,
    HUMILIATION_PHRASES,
    MOVE_CLASS_QUESTION,
    PACING_CONTAINMENT,
    PACING_THIN_EDGE,
    PROBE_PHRASES,
    REPAIR_PHRASES,
    REVEAL_PHRASES,
    SILENCE_PAUSE_PHRASES,
    THIN_EDGE_SILENCE_PHRASES,
    combined_player_text,
    contains_any,
)


def legacy_keyword_scene_candidates(
    *,
    pacing_mode: str,
    player_input: str,
    interpreted_move: dict[str, Any],
    prior_classes: list[str],
) -> tuple[list[str], dict[str, str], list[str]]:
    """Pre-semantic keyword/tie-break heuristic — bounded fallback only when semantic record absent."""
    move_class = str(interpreted_move.get("move_class") or "").lower()
    intent = str(interpreted_move.get("player_intent") or "").lower()
    text = combined_player_text(player_input, intent)
    implied: dict[str, str] = {}
    candidates: list[str] = []
    heuristic_trace: list[str] = []

    if pacing_mode == PACING_CONTAINMENT:
        candidates.append("scene_pivot")
        implied["scene_pivot"] = "refused_cooperation"
        heuristic_trace.append("pacing_mode:containment->scene_pivot")
    elif pacing_mode == PACING_THIN_EDGE:
        if contains_any(text, THIN_EDGE_SILENCE_PHRASES):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("thin_edge:silence_keyword->withhold_or_evade")
        else:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("thin_edge:default->establish_pressure")
    else:
        if contains_any(text, SILENCE_PAUSE_PHRASES):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("keyword:silence_pause->withhold_or_evade")
        if contains_any(text, HUMILIATION_PHRASES):
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
            heuristic_trace.append("keyword:humiliation->redirect_blame")
        if contains_any(text, EVASION_PHRASES):
            candidates.append("withhold_or_evade")
            implied["withhold_or_evade"] = "silent_carry"
            heuristic_trace.append("keyword:evasion->withhold_or_evade")
        if contains_any(text, REPAIR_PHRASES):
            candidates.append("repair_or_stabilize")
            implied["repair_or_stabilize"] = "repair_attempt"
            heuristic_trace.append("keyword:repair->repair_or_stabilize")
        if contains_any(text, REVEAL_PHRASES):
            candidates.append("reveal_surface")
            implied["reveal_surface"] = "revealed_fact"
            heuristic_trace.append("keyword:reveal->reveal_surface")
        if contains_any(text, BLAME_PHRASES):
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("keyword:blame->redirect_blame")
        if contains_any(text, PROBE_PHRASES):
            candidates.append("probe_motive")
            implied["probe_motive"] = "situational_pressure"
            heuristic_trace.append("keyword:probe->probe_motive")
        if contains_any(text, ESCALATION_PHRASES):
            candidates.append("escalate_conflict")
            implied["escalate_conflict"] = "situational_pressure"
            heuristic_trace.append("keyword:escalation->escalate_conflict")
        if contains_any(text, ALLIANCE_REPOSITION_PHRASES):
            candidates.append("scene_pivot")
            implied["scene_pivot"] = "alliance_shift"
            heuristic_trace.append("keyword:alliance_reposition->scene_pivot")

        if (
            (MOVE_CLASS_QUESTION in move_class or MOVE_CLASS_QUESTION in intent or player_input.strip().endswith("?"))
            and "probe_motive" not in candidates
            and PACING_CONTAINMENT not in pacing_mode
        ):
            candidates.append("probe_motive")
            implied["probe_motive"] = "situational_pressure"
            heuristic_trace.append("interpreted_move:question_nudge->probe_motive")

        if "blame_pressure" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("continuity:blame_pressure_fallback->redirect_blame")
        if "dignity_injury" in prior_classes and not candidates:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "dignity_injury"
            heuristic_trace.append("continuity:dignity_injury_fallback->redirect_blame")
        if "alliance_shift" in prior_classes and "probe_motive" not in candidates and "why" in text:
            candidates.append("probe_motive")
            implied["probe_motive"] = "alliance_shift"
            heuristic_trace.append("continuity:alliance_shift_nudge->probe_motive")
        if "blame_pressure" in prior_classes and "redirect_blame" not in candidates and "watch" in text:
            candidates.append("redirect_blame")
            implied["redirect_blame"] = "blame_pressure"
            heuristic_trace.append("continuity:watch_under_blame->redirect_blame")

        if not candidates:
            candidates.append("establish_pressure")
            implied["establish_pressure"] = "situational_pressure"
            heuristic_trace.append("default->establish_pressure")

    return candidates, implied, heuristic_trace
