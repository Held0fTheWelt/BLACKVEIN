from __future__ import annotations

import pytest


@pytest.mark.mvp4
def test_create_run_persists_runtime_profile_handoff_for_backend_resume(client):
    response = client.post(
        "/api/runs",
        json={
            "runtime_profile_id": "god_of_carnage_solo",
            "selected_player_role": "annette",
            "account_id": "mvp4-handoff",
            "display_name": "MVP4 Handoff",
        },
    )
    assert response.status_code == 200
    created = response.json()
    run_id = created["run"]["id"]

    detail_response = client.get(
        f"/api/runs/{run_id}",
        headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
    )
    assert detail_response.status_code == 200
    details = detail_response.json()

    assert details["contract"] == "create_run_response.v1"
    assert details["content_module_id"] == "god_of_carnage"
    assert details["runtime_profile_id"] == "god_of_carnage_solo"
    assert details["runtime_module_id"] == "solo_story_runtime"
    assert details["runtime_mode"] == "solo_story"
    assert details["selected_player_role"] == "annette"
    assert details["human_actor_id"] == "annette_reille"
    assert set(details["npc_actor_ids"]) == {
        "alain_reille",
        "veronique_vallon",
        "michel_longstreet",
    }
    assert details["actor_lanes"]["annette_reille"] == "human"
    assert details["actor_lanes"]["alain_reille"] == "npc"
    assert details["visitor_present"] is False
    assert "visitor" not in details["actor_lanes"]
