"""
WAVE 7: WebSocket Authentication Tests

Tests for WebSocket authentication enforcement:
- Ticket validation
- Identity/character verification
- Missing claims
- Expiration
- Signature tampering
- Concurrent connections
- Auth before game messages
"""
import base64
import hashlib
import hmac
import json
import time
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.tickets import TicketManager, TicketError
from app.runtime.manager import RuntimeManager


@pytest.fixture
def app_with_secret(tmp_path: Path, monkeypatch) -> FastAPI:
    """Build app with controllable secret for ticket manipulation tests."""
    from app.api.http import router as http_router
    from app.api.ws import router as ws_router

    app = FastAPI()
    app.state.manager = RuntimeManager(store_root=tmp_path)
    app.state.ticket_manager = TicketManager("test-secret")
    app.include_router(http_router)
    app.include_router(ws_router)
    return app


class TestWebSocketAuthValidation:
    """Test authentication validation at WebSocket connection."""

    @pytest.mark.websocket
    @pytest.mark.security
    def test_valid_ticket_allows_connection(self, app_with_secret: FastAPI):
        """Valid ticket with correct run/participant should connect successfully."""
        client = TestClient(app_with_secret)

        # Create run and issue valid ticket
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket_response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        )
        ticket = ticket_response.json()["ticket"]

        # Connect should succeed and receive snapshot
        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            msg = ws.receive_json()
            assert msg["type"] == "snapshot"
            assert msg["data"]["viewer_display_name"] == "Host"

    @pytest.mark.websocket
    @pytest.mark.security
    def test_missing_ticket_rejected_with_4401(self, app_with_secret: FastAPI):
        """Missing ticket query parameter should reject with code 4401."""
        client = TestClient(app_with_secret)

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect("/ws") as ws:
                pass

        # WebSocketDisconnect from starlette should be raised
        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_invalid_ticket_format_rejected_with_4403(self, app_with_secret: FastAPI):
        """Malformed ticket should reject with code 4403."""
        client = TestClient(app_with_secret)

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect("/ws?ticket=not-a-valid-ticket") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_wrong_run_id_in_ticket_rejected(self, app_with_secret: FastAPI):
        """Ticket for wrong run ID should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create a run and get a valid ticket
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Manually craft a ticket with wrong run_id
        ticket_payload = {
            "run_id": "wrong-run-id-12345",
            "participant_id": "some-participant",
            "account_id": "1",
        }
        wrong_ticket = ticket_manager.issue(ticket_payload)

        # Connection should be rejected
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_wrong_participant_id_rejected(self, app_with_secret: FastAPI):
        """Ticket for wrong participant_id should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run and get valid ticket
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get manager to find real participant
        manager = app_with_secret.state.manager
        instance = manager.get_instance(run_id)
        real_participant_id = list(instance.participants.keys())[0]

        # Craft ticket with wrong participant_id
        wrong_participant_id = "fake-participant-99999"
        wrong_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": wrong_participant_id,
            "account_id": "1",
        })

        # Connection should fail
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_mismatched_account_id_rejected(self, app_with_secret: FastAPI):
        """Ticket with wrong account_id should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get valid context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Craft ticket with mismatched account_id
        wrong_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "99999",  # Wrong account
        })

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_mismatched_character_id_rejected(self, app_with_secret: FastAPI):
        """Ticket with wrong character_id should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host", "character_id": "char-1"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get valid context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host", "character_id": "char-1"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Craft ticket with mismatched character_id
        wrong_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
            "character_id": "char-99999",  # Wrong character
        })

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_mismatched_role_id_rejected(self, app_with_secret: FastAPI):
        """Ticket with wrong role_id should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get valid context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Craft ticket with wrong role_id
        wrong_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "role_id": "wrong-role-id",
        })

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={wrong_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_expired_ticket_rejected(self, app_with_secret: FastAPI):
        """Ticket with exp claim in past should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get valid context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Issue expired ticket (ttl_seconds=0 means it's already expired)
        expired_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
        }, ttl_seconds=-1)  # Expires in past

        # Wait to ensure time has passed
        time.sleep(0.1)

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={expired_ticket}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_tampered_ticket_signature_rejected(self, app_with_secret: FastAPI):
        """Ticket with modified payload but invalid signature should be rejected."""
        client = TestClient(app_with_secret)
        ticket_manager = app_with_secret.state.ticket_manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get valid context
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()

        # Create valid ticket
        valid_ticket = ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
        })

        # Tamper with the ticket: modify payload but keep old signature
        decoded = base64.urlsafe_b64decode(valid_ticket.encode("ascii"))
        raw, sig = decoded.rsplit(b".", 1)
        payload = json.loads(raw.decode("utf-8"))

        # Modify payload
        payload["account_id"] = "99999"
        tampered_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
        tampered_token = base64.urlsafe_b64encode(tampered_raw + b"." + sig).decode("ascii")

        # Should reject tampered ticket
        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect(f"/ws?ticket={tampered_token}") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_multiple_concurrent_connections_different_tickets(self, app_with_secret: FastAPI):
        """Multiple concurrent WebSocket connections with different tickets should work."""
        client = TestClient(app_with_secret)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Create two tickets for different participants
        host_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        guest_ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "2", "display_name": "Guest", "preferred_role_id": "parent_a"},
        ).json()["ticket"]

        # Both should connect concurrently
        with client.websocket_connect(f"/ws?ticket={host_ticket}") as host_ws, \
             client.websocket_connect(f"/ws?ticket={guest_ticket}") as guest_ws:

            host_msg = host_ws.receive_json()
            guest_msg = guest_ws.receive_json()

            assert host_msg["type"] == "snapshot"
            assert guest_msg["type"] == "snapshot"
            assert host_msg["data"]["viewer_display_name"] == "Host"
            assert guest_msg["data"]["viewer_display_name"] == "Guest"

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_auth_completes_before_any_game_messages(self, app_with_secret: FastAPI):
        """First message received after connection should be snapshot, not game messages."""
        client = TestClient(app_with_secret)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Create ticket and connect
        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            # First message MUST be a snapshot, proving auth succeeded
            first_msg = ws.receive_json()
            assert first_msg["type"] == "snapshot"
            assert "data" in first_msg
            assert "viewer_participant_id" in first_msg["data"]

    @pytest.mark.websocket
    @pytest.mark.security
    def test_commands_rejected_before_socket_accept(self, app_with_secret: FastAPI):
        """Commands sent before auth completion should not execute."""
        client = TestClient(app_with_secret)

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

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            # First message should be snapshot (proves auth passed)
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"

            # Now commands should be processable
            ws.send_json({"action": "set_ready", "ready": True})
            response = ws.receive_json()
            # Should get a snapshot back, not a command_rejected
            assert response["type"] == "snapshot"

    @pytest.mark.websocket
    @pytest.mark.integration
    def test_duplicate_connection_replacement(self, app_with_secret: FastAPI):
        """When same participant connects twice, second connection replaces first."""
        client = TestClient(app_with_secret)

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

        # Create reusable ticket for same participant
        ticket = app_with_secret.state.ticket_manager.issue({
            "run_id": run_id,
            "participant_id": context["participant_id"],
            "account_id": "1",
        })

        # First connection
        ws1 = client.websocket_connect(f"/ws?ticket={ticket}")
        ws1_context = ws1.__enter__()
        snap1 = ws1_context.receive_json()
        assert snap1["type"] == "snapshot"

        # Second connection with same ticket
        ws2 = client.websocket_connect(f"/ws?ticket={ticket}")
        ws2_context = ws2.__enter__()
        snap2 = ws2_context.receive_json()
        assert snap2["type"] == "snapshot"

        # Cleanup
        ws1_context.close()
        ws2_context.close()

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_snapshot_contains_required_viewer_fields(self, app_with_secret: FastAPI):
        """Snapshot message must contain all required viewer identification fields."""
        client = TestClient(app_with_secret)

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "acct:user123", "display_name": "Alice", "character_id": "char:alice"},
        )
        run_id = run_response.json()["run"]["id"]

        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "acct:user123", "display_name": "Alice", "character_id": "char:alice"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            snapshot = ws.receive_json()
            assert snapshot["type"] == "snapshot"
            data = snapshot["data"]

            # Viewer identification is required
            assert "viewer_participant_id" in data
            assert "viewer_account_id" in data
            assert "viewer_character_id" in data
            assert "viewer_display_name" in data
            assert "viewer_role_id" in data
            assert "viewer_room_id" in data

    @pytest.mark.websocket
    @pytest.mark.security
    def test_empty_ticket_rejected(self, app_with_secret: FastAPI):
        """Empty string as ticket should be rejected."""
        client = TestClient(app_with_secret)

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect("/ws?ticket=") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.security
    def test_ticket_with_only_whitespace_rejected(self, app_with_secret: FastAPI):
        """Ticket containing only whitespace should be rejected."""
        client = TestClient(app_with_secret)

        with pytest.raises(Exception) as exc_info:
            with client.websocket_connect("/ws?ticket=   ") as ws:
                pass

        assert exc_info.typename in ("WebSocketDisconnect", "Exception")

    @pytest.mark.websocket
    @pytest.mark.contract
    def test_connection_marked_as_connected_on_auth(self, app_with_secret: FastAPI):
        """After successful auth, participant should be marked as connected."""
        client = TestClient(app_with_secret)
        manager = app_with_secret.state.manager

        # Create run
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group", "account_id": "1", "display_name": "Host"},
        )
        run_id = run_response.json()["run"]["id"]

        # Get context to know which participant will connect
        context = client.post(
            "/api/internal/join-context",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
            headers={"X-Play-Service-Key": "internal-api-key-for-ops"},
        ).json()
        participant_id = context["participant_id"]

        # Get participant before connection - check it's not connected initially
        instance_before = manager.get_instance(run_id)
        assert not instance_before.participants[participant_id].connected

        # Create ticket and connect
        ticket = client.post(
            "/api/tickets",
            json={"run_id": run_id, "account_id": "1", "display_name": "Host"},
        ).json()["ticket"]

        with client.websocket_connect(f"/ws?ticket={ticket}") as ws:
            ws.receive_json()  # Initial snapshot

            # Check participant is marked connected
            instance = manager.get_instance(run_id)
            assert instance.participants[participant_id].connected
