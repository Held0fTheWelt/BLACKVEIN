"""Synthetic narrator / clarification surfaces for action-resolution branch (no LLM)."""

from __future__ import annotations

from typing import Any

from story_runtime_core.content_locale import resolve_string


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
        "content": narr,
        "text": narr,
        "metadata": {
            "adapter": "action_resolution_synthetic",
            "structured_output": structured,
            "synthetic_action_resolution": True,
        },
    }
