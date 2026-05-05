"""ADR-0033 backend contract for live session opening readiness."""

from __future__ import annotations

from app.api.v1.game_routes import _player_session_bundle


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
