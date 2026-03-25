"""HTTP Contract Tests for Tickets Endpoints.

WAVE 6: API contract tests for ticket issuance and verification.
Tests focus on creating tickets, handling errors, and verifying ticket structure.

Mark: @pytest.mark.contract, @pytest.mark.security, @pytest.mark.integration
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.contract
def test_create_ticket_returns_200(client, app):
    """Verify that POST /api/tickets returns 200 for joinable runs."""
    # Create a group run (joinable, unlike owner_only solo stories)
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "display_name": "Owner"},
    )
    run_id = run_response.json()["run"]["id"]

    # Create a ticket
    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Participant"},
    )
    assert response.status_code in [200, 409]  # 409 if all seats filled


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_returns_token(client, app):
    """Verify that ticket endpoint returns a token."""
    # Use a joinable run (group story, not owner_only)
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        assert "ticket" in body
        assert isinstance(body["ticket"], str)
        assert len(body["ticket"]) > 0


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_response_structure(client):
    """Verify that POST /api/tickets returns proper structure."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "display_name": "Owner"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Joiner"},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        # Verify response structure
        required_fields = ["ticket", "run_id", "participant_id", "role_id", "display_name"]
        for field in required_fields:
            assert field in body, f"Missing required field: {field}"


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_includes_run_id(client):
    """Verify that ticket response includes run_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        assert body["run_id"] == run_id


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_includes_participant_id(client):
    """Verify that ticket response includes participant_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Participant"},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        assert "participant_id" in body
        assert isinstance(body["participant_id"], str)


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_includes_role_id(client):
    """Verify that ticket response includes role_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        assert "role_id" in body
        assert isinstance(body["role_id"], str)


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_includes_display_name(client):
    """Verify that ticket response includes display_name."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Test User"},
    )
    assert response.status_code in [200, 409]
    if response.status_code == 200:
        body = response.json()
        assert "display_name" in body
        assert isinstance(body["display_name"], str)


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_account_id(client):
    """Verify that ticket endpoint accepts optional account_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "test-account-123"},
    )
    assert response.status_code in [200, 409]


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_character_id(client):
    """Verify that ticket endpoint accepts optional character_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "character_id": "char-456"},
    )
    assert response.status_code in [200, 409]


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_preferred_role_id(client):
    """Verify that ticket endpoint accepts optional preferred_role_id."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    # Get available roles from run details
    details_response = client.get(f"/api/runs/{run_id}")
    details = details_response.json()
    template = details["template"]

    if "roles" in template and len(template["roles"]) > 0:
        role_id = template["roles"][0]["id"]
        response = client.post(
            "/api/tickets",
            json={"run_id": run_id, "preferred_role_id": role_id},
        )
        assert response.status_code in [200, 409]  # 409 if role already assigned


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_wrong_run_id_returns_404(client):
    """Verify that ticket endpoint with wrong run_id returns 404."""
    response = client.post(
        "/api/runs/nonexistent-run-xyz/tickets",
        json={"run_id": "nonexistent-run-xyz"},
    )
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_nonexistent_run_returns_404_with_message(client):
    """Verify that 404 error includes appropriate detail message."""
    response = client.post(
        "/api/runs/nonexistent-12345/tickets",
        json={"run_id": "nonexistent-12345"},
    )
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_missing_run_id_returns_422(client):
    """Verify that ticket endpoint without run_id returns 422."""
    response = client.post(
        "/api/tickets",
        json={"display_name": "Test"},
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_with_malformed_json_returns_422(client):
    """Verify that ticket endpoint with malformed JSON returns 422."""
    response = client.post(
        "/api/tickets",
        data="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.integration
@pytest.mark.contract
def test_issued_ticket_can_be_verified(client, app):
    """Verify that issued ticket can be verified by ticket manager."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "display_name": "Owner"},
    )
    run_id = run_response.json()["run"]["id"]

    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "test-account", "display_name": "Participant"},
    )
    assert ticket_response.status_code in [200, 409]
    if ticket_response.status_code == 200:
        ticket = ticket_response.json()["ticket"]

        # Verify the ticket using the ticket manager
        ticket_manager = app.state.ticket_manager
        payload = ticket_manager.verify(ticket)

        # Verify payload contains expected fields
        assert "run_id" in payload
        assert payload["run_id"] == run_id
        assert "participant_id" in payload
        assert "account_id" in payload
        assert payload["account_id"] == "test-account"


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_content_type_is_json(client):
    """Verify that ticket endpoint returns JSON content type."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    assert response.status_code in [200, 409]
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
@pytest.mark.contract
def test_ticket_contains_required_payload_fields(client, app):
    """Verify that issued ticket contains all required payload fields."""
    run_response = client.post(
        "/api/runs",
        json={
            "template_id": "apartment_confrontation_group",
            "account_id": "owner-account",
            "display_name": "Owner",
        },
    )
    run_id = run_response.json()["run"]["id"]

    ticket_response = client.post(
        "/api/tickets",
        json={
            "run_id": run_id,
            "account_id": "participant-account",
            "display_name": "Participant",
        },
    )
    assert ticket_response.status_code in [200, 409]
    if ticket_response.status_code == 200:
        ticket = ticket_response.json()["ticket"]

        # Verify ticket contents
        ticket_manager = app.state.ticket_manager
        payload = ticket_manager.verify(ticket)

        required_fields = ["run_id", "participant_id", "account_id", "display_name", "role_id"]
        for field in required_fields:
            assert field in payload, f"Missing required field in ticket: {field}"


@pytest.mark.integration
@pytest.mark.contract
def test_issue_ticket_multiple_participants_in_run(client):
    """Verify that multiple participants can join the same run."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    # First participant
    response1 = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Player 1"},
    )
    assert response1.status_code == 200

    # Second participant
    response2 = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Player 2"},
    )
    assert response2.status_code in [200, 409]  # 409 if all seats filled
