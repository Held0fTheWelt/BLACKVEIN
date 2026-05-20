"""NPC mundane action bridge — shared resolution path (Sub-Plan 3)."""

from __future__ import annotations

from unittest.mock import patch

from ai_stack.npc_mundane_action_bridge import resolve_npc_mundane_action


def test_bridge_marks_npc_lane_and_delegates() -> None:
    fake_out = {
        "player_action_frame": {"verb": "wait", "action_kind": "wait"},
        "affordance_resolution": {"affordance_status": "allowed"},
    }
    with patch(
        "ai_stack.npc_mundane_action_bridge.resolve_player_action",
        return_value=fake_out,
    ) as mock_resolve:
        out = resolve_npc_mundane_action(
            raw_text="Alain holt Wasser",
            interpreted_input={"verb": "object_interaction"},
            module_id="god_of_carnage",
            runtime_projection={},
            content_modules_root="content/modules",
            npc_actor_id="alain_reille",
        )
    mock_resolve.assert_called_once()
    call_kw = mock_resolve.call_args.kwargs
    assert call_kw["interpreted_input"]["actor_lane"] == "npc"
    assert call_kw["interpreted_input"]["acting_actor_id"] == "alain_reille"
    assert out["resolution_lane"] == "npc_mundane_action_bridge.v1"
    assert out["player_action_frame"]["acting_actor_id"] == "alain_reille"
