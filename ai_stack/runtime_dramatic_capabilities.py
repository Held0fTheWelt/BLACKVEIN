"""Dramatic runtime capability selection for story turns.

These capabilities describe narrative authority at runtime. They are distinct
from the technical tool/capability registry in ``ai_stack.capabilities``.
"""

from __future__ import annotations

from typing import Any


FORBIDDEN_NPC_CAPABILITIES: tuple[str, ...] = (
    "npc.execute_player_action",
    "npc.narrate_player_perception",
    "npc.override_human_actor",
    "npc.commit_world_truth_without_validation",
)


def _add_unique(items: list[str], value: str | None) -> None:
    text = str(value or "").strip()
    if text and text not in items:
        items.append(text)


def _player_capability(frame: dict[str, Any], player_input_kind: str) -> str | None:
    if player_input_kind == "perception":
        return "player.perception.request"
    if player_input_kind == "mixed":
        return "player.social_action.perform"
    action_kind = str(frame.get("action_kind") or "").strip().lower()
    if action_kind == "object_interaction":
        return "player.object_interaction.attempt"
    if action_kind == "movement":
        return "player.movement.attempt"
    if action_kind == "social_action":
        return "player.social_action.perform"
    if player_input_kind == "action":
        return "player.action.attempt"
    return None


def _narrator_capability(frame: dict[str, Any], player_input_kind: str) -> str:
    verb = str(frame.get("verb") or "").strip().lower()
    if player_input_kind == "perception" or verb in {"look_at", "listen_to"}:
        return "narrator.perception_result"
    if verb == "move_to":
        return "narrator.transition"
    return "narrator.physical_consequence"


def build_capability_selection_record(
    *,
    interpreted_input: dict[str, Any],
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
) -> dict[str, Any]:
    """Return requested/selected/realized dramatic runtime capabilities."""
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    aff = affordance_resolution if isinstance(affordance_resolution, dict) else {}
    player_input_kind = str(frame.get("player_input_kind") or interp.get("player_input_kind") or "").strip().lower()
    requested: list[str] = []
    selected: list[str] = []
    realized: list[str] = []
    blocked: list[str] = list(FORBIDDEN_NPC_CAPABILITIES)
    violations: list[dict[str, Any]] = []

    player_cap = _player_capability(frame, player_input_kind)
    _add_unique(requested, player_cap)
    _add_unique(selected, player_cap)
    if str(aff.get("action_commit_policy") or "").strip().lower() in {"commit_action", "commit_speech"}:
        _add_unique(realized, player_cap)

    narr_expected = narrator_authority.get("expected") if isinstance(narrator_authority.get("expected"), dict) else {}
    narr_actual = narrator_authority.get("actual") if isinstance(narrator_authority.get("actual"), dict) else {}
    narrator_required = bool(narr_expected.get("required"))
    narrator_cap = _narrator_capability(frame, player_input_kind)
    if narrator_required:
        _add_unique(selected, narrator_cap)
        if bool(narr_actual.get("narrator_block_present") or narr_actual.get("consequence_realized")):
            _add_unique(realized, narrator_cap)

    npc_actual = npc_authority.get("actual") if isinstance(npc_authority.get("actual"), dict) else {}
    if bool(interp.get("npc_response_expected")) or int(npc_actual.get("spoken_line_count") or 0) > 0:
        _add_unique(selected, "npc.social_reaction.optional")
    if int(npc_actual.get("spoken_line_count") or 0) > 0:
        _add_unique(realized, "npc.dialogue")
    if int(npc_actual.get("action_line_count") or 0) > 0:
        _add_unique(realized, "npc.gesture")

    failure_reason = str(npc_authority.get("failure_reason") or "").strip()
    if failure_reason == "npc_executed_player_action":
        _add_unique(realized, "npc.execute_player_action")
        violations.append(
            {
                "capability": "npc.execute_player_action",
                "reason": failure_reason,
                "offending_actor_id": npc_authority.get("offending_actor_id"),
            }
        )
    elif failure_reason == "npc_narrated_player_perception":
        _add_unique(realized, "npc.narrate_player_perception")
        violations.append(
            {
                "capability": "npc.narrate_player_perception",
                "reason": failure_reason,
                "offending_actor_id": npc_authority.get("offending_actor_id"),
            }
        )
    elif failure_reason == "ai_controlled_human_actor":
        _add_unique(realized, "npc.override_human_actor")
        violations.append(
            {
                "capability": "npc.override_human_actor",
                "reason": failure_reason,
                "offending_actor_id": npc_authority.get("offending_actor_id"),
            }
        )

    missing_required = [cap for cap in selected if cap.startswith("narrator.") and cap not in realized]
    status = "failed" if violations else "partial" if missing_required else "passed"
    return {
        "requested_capabilities": requested,
        "selected_capabilities": selected,
        "blocked_capabilities": blocked,
        "realized_capabilities": realized,
        "violations": violations,
        "missing_required_capabilities": missing_required,
        "status": status,
    }
