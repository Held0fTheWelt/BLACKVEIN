"""Player-shell payload W5 view contract tests (Phase 5A)."""

from __future__ import annotations

from pathlib import Path

from app.api.v1.game_routes import _player_shell_state_view


def test_shell_state_view_omits_w5_player_view_when_runtime_state_is_fallback_only() -> None:
    state = {
        "turn_counter": 3,
        "current_scene_id": "opening",
        "history_count": 1,
        "runtime_world": {"current_room_id": "fallback_salon"},
        "committed_state": {
            "environment_state": {"current_room_id": "fallback_salon"},
            "player_shell_context": {"status": "fallback"},
        },
    }
    shell = _player_shell_state_view(
        state=state,
        run_id="run-1",
        template_id="tpl-1",
        module_id="god_of_carnage",
        runtime_session_id="sess-1",
    )
    assert "w5_player_view" not in shell
    assert "w5_player_view_diagnostics" not in shell
    assert shell["environment_state"]["current_room_id"] == "fallback_salon"


def test_shell_state_view_includes_w5_player_view_and_current_room_source_when_enabled() -> None:
    state = {
        "turn_counter": 3,
        "current_scene_id": "opening",
        "history_count": 1,
        "runtime_world": {"current_room_id": "fallback_salon"},
        "feature_flags": {"W5_AST_FRONTEND_PLAYER_VIEW_ENABLED": True},
        "w5_player_view": {
            "target_consumer": "player_shell",
            "actor_id": "annette",
            "where_summary": {
                "current_visible_location": "salon_w5",
                "scene_location": {"value": "salon_w5"},
            },
            "how_summary": {"facts": {"tone": "strained"}},
            "what_summary": {"facts": {"current_action": "listens"}},
        },
        "w5_player_view_diagnostics": {
            "w5_player_view_used": True,
            "w5_player_view_source": "w5_projection",
            "current_room_source": "w5_player_view",
        },
        "committed_state": {
            "environment_state": {"current_room_id": "fallback_salon"},
            "player_shell_context": {"status": "w5"},
        },
    }
    shell = _player_shell_state_view(
        state=state,
        run_id="run-1",
        template_id="tpl-1",
        module_id="god_of_carnage",
        runtime_session_id="sess-1",
    )
    assert shell["w5_player_view"]["target_consumer"] == "player_shell"
    assert shell["w5_player_view"]["how_summary"]["facts"]["tone"] == "strained"
    assert "tone" not in shell["w5_player_view"]["what_summary"]["facts"]
    assert shell["current_room_id"] == "salon_w5"
    assert shell["current_room_source"] == "w5_player_view"
    assert shell["feature_flags"]["W5_AST_FRONTEND_PLAYER_VIEW_ENABLED"] is True
    assert "w5_history" not in shell


def test_backend_static_current_room_helper_is_w5_first_with_fallback_current_room() -> None:
    source = (Path(__file__).resolve().parents[1] / "app/web/static/app.js").read_text(encoding="utf-8")
    assert "function currentRoomFromSnapshot(snapshot)" in source
    assert "if (w5FrontendPlayerViewEnabled(snapshot))" in source
    assert "const w5Room = roomFromW5PlayerView(snapshot);" in source
    assert "if (w5Room) return w5Room;" in source
    assert "return snapshot.current_room || null;" in source
    assert "function currentRoom() {\n  return currentRoomFromSnapshot(state.snapshot);\n}" in source
