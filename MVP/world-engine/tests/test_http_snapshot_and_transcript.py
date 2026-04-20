"""HTTP Contract Tests for Snapshot and Transcript Endpoints.

WAVE 6: API contract tests for snapshot and transcript endpoints.
Tests focus on response structure, error handling, and data validation.

Mark: @pytest.mark.contract, @pytest.mark.integration
"""

from __future__ import annotations

import pytest


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_returns_200_for_valid_run_and_participant(client):
    """Verify that GET /api/runs/{run_id}/snapshot/{participant_id} returns 200."""
    # Create a run
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "display_name": "Owner"},
    )
    run_id = run_response.json()["run"]["id"]

    # Get run details to find a participant
    details_response = client.get(f"/api/runs/{run_id}")
    details = details_response.json()

    # Find an NPC participant (should exist in god_of_carnage_solo)
    participant_id = None
    if "snapshot" in details and "participants" in details["snapshot"]:
        participants = details["snapshot"]["participants"]
        if participants:
            participant_id = list(participants.keys())[0]

    if participant_id:
        response = client.get(f"/api/runs/{run_id}/snapshot/{participant_id}")
        assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_response_structure(client):
    """Verify that snapshot response has required structure."""
    # Create a run with a participant
    run_response = client.post(
        "/api/runs",
        json={"template_id": "apartment_confrontation_group"},
    )
    run_id = run_response.json()["run"]["id"]

    # Join the run to get a participant
    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "display_name": "Joiner"},
    )
    if ticket_response.status_code == 200:
        participant_id = ticket_response.json()["participant_id"]

        response = client.get(f"/api/runs/{run_id}/snapshot/{participant_id}")
        assert response.status_code == 200
        snapshot = response.json()

        # Verify it's a dict with snapshot-like structure
        assert isinstance(snapshot, dict)
        # Should have core snapshot fields
        assert "run_id" in snapshot
        assert "viewer_participant_id" in snapshot


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_with_invalid_run_returns_404(client):
    """Verify that snapshot with invalid run_id returns 404."""
    response = client.get("/api/runs/nonexistent-run/snapshot/participant-123")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_with_invalid_participant_returns_404(client):
    """Verify that snapshot with invalid participant_id returns 404."""
    # Create a run
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/snapshot/nonexistent-participant")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_404_includes_detail_message(client):
    """Verify that snapshot 404 includes error detail."""
    response = client.get("/api/runs/nonexistent/snapshot/nonexistent")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body


@pytest.mark.integration
@pytest.mark.contract
def test_get_snapshot_content_type_is_json(client):
    """Verify that snapshot endpoint returns JSON content type."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    participant_id = ticket_response.json()["participant_id"]

    response = client.get(f"/api/runs/{run_id}/snapshot/{participant_id}")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_returns_200_for_valid_run(client):
    """Verify that GET /api/runs/{run_id}/transcript returns 200."""
    # Create a run
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_returns_valid_structure(client):
    """Verify that transcript response has expected structure."""
    # Create a run
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()

    # Should have run_id and entries
    assert "run_id" in body
    assert "entries" in body
    assert body["run_id"] == run_id
    assert isinstance(body["entries"], list)


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_entries_is_list(client):
    """Verify that transcript entries is always a list."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()

    assert isinstance(body["entries"], list)


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_entries_have_required_fields(client):
    """Verify that transcript entries have required fields."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()
    entries = body["entries"]

    # For each entry that exists, verify it has required fields
    for entry in entries:
        assert isinstance(entry, dict)
        # Entries should have these fields
        assert "id" in entry
        assert "at" in entry
        assert "kind" in entry
        assert "text" in entry


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_entry_field_types(client):
    """Verify that transcript entry fields have correct types."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()
    entries = body["entries"]

    for entry in entries:
        assert isinstance(entry["id"], str)
        assert isinstance(entry["at"], str)
        assert isinstance(entry["kind"], str)
        assert isinstance(entry["text"], str)


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_with_invalid_run_returns_404(client):
    """Verify that transcript with invalid run_id returns 404."""
    response = client.get("/api/runs/nonexistent-run-xyz/transcript")
    assert response.status_code == 404


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_404_includes_detail_message(client):
    """Verify that transcript 404 includes error detail."""
    response = client.get("/api/runs/nonexistent-12345/transcript")
    assert response.status_code == 404
    body = response.json()
    assert "detail" in body
    assert body["detail"] == "Run not found"


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_content_type_is_json(client):
    """Verify that transcript endpoint returns JSON content type."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_run_id_matches_request(client):
    """Verify that transcript response run_id matches request."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == run_id


@pytest.mark.integration
@pytest.mark.contract
def test_snapshot_and_transcript_different_endpoints(client):
    """Verify that snapshot and transcript are different endpoints."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    ticket_response = client.post(
        "/api/tickets",
        json={"run_id": run_id},
    )
    participant_id = ticket_response.json()["participant_id"]

    snapshot_response = client.get(f"/api/runs/{run_id}/snapshot/{participant_id}")
    transcript_response = client.get(f"/api/runs/{run_id}/transcript")

    # Both should be successful
    assert snapshot_response.status_code == 200
    assert transcript_response.status_code == 200

    # But they should be different responses
    snapshot = snapshot_response.json()
    transcript = transcript_response.json()

    # Snapshot has viewer_participant_id, transcript has entries
    assert "viewer_participant_id" in snapshot
    assert "entries" in transcript


@pytest.mark.integration
@pytest.mark.contract
def test_get_transcript_empty_for_new_run(client):
    """Verify that new run may have empty transcript."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()

    # Entries might be empty list for new run
    assert isinstance(body["entries"], list)


@pytest.mark.integration
@pytest.mark.contract
def test_transcript_entry_optional_fields(client):
    """Verify that transcript entries may have optional fields."""
    run_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo"},
    )
    run_id = run_response.json()["run"]["id"]

    response = client.get(f"/api/runs/{run_id}/transcript")
    assert response.status_code == 200
    body = response.json()
    entries = body["entries"]

    # Optional fields should be present or null in entries
    for entry in entries:
        # actor and room_id are optional
        if "actor" in entry:
            assert entry["actor"] is None or isinstance(entry["actor"], str)
        if "room_id" in entry:
            assert entry["room_id"] is None or isinstance(entry["room_id"], str)
