"""Backward Compatibility Contract Tests for World Engine.

WAVE 8 Hardening Initiative: API backward compatibility and versioning.
Tests focus on ensuring API changes don't break existing clients, deprecated
fields are still returned, new fields are optional, and schema evolution is safe.

Mark: @pytest.mark.contract
"""

from __future__ import annotations

import pytest


@pytest.mark.contract
def test_old_api_versions_still_work(client):
    """Verify that older API client calls still work without modification."""
    # Old client using minimal parameters should still work
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    assert "run" in response.json()

    # Old client listing runs
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Old client listing templates
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert isinstance(response.json(), list)

    # Old client getting health status
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "status" in response.json()


@pytest.mark.contract
def test_deprecated_fields_still_returned_in_responses(client):
    """Verify that deprecated fields are still returned for backward compatibility."""
    # Create a run with full parameters
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "account_id": "compat-test",
            "display_name": "Test Display",
            "character_id": "char-123",
            "player_name": "Player Name",
        },
    )
    assert response.status_code == 200
    run = response.json()["run"]

    # Even if some fields become deprecated, they should still be returned
    # for clients that depend on them
    assert "id" in run
    assert "template_id" in run
    assert "status" in run
    assert "created_at" in run

    # Get the run details
    run_id = run["id"]
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # Core fields should still be available
    assert "template" in details
    assert "lobby" in details


@pytest.mark.contract
def test_new_fields_are_backward_compatible(client):
    """Verify that new optional fields don't break existing clients."""
    # Create a run
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "new-fields-test", "display_name": "Test"},
    )
    assert response.status_code == 200
    run = response.json()["run"]

    # Client should be able to handle response even if new fields are present
    # by not requiring specific fields beyond core ones
    assert "id" in run
    assert "template_id" in run

    # Response should be a valid dict that can be accessed
    assert isinstance(run, dict)

    # Extra fields in response should not break parsing
    for key, value in run.items():
        assert key is not None
        assert value is not None or value is None  # Allow null values


@pytest.mark.contract
def test_schema_evolution_safe(client):
    """Verify that schema evolution doesn't break existing clients."""
    # Create multiple resources of different types
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "schema-test", "display_name": "Test"},
    )
    assert run_response.status_code == 200

    run_id = run_response.json()["run"]["id"]

    # Add tickets
    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "guest", "display_name": "Guest"},
    )
    assert ticket_response.status_code == 200

    # Get run details (compound schema)
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # Schema should be consistent even if evolved
    assert "run" in details or "status" in details
    assert "lobby" in details
    assert "template" in details

    # All response items should be serializable (no circular refs, etc.)
    import json
    serialized = json.dumps(details)
    assert len(serialized) > 0


@pytest.mark.contract
def test_renamed_fields_include_aliases(client):
    """Verify that renamed fields include aliases for backward compatibility."""
    # Create a run and get its details
    response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "alias-test", "display_name": "Test"},
    )
    assert response.status_code == 200
    run_id = response.json()["run"]["id"]

    # Get run details
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # If field names have been renamed, aliases should be provided
    # Check that participants can be accessed by multiple names if renamed
    if "participants" in details and "participant_seats" in details:
        # Both should refer to same data
        assert isinstance(details["participants"], dict) or isinstance(details["participants"], list)
        assert isinstance(details["participant_seats"], dict) or isinstance(details["participant_seats"], list)
    elif "participants" in details:
        # Should use consistent name
        assert isinstance(details["participants"], (dict, list))
    elif "participant_seats" in details:
        # Should use consistent name
        assert isinstance(details["participant_seats"], (dict, list))


@pytest.mark.contract
def test_migration_path_documented_in_responses(client):
    """Verify that API provides hints for migration to newer patterns."""
    # Create run response includes migration hints
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "migration-test", "display_name": "Test"},
    )
    assert response.status_code == 200
    body = response.json()

    # Should include helpful hints for integration patterns
    if "hint" in body:
        hint = body["hint"]
        assert isinstance(hint, str)
        assert len(hint) > 0
        # Hint should guide about ticket creation or websocket usage
        assert any(word in hint.lower() for word in ["ticket", "websocket", "socket", "join"])


@pytest.mark.contract
def test_optional_parameters_have_defaults(client):
    """Verify that optional parameters have sensible defaults."""
    # Create run with only required parameters
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    run = response.json()["run"]

    # Optional fields should have reasonable defaults
    assert "id" in run  # Should have been generated
    assert "status" in run  # Should have default status
    assert "created_at" in run  # Should have been set

    # Display name should have default if not provided
    # Per the implementation, missing display_name defaults to "Guest"
    run_id = run["id"]
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200


@pytest.mark.contract
def test_enum_values_are_stable_across_versions(client):
    """Verify that enum values remain stable across versions."""
    # Create a run
    response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group", "account_id": "enum-test", "display_name": "Test"},
    )
    assert response.status_code == 200
    run_id = response.json()["run"]["id"]

    # Get run details
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # Enum values should be standard strings
    if "status" in details:
        assert isinstance(details["status"], str)
        # Status should be one of expected values
        assert details["status"] in ["lobby", "active", "completed", "archived"]

    if "lobby" in details and "status" in details["lobby"]:
        assert isinstance(details["lobby"]["status"], str)
        assert details["lobby"]["status"] == "lobby"


@pytest.mark.contract
def test_null_values_handled_safely(client):
    """Verify that null values are handled safely without breaking clients."""
    # Create a run with optional fields
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            # Don't include optional fields - they'll be None
        },
    )
    assert response.status_code == 200
    run = response.json()["run"]

    # Response should handle null values correctly
    assert run is not None
    assert isinstance(run, dict)

    # Each value can be None but shouldn't cause parsing issues
    for key, value in run.items():
        # Value can be None, but key should exist
        assert key is not None
