from __future__ import annotations

import base64
import json

import pytest

import app.auth.tickets as tickets_module



def test_ticket_roundtrip_preserves_payload_fields():
    manager = tickets_module.TicketManager("unit-test-secret")

    token = manager.issue(
        {
            "run_id": "run-1",
            "participant_id": "p-1",
            "account_id": "acct-1",
            "role_id": "citizen",
        },
        ttl_seconds=60,
    )

    payload = manager.verify(token)
    assert payload["run_id"] == "run-1"
    assert payload["participant_id"] == "p-1"
    assert payload["account_id"] == "acct-1"
    assert payload["role_id"] == "citizen"
    assert payload["exp"] >= payload["iat"]



def test_ticket_rejects_malformed_token():
    manager = tickets_module.TicketManager("unit-test-secret")

    with pytest.raises(tickets_module.TicketError, match="Malformed ticket"):
        manager.verify("not-a-valid-ticket")



def test_ticket_rejects_tampered_payload():
    manager = tickets_module.TicketManager("unit-test-secret")
    token = manager.issue({"run_id": "run-1", "participant_id": "p-1"}, ttl_seconds=60)

    decoded = base64.urlsafe_b64decode(token.encode("ascii"))
    raw, provided_sig = decoded.rsplit(b".", 1)
    payload = json.loads(raw.decode("utf-8"))
    payload["participant_id"] = "p-2"
    tampered_raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    tampered_token = base64.urlsafe_b64encode(tampered_raw + b"." + provided_sig).decode("ascii")

    with pytest.raises(tickets_module.TicketError, match="Invalid signature"):
        manager.verify(tampered_token)



def test_ticket_rejects_expired_token():
    manager = tickets_module.TicketManager("unit-test-secret")
    token = manager.issue({"run_id": "run-1", "participant_id": "p-1"}, ttl_seconds=-1)

    with pytest.raises(tickets_module.TicketError, match="Expired ticket"):
        manager.verify(token)
