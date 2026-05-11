"""Deterministic authoritative action-resolution surfaces (no LLM invoke).

This module builds the runtime short path for affordance-resolved mundane
actions. It is **not** a mock of live generation: there is no adapter.generate
call, no LDSS fallback, and no model fallback — see ``metadata`` flags.
"""

from __future__ import annotations

from typing import Any

from story_runtime_core.content_locale import resolve_string

from ai_stack.runtime_turn_contracts import ADAPTER_INVOCATION_AUTHORITATIVE_ACTION_RESOLUTION


def build_synthetic_generation_for_action_resolution(
    *,
    module_id: str,
    lang: str,
    player_action_frame: dict[str, Any],
    affordance_resolution: dict[str, Any],
    content_modules_root: Any = None,
) -> dict[str, Any]:
    """Return a minimal successful generation dict with structured_output for proposal_normalize."""
    status = str(affordance_resolution.get("affordance_status") or "").strip().lower()
    pol = str(affordance_resolution.get("action_commit_policy") or "").strip().lower()
    verb = str(player_action_frame.get("verb") or "").strip().lower()
    rt = player_action_frame.get("resolved_target") if isinstance(player_action_frame.get("resolved_target"), dict) else {}
    target_label = str(rt.get("matched_alias") or rt.get("canonical_name") or rt.get("target_id") or "").strip()
    action_kind = str(player_action_frame.get("action_kind") or "").strip().lower()

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
        },
    }
