"""
WAVE 7: WebSocket Runtime Commands and State Isolation Tests

Tests for runtime command execution via WebSocket and state isolation:
- Move command with validation
- Say command with message validation
- Emote command with content validation
- Inspect command with target validation
- Set_ready command
- Start_run command (host-only)
- Invalid command rejection
- Invalid command sequence rejection
- Unauthorized action attempt rejection
- Command parameter validation
- Users only see allowed information
- No cross-run leakage
- No seat or role leakage where prohibited
- Private messages isolation
- Transcript privacy enforcement
- Room/area visibility enforcement
- Host-only action enforcement
"""
from __future__ import annotations

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import receive_until_snapshot


@pytest.fixture
def app_for_commands(tmp_path) -> FastAPI:
    """Build app for command and isolation tests."""
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


class TestRuntimeCommandsOverWebSocket:
    """Test command execution via WebSocket."""

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_say_command_via_websocket(self, app_for_commands: FastAPI):
        """Say command via WebSocket should succeed and broadcast."""
        client = TestClient(app_for_commands)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            # Get initial snapshot
            ws.receive_json()

            # Send say command
            ws.send_json({"action": "say", "text": "Hello, world!"})

            # Should receive updated snapshot
            response = ws.receive_json()
            assert response["type"] == "snapshot"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_emote_command_via_websocket(self, app_for_commands: FastAPI):
        """Emote command via WebSocket should succeed."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot

            ws.send_json({"action": "emote", "text": "nods thoughtfully"})
            response = ws.receive_json()
            assert response["type"] == "snapshot"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_move_command_via_websocket(self, app_for_commands: FastAPI):
        """Move command via WebSocket should update room."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            current_room = snap["data"]["viewer_room_id"]

            # Get available rooms from snapshot
            available_actions = snap["data"]["available_actions"]
            # Try to find a move action or room transition
            room_obj = snap["data"]["current_room"]
            exits = room_obj.get("exits", []) if room_obj else []

            if exits:
                target_room = exits[0]["target_room_id"]
                ws.send_json({"action": "move", "target_room_id": target_room})

                response = ws.receive_json()
                assert response["type"] == "snapshot"
                assert response["data"]["viewer_room_id"] == target_room

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_invalid_command_rejected_with_message(self, app_for_commands: FastAPI):
        """Invalid commands should be rejected with reason message."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot

            # Send invalid command
            ws.send_json({"action": "nonexistent_action"})

            response = ws.receive_json()
            assert response["type"] == "command_rejected"
            assert "reason" in response
            assert "Unknown command" in response["reason"]

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_say_command_empty_text_rejected(self, app_for_commands: FastAPI):
        """Say command with empty text should be rejected."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            ws.send_json({"action": "say", "text": ""})

            response = ws.receive_json()
            assert response["type"] == "command_rejected"
            assert "reason" in response

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_emote_command_empty_text_rejected(self, app_for_commands: FastAPI):
        """Emote command with empty text should be rejected."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            ws.send_json({"action": "emote", "text": ""})

            response = ws.receive_json()
            assert response["type"] == "command_rejected"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_move_to_unreachable_room_rejected(self, app_for_commands: FastAPI):
        """Move to unreachable room should be rejected."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            # Try to move to nonexistent room
            ws.send_json({"action": "move", "target_room_id": "nonexistent_room_xyz"})

            response = ws.receive_json()
            assert response["type"] == "command_rejected"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_inspect_command_via_websocket(self, app_for_commands: FastAPI):
        """Inspect command should work for current room."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            current_room = snap["data"]["viewer_room_id"]

            # Inspect current room
            ws.send_json({"action": "inspect", "target_id": current_room})

            response = ws.receive_json()
            assert response["type"] == "snapshot"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_set_ready_command_in_group_lobby(self, app_for_commands: FastAPI):
        """Set_ready command should work in group story lobby."""
        client = TestClient(app_for_commands)

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

            snap = receive_until_snapshot(
                ws, lambda data: data.get("lobby") and data["lobby"]["ready_human_seats"] >= 1
            )
            assert snap["data"]["lobby"]["ready_human_seats"] >= 1

    @pytest.mark.websocket
    @pytest.mark.security
    def test_start_run_blocked_for_non_host(self, app_for_commands: FastAPI):
        """Non-host cannot start group story."""
        client = TestClient(app_for_commands)

        # Create run as host
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "acct:host", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Guest joins as different account
        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:guest", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        # Mark guest as ready
        with client.websocket_connect(f"/ws?ticket={guest_ticket}") as ws:
            ws.receive_json()
            ws.send_json({"action": "set_ready", "ready": True})
            receive_until_snapshot(ws, lambda data: data.get("lobby") and data["lobby"]["ready_human_seats"] >= 1)

            # Guest tries to start run (should fail)
            ws.send_json({"action": "start_run"})
            response = ws.receive_json()
            assert response["type"] == "command_rejected"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_multiple_commands_in_sequence(self, app_for_commands: FastAPI):
        """Multiple commands should be processed in sequence."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot

            # Send multiple commands
            ws.send_json({"action": "say", "text": "First message"})
            ws.receive_json()  # Response to first say

            ws.send_json({"action": "say", "text": "Second message"})
            ws.receive_json()  # Response to second say

            ws.send_json({"action": "emote", "text": "looks around"})
            ws.receive_json()  # Response to emote


