"""Dramatic runtime capability selection for story turns.

These capabilities describe narrative authority at runtime. They are distinct
from the technical tool/capability registry in ``ai_stack.capabilities``.
"""

from __future__ import annotations

from typing import Any

from ai_stack.dramatic_capability_contracts import (
    NPC_ACTION_GESTURE_OPTIONAL,
    NPC_DIRECT_ANSWER_ALLOWED,
    NPC_EXECUTE_PLAYER_ACTION_FORBIDDEN,
    NPC_FORCE_PLAYER_SPEECH_FORBIDDEN,
    NPC_NARRATE_PLAYER_PERCEPTION_FORBIDDEN,
    NPC_SOCIAL_REACTION_OPTIONAL,
    NARRATOR_ACTION_CONSEQUENCE_DESCRIBE,
    NARRATOR_LOCATION_TRANSITION_DESCRIBE,
    PLAYER_SPEECH_REQUEST,
    add_unique,
    default_capability_policy,
    forbidden_capability_for_reason,
    narrator_capability_for_frame,
    player_capability_for_frame,
)
from story_runtime_core.player_input_intent_contract import is_speech_like_player_input_kind


def _capability_policy(module_runtime_policy: dict[str, Any] | None) -> dict[str, Any]:
    if isinstance(module_runtime_policy, dict):
        policy = module_runtime_policy.get("capability_policy")
        if isinstance(policy, dict):
            return policy
    return default_capability_policy()


def _blocked_capabilities(module_runtime_policy: dict[str, Any] | None) -> list[str]:
    policy = _capability_policy(module_runtime_policy)
    raw = policy.get("forbidden")
    if not isinstance(raw, list):
        raw = default_capability_policy()["forbidden"]
    return [str(item).strip() for item in raw if str(item).strip()]


def build_capability_selection_record(
    *,
    interpreted_input: dict[str, Any],
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    narrator_authority: dict[str, Any],
    npc_authority: dict[str, Any],
    module_runtime_policy: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Return requested/selected/realized dramatic runtime capabilities."""
    frame = player_action_frame if isinstance(player_action_frame, dict) else {}
    interp = interpreted_input if isinstance(interpreted_input, dict) else {}
    aff = affordance_resolution if isinstance(affordance_resolution, dict) else {}
    player_input_kind = str(frame.get("player_input_kind") or interp.get("player_input_kind") or "").strip().lower()
    requested: list[str] = []
    selected: list[str] = []
    required: list[str] = []
    realized: list[str] = []
    blocked: list[str] = _blocked_capabilities(module_runtime_policy)
    violations: list[dict[str, Any]] = []

    player_cap = player_capability_for_frame(frame, player_input_kind)
    add_unique(requested, player_cap)
    add_unique(selected, player_cap)
    if player_cap == PLAYER_SPEECH_REQUEST and str(aff.get("action_commit_policy") or "").strip().lower() == "commit_speech":
        add_unique(realized, player_cap)
    elif str(aff.get("action_commit_policy") or "").strip().lower() in {"commit_action", "commit_speech"}:
        add_unique(realized, player_cap)

    narr_expected = narrator_authority.get("expected") if isinstance(narrator_authority.get("expected"), dict) else {}
    narr_actual = narrator_authority.get("actual") if isinstance(narrator_authority.get("actual"), dict) else {}
    narrator_required = bool(narr_expected.get("required"))
    narrator_cap = narrator_capability_for_frame(frame, player_input_kind)
    if narrator_required:
        add_unique(selected, narrator_cap)
        add_unique(required, narrator_cap)
        if bool(narr_actual.get("narrator_block_present") or narr_actual.get("consequence_realized")):
            add_unique(realized, narrator_cap)
            add_unique(realized, player_cap)

    npc_actual = npc_authority.get("actual") if isinstance(npc_authority.get("actual"), dict) else {}
    npc_response_cap = (
        NPC_DIRECT_ANSWER_ALLOWED
        if is_speech_like_player_input_kind(player_input_kind)
        else NPC_SOCIAL_REACTION_OPTIONAL
    )
    if bool(interp.get("npc_response_expected")) or int(npc_actual.get("spoken_line_count") or 0) > 0:
        add_unique(selected, npc_response_cap)
    if int(npc_actual.get("spoken_line_count") or 0) > 0:
        add_unique(realized, npc_response_cap)
    if int(npc_actual.get("action_line_count") or 0) > 0:
        add_unique(realized, NPC_ACTION_GESTURE_OPTIONAL)

    failure_reason = str(npc_authority.get("failure_reason") or "").strip()
    violated = forbidden_capability_for_reason(failure_reason)
    if violated:
        add_unique(realized, violated)
        violations.append(
            {
                "capability": violated,
                "reason": failure_reason,
                "offending_actor_id": npc_authority.get("offending_actor_id"),
            }
        )
    elif failure_reason == "narrator_required_missing":
        add_unique(required, NARRATOR_ACTION_CONSEQUENCE_DESCRIBE)

    missing_required = [cap for cap in required if cap not in realized]
    status = "failed" if violations else "partial" if missing_required else "passed"
    return {
        "requested_capabilities": requested,
        "selected_capabilities": selected,
        "required_capabilities": required,
        "blocked_capabilities": blocked,
        "realized_capabilities": realized,
        "violated_capabilities": [v["capability"] for v in violations if isinstance(v, dict)],
        "violations": violations,
        "missing_required_capabilities": missing_required,
        "status": status,
    }
