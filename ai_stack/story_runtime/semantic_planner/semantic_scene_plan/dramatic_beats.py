"""Dramatic beat assembly from narrative scene functions."""

from __future__ import annotations

from typing import Any

from .mappings import _BEAT_INTENTS_BY_SCENE_FUNCTION, _BEAT_TEMPLATES_BY_NARRATIVE_FUNCTION
from .utils import _clean


def _dramatic_beats(
    *,
    selected_scene_function: str,
    narrative_scene_function: str,
    scene_target: dict[str, Any],
    expected_transition_pattern: str,
    pacing_mode: str,
) -> list[dict[str, Any]]:
    templates = _BEAT_TEMPLATES_BY_NARRATIVE_FUNCTION.get(
        narrative_scene_function,
        tuple(
            ("npc_dialogue_beat", intent, intent, "npc")
            for intent in _BEAT_INTENTS_BY_SCENE_FUNCTION.get(
                selected_scene_function,
                _BEAT_INTENTS_BY_SCENE_FUNCTION["establish_pressure"],
            )
        ),
    )
    actor_id = _clean(scene_target.get("target_actor_id"))
    beats: list[dict[str, Any]] = []
    for idx, (beat_kind, beat_function, beat_intent, owner) in enumerate(templates, start=1):
        owner_actor_id = actor_id if owner == "npc" and actor_id else None
        beats.append(
            {
                "beat_order": idx,
                "beat_kind": beat_kind,
                "beat_function": beat_function,
                "beat_intent": beat_intent,
                "owner": owner,
                "owner_actor_id": owner_actor_id,
                "visibility": "visible_to_player",
                "target_actor_id": actor_id or None,
                "target_function": scene_target.get("target_function"),
                "pressure_axis": scene_target.get("pressure_axis"),
                "pressure_function": scene_target.get("pressure_function"),
                "expected_transition_pattern": expected_transition_pattern,
                "pacing_mode": pacing_mode,
                "required": idx == 1 or beat_kind == "player_handover_beat",
                "success_condition": f"{beat_function}_realized",
                "constraints": [
                    "planner_advisory_only",
                    "visible_realization_required" if idx == 1 else "may_defer_if_validator_rejects",
                ],
            }
        )
    return beats
