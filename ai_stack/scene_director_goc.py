"""Deterministic scene director for God of Carnage (CANONICAL_TURN_CONTRACT_GOC.md §3)."""

from __future__ import annotations

from typing import Any

from ai_stack.goc_frozen_vocab import (
    CONTINUITY_CLASS_SEVERITY_ORDER,
    GOC_MODULE_ID,
    SCENE_FUNCTIONS,
    assert_pacing_mode,
    assert_scene_function,
    assert_silence_brevity_mode,
)


def _severity_index(continuity_class: str) -> int:
    try:
        return CONTINUITY_CLASS_SEVERITY_ORDER.index(continuity_class)
    except ValueError:
        return len(CONTINUITY_CLASS_SEVERITY_ORDER)


def select_single_scene_function(
    candidates: list[str],
    *,
    implied_continuity_by_function: dict[str, str],
) -> str:
    """CANONICAL_TURN_CONTRACT_GOC.md §3.5 — single function from competing candidates."""
    valid = [c for c in candidates if c in SCENE_FUNCTIONS]
    if not valid:
        return "establish_pressure"
    if len(valid) == 1:
        return assert_scene_function(valid[0])

    def rank(fn: str) -> tuple[int, str]:
        implied = implied_continuity_by_function.get(fn, "silent_carry")
        return (_severity_index(implied), fn)

    best_rank = min(rank(f) for f in valid)
    tied = [f for f in valid if rank(f) == best_rank]
    tied.sort()
    return assert_scene_function(tied[0])


def build_scene_assessment(
    *,
    module_id: str,
    current_scene_id: str,
    canonical_yaml: dict[str, Any] | None,
) -> dict[str, Any]:
    setting = "unknown"
    narrative_scope = "unknown"
    if canonical_yaml:
        content = canonical_yaml.get("content")
        if isinstance(content, dict):
            setting = str(content.get("setting") or setting)
            narrative_scope = str(content.get("narrative_scope") or narrative_scope)
    return {
        "scene_core": f"goc_scene:{current_scene_id}",
        "pressure_state": "moderate_tension",
        "module_slice": module_id,
        "canonical_setting": setting,
        "narrative_scope": narrative_scope,
    }


def build_responder_and_function(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    pacing_mode: str,
) -> tuple[list[dict[str, Any]], str, dict[str, str]]:
    """Choose responder set and scene function using deterministic keyword + intent heuristics."""
    text = f"{player_input} {interpreted_move.get('player_intent', '')}".lower()
    implied: dict[str, str] = {}

    candidates: list[str] = []

    if "sorry" in text or "apolog" in text or "repair" in text:
        candidates.append("repair_or_stabilize")
        implied["repair_or_stabilize"] = "repair_attempt"
    if "reveal" in text or "secret" in text or "truth" in text or "admit" in text:
        candidates.append("reveal_surface")
        implied["reveal_surface"] = "revealed_fact"
    if "blame" in text or "fault" in text:
        candidates.append("redirect_blame")
        implied["redirect_blame"] = "blame_pressure"
    if "why" in text or "motive" in text or "reason" in text:
        candidates.append("probe_motive")
        implied["probe_motive"] = "situational_pressure"
    if "escalat" in text or "fight" in text or "angry" in text:
        candidates.append("escalate_conflict")
        implied["escalate_conflict"] = "situational_pressure"
    if not candidates:
        candidates.append("establish_pressure")
        implied["establish_pressure"] = "situational_pressure"

    if (
        pacing_mode == "multi_pressure"
        and "repair_or_stabilize" in candidates
        and "reveal_surface" in candidates
    ):
        scene_fn = select_single_scene_function(
            ["repair_or_stabilize", "reveal_surface"],
            implied_continuity_by_function=implied,
        )
    else:
        scene_fn = select_single_scene_function(candidates, implied_continuity_by_function=implied)

    if "annette" in text:
        actor = "annette_reille"
        reason = "named_in_player_move"
    elif "alain" in text:
        actor = "alain_reille"
        reason = "named_in_player_move"
    elif "michel" in text or "michael" in text:
        actor = "michel_longstreet"
        reason = "named_in_player_move"
    elif "veronique" in text or "penelope" in text:
        actor = "veronique_vallon"
        reason = "named_in_player_move"
    else:
        actor = "annette_reille"
        reason = "default_pressure_bearer"

    responders = [{"actor_id": actor, "reason": reason}]

    return responders, scene_fn, implied


def build_pacing_and_silence(
    *,
    player_input: str,
    interpreted_move: dict[str, Any],
    module_id: str,
) -> tuple[str, dict[str, Any]]:
    text = f"{player_input} {interpreted_move.get('move_class', '')}".lower()
    if module_id != GOC_MODULE_ID:
        return assert_pacing_mode("standard"), {
            "mode": assert_silence_brevity_mode("normal"),
            "reason": "non_goc_slice_default",
        }
    if "brief" in text or "short" in text:
        pacing = assert_pacing_mode("compressed")
        silence = {"mode": assert_silence_brevity_mode("brief"), "reason": "player_requested_brevity"}
    elif "silent" in text or "say nothing" in text:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("withheld"), "reason": "dramatic_silence_move"}
    elif "multi" in text or "pressure" in text:
        pacing = assert_pacing_mode("multi_pressure")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    else:
        pacing = assert_pacing_mode("standard")
        silence = {"mode": assert_silence_brevity_mode("normal"), "reason": "default_verbal_density"}
    return pacing, silence
