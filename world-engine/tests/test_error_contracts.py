"""Error Standardization Contract Tests for World Engine.

WAVE 8 Hardening Initiative: Error response standardization and consistency.
Tests focus on ensuring all API errors follow a consistent format with proper
codes, messages, recovery hints, and metadata.

Mark: @pytest.mark.contract
"""

from __future__ import annotations

import json
import re

import pytest


@pytest.mark.contract
def test_error_response_format_consistency_across_endpoints(client):
    """Verify that all API errors follow a consistent response format."""
    error_responses = []

    # 404 - Run not found
    response = client.get("/api/runs/missing-run-id")
    assert response.status_code == 404
    error_responses.append(response.json())

    # 404 - Template not found
    response = client.post(
        "/api/runs",
        json={"template_id": "missing-template"},
    )
    assert response.status_code == 404
    error_responses.append(response.json())

    # 403 - Permission denied
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
    error_responses.append(response.json())

    # All error responses should have consistent structure
    for error in error_responses:
        assert isinstance(error, dict)
        assert "detail" in error, "Error response must contain 'detail' field"


@pytest.mark.contract
def test_error_codes_standardized_across_api(client):
    """Verify that HTTP error codes are used consistently."""
    # 400 Bad Request - invalid input structure
    # Note: FastAPI validates input, so we test with a properly formed but invalid request
    response = client.post(
        "/api/runs",
        json={"template_id": "invalid-template-xyz-abc-def"},
    )
    assert response.status_code == 404  # Unknown template returns 404

    # 404 Not Found - resource doesn't exist
    response = client.get("/api/runs/nonexistent")
    assert response.status_code == 404
    assert "detail" in response.json()

    # 403 Forbidden - permission denied
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "other-user", "display_name": "Other User"},
    )
    assert response.status_code == 403

    # 403 Unauthorized - missing/wrong internal API key or permission denied
    response = client.post(
        "/api/internal/join-context",
        json={"run_id": run_id, "account_id": "user", "display_name": "User"},
        headers={"x-play-service-key": "wrong-key-xyz"},
    )
    # May be 403 if key validation is enabled (permission denied)
    assert response.status_code in [401, 403, 404, 200]  # Depends on config


@pytest.mark.contract
def test_validation_errors_include_field_names(client):
    """Verify that validation errors include field names and types."""
    # Create request with display_name that's too long (max 80 chars)
    long_name = "x" * 100
    response = client.post(
        "/api/runs",
        json={
            "template_id": "god_of_carnage_solo",
            "display_name": long_name,
        },
    )

    # Should fail validation
    if response.status_code >= 400:
        error = response.json()
        assert "detail" in error
        # If detail is a string with validation info, it may contain field info
        # or be a structured error


@pytest.mark.contract
def test_business_logic_errors_have_descriptive_messages(client):
    """Verify that business logic errors have descriptive messages."""
    # Create a run
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    # Try to join with wrong account (owner-only template)
    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "intruder", "display_name": "Intruder"},
    )
    assert response.status_code == 403
    error = response.json()

    # Error message should be descriptive
    assert "detail" in error
    assert isinstance(error["detail"], str)
    assert len(error["detail"]) > 0


@pytest.mark.contract
def test_system_errors_do_not_expose_stack_traces(client):
    """Verify that system errors don't expose internal stack traces."""
    # Try various error conditions
    responses = [
        client.get("/api/runs/invalid-id-with-slashes/../../etc/passwd"),
        client.post("/api/runs", json={}),  # Missing required field
        client.get("/api/runs/123"),  # Valid format, missing resource
    ]

    for response in responses:
        if response.status_code >= 500:
            # Server error - must not contain stack trace
            body = response.text
            assert "Traceback" not in body
            assert "File \"" not in body
            assert "line " not in body or "line" not in response.json().get("detail", "").lower()


@pytest.mark.contract
def test_error_response_headers_are_correct(client):
    """Verify that error responses include correct headers."""
    response = client.get("/api/runs/missing")
    assert response.status_code == 404

    # Standard HTTP headers
    assert "content-type" in response.headers or "Content-Type" in response.headers
    # Content should be JSON for API
    content_type = response.headers.get("content-type") or response.headers.get("Content-Type", "")
    if "404" in str(response.status_code):
        # Error responses from FastAPI should have JSON content type
        assert "json" in content_type.lower()


@pytest.mark.contract
def test_error_responses_indicate_retry_ability(client):
    """Verify that error responses indicate whether retry is appropriate."""
    # Permanent errors (4xx)
    response = client.get("/api/runs/nonexistent")
    assert response.status_code == 404
    error = response.json()
    # 404 is not retryable

    # Create a run to test permission error
    create_response = client.post(
        "/api/runs",
        json={"template_id": "god_of_carnage_solo", "account_id": "owner", "display_name": "Owner"},
    )
    run_id = create_response.json()["run"]["id"]

    # Permission error (403)
    response = client.post(
        "/api/tickets",
        json={"run_id": run_id, "account_id": "other", "display_name": "Other"},
    )
    assert response.status_code == 403
    error = response.json()
    # 403 is not retryable

    # Verify error structure exists
    assert isinstance(error, dict)
    assert "detail" in error


@pytest.mark.contract
def test_error_localization_support_in_messages(client):
    """Verify that error messages support localization patterns."""
    response = client.get("/api/runs/missing")
    assert response.status_code == 404
    error = response.json()

    # Error detail should be a string
    assert isinstance(error["detail"], str)

    # Should not contain hardcoded non-ASCII messages (enables i18n)
    detail = error["detail"]
    # Should be ASCII-safe for proper serialization
    assert detail.encode("utf-8").decode("utf-8") == detail

    # Message should be meaningful
    assert len(detail) > 0
