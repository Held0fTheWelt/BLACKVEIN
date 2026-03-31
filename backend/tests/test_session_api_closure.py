"""Test W3.1 Session API endpoints scope boundaries.

These endpoints are deferred to W3.2 (persistence layer not yet implemented).
Tests verify they return 501 Not Implemented as per W3.1 contract.
"""

import pytest
import json
from app.services.session_service import create_session


def test_get_session_returns_501_not_implemented(client, test_user, monkeypatch):
    """GET /api/v1/sessions/<id> implemented in A1.3 (requires MCP_SERVICE_TOKEN)."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    # Without token: 401
    response = client.get(f"/api/v1/sessions/{session_id}")
    assert response.status_code == 401

    # With token: 200 (endpoint now implemented in A1.3)
    response = client.get(f"/api/v1/sessions/{session_id}",
        headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "session_id" in data  # Snapshot structure


def test_post_execute_turn_returns_501_not_implemented(client, test_user):
    """POST /api/v1/sessions/<id>/turns deferred to W3.2."""
    session = create_session("god_of_carnage")
    session_id = session.session_id

    response = client.post(
        f"/api/v1/sessions/{session_id}/turns",
        json={"operator_input": "test action", "turn_number": 1},
        content_type="application/json"
    )

    assert response.status_code == 501
    data = json.loads(response.data)
    assert "error" in data


def test_get_logs_returns_501_not_implemented(client, test_user, monkeypatch):
    """GET /api/v1/sessions/<id>/logs implemented in A1.3 (requires MCP_SERVICE_TOKEN)."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    # Without token: 401
    response = client.get(f"/api/v1/sessions/{session_id}/logs")
    assert response.status_code == 401

    # With token: 200 (endpoint now implemented in A1.3)
    response = client.get(f"/api/v1/sessions/{session_id}/logs",
        headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "events" in data  # Logs structure


def test_get_state_returns_501_not_implemented(client, test_user, monkeypatch):
    """GET /api/v1/sessions/<id>/state implemented in A1.3 (requires MCP_SERVICE_TOKEN)."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "test-token")
    session = create_session("god_of_carnage")
    session_id = session.session_id

    # Without token: 401
    response = client.get(f"/api/v1/sessions/{session_id}/state")
    assert response.status_code == 401

    # With token: 200 (endpoint now implemented in A1.3)
    response = client.get(f"/api/v1/sessions/{session_id}/state",
        headers={"Authorization": "Bearer test-token"})
    assert response.status_code == 200
    data = json.loads(response.data)
    assert "canonical_state" in data  # State structure


def test_create_session_still_works(client, test_user):
    """POST /api/v1/sessions (create) is fully implemented in W3.1."""
    response = client.post(
        "/api/v1/sessions",
        json={"module_id": "god_of_carnage"},
        content_type="application/json"
    )

    assert response.status_code == 201
    data = json.loads(response.data)
    assert "session_id" in data
    assert data["module_id"] == "god_of_carnage"
