"""
WAVE 7: WebSocket Rejoin Tests

Tests for WebSocket reconnection/rejoin capability:
- Disconnect and reconnect with same ticket
- Rejoin after timeout (stale rejoin)
- Foreign participant rejoin (wrong character)
- Seat ownership preservation
- State consistency across rejoin
- Normal disconnect vs abrupt close
"""
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from conftest import receive_until_snapshot


@pytest.fixture
def app_for_rejoin(tmp_path: Path) -> FastAPI:
    """Build app for rejoin tests."""
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


class TestWebSocketRejoin:
    """Test reconnection and rejoin after disconnect."""

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_disconnect_and_reconnect_with_same_ticket(self, app_for_rejoin: FastAPI):
        """Disconnect and reconnect with same ticket should maintain participant state."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Create ticket
        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # First connection
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws1:
            snap1 = ws1.receive_json()
            participant_id_1 = snap1["data"]["viewer_participant_id"]
            assert snap1["type"] == "snapshot"

        # Reconnect with same ticket
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws2:
            snap2 = ws2.receive_json()
            participant_id_2 = snap2["data"]["viewer_participant_id"]
            assert snap2["type"] == "snapshot"

        # Should get same participant back
        assert participant_id_1 == participant_id_2

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_reconnect_preserves_ready_state(self, app_for_rejoin: FastAPI):
        """Participant's ready state should persist across disconnect/reconnect."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Connect and mark as ready
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot
            ws.send_json({"action": "set_ready", "ready": True})
            ready_snap = receive_until_snapshot(ws, lambda data: data["lobby"]["ready_human_seats"] == 1)
            assert ready_snap["data"]["lobby"]["ready_human_seats"] == 1

        # Reconnect and verify ready state persists
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap = receive_until_snapshot(ws, lambda data: "lobby" in data and data["lobby"] is not None)
            # Host should still be marked ready in the lobby
            assert snap["data"]["lobby"]["ready_human_seats"] == 1

    @pytest.mark.websocket
    @pytest.mark.security
    def test_rejoin_with_stale_ticket_fails(self, app_for_rejoin: FastAPI):
        """Attempt to rejoin after ticket expiration should fail."""
        client = TestClient(app_for_rejoin)
        ticket_manager = app_for_rejoin.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get participant context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Issue ticket that is already expired (ttl_seconds=-1 means exp is in past)
        # This tests that expired tickets are rejected on connection
        short_ttl_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
        }, ttl_seconds=-10)  # Already expired

        # Try to connect with already-expired ticket
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={short_ttl_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_foreign_participant_rejoin_fails(self, app_for_rejoin: FastAPI):
        """Participant with wrong identity cannot take over another's seat."""
        client = TestClient(app_for_rejoin)
        ticket_manager = app_for_rejoin.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get host context
        host_context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Create valid ticket for host
        host_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": host_context["participant_id"],
            "account_id": "1",
        })

        # Connect as host
        with client.websocket_connect(f"/ws?ticket={host_ticket}") as ws:
            ws.receive_json()

        # Try to reconnect as different account with host's participant_id
        foreign_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": host_context["participant_id"],
            "account_id": "999",  # Different account!
        })

        # Should be rejected
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={foreign_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_wrong_character_rejoin_fails(self, app_for_rejoin: FastAPI):
        """Participant with different character_id cannot rejoin."""
        client = TestClient(app_for_rejoin)
        ticket_manager = app_for_rejoin.state.ticket_manager

        # Create run with character_id
        run_response = client.post(
            "/api/runs",
            json={
                "template_id": "apartment_confrontation_group",
                "account_id": "1",
                "display_name": "Host",
                "character_id": "char-1",
            },
        )
        run_id = run_response.json()["run"]["id"]

        # Get context
        context = client.post(
            "/api/internal/join-context",
            json={
                "run_id": run_id,
                "account_id": "1",
                "display_name": "Host",
                "character_id": "char-1",
            },
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Valid ticket with char-1
        valid_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
            "character_id": "char-1",
        })

        # Connect first time
        with client.websocket_connect(f"/ws?ticket={valid_ticket}") as ws:
            ws.receive_json()

        # Try to reconnect with different character_id
        wrong_char_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
            "character_id": "char-999",  # Different character!
        })

        # Should be rejected
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_char_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_seat_ownership_preserved_across_rejoin(self, app_for_rejoin: FastAPI):
        """Participant's lobby seat ownership should persist across disconnect/reconnect."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Connect and get seat assignment
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap1 = receive_until_snapshot(ws, lambda data: "lobby" in data and data["lobby"] is not None)
            seat1_role = snap1["data"]["lobby"]["seats"][0]["role_id"]
            seat1_occupant = snap1["data"]["lobby"]["seats"][0]["occupant_display_name"]

        # Disconnect and reconnect
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap2 = receive_until_snapshot(ws, lambda data: "lobby" in data and data["lobby"] is not None)
            seat2_role = snap2["data"]["lobby"]["seats"][0]["role_id"]
            seat2_occupant = snap2["data"]["lobby"]["seats"][0]["occupant_display_name"]

        # Seat assignment should be unchanged
        assert seat1_role == seat2_role
        assert seat1_occupant == seat2_occupant

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_state_consistency_across_rejoin(self, app_for_rejoin: FastAPI):
        """Game state should remain consistent across disconnect/reconnect."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # First connection - capture state
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap1 = ws.receive_json()
            state1 = {
                "beat_id": snap1["data"]["beat_id"],
                "tension": snap1["data"]["tension"],
                "flags": snap1["data"]["flags"],
                "viewer_room_id": snap1["data"]["viewer_room_id"],
            }

        # Reconnect immediately - state should match
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snap2 = ws.receive_json()
            state2 = {
                "beat_id": snap2["data"]["beat_id"],
                "tension": snap2["data"]["tension"],
                "flags": snap2["data"]["flags"],
                "viewer_room_id": snap2["data"]["viewer_room_id"],
            }

        assert state1 == state2

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_normal_disconnect_reconnect(self, app_for_rejoin: FastAPI):
        """Normal close (via context manager) and reconnect should work."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Normal close by exiting context
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            msg1 = ws.receive_json()
            assert msg1["type"] == "snapshot"
        # WebSocket closed normally here

        # Should be able to reconnect
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            msg2 = ws.receive_json()
            assert msg2["type"] == "snapshot"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_concurrent_rejoin_attempts(self, app_for_rejoin: FastAPI):
        """Multiple concurrent rejoin attempts should each get independent connections."""
        client = TestClient(app_for_rejoin)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Initial connection
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()

        # Concurrent rejoin attempts should work
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws1, \
             client.websocket_connect(f"/ws?ticket={ticket}") as ws2:

            msg1 = ws1.receive_json()
            msg2 = ws2.receive_json()

            assert msg1["type"] == "snapshot"
            assert msg2["type"] == "snapshot"
            # Both should show same participant connected
            assert msg1["data"]["viewer_participant_id"] == msg2["data"]["viewer_participant_id"]

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_rejoin_after_guest_joins(self, app_for_rejoin: FastAPI):
        """Host rejoin after guest joins should reflect updated state."""
        client = TestClient(app_for_rejoin)

        # Create run
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

        # Host and guest connect concurrently
        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            snap1 = receive_until_snapshot(host_ws, lambda data: "lobby" in data and data["lobby"] is not None)
            guest_ws.receive_json()

            # Both should see 2 occupied seats
            occupied1 = snap1["data"]["lobby"]["occupied_human_seats"]
            assert occupied1 == 2

            # Disconnect host
        # Host is now offline, guest still online

        # Host reconnects after guest already joined
        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws:
            snap2 = receive_until_snapshot(host_ws, lambda data: "lobby" in data and data["lobby"] is not None)
            occupied2 = snap2["data"]["lobby"]["occupied_human_seats"]

        # Host should still see guest present (2 occupied)
        assert occupied2 == 2

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_participant_marked_disconnected_on_graceful_close(self, app_for_rejoin: FastAPI):
        """When WebSocket closes gracefully, participant should be marked disconnected."""
        client = TestClient(app_for_rejoin)
        manager = app_for_rejoin.state.manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get context to identify which participant will connect
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()
        participant_id = context["participant_id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        # Connect
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()
            # While connected, participant should be marked connected
            assert manager.get_instance(run_id).participants[participant_id].connected

        # After graceful close (exit context), participant should be marked disconnected
        assert not manager.get_instance(run_id).participants[participant_id].connected

    @pytest.mark.websocket
    @pytest.mark.security
    def test_reconnect_with_wrong_run_id_fails(self, app_for_rejoin: FastAPI):
        """Cannot reconnect to wrong run even with valid ticket for another run."""
        client = TestClient(app_for_rejoin)
        ticket_manager = app_for_rejoin.state.ticket_manager

        # Create two runs
        run1_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host1"},
        )
        run1_id = run1_response.json()["run"]["id"]

        run2_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": "2", "display_name": "Host2"},
        )
        run2_id = run2_response.json()["run"]["id"]

        # Get contexts
        context1 = client.post(
            "/api/internal/join-context",
            json={"run_id": run1_id, "account_id": "1", "display_name": "Host1"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        context2 = client.post(
            "/api/internal/join-context",
            json={"run_id": run2_id, "account_id": "2", "display_name": "Host2"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Create ticket for run1
        ticket_for_run1 = ticket_manager.issue({
            "run_id": run1_id,
            "participant_id": context1["participant_id"],
            "account_id": "1",
        })

        # Connect to run1 works
        with client.websocket_connect(f"/ws?ticket={ticket_for_run1}") as ws:
            ws.receive_json()

        # Now try to use run1 ticket on run2 endpoint (fake by trying different participant)
        # Create a cross-run ticket manipulation
        cross_run_ticket = ticket_manager.issue({
            "run_id": run2_id,  # Different run!
            "participant_id": context1["participant_id"],  # But same participant from run1
            "account_id": "1",
        })

        # Should be rejected because participant doesn't exist in run2
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={cross_run_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")