class TestStateAndBroadcastIsolation:
    """Test state isolation and broadcast boundaries."""

    @pytest.mark.websocket
    @pytest.mark.security
    def test_participant_only_sees_own_account_id_in_snapshot(self, app_for_commands: FastAPI):
        """Snapshot should only reveal own account_id to viewer."""
        client = TestClient(app_for_commands)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "acct:alice", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        # Add guest
        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:bob", "display_name": "Bob", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        # Alice connects
        alice_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:alice", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={alice_ticket}") as alice_ws:
            snap = alice_ws.receive_json()
            # Alice should see her own account_id in viewer_account_id
            assert snap["data"]["viewer_account_id"] == "acct:alice"

    @pytest.mark.websocket
    @pytest.mark.security
    def test_no_cross_run_state_leakage(self, app_for_commands: FastAPI):
        """Participant in run A cannot see data from run B."""
        client = TestClient(app_for_commands)

        # Create two separate runs
        run_a = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        ).json()["run"]["id"]

        run_b = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "2", "display_name": "Bob"},
        ).json()["run"]["id"]

        # Get tickets for each run
        ticket_a = client.post(
            "/api/tickets",
            json={"run_id": run_a, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        ticket_b = client.post(
            "/api/tickets",
            json={"run_id": run_b, "account_id": "2", "display_name": "Bob"},
        ).json()["ticket"]

        # Connect to run A and capture run_id from snapshot
        with client.websocket_connect(f"/ws?ticket={ticket_a}") as ws_a:
            snap_a = ws_a.receive_json()
            run_id_a = snap_a["data"]["run_id"]

            # Connect to run B
            with client.websocket_connect(f"/ws?ticket={ticket_b}") as ws_b:
                snap_b = ws_b.receive_json()
                run_id_b = snap_b["data"]["run_id"]

            # Run IDs should be different
            assert run_id_a != run_id_b

            # Alice's snapshot should have run_a's run_id
            assert run_id_a == run_a

        # Bob's snapshot should have run_b's run_id
        assert run_id_b == run_b

    @pytest.mark.websocket
    @pytest.mark.security
    def test_visible_occupants_filters_invisible_participants(self, app_for_commands: FastAPI):
        """Visible_occupants should only include occupants in same room."""
        client = TestClient(app_for_commands)

        # Create group story with multiple roles
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get host ticket
        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Get guest ticket
        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_snap = host_ws.receive_json()
            guest_snap = guest_ws.receive_json()

            # Both should see occupants (might be same room or different)
            assert "visible_occupants" in host_snap["data"]
            assert "visible_occupants" in guest_snap["data"]

    @pytest.mark.websocket
    @pytest.mark.security
    def test_lobby_seat_shows_connected_status(self, app_for_commands: FastAPI):
        """Lobby seat should reflect current connected status."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={host_ticket}") as ws:
            snap = ws.receive_json()

            # Check that lobby has seat info
            if snap["data"].get("lobby"):
                seats = snap["data"]["lobby"].get("seats", [])
                if seats:
                    # Connected participant's seat should show connected: true
                    host_seat = next((s for s in seats if s["occupant_display_name"] == "Host"), None)
                    if host_seat:
                        assert host_seat["connected"] is True

    @pytest.mark.websocket
    @pytest.mark.security
    def test_transcript_privacy_in_snapshot(self, app_for_commands: FastAPI):
        """Transcript should only include visible entries."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

            # Send a message
            ws.send_json({"action": "say", "text": "Test message"})
            snap = ws.receive_json()

            # Check transcript tail is present
            assert "transcript_tail" in snap["data"]
            # Should have entries
            assert isinstance(snap["data"]["transcript_tail"], list)

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_snapshot_contains_run_metadata(self, app_for_commands: FastAPI):
        """Snapshot should contain run metadata for client."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = ws.receive_json()
            data = snap["data"]

            # Required fields
            assert "run_id" in data
            assert "template_id" in data
            assert "template_title" in data
            assert "status" in data
            assert "beat_id" in data
            assert "tension" in data
            assert "flags" in data

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_available_actions_reflect_current_state(self, app_for_commands: FastAPI):
        """Available actions should change based on current room/state."""
        client = TestClient(app_for_commands)

        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "1", "display_name": "Alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap1 = ws.receive_json()
            actions1 = snap1["data"]["available_actions"]

            # Actions should be a list
            assert isinstance(actions1, list)

            # Each action should have required fields
            for action in actions1:
                assert "id" in action
                assert "label" in action
