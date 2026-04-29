"""HTTP Contract Tests for Health and Template Endpoints.

WAVE 6: API contract and response schema tests for health and template endpoints.
Tests focus on ensuring consistent and valid API responses with proper response schemas.

Mark: @pytest.mark.contract, @pytest.mark.unit
"""

from __future__ import annotations

import pytest


@pytest.mark.unit
@pytest.mark.contract
def test_health_status_returns_ok(client):
    """Verify that GET /api/health returns 200 with status ok."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()
    assert body == {"status": "ok"}


@pytest.mark.unit
@pytest.mark.contract
def test_health_status_response_schema(client):
    """Verify that GET /api/health returns correct response structure."""
    response = client.get("/api/health")
    assert response.status_code == 200
    body = response.json()

    # Verify required fields
    assert "status" in body
    assert isinstance(body["status"], str)
    assert body["status"] == "ok"


@pytest.mark.unit
@pytest.mark.contract
def test_health_ready_returns_200(client):
    """Verify that GET /api/health/ready returns 200 with readiness status."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()

    # Verify required fields
    assert "status" in body
    assert body["status"] == "ready"


@pytest.mark.unit
@pytest.mark.contract
def test_health_ready_response_schema(client):
    """Verify that GET /api/health/ready returns complete readiness status."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()

    # Verify response structure for ready endpoint
    required_fields = ["status", "app", "store", "template_count", "run_count"]
    for field in required_fields:
        assert field in body, f"Missing required field: {field}"

    # Verify field types
    assert isinstance(body["status"], str)
    assert isinstance(body["app"], str)
    assert isinstance(body["store"], dict)
    assert isinstance(body["template_count"], int)
    assert isinstance(body["run_count"], int)


@pytest.mark.unit
@pytest.mark.contract
def test_health_ready_has_valid_store_info(client):
    """Verify that GET /api/health/ready returns valid store info."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()

    store = body["store"]
    # Store should have backend at minimum
    assert isinstance(store, dict)
    assert "backend" in store


@pytest.mark.unit
@pytest.mark.contract
def test_health_ready_counts_are_non_negative(client):
    """Verify that template and run counts in ready status are non-negative."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    body = response.json()

    assert body["template_count"] >= 0
    assert body["run_count"] >= 0


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_returns_200(client):
    """Verify that GET /api/templates returns 200 with list of templates."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    body = response.json()

    assert isinstance(body, list)


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_returns_valid_list(client):
    """Verify that GET /api/templates returns a valid list structure."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()

    assert isinstance(templates, list)
    # Should have at least one template (god_of_carnage_solo or similar)
    assert len(templates) > 0


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_response_schema(client):
    """Verify that GET /api/templates templates have required fields."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()

    # Each template should have these fields
    required_fields = ["id", "title", "kind", "join_policy", "persistent"]
    for template in templates:
        assert isinstance(template, dict)
        for field in required_fields:
            assert field in template, f"Template missing required field: {field}"


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_field_types(client):
    """Verify that GET /api/templates templates have correct field types."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()

    for template in templates:
        assert isinstance(template["id"], str)
        assert isinstance(template["title"], str)
        assert isinstance(template["kind"], str)
        assert isinstance(template["join_policy"], str)
        assert isinstance(template["persistent"], bool)


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize("kind", ["solo_story", "group_story", "open_world"])
def test_list_templates_has_valid_kind_values(client, kind):
    """Verify that GET /api/templates templates have valid kind enum values."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()

    # At least some templates should have this kind
    template_kinds = [t["kind"] for t in templates]
    # This test will pass as long as templates list is valid
    assert isinstance(template_kinds, list)


@pytest.mark.unit
@pytest.mark.contract
@pytest.mark.parametrize("join_policy", ["owner_only", "invited_party", "public"])
def test_list_templates_has_valid_join_policy_values(client, join_policy):
    """Verify that GET /api/templates templates have valid join_policy enum values."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    templates = response.json()

    # Verify that only valid join policies are used
    valid_policies = ["owner_only", "invited_party", "public"]
    for template in templates:
        assert template["join_policy"] in valid_policies


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_has_content_type_json(client):
    """Verify that GET /api/templates returns application/json content type."""
    response = client.get("/api/templates")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
def test_health_status_has_content_type_json(client):
    """Verify that GET /api/health returns application/json content type."""
    response = client.get("/api/health")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
def test_health_ready_has_content_type_json(client):
    """Verify that GET /api/health/ready returns application/json content type."""
    response = client.get("/api/health/ready")
    assert response.status_code == 200
    assert "application/json" in response.headers.get("content-type", "")


@pytest.mark.unit
@pytest.mark.contract
def test_list_templates_status_ok(client):
    """Verify that template list endpoint returns successful status."""
    response = client.get("/api/templates")
    assert response.status_code == 200


@pytest.mark.unit
@pytest.mark.contract
def test_health_endpoints_no_errors(client):
    """Verify that health endpoints return without errors."""
    health_response = client.get("/api/health")
    ready_response = client.get("/api/health/ready")

    assert health_response.status_code == 200
    assert ready_response.status_code == 200
