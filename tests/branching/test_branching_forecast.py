from __future__ import annotations

from story_runtime_core.branching import build_branching_forecast


def _commit() -> dict:
    return {
        "turn_number": 3,
        "turn_kind": "player",
        "committed_scene_id": "scene_1",
        "situation_status": "continue",
        "allowed": False,
        "committed_consequences": ["interpretation_kind:speech"],
        "open_pressures": ["interpretation_ambiguity:who is blamed"],
        "planner_truth": {
            "social_pressure_shift": "escalated",
            "primary_responder_id": "annette_reille",
            "secondary_responder_ids": ["michel_longstreet"],
        },
    }


def test_branching_forecast_is_bounded_and_non_authoritative() -> None:
    forecast = build_branching_forecast(
        story_session_id="session-branch",
        module_id="god_of_carnage",
        runtime_profile_id="god_of_carnage_solo",
        canonical_turn_id="session-branch:turn:3",
        turn_number=3,
        turn_kind="player",
        narrative_commit=_commit(),
        narrative_threads={
            "active": [
                {
                    "thread_id": "threadabcdef123456",
                    "thread_kind": "interpretation_pressure",
                    "status": "active",
                    "intensity": 4,
                    "persistence_turns": 2,
                    "related_entities": ["annette_reille"],
                }
            ]
        },
        thread_metrics={"dominant_thread_kind": "interpretation_pressure", "thread_pressure_level": 4},
        selected_responder_set=[{"actor_id": "annette_reille"}, {"actor_id": "michel_longstreet"}],
    )

    assert forecast["schema_version"] == "branching_forecast.v1"
    assert forecast["status"] == "forecasted"
    assert forecast["forecast_only"] is True
    assert forecast["authoritative"] is False
    assert forecast["inactive_branches_authoritative"] is False
    assert forecast["mutates_canonical_state"] is False
    assert forecast["selection_required_to_commit"] is True
    assert forecast["option_count"] == 3
    assert {option["family"] for option in forecast["options"]} == {
        "press_pressure",
        "repair_pressure",
        "shift_focus",
    }


def test_branching_forecast_ids_are_stable_for_same_committed_inputs() -> None:
    kwargs = {
        "story_session_id": "session-branch",
        "module_id": "god_of_carnage",
        "canonical_turn_id": "session-branch:turn:3",
        "turn_number": 3,
        "turn_kind": "player",
        "narrative_commit": _commit(),
        "narrative_threads": {"active": []},
        "thread_metrics": {},
    }

    first = build_branching_forecast(**kwargs)
    second = build_branching_forecast(**kwargs)

    assert first["path_signature"] == second["path_signature"]
    assert [o["option_id"] for o in first["options"]] == [o["option_id"] for o in second["options"]]


def test_branching_forecast_opening_turn_is_not_applicable() -> None:
    forecast = build_branching_forecast(
        story_session_id="session-branch",
        module_id="god_of_carnage",
        canonical_turn_id="session-branch:turn:0",
        turn_number=0,
        turn_kind="opening",
        narrative_commit={"turn_number": 0, "committed_scene_id": "scene_1"},
    )

    assert forecast["status"] == "not_applicable"
    assert forecast["option_count"] == 0
    assert forecast["trigger_reasons"] == ["opening_turn"]
