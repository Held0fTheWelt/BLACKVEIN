import importlib.util

import pytest

SQLALCHEMY_AVAILABLE = importlib.util.find_spec("sqlalchemy") is not None

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.http import router as http_router
from app.api.ws import router as ws_router
from app.auth.tickets import TicketManager
from app.runtime.manager import RuntimeManager
from conftest import receive_until_snapshot

def build_test_app(tmp_path: Path, *, store_backend: str = "json", store_url: str | None = None) -> FastAPI:
    app = FastAPI()
    app.state.manager = RuntimeManager(store_root=tmp_path, store_backend=store_backend, store_url=store_url)
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


def test_ready_endpoint_reports_store(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["store"]["backend"] == "json"


def test_run_details_include_lobby_state(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "100", "display_name": "Host"},
    )
    run_id = run_response.json()["run"]["id"]
    detail_response = client.get(f"/api/runs/{run_id}")
    assert detail_response.status_code == 200
    body = detail_response.json()
    assert body["lobby"]["status"] == "lobby"
    assert body["template"]["min_humans_to_start"] == 2


def test_internal_join_context_reuses_same_account_seat(tmp_path: Path):
    app = build_test_app(tmp_path)
    client = TestClient(app)

    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "100", "display_name": "Host"},
    )
    run_id = run_response.json()["run"]["id"]

    first = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "100", "display_name": "Host"},
    )
    second = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "100", "display_name": "Host Updated"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["participant_id"] == second.json()["participant_id"]
    assert second.json()["display_name"] == "Host Updated"


def test_websocket_group_lobby_concurrent_connections(tmp_path: Path):
    """Test concurrent WebSocket connections and host ready action."""
    app = build_test_app(tmp_path)
    client = TestClient(app)

    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "7", "display_name": "Host"},
    )
    run_id = run_response.json()["run"]["id"]

    guest_ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "8", "display_name": "Guest", "preferred_role_id": "parent_a"},
    )
    guest_ticket = guest_ticket_response.json()["ticket"]

    host_ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "7", "display_name": "Host"},
    )
    host_ticket = host_ticket_response.json()["ticket"]

    with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:
        # Test initial snapshots for both participants
        host_snap = receive_until_snapshot(host_ws, lambda data: data["viewer_role_id"] == "mediator")
        assert host_snap["data"]["viewer_role_id"] == "mediator"

        guest_initial = receive_until_snapshot(guest_ws, lambda data: data["viewer_role_id"] == "parent_a")
        assert guest_initial["data"]["lobby"]["status"] == "lobby"

        # Test host sending ready action
        host_ws.send_json({"action": "set_ready", "ready": True})
        host_after_ready = receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1)
        guest_after_host_ready = receive_until_snapshot(guest_ws, lambda data: data["lobby"]["ready_human_seats"] == 1)
        assert host_after_ready["data"]["lobby"]["ready_human_seats"] == 1
        assert guest_after_host_ready["data"]["lobby"]["ready_human_seats"] == 1


def test_websocket_resume_with_new_ticket(tmp_path: Path):
    """Test rejoining a run with a new ticket."""
    app = build_test_app(tmp_path)
    client = TestClient(app)

    # Create run with host
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "7", "display_name": "Host"},
    )
    run_id = run_response.json()["run"]["id"]

    # Create initial ticket for guest with preferred role
    initial_ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "8", "display_name": "Guest", "preferred_role_id": "parent_a"},
    )
    initial_ticket = initial_ticket_response.json()["ticket"]

    # Connect once to establish the role
    with client.websocket_connect(f"/ws?ticket={initial_ticket}") as initial_ws:
        initial_snap = initial_ws.receive_json()
        assert initial_snap["data"]["viewer_display_name"] == "Guest"
        assert initial_snap["data"]["viewer_role_id"] == "parent_a"

    # Create new ticket for same account (simulating resume/rejoin)
    resume_ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "8", "display_name": "Guest Reloaded"},
    )
    resume_ticket = resume_ticket_response.json()["ticket"]

    # Connect with resume ticket and verify reconnection preserves role
    with client.websocket_connect(f"/ws?ticket={resume_ticket}") as guest_rejoin_ws:
        resumed = guest_rejoin_ws.receive_json()
        assert resumed["data"]["viewer_display_name"] == "Guest Reloaded"
        assert resumed["data"]["viewer_role_id"] == "parent_a"


@pytest.mark.skipif(not SQLALCHEMY_AVAILABLE, reason="sqlalchemy not installed")
def test_sqlalchemy_ready_endpoint_with_sqlite(tmp_path: Path):
    db_url = f"sqlite:///{tmp_path / 'runtime_api.db'}"
    app = build_test_app(tmp_path, store_backend="sqlalchemy", store_url=db_url)
    client = TestClient(app)
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert response.json()["store"]["backend"] == "sqlalchemy"



def test_ticket_manager_accepts_shared_secret_alias(monkeypatch):
    import app.auth.tickets as tickets_module

    monkeypatch.setattr(tickets_module, "PLAY_SERVICE_SECRET", "alias-secret")

    manager = tickets_module.TicketManager()
    token = manager.issue({"run_id": "run-1", "participant_id": "p-1"}, ttl_seconds=60)
    payload = manager.verify(token)
    assert payload["run_id"] == "run-1"
    assert payload["participant_id"] == "p-1"
