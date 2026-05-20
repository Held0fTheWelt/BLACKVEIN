"""Deterministic authoritative action-resolution surfaces (no LLM invoke).

This module builds the runtime short path for affordance-resolved mundane
actions. It is **not** a mock of live generation: there is no adapter.generate
call, no LDSS fallback, and no model fallback — see ``metadata`` flags.
"""

from __future__ import annotations

from typing import Any

from ai_stack.language_io.language_adapter import resolve_string

from ai_stack.runtime_turn_contracts import ADAPTER_INVOCATION_AUTHORITATIVE_ACTION_RESOLUTION
from ai_stack.narrator.narrator_consequence_contracts import (
    build_local_context_transition,
    build_narrator_consequence_plan,
    build_updated_player_local_context,
    normalize_scene_affordance_model_for_contracts,
)
from ai_stack.environment_state_contracts import apply_action_to_environment_state


def build_synthetic_generation_for_action_resolution(
    *,
    module_id: str,
    lang: str,
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    content_modules_root: Any = None,
    scene_affordance_model: dict[str, Any] | None = None,
    current_player_local_context: dict[str, Any] | None = None,
    environment_state: dict[str, Any] | None = None,
    environment_model: dict[str, Any] | None = None,
    actor_lane_context: dict[str, Any] | None = None,
    turn_number: int | None = None,
) -> dict[str, Any]:
    """Return a minimal successful generation dict with structured_output for proposal_normalize."""
    status = str(affordance_resolution.get("affordance_status") or "").strip().lower()
    pol = str(affordance_resolution.get("action_commit_policy") or "").strip().lower()
    verb = str(player_action_frame.get("verb") or "").strip().lower()
    rt = player_action_frame.get("resolved_target") if isinstance(player_action_frame.get("resolved_target"), dict) else {}
    target_label = str(rt.get("matched_alias") or rt.get("canonical_name") or rt.get("target_id") or "").strip()
    action_kind = str(player_action_frame.get("action_kind") or "").strip().lower()

    # Compute local context transition and narrator consequence plan when scene data is available.
    # Flat ``scene_affordance_model`` from ``resolve_player_action`` must be wrapped for
    # narrator consequence contracts (nested ``scene_affordances``).
    sam = normalize_scene_affordance_model_for_contracts(
        scene_affordance_model if isinstance(scene_affordance_model, dict) else {},
    )
    local_context_transition: dict[str, Any] = {}
    narrator_consequence_plan: dict[str, Any] = {}
    updated_player_local_context: dict[str, Any] = {}
    candidate_environment_state: dict[str, Any] = {}

    if sam:
        local_context_transition = build_local_context_transition(
            player_action_frame=player_action_frame,
            affordance_resolution=affordance_resolution,
            scene_affordance_model=sam,
            current_player_local_context=current_player_local_context,
        )
        narrator_consequence_plan = build_narrator_consequence_plan(
            lang=lang,
            player_action_frame=player_action_frame,
            affordance_resolution=affordance_resolution,
            scene_affordance_model=sam,
            local_context_transition=local_context_transition,
        )
        updated_player_local_context = build_updated_player_local_context(
            current_player_local_context=current_player_local_context,
            local_context_transition=local_context_transition,
            narrator_consequence_plan=narrator_consequence_plan,
            scene_affordance_model=sam,
        )
        candidate_environment_state = apply_action_to_environment_state(
            environment_state=environment_state,
            environment_model=environment_model,
            player_action_frame=player_action_frame,
            affordance_resolution=affordance_resolution,
            local_context_transition=local_context_transition,
            narrator_consequence_plan=narrator_consequence_plan,
            actor_lane_context=actor_lane_context,
            turn_number=turn_number,
        )

    # Select template key (fallback path when scene affordance detail is absent).
    key = "action_resolution.narrator.generic"
    if pol == "needs_clarification" or status in {"unknown_target", "ambiguous"}:
        key = (
            "action_resolution.clarification.ambiguous"
            if status == "ambiguous"
            else "action_resolution.clarification.unknown_target"
        )
    elif status in {"blocked", "unsafe"}:
        key = "action_resolution.blocked.generic"
    elif verb in {"move_to", "stand_up"} or action_kind == "movement":
        key = (
            "action_resolution.narrator.move_offscreen"
            if status == "allowed_offscreen"
            else "action_resolution.narrator.move_local"
        )
    elif verb in {"look_at", "listen_to"} or action_kind == "perception":
        key = (
            "action_resolution.narrator.perception_object"
            if target_label
            else "action_resolution.narrator.perception_generic"
        )
    elif action_kind == "object_interaction" or verb in {
        "activate",
        "deactivate",
        "open",
        "place",
        "take",
    }:
        key = (
            "action_resolution.narrator.object_interaction"
            if target_label
            else "action_resolution.narrator.generic"
        )
    elif status == "partial":
        key = "action_resolution.narrator.partial"

    # Use authored scene-affordance consequence text when available; fall back to template.
    authored_text = narrator_consequence_plan.get("consequence_text") if narrator_consequence_plan else None
    if authored_text:
        narr = authored_text
    else:
        try:
            narr = resolve_string(
                module_id,
                key,
                lang,
                content_modules_root=content_modules_root,
                target_label=target_label or "…",
            )
        except KeyError:
            narr = resolve_string(
                module_id,
                "action_resolution.narrator.generic",
                lang,
                content_modules_root=content_modules_root,
                target_label=target_label or "…",
            )

    structured: dict[str, Any] = {
        "schema_version": "runtime_actor_turn_v1",
        "narration_summary": narr,
        "narrative_response": narr,
        "spoken_lines": [],
        "action_lines": [],
        "function_type": "action_resolution_surface",
    }
    return {
        "success": True,
        "attempted": False,
        "fallback_used": False,
        "content": narr,
        "text": narr,
        "metadata": {
            "adapter": "action_resolution_authoritative",
            "adapter_invocation_mode": ADAPTER_INVOCATION_AUTHORITATIVE_ACTION_RESOLUTION,
            "structured_output": structured,
            "authoritative_action_resolution": True,
            "generation_required": False,
            "mock_used": False,
            "ldss_fallback": False,
            "local_context_transition": local_context_transition or None,
            "narrator_consequence_plan": narrator_consequence_plan or None,
            "updated_player_local_context": updated_player_local_context or None,
            "candidate_environment_state": candidate_environment_state or None,
        },
    }
