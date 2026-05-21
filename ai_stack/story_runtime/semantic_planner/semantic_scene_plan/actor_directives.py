"""Actor directive and scene-handover policy helpers."""

from __future__ import annotations

from typing import Any

from .utils import _clean


def _directive_for_responder(
    *,
    narrative_scene_function: str,
    role: str,
    index: int,
    silence_brevity_decision: dict[str, Any] | None,
) -> str:
    silence = silence_brevity_decision if isinstance(silence_brevity_decision, dict) else {}
    silence_mode = _clean(silence.get("mode")).lower()
    if narrative_scene_function == "arrange_scene":
        return "stage_npc_presence"
    if narrative_scene_function == "shift_social_arrangement" or role == "interruption_candidate":
        return "force_npc_interruption"
    if narrative_scene_function == "surface_information":
        return "force_npc_disclosure_pressure"
    if narrative_scene_function == "preserve_negative_space" or silence_mode in {"withheld", "silent"}:
        return "hold_silence"
    if role == "secondary_reactor" or index > 1:
        return "force_secondary_reaction"
    if narrative_scene_function in {
        "force_accountability",
        "probe_motive",
        "raise_pressure",
        "test_repair_sincerity",
        "establish_scene_pressure",
    }:
        return "force_npc_reaction"
    return "support_scene_arrangement"


def _actor_directives(
    *,
    selected_responder_set: list[dict[str, Any]] | None,
    narrative_scene_function: str,
    scene_target: dict[str, Any],
    silence_brevity_decision: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    responders = selected_responder_set or []
    directives: list[dict[str, Any]] = []
    base_constraints = [
        "do_not_speak_for_player",
        "respect_actor_lane",
        "do_not_commit_new_truth",
    ]
    for idx, row in enumerate(responders, start=1):
        if not isinstance(row, dict):
            continue
        actor_id = _clean(row.get("actor_id") or row.get("responder_id"))
        if not actor_id:
            continue
        role = _clean(row.get("role") or row.get("reason")) or "responder"
        directive = _directive_for_responder(
            narrative_scene_function=narrative_scene_function,
            role=role,
            index=idx,
            silence_brevity_decision=silence_brevity_decision,


        )
        directives.append(
            {
                "directive_order": idx,
                "actor_id": actor_id,
                "actor_role": role,
                "directive": directive,
                "visibility": "visible_action_or_dialogue",
                "required": idx == 1,
                "target_function": scene_target.get("target_function"),
                "constraints": list(base_constraints),
                "reason_codes": [
                    f"narrative_scene_function:{narrative_scene_function}",
                    f"responder_role:{role}",
                ],
            }
        )

    if not directives and narrative_scene_function in {
        "arrange_scene",
        "establish_scene_anchor",
        "contain_out_of_scope",
        "narrate_consequence",
        "narrate_sensory_focus",
    }:
        directive = "stage_scene_arrangement"
        if narrative_scene_function == "contain_out_of_scope":
            directive = "contain_without_forcing_npc"
        elif narrative_scene_function in {"narrate_consequence", "narrate_sensory_focus"}:
            directive = "narrate_without_forcing_npc"
        directives.append(
            {
                "directive_order": 1,
                "actor_id": None,
                "actor_role": "director",
                "directive": directive,
                "visibility": "narrated_or_structural",
                "required": True,
                "target_function": scene_target.get("target_function"),
                "constraints": list(base_constraints),
                "reason_codes": [f"narrative_scene_function:{narrative_scene_function}"],
            }
        )
    return directives


def _handover_policy(
    *,
    narrative_scene_function: str,
    dramatic_beats: list[dict[str, Any]],
    expected_transition_pattern: str,
) -> dict[str, Any]:
    if narrative_scene_function == "contain_out_of_scope":
        policy = "contain_and_return_to_scene"
        requires_affordance = True
    elif narrative_scene_function in {"arrange_scene", "establish_scene_anchor", "establish_scene_pressure"}:
        policy = "offer_player_action_after_setup"
        requires_affordance = True
    elif narrative_scene_function == "preserve_negative_space":
        policy = "preserve_player_silence"
        requires_affordance = True
    elif narrative_scene_function in {"narrate_consequence", "narrate_sensory_focus"}:
        policy = "return_control_after_narration"
        requires_affordance = True
    elif expected_transition_pattern == "hard":
        policy = "offer_response_under_tension"
        requires_affordance = True
    else:
        policy = "offer_player_action"
        requires_affordance = True

    return {


        "policy": policy,
        "player_control_preserved": True,
        "requires_player_affordance": requires_affordance,
        "handover_after_beat_order": dramatic_beats[-1]["beat_order"] if dramatic_beats else 0,
        "success_condition": f"{policy}_available",
        "constraints": ["do_not_coerce_player_action", "do_not_close_scene_without_commit"],
    }
