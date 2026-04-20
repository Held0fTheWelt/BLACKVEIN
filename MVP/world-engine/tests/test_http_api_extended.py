from __future__ import annotations

from app.api import http as http_module



def test_templates_endpoint_lists_builtin_templates(client):
    response = client.get("/api/templates")

    assert response.status_code == 200
    ids = {item["id"] for item in response.json()}
    assert {"god_of_carnage_solo", "apartment_confrontation_group", "better_tomorrow_district_alpha"} <= ids



def test_create_run_rejects_unknown_template(client):
    response = client.post("/api/runs", json={"template_id": "missing", "display_name": "Hollywood"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Unknown template id"



def test_create_ticket_rejects_unknown_run(client):
    response = client.post("/api/tickets", json={"run_id": "missing", "display_name": "Hollywood"})

    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"



def test_owner_only_story_rejects_foreign_join(client):
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "intruder", "display_name": "Intruder"},
    )

    assert response.status_code == 403
    assert "private to its owner" in response.json()["detail"]



def test_get_run_details_returns_404_for_missing_run(client):
    response = client.get("/api/runs/missing")
    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"



def test_get_snapshot_returns_404_for_missing_participant(client):
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "acct-1", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/snapshot/missing-participant")

    assert response.status_code == 404
    assert response.json()["detail"] == "Run or participant not found"



def test_get_transcript_returns_404_for_missing_run(client):
    response = client.get("/api/runs/missing/transcript")
    assert response.status_code == 404
    assert response.json()["detail"] == "Run not found"



def test_ready_endpoint_run_count_increases_after_run_creation(client):
    before = client.get("/api/health/ready").json()

    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "acct-1", "display_name": "Owner"},
    )
    assert create_response.status_code == 200

    after = client.get("/api/health/ready").json()
    assert after["template_count"] >= 3
    assert after["run_count"] == before["run_count"] + 1



def test_internal_join_context_allows_calls_when_no_key_is_configured(client, monkeypatch):
    monkeypatch.setattr(http_module, "PLAY_SERVICE_INTERNAL_API_KEY", None)
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "acct-host", "display_name": "Host"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "acct-guest", "display_name": "Guest"},
    )

    assert response.status_code == 200
    assert response.json()["display_name"] == "Guest"



def test_internal_join_context_requires_matching_internal_api_key(client, monkeypatch):
    monkeypatch.setattr(http_module, "PLAY_SERVICE_INTERNAL_API_KEY", "internal-secret")
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "acct-host", "display_name": "Host"},
    )
    run_id = create_response.json()["run"]["id"]

    missing = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "acct-guest", "display_name": "Guest"},
    )
    wrong = client.post(
        "/api/internal/join-context",
        headers={"x-play-service-key": "wrong"},
        json={"run_id": run_id, "account_id": "acct-guest", "display_name": "Guest"},
    )
    ok = client.post(
        "/api/internal/join-context",
        headers={"x-play-service-key": "internal-secret"},
        json={"run_id": run_id, "account_id": "acct-guest", "display_name": "Guest"},
    )

    assert missing.status_code == 401
    assert wrong.status_code == 401
    assert ok.status_code == 200
    assert ok.json()["account_id"] == "acct-guest"
