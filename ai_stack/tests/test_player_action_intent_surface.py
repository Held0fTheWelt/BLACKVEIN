"""PLAYER-ACTION-INTENT-01 surface diagnostics on validation seam."""

from __future__ import annotations

from ai_stack.story_runtime.turn.god_of_carnage_turn_seams import _detect_npc_narrated_player_action_violation


def test_detect_npc_echoes_physical_player_input():
    structured = {
        "spoken_lines": [
            {"speaker_id": "michel_longstreet", "text": "Natürlich, gehe in die Küche, die Küche ist gleich da."},
        ]
    }
    assert _detect_npc_narrated_player_action_violation(
        structured=structured,
        raw_player_input="Gehe in die Küche",
        player_input_kind="action",
        human_actor_id="annette_reille",
    )
