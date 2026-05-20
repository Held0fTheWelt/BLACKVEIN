"""Runtime diagnostic snapshot aggregator (PR-D)."""

from __future__ import annotations

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.manager import StorySession


def test_runtime_diagnostic_snapshot_aggregates_thin_path_row() -> None:
    manager = StoryRuntimeManager()
    session = StorySession(
        session_id="runtime-diagnostic-snapshot-test",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": "annette_reille"},
        canonical_step_id="opening_005_statement_reading",
        turn_counter=1,
    )
    session.diagnostics = [
        {
            "turn_number": 1,
            "turn_kind": "player",
            "turn_status": "committed",
            "raw_input": "Ich gehe in die Küche",
            "observability_path_summary": {
                "free_player_action_resolution": {
                    "schema_version": "free_player_action_resolution.v1",
                    "target_location": "kitchen",
                },
                "canonical_path_hold_effect": {
                    "schema_version": "canonical_path_hold_effect.v1",
                    "effect_kind": "hold_current_step",
                },
                "director_gathering_state": {
                    "schema_version": "director_gathering_state.v1",
                    "paused": False,
                },
                "narrator_consequence_realization": {
                    "schema_version": "narrator_consequence_realization.v1",
                    "requires_model_realization": True,
                },
                "visible_block_emitted": True,
                "selected_capabilities": ["narrator.location_transition.describe"],
            },
            "diagnostics": {
                "director_pulse": {
                    "shadow_only": False,
                    "director_tick_decision": {"tick_id": "t1"},
                    "parity": {"bundle_block_count": 2, "event_stream_block_count": 2},
                },
            },
        },
    ]
    manager.sessions[session.session_id] = session

    snap = manager.get_runtime_diagnostic_snapshot(session.session_id)
    assert snap["schema_version"] == "runtime_diagnostic_snapshot.v1"
    assert snap["session_id"] == session.session_id
    assert snap["canonical_step_id"] == "opening_005_statement_reading"
    assert snap["resolver_output"]["not_yet_wired"] is False
    assert snap["resolver_output"]["payload"]["target_location"] == "kitchen"
    assert snap["canonical_path_hold_effect"]["payload"]["effect_kind"] == "hold_current_step"
    assert snap["pulse"]["not_yet_wired"] is False
    assert snap["pulse"]["payload"]["director_tick_decision"]["tick_id"] == "t1"
    assert snap["bundle_vs_event_stream_parity"]["not_yet_wired"] is False


def test_runtime_diagnostic_snapshot_http_route(client, internal_api_key) -> None:
    create = client.post(
        "/api/story/sessions",
        headers={"X-Play-Service-Key": internal_api_key},
        json={
            "module_id": "god_of_carnage",
            "runtime_projection": {
                "module_id": "god_of_carnage",
                "start_scene_id": "scene_1",
                "selected_player_role": "annette_reille",
                "human_actor_id": "annette_reille",
                "npc_actor_ids": ["alain_reille"],
                "actor_lanes": {"annette_reille": "human", "alain_reille": "npc"},
            },
            "session_output_language": "de",
            "skip_graph_opening_on_create": True,
        },
    )
    assert create.status_code == 200
    session_id = create.json()["session_id"]

    response = client.get(
        f"/api/story/sessions/{session_id}/runtime-diagnostic-snapshot",
        headers={"X-Play-Service-Key": internal_api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "runtime_diagnostic_snapshot.v1"
    assert body["session_id"] == session_id
    assert "resolver_output" in body
    assert "pulse" in body
