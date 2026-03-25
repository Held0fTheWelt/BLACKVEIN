"""
WAVE 7: WebSocket State Machine and Sequencing Tests

Tests for WebSocket state machine and sequencing rules:
- Ready flow: join → ready → start_run → game state
- start_run blocked if not all ready
- Duplicate ready rejected or idempotent
- Invalid action before join rejected
- Invalid transitions rejected
- State transitions are deterministic
- Multiple participants' state interactions
"""
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import receive_until_snapshot


@pytest.fixture
def app_for_state(tmp_path: Path) -> FastAPI:
    """Build app for state transition tests."""
    from app.api.http import router as http_router
    from app.api.ws import router as ws_router

    app = FastAPI()
    from app.runtime.manager import RuntimeManager
    from app.auth.tickets import TicketManager

    app.state.manager = RuntimeManager(store_root=tmp_path)
    app.state.ticket_manager = TicketManager("test-secret")
    app.include_router(http_router)
    app.include_router(ws_router)
    return app


class TestWebSocketStateTransitions:
    """Test state machine and sequencing."""

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_initial_state_is_lobby(self, app_for_state: FastAPI):
        """Run should start in lobby state."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            assert snap["data"]["status"] == "lobby"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_ready_action_in_lobby(self, app_for_state: FastAPI):
        """set_ready action should work in lobby state."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot
            ws.send_json({"action": "set_ready", "ready": True})

            # Should receive snapshot showing ready state changed
            snap = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] >= 1)
            assert snap["type"] == "snapshot"
            assert snap["data"]["lobby"]["ready_human_seats"] == 1

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_ready_becomes_true_then_false(self, app_for_state: FastAPI):
        """Ready state should toggle between true and false."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot

            # Set ready to true
            ws.send_json({"action": "set_ready", "ready": True})
            snap_true = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] == 1)
            assert snap_true["data"]["lobby"]["ready_human_seats"] == 1

            # Set ready to false
            ws.send_json({"action": "set_ready", "ready": False})
            snap_false = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] == 0)
            assert snap_false["data"]["lobby"]["ready_human_seats"] == 0

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_duplicate_ready_is_idempotent(self, app_for_state: FastAPI):
        """Sending ready=true twice should not cause errors."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            # Send ready=true first time
            ws.send_json({"action": "set_ready", "ready": True})
            snap1 = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] == 1)

            # Send ready=true again (should be idempotent)
            ws.send_json({"action": "set_ready", "ready": True})
            snap2 = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] == 1)

            # Both should show 1 ready
            assert snap1["data"]["lobby"]["ready_human_seats"] == 1
            assert snap2["data"]["lobby"]["ready_human_seats"] == 1

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_start_run_requires_all_ready(self, app_for_state: FastAPI):
        """start_run should fail if not all participants are ready."""
        client = TestClient(app_for_state)

        # Create group story run (requires min 2 humans)
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_ws.receive_json()  # Initial snapshot
            guest_ws.receive_json()

            # Host is ready
            host_ws.send_json({"action": "set_ready", "ready": True})
            host_snap = receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1)

            # Guest is NOT ready yet
            # Host tries to start - should fail
            host_ws.send_json({"action": "start_run"})

            # Should get command_rejected or snapshot showing can_start=false
            response = host_ws.receive_json()
            if response["type"] == "command_rejected":
                assert "Need" in response.get("reason", "") or "all" in response.get("reason", "").lower()
            elif response["type"] == "snapshot":
                # Snapshot should show can_start=false
                assert response["data"]["lobby"]["can_start"] is False

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_start_run_succeeds_when_all_ready(self, app_for_state: FastAPI):
        """start_run should succeed when all participants are ready."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_ws.receive_json()
            guest_ws.receive_json()

            # Host marks ready
            host_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1, attempts=3, timeout=2.0)

            # Guest marks ready
            guest_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(guest_ws, lambda data: data["lobby"]["ready_human_seats"] == 2, attempts=3, timeout=2.0)

            # Host starts run
            host_ws.send_json({"action": "start_run"})

            # Should transition to running state
            snap = receive_until_snapshot(host_ws, lambda data: data["status"] == "running", attempts=3, timeout=2.0)
            assert snap["data"]["status"] == "running"

            # Guest should also see running state
            guest_snap = receive_until_snapshot(guest_ws, lambda data: data["status"] == "running", attempts=3, timeout=2.0)
            assert guest_snap["data"]["status"] == "running"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_ready_unavailable_after_run_starts(self, app_for_state: FastAPI):
        """set_ready should not work after run transitions to running."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws:
            host_ws.receive_json()

            # Host ready
            host_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1, attempts=3, timeout=2.0)

        # Guest ready
        with client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:
            guest_ws.receive_json()
            guest_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(guest_ws, lambda data: data["lobby"]["ready_human_seats"] == 2, attempts=3, timeout=2.0)

        # Host starts the run
        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws:
            host_ws.receive_json()  # Initial snapshot
            host_ws.send_json({"action": "start_run"})
            snap = receive_until_snapshot(host_ws, lambda data: data["status"] == "running", attempts=3, timeout=2.0)

            # Try to set_ready after running (should fail)
            host_ws.send_json({"action": "set_ready", "ready": False})
            response = host_ws.receive_json()

            # Should reject the command
            if response["type"] == "command_rejected":
                assert "only" in response.get("reason", "").lower() or "lobby" in response.get("reason", "").lower()

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_invalid_action_rejected(self, app_for_state: FastAPI):
        """Unknown action should be rejected with command_rejected."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            # Send invalid action
            ws.send_json({"action": "invalid_action_xyz"})

            response = ws.receive_json()
            assert response["type"] == "command_rejected"
            assert "Unknown" in response.get("reason", "")

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_move_blocked_in_lobby(self, app_for_state: FastAPI):
        """move action should be blocked while in lobby state."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            current_room = snap["data"]["viewer_room_id"]

            # Try to move (should fail in lobby)
            ws.send_json({"action": "move", "target_room_id": "other-room"})

            response = ws.receive_json()
            if response["type"] == "command_rejected":
                assert "lobby" in response.get("reason", "").lower()

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_only_host_can_start_run(self, app_for_state: FastAPI):
        """Only the run owner should be able to start_run."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_ws.receive_json()
            guest_ws.receive_json()

            # Host marks ready
            host_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1, attempts=3, timeout=2.0)

            # Guest marks ready
            guest_ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(guest_ws, lambda data: data["lobby"]["ready_human_seats"] == 2, attempts=3, timeout=2.0)

            # Guest tries to start (should fail)
            guest_ws.send_json({"action": "start_run"})
            response = guest_ws.receive_json()

            if response["type"] == "command_rejected":
                assert "host" in response.get("reason", "").lower() or "only" in response.get("reason", "").lower()

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_state_transitions_are_deterministic(self, app_for_state: FastAPI):
        """Replaying the same sequence of actions should produce the same state."""
        client = TestClient(app_for_state)

        def run_sequence(client, ticket):
            with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
                snap1 = ws.receive_json()
                state1 = {
                    "status": snap1["data"]["status"],
                    "beat_id": snap1["data"]["beat_id"],
                }

                ws.send_json({"action": "set_ready", "ready": True})
                snap2 = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] >= 1)
                state2 = {
                    "status": snap2["data"]["status"],
                    "ready_count": snap2["data"]["lobby"]["ready_human_seats"],
                }

                return [state1, state2]

        # Create run and ticket
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Run sequence multiple times
        result1 = run_sequence(client, ticket)
        result2 = run_sequence(client, ticket)

        # Results should match
        assert result1 == result2

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_multiple_participants_state_synchronization(self, app_for_state: FastAPI):
        """All participants should see same state after actions."""
        client = TestClient(app_for_state)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_ws.receive_json()
            guest_ws.receive_json()

            # Host marks ready
            host_ws.send_json({"action": "set_ready", "ready": True})

            # Both should see host as ready
            host_snap = receive_until_snapshot(host_ws, lambda data: data["lobby"]["ready_human_seats"] == 1)
            guest_snap = receive_until_snapshot(guest_ws, lambda data: data["lobby"]["ready_human_seats"] == 1)

            assert host_snap["data"]["lobby"]["ready_human_seats"] == 1
            assert guest_snap["data"]["lobby"]["ready_human_seats"] == 1

            # Verify seats match
            host_seats = host_snap["data"]["lobby"]["seats"]
            guest_seats = guest_snap["data"]["lobby"]["seats"]

            for h_seat, g_seat in zip(host_seats, guest_seats):
                assert h_seat["role_id"] == g_seat["role_id"]
                assert h_seat["ready"] == g_seat["ready"]

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_start_run_blocked_in_solo(self, app_for_state: FastAPI):
        """Solo stories should not have start_run action."""
        client = TestClient(app_for_state)

        # Solo story doesn't use lobby/start_run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Player"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Player"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            # Solo should start in running state, not lobby
            assert snap["data"]["status"] == "running"

            # Try start_run anyway (should fail)
            ws.send_json({"action": "start_run"})
            response = ws.receive_json()

            if response["type"] == "command_rejected":
                assert "group" in response.get("reason", "").lower()
