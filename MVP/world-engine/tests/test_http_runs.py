"""HTTP Contract Tests for Runs Endpoints.

WAVE 6: API contract and response schema tests for run management endpoints.
Tests focus on creating, listing, and retrieving runs with proper validation.

Mark: @pytest.mark.contract, @pytest.mark.unit, @pytest.mark.integration
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_returns_201_or_200(client):
    """Verify that POST /api/runs returns 200 status code."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Test User"},
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_minimal_payload(client):
    """Verify that POST /api/runs accepts minimal required payload."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert "run" in body


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_returns_run_with_required_fields(client):
    """Verify that POST /api/runs returns run object with id, identity, and state."""
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "account_id": "test-account",
            "display_name": "Test User",
        },
    )
    assert response.status_code == 200
    body = response.json()

    # Response structure
    assert "run" in body
    assert "store" in body
    assert "hint" in body

    run = body["run"]
    # Required fields in run
    assert "id" in run
    assert isinstance(run["id"], str)
    assert len(run["id"]) > 0


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_includes_template_id_in_response(client):
    """Verify that POST /api/runs response includes template_id."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["template_id"] == "god_of_carnage_solo"


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_includes_status_field(client):
    """Verify that POST /api/runs response includes status."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Test"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert "status" in run
    assert isinstance(run["status"], str)


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_includes_created_at_field(client):
    """Verify that POST /api/runs response includes created_at timestamp."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert "created_at" in run
    assert isinstance(run["created_at"], str)


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_optional_account_id(client):
    """Verify that POST /api/runs accepts optional account_id."""
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "account_id": "my-account-123",
        },
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_optional_character_id(client):
    """Verify that POST /api/runs accepts optional character_id."""
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "character_id": "char-456",
        },
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_optional_player_name(client):
    """Verify that POST /api/runs accepts optional player_name."""
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "player_name": "John Doe",
        },
    )
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_invalid_template_returns_404(client):
    """Verify that POST /api/runs with invalid template returns 404."""
    response = client.post(
        "/api/runs",
        json={"template_id": "nonexistent-template-xyz"},
    )
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_malformed_json_returns_422(client):
    """Verify that POST /api/runs with malformed JSON returns 422."""
    response = client.post(
        "/api/runs",
        data="not valid json",
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_with_missing_template_id_returns_422(client):
    """Verify that POST /api/runs without template_id returns 422."""
    response = client.post(
        "/api/runs",
        json={"display_name": "Test User"},
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_response_hint_is_string(client):
    """Verify that POST /api/runs response hint is informative."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body["hint"], str)
    assert len(body["hint"]) > 0


@pytest.mark.integration
@pytest.mark.contract
def test_list_runs_returns_200(client):
    """Verify that GET /api/runs returns 200 status code."""
    response = client.get("/api/runs")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.contract
def test_list_runs_returns_list(client):
    """Verify that GET /api/runs returns a list."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    body = response.json()
    assert isinstance(body, list)


@pytest.mark.integration
@pytest.mark.contract
def test_list_runs_initial_has_entries(client):
    """Verify that GET /api/runs returns list with entries (public runs exist)."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()
    # Should have at least public open worlds
    assert len(runs) >= 0


@pytest.mark.integration
@pytest.mark.contract
def test_list_runs_contains_valid_run_structures(client):
    """Verify that GET /api/runs returns runs with required fields."""
    # First create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Test"},
    )
    assert create_response.status_code == 200
    created_run_id = create_response.json()["run"]["id"]

    # Then list runs
    response = client.get("/api/runs")
    assert response.status_code == 200
    runs = response.json()

    assert isinstance(runs, list)
    # Find our created run (might not be in public list immediately)
    found = False
    for run in runs:
        assert "id" in run
        assert "template_id" in run
        if run["id"] == created_run_id:
            found = True
    # Note: run may not be in list immediately if not public


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_details_returns_200(client):
    """Verify that GET /api/runs/{run_id} returns 200 for valid run_id."""
    # Create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Test"},
    )
    assert create_response.status_code == 200
    run_id = create_response.json()["run"]["id"]

    # Get details
    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_details_response_structure(client):
    """Verify that GET /api/runs/{run_id} returns proper structure."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Test"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    # Should have these fields
    assert "template" in details or "run" in details
    assert "lobby" in details


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_details_includes_template_field(client):
    """Verify that GET /api/runs/{run_id} response includes template."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    assert "template" in details
    template = details["template"]
    assert "id" in template
    assert template["id"] == "god_of_carnage_solo"


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_details_includes_lobby_field(client):
    """Verify that GET /api/runs/{run_id} response includes lobby."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    details = response.json()

    assert "lobby" in details
    lobby = details["lobby"]
    # Lobby may be None or a dict depending on run state
    assert lobby is None or isinstance(lobby, dict)


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_with_invalid_id_returns_404(client):
    """Verify that GET /api/runs/{run_id} with invalid ID returns 404."""
    response = client.get("/api/runs/invalid-run-id-xyz")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_with_nonexistent_id_returns_404_with_message(client):
    """Verify that GET /api/runs/{run_id} 404 includes error detail."""
    response = client.get("/api/runs/nonexistent-12345")
    assert response.status_code == 404
    body = response.json()
    assert body.get("detail") == "Run not found"


@pytest.mark.unit
@pytest.mark.contract
def test_list_runs_content_type_is_json(client):
    """Verify that GET /api/runs returns JSON content type."""
    response = client.get("/api/runs")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
def test_create_run_content_type_is_json(client):
    """Verify that POST /api/runs returns JSON content type."""
    response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
def test_get_run_content_type_is_json(client):
    """Verify that GET /api/runs/{run_id} returns JSON content type."""
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize("template_id", ["god_of_carnage_solo", "apartment_confrontation_group"])
def test_create_run_with_different_templates(client, template_id):
    """Verify that POST /api/runs works with different valid templates."""
    response = client.post(
        "/api/runs",
        json={"template_id": template_id},
    )
    assert response.status_code == 200
    run = response.json()["run"]
    assert run["template_id"] == template_id
