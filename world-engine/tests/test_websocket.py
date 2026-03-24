from __future__ import annotations

import pytest
from starlette.websockets import WebSocketDisconnect

from conftest import build_test_app, receive_until_snapshot



def test_websocket_rejects_missing_ticket(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws"):
                pass

    assert exc_info.value.code == 4401



def test_websocket_rejects_invalid_ticket(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        with pytest.raises((WebSocketDisconnect, Exception)) as exc_info:
            with client.websocket_connect("/ws?ticket=definitely-invalid") as websocket:
                websocket.receive_text()

    assert exc_info.value.code == 4403



def test_websocket_rejects_ticket_identity_mismatch(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        create_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "acct:owner", "display_name": "Owner"},
        )
        run_id = create_response.json()["run"]["id"]
        ticket_response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:owner", "display_name": "Owner"},
        )
        participant_id = ticket_response.json()["participant_id"]
        participant = app.state.manager.get_instance(run_id).participants[participant_id]
        bad_ticket = app.state.ticket_manager.issue(
            {
                "run_id": run_id,
                "participant_id": participant.id,
                "account_id": "acct:intruder",
                "display_name": participant.display_name,
                "role_id": participant.role_id,
            }
        )

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws?ticket={bad_ticket}") as websocket:
                websocket.receive_text()

    assert exc_info.value.code == 4403



def test_websocket_rejects_role_mismatch(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        create_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "acct:owner", "display_name": "Owner"},
        )
        run = create_response.json()["run"]
        participant = next(iter(app.state.manager.get_instance(run["id"]).participants.values()))
        bad_ticket = app.state.ticket_manager.issue(
            {
                "run_id": run["id"],
                "participant_id": participant.id,
                "account_id": participant.account_id,
                "display_name": participant.display_name,
                "role_id": "wrong-role",
            }
        )

        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect(f"/ws?ticket={bad_ticket}") as websocket:
                websocket.receive_text()

    assert exc_info.value.code == 4403



def test_invalid_command_produces_command_rejected_message(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        create_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "acct:owner", "display_name": "Owner"},
        )
        run_id = create_response.json()["run"]["id"]
        ticket_response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:owner", "display_name": "Owner"},
        )
        ticket = ticket_response.json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
            receive_until_snapshot(websocket, lambda data: data["viewer_account_id"] == "acct:owner")
            websocket.send_json({"action": "say", "text": ""})
            rejection = websocket.receive_json()

        assert rejection == {"type": "command_rejected", "reason": "Say what?"}



def test_websocket_disconnect_marks_participant_as_offline(tmp_path):
    app = build_test_app(tmp_path)

    from fastapi.testclient import TestClient

    with TestClient(app) as client:
        create_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "acct:owner", "display_name": "Owner"},
        )
        run_id = create_response.json()["run"]["id"]
        ticket_response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:owner", "display_name": "Owner"},
        )
        participant_id = ticket_response.json()["participant_id"]
        ticket = ticket_response.json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as websocket:
            receive_until_snapshot(websocket, lambda data: data["viewer_participant_id"] == participant_id)
            assert app.state.manager.get_instance(run_id).participants[participant_id].connected is True

        assert app.state.manager.get_instance(run_id).participants[participant_id].connected is False
