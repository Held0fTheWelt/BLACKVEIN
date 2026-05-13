"""ADR-0033 backend contract for live session opening readiness."""

from __future__ import annotations

from app.api.v1.game_routes import (
    _player_session_bundle,
    _player_shell_state_view,
    _shell_committed_turn_display_counter,
)


def test_live_session_without_opening_is_not_ready_for_play():
    bundle = _player_session_bundle(
        run_id="run-empty-opening",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="story-empty-opening",
        state={
            "turn_counter": 0,
            "story_window": {
                "contract": "authoritative_story_window_v1",
                "entries": [],
                "entry_count": 0,
                "latest_entry": None,
            },
        },
        created={
            "runtime_config_status": {
                "governed_runtime_active": True,
                "runtime_profile_id": "goc_live_profile",
            },
            "opening_turn": {
                "turn_kind": "opening",
                "turn_number": 0,
                "committed_result": {"commit_applied": True},
                "runtime_governance_surface": {
                    "quality_class": "healthy",
                    "degradation_signals": [],
                },
                "visible_output_bundle": {"gm_narration": [], "scene_blocks": []},
                "visible_scene_output": {"blocks": []},
            },
        },
    )

    assert bundle["runtime_session_ready"] is False
    assert bundle["can_execute"] is False
    assert bundle["opening_generation_status"] in {"blocked_missing_opening", "failed_opening_generation"}


def test_shell_committed_turn_display_counter_prefers_history_over_player_graph_counter():
    assert _shell_committed_turn_display_counter({"turn_counter": 0, "history_count": 1}) == 1
    assert (
        _shell_committed_turn_display_counter(
            {"turn_counter": 0, "history_count": 1, "committed_canonical_turn_count": 2}
        )
        == 2
    )
    assert _shell_committed_turn_display_counter({"turn_counter": 5}) == 5


def test_player_shell_state_view_turn_counter_matches_committed_rows():
    view = _player_shell_state_view(
        state={"turn_counter": 0, "history_count": 1},
        run_id="r1",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="we-s1",
    )
    assert view["turn_counter"] == 1
    assert view["player_graph_turn_counter"] == 0
    assert view["history_count"] == 1


def test_player_session_bundle_shell_shows_committed_count_when_we_turn_counter_zero():
    bundle = _player_session_bundle(
        run_id="run-opening",
        template_id="god_of_carnage_solo",
        module_id="god_of_carnage",
        runtime_session_id="story-we-1",
        state={
            "turn_counter": 0,
            "history_count": 1,
            "committed_canonical_turn_count": 1,
            "current_scene_id": "scene_1",
            "story_window": {
                "contract": "authoritative_story_window_v1",
                "entries": [
                    {
                        "kind": "opening",
                        "turn_number": 0,
                        "role": "runtime",
                        "text": "Opening line.",
                    }
                ],
                "entry_count": 1,
                "latest_entry": {"kind": "opening", "turn_number": 0},
            },
        },
        created={
            "runtime_config_status": {
                "governed_runtime_active": True,
                "runtime_profile_id": "goc_live_profile",
            },
            "opening_turn": {
                "turn_kind": "opening",
                "turn_number": 0,
                "committed_result": {"commit_applied": True},
                "runtime_governance_surface": {
                    "quality_class": "healthy",
                    "degradation_signals": [],
                },
                "visible_output_bundle": {
                    "gm_narration": [{"text": "Opening line."}],
                    "scene_blocks": [],
                },
                "visible_scene_output": {"blocks": []},
            },
        },
    )
    assert bundle["shell_state_view"]["turn_counter"] == 1
    assert bundle["shell_state_view"]["player_graph_turn_counter"] == 0
