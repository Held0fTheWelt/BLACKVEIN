from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.http import router as http_router
from app.api.ws import router as ws_router
from app.auth.tickets import TicketManager
from app.runtime.manager import RuntimeManager


def build_test_app(tmp_path: Path) -> FastAPI:
    app = FastAPI()
    app.state.manager = RuntimeManager(store_root=tmp_path)
    app.state.ticket_manager = TicketManager("test-secret")
    app.include_router(http_router)
    app.include_router(ws_router)
    return app


def test_create_run_and_ticket_include_backend_identity(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)

    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "42", "display_name": "Hollywood"},
    )
    assert response.status_code == 200
    run_id = response.json()["run"]["id"]

    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "42", "display_name": "Hollywood"},
    )
    assert ticket_response.status_code == 200
    payload = app.state.ticket_manager.verify(ticket_response.json()["ticket"])
    assert payload["account_id"] == "42"
    assert payload["display_name"] == "Hollywood"


def test_internal_join_context_reuses_same_account_seat(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)

    api_key = {"X-Play-Service-Key": "internal-api-key-for-ops"}

    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "100", "display_name": "Host"},
    )
    run_id = run_response.json()["run"]["id"]

    first = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "100", "display_name": "Host"},
        headers=api_key,
    )
    second = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "100", "display_name": "Host Updated"},
        headers=api_key,
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["participant_id"] == second.json()["participant_id"]
    assert second.json()["display_name"] == "Host Updated"


def test_websocket_move_flow(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)

    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "7", "display_name": "Hollywood"},
    )
    run_id = run_response.json()["run"]["id"]
    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "7", "display_name": "Hollywood"},
    )
    ticket = ticket_response.json()["ticket"]

    with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
        first_payload = websocket.receive_json()
        assert first_payload["type"] == "snapshot"
        assert first_payload["data"]["viewer_room_id"] == "hallway"

        websocket.send_json({"action": "move", "target_room_id": "living_room"})
        second_payload = websocket.receive_json()
        assert second_payload["type"] == "snapshot"
        assert second_payload["data"]["viewer_room_id"] == "living_room"
        assert any(entry["kind"] == "room_changed" for entry in second_payload["data"]["transcript_tail"])


def test_internal_run_detail_and_terminate(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)

    api_key = {"X-Play-Service-Key": "internal-api-key-for-ops"}

    run_response = client.post("/api/runs", json={"template_id": "god_of_carnage_solo", "account_id": "7", "display_name": "Hollywood"})
    run_id = run_response.json()["run"]["id"]

    detail_response = client.get(f"/api/internal/runs/{run_id}", headers=api_key)
    assert detail_response.status_code == 200
    assert detail_response.json()["run"]["id"] == run_id

    transcript_response = client.get(f"/api/internal/runs/{run_id}/transcript", headers=api_key)
    assert transcript_response.status_code == 200
    assert transcript_response.json()["run_id"] == run_id

    terminate_response = client.post(f"/api/internal/runs/{run_id}/terminate", json={"actor_display_name": "Ops", "reason": "Test stop"}, headers=api_key)
    assert terminate_response.status_code == 200
    body = terminate_response.json()
    assert body["terminated"] is True
    assert body["run_id"] == run_id
    assert body["actor_display_name"] == "Ops"
    assert body["reason"] == "Test stop"
    assert isinstance(body.get("template_id"), str) and body["template_id"]
