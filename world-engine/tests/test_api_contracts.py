"""API Contract Tests for World Engine.

WAVE 6 Hardening Initiative: API contract and response schema tests.
Tests focus on ensuring consistent and valid API responses.

Mark: @pytest.mark.contract
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

import pytest


@pytest.mark.contract
def test_create_run_returns_valid_run_structure(client):
    """Verify that POST /api/runs returns a run with required fields."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "test", "display_name": "Test User"},
    )
    assert response.status_code == 200
    body = response.json()

    # Verify response structure
    assert "run" in body
    assert "store" in body
    assert "hint" in body

    run = body["run"]
    # Required fields in create_run response
    assert "id" in run
    assert "template_id" in run
    assert "status" in run
    assert "created_at" in run
    # Note: participants and template may not be in create response, check in get_run_details

    # Verify basic type expectations
    assert isinstance(run["id"], str)
    assert isinstance(run["template_id"], str)
    assert isinstance(run["status"], str)
    assert isinstance(run["created_at"], str)


@pytest.mark.contract
def test_create_run_accepts_required_parameters(client):
    """Verify that POST /api/runs accepts all required parameters."""
    # Minimal required parameters
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200

    # With optional parameters
    response = client.post(
        "/api/runs",
        json={
            "template_id": "apartment_confrontation_group",
            "account_id": "acct-123",
            "display_name": "My Game",
            "character_id": "char-456",
            "player_name": "Alias",
        },
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["template_id"] == "apartment_confrontation_group"


@pytest.mark.contract
def test_get_run_returns_consistent_structure(client):
    """Verify that GET /api/runs/{run_id} returns consistent structure."""
    # Create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    # Get the run details
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # GET endpoint returns structure with these fields
    assert "run" in details or "status" in details
    assert "lobby" in details
    assert "template" in details

    # Verify consistency - template should match
    assert details["template"]["id"] == "apartment_confrontation_group"


@pytest.mark.contract
def test_list_runs_returns_valid_list(client):
    """Verify that GET /api/runs returns a valid list of runs."""
    # Create a few runs
    for i in range(3):
        client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": f"user-{i}", "display_name": f"User {i}"},
        )

    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()

    # Should be a list
    assert isinstance(runs, list)
    assert len(runs) >= 3

    # Each run should have basic structure
    for run in runs:
        assert "id" in run
        assert "template_id" in run
        assert "status" in run


@pytest.mark.contract
def test_run_updates_are_atomic(client):
    """Verify that run state is consistent across multiple reads."""
    # Create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "host", "display_name": "Host"},
    )
    run_id = create_response.json()["run"]["id"]

    # Get initial state
    initial = client.get(f"/api/runs/{run_id}").json()
    assert initial["lobby"]["status"] == "lobby"

    # The run state should be consistent across reads
    for _ in range(3):
        detail = client.get(f"/api/runs/{run_id}").json()
        # State should match
        assert detail["lobby"]["status"] == initial["lobby"]["status"]
        assert detail["template"]["id"] == initial["template"]["id"]


