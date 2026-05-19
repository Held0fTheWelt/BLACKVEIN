"""Thin-path summary API — Resolver → Director → Narrator diagnostics (PR-A A-11)."""

from __future__ import annotations

from app.story_runtime import StoryRuntimeManager
from app.story_runtime.manager import StorySession


def test_get_thin_path_summary_reads_observability_path_summary() -> None:
    manager = StoryRuntimeManager()
    session = StorySession(
        session_id="thin-path-summary-test",
        module_id="god_of_carnage",
        runtime_projection={"human_actor_id": "annette_reille"},
        current_scene_id="living_room",
        turn_counter=2,
    )
    session.diagnostics = [
        {
            "turn_number": 1,
            "turn_kind": "player",
            "turn_status": "committed",
            "raw_input": "Gehe in die Küche",
            "observability_path_summary": {
                "realization_plan": {
                    "schema_version": "realization_plan.v1",
                    "realization_owner": "narrator",
                    "capabilities_selected": ["narrator.location_transition.describe"],
                },
                "realize_via_capabilities_used_capability": "narrator.location_transition.describe",
                "realize_via_capabilities_outcome": "success",
                "kanon_break": False,
                "kanon_break_reason": None,
                "director_path_mode": "director_realization_composer",
                "selected_capabilities": ["narrator.location_transition.describe"],
                "nodes_executed": [
                    "resolve_player_action",
                    "director_compose_realization",
                    "realize_via_capabilities",
                ],
            },
            "visible_output_bundle": {
                "scene_blocks": [
                    {"block_type": "player_input", "text": "Gehe in die Küche"},
                    {"block_type": "player_input_outcome", "text": "Du betrittst die Küche."},
                ],
            },
        },
    ]
    manager.sessions[session.session_id] = session

    summary = manager.get_thin_path_summary(session.session_id, limit=5)
    assert summary["schema_version"] == "thin_path_summary.v1"
    assert summary["session_id"] == session.session_id
    assert len(summary["rows"]) == 1
    row = summary["rows"][0]
    assert row["realization_plan"]["capabilities_selected"] == ["narrator.location_transition.describe"]
    assert row["realize_via_capabilities_used_capability"] == "narrator.location_transition.describe"
    assert row["kanon_break"] is False
    assert row["visible_scene_block_count"] == 2


def test_thin_path_summary_http_route(client, internal_api_key) -> None:
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
        f"/api/story/sessions/{session_id}/thin-path-summary",
        headers={"X-Play-Service-Key": internal_api_key},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["schema_version"] == "thin_path_summary.v1"
    assert body["session_id"] == session_id
    assert isinstance(body.get("rows"), list)
