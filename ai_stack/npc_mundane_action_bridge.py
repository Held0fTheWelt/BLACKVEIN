"""Actor-symmetry bridge: route NPC mundane actions through player resolution machinery.

Sub-Plan 3 (ADR-0059): NPCs use the same Possibility × Morality classification path as
the human player. This module does not duplicate verb lists or room enums — it wraps
``resolve_player_action`` with an ``actor_lane: npc`` marker and the acting NPC id.
"""

from __future__ import annotations

from typing import Any

from ai_stack.story_runtime.player_action_resolution import resolve_player_action


def resolve_npc_mundane_action(
    *,
    raw_text: str,
    interpreted_input: dict[str, Any],
    module_id: str,
    runtime_projection: dict[str, Any],
    content_modules_root: str,
    npc_actor_id: str,
) -> dict[str, Any]:
    """Resolve an NPC mundane action using the shared semantic player-action path."""
    actor_id = str(npc_actor_id or "").strip()
    if not actor_id:
        raise ValueError("resolve_npc_mundane_action requires npc_actor_id")

    enriched = dict(interpreted_input or {})
    enriched.setdefault("actor_lane", "npc")
    enriched["acting_actor_id"] = actor_id
    enriched.setdefault("narrator_response_expected", False)
    enriched.setdefault("npc_response_expected", True)

    out = resolve_player_action(
        raw_text=raw_text,
        interpreted_input=enriched,
        module_id=module_id,
        runtime_projection=runtime_projection,
        content_modules_root=content_modules_root,
    )
    frame = out.get("player_action_frame") if isinstance(out.get("player_action_frame"), dict) else {}
    frame = dict(frame)
    frame["actor_lane"] = "npc"
    frame["acting_actor_id"] = actor_id
    out["player_action_frame"] = frame
    out["resolution_lane"] = "npc_mundane_action_bridge.v1"
    return out


__all__ = ["resolve_npc_mundane_action"]