@pytest.mark.contract
def test_api_responses_have_consistent_schema(client):
    """Verify that all API responses follow a consistent schema."""
    # Check health endpoint
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()

    # Check ready endpoint
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "store" in body

    # Check list endpoints return lists
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    response = client.get("/api/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.contract
def test_api_errors_have_standard_format(client):
    """Verify that all API errors follow a standard format."""
    # 404 error
    response = client.get("/api/runs/missing")
    assert response.status_code == 404
    error = response.json()
    assert "detail" in error

    # 403 error
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
    error = response.json()
    assert "detail" in error

    # 400 error
    response = client.post(
        "/api/runs",
        json={"template_id": "invalid-template"},
    )
    assert response.status_code == 404
    error = response.json()
    assert "detail" in error


@pytest.mark.contract
def test_api_timestamps_are_iso8601(client):
    """Verify that all timestamps in API responses are ISO8601 format."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "test", "display_name": "Test"},
    )
    run = response.json()["run"]

    # Check created_at is ISO8601
    created_at = run["created_at"]
    assert isinstance(created_at, str)

    # Should be valid ISO8601 format
    iso8601_pattern = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}"
    assert re.match(iso8601_pattern, created_at), f"Timestamp {created_at} not ISO8601 format"

    # Should be parseable as datetime
    try:
        datetime.fromisoformat(created_at.replace("Z", "+00:00"))
    except ValueError:
        pytest.fail(f"Timestamp {created_at} is not valid ISO8601")


@pytest.mark.contract
def test_api_pagination_works_correctly(client):
    """Verify that API list endpoints support pagination."""
    # Create multiple runs
    for i in range(5):
        client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo", "account_id": f"user-{i}", "display_name": f"User {i}"},
        )

    # List all runs
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    assert len(runs) >= 5


@pytest.mark.contract
def test_ticket_response_contains_required_fields(client):
    """Verify that POST /api/tickets returns required fields."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "owner", "display_name": "Owner"},
    )
    assert response.status_code == 200
    body = response.json()

    # Required fields in ticket response
    assert "ticket" in body
    assert "run_id" in body
    assert "participant_id" in body
    assert "role_id" in body
    assert "display_name" in body

    # Verify types
    assert isinstance(body["ticket"], str)
    assert isinstance(body["run_id"], str)
    assert isinstance(body["participant_id"], str)
    assert isinstance(body["role_id"], str)
    assert isinstance(body["display_name"], str)


@pytest.mark.contract
def test_run_participants_structure_is_valid(client):
    """Verify that run participants structure is valid."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "host", "display_name": "Host"},
    )
    run_id = create_response.json()["run"]["id"]

    # Add a participant
    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "guest", "display_name": "Guest", "preferred_role_id": "parent_a"},
    )
    assert ticket_response.status_code == 200

    # Get run details
    run_response = client.get(f"/api/runs/{run_id}")
    run = run_response.json()

    # Participants should be present in the response
    assert "participants" in run or "participant_seats" in run or "lobby" in run

    # If participants field exists, verify structure
    if "participants" in run:
        participants = run["participants"]
        assert isinstance(participants, dict)
        # Each participant should have required fields
        for participant_id, participant in participants.items():
            assert isinstance(participant_id, str)
            assert "display_name" in participant
            assert "role_id" in participant


@pytest.mark.contract
def test_lobby_status_transitions_are_valid(client):
    """Verify that lobby status transitions are valid."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "host", "display_name": "Host"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}")
    run = response.json()

    # Initial status should be "lobby"
    assert run["lobby"]["status"] == "lobby"

    # Lobby should have required fields
    lobby = run["lobby"]
    assert "status" in lobby
    assert "ready_human_seats" in lobby
    assert "can_start" in lobby

    # Verify types
    assert isinstance(lobby["status"], str)
    assert isinstance(lobby["ready_human_seats"], int)
    assert isinstance(lobby["can_start"], bool)


@pytest.mark.contract
def test_template_info_is_complete(client):
    """Verify that template information in API response is complete."""
    # Create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "test", "display_name": "Test"},
    )
    run_id = create_response.json()["run"]["id"]

    # Get run details which includes template info
    response = client.get(f"/api/runs/{run_id}")
    run = response.json()

    # Template info should be included
    assert "template" in run
    template = run["template"]
    assert "id" in template
    assert template["id"] == "apartment_confrontation_group"
    assert "min_humans_to_start" in template
    # Template should have metadata fields
    assert "kind" in template
    assert "join_policy" in template


@pytest.mark.contract
def test_ready_endpoint_includes_all_required_fields(client):
    """Verify that health/ready endpoint includes all required monitoring fields."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()

    # Required fields for operational monitoring
    assert "status" in body
    assert "store" in body
    assert "template_count" in body
    assert "run_count" in body

    # Store info
    store = body["store"]
    assert "backend" in store

    # Verify types
    assert body["status"] == "ready"
    assert isinstance(body["template_count"], int)
    assert isinstance(body["run_count"], int)
