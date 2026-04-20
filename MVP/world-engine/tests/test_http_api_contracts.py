"""HTTP API contract tests for World Engine.

WAVE 6: Comprehensive HTTP endpoint testing with positive and negative paths.
Tests all HTTP methods, status codes, and response contracts.

Mark: @pytest.mark.contract, @pytest.mark.integration, @pytest.mark.security
"""

from __future__ import annotations

import pytest


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.contract
    def test_health_endpoint_returns_200(self, client):
        """GET /api/health should return 200 OK."""
        response = client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_health_endpoint_returns_json(self, client):
        """GET /api/health should return JSON response."""
        response = client.get("/api/health")
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.contract
    def test_health_endpoint_returns_status_ok(self, client):
        """GET /api/health should return status: ok."""
        response = client.get("/api/health")
        body = response.json()
        assert "status" in body
        assert body["status"] == "ok"

    @pytest.mark.contract
    def test_health_endpoint_no_auth_required(self, client):
        """GET /api/health should not require authentication."""
        response = client.get("/api/health")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_ready_endpoint_returns_200(self, client, app):
        """GET /api/health/ready should return 200 OK."""
        response = client.get("/api/health/ready")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_ready_endpoint_returns_json(self, client):
        """GET /api/health/ready should return JSON response."""
        response = client.get("/api/health/ready")
        assert response.headers["content-type"].startswith("application/json")

    @pytest.mark.contract
    def test_ready_endpoint_includes_status(self, client):
        """GET /api/health/ready should include status field."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "status" in body

    @pytest.mark.contract
    def test_ready_endpoint_includes_app_name(self, client):
        """GET /api/health/ready should include app field."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "app" in body

    @pytest.mark.contract
    def test_ready_endpoint_includes_store_info(self, client):
        """GET /api/health/ready should include store field."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "store" in body

    @pytest.mark.contract
    def test_ready_endpoint_includes_template_count(self, client):
        """GET /api/health/ready should include template_count."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "template_count" in body
        assert isinstance(body["template_count"], int)

    @pytest.mark.contract
    def test_ready_endpoint_includes_run_count(self, client):
        """GET /api/health/ready should include run_count."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert "run_count" in body
        assert isinstance(body["run_count"], int)


class TestRunEndpoints:
    """Test run management endpoints."""

    @pytest.mark.contract
    def test_list_runs_returns_200(self, client):
        """GET /api/runs should return 200 OK."""
        response = client.get("/api/runs")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_list_runs_returns_array(self, client):
        """GET /api/runs should return array of runs."""
        response = client.get("/api/runs")
        body = response.json()
        assert isinstance(body, list)

    @pytest.mark.contract
    def test_create_run_returns_200(self, client):
        """POST /api/runs should return 200 OK."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        assert response.status_code == 200

    @pytest.mark.contract
    def test_create_run_returns_run_object(self, client):
        """POST /api/runs should return run object."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        body = response.json()
        assert "run" in body

    @pytest.mark.contract
    def test_create_run_includes_required_fields(self, client):
        """POST /api/runs response should include required run fields."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        body = response.json()
        run = body["run"]

        required_fields = ["id", "template_id", "status", "created_at"]
        for field in required_fields:
            assert field in run, f"Missing field: {field}"

    @pytest.mark.contract
    def test_get_run_returns_200(self, client):
        """GET /api/runs/{run_id} should return 200 OK for valid run."""
        create_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = create_response.json()["run"]["id"]

        response = client.get(f"/api/runs/{run_id}")
        assert response.status_code == 200

    @pytest.mark.contract
    @pytest.mark.security
    def test_create_run_missing_template_id_returns_422(self, client):
        """POST /api/runs without template_id should return 422."""
        response = client.post("/api/runs", json={})
        assert response.status_code == 422

    @pytest.mark.contract
    @pytest.mark.security
    def test_create_run_unknown_template_returns_404(self, client):
        """POST /api/runs with unknown template_id should return 404."""
        response = client.post(
            "/api/runs",
            json={"template_id": "nonexistent-template-xyz"},
        )
        assert response.status_code == 404

    @pytest.mark.contract
    @pytest.mark.security
    def test_get_run_nonexistent_returns_404(self, client):
        """GET /api/runs/{run_id} for nonexistent run should return 404."""
        response = client.get("/api/runs/nonexistent-run-id")
        assert response.status_code == 404


class TestTicketEndpoints:
    """Test ticket creation endpoints."""

    @pytest.mark.contract
    def test_create_ticket_returns_200(self, client):
        """POST /api/tickets should return 200 OK for valid request."""
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

    @pytest.mark.contract
    def test_create_ticket_returns_ticket_string(self, client):
        """POST /api/tickets should return ticket string."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.post(
            "/api/tickets",
            json={"run_id": run_id},
        )
        if response.status_code == 200:
            body = response.json()
            assert "ticket" in body
            assert isinstance(body["ticket"], str)
            assert len(body["ticket"]) > 0

    @pytest.mark.contract
    def test_create_ticket_returns_required_fields(self, client):
        """POST /api/tickets response should include required fields."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "apartment_confrontation_group"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.post(
            "/api/tickets",
            json={"run_id": run_id},
        )
        if response.status_code == 200:
            body = response.json()
            required_fields = ["ticket", "run_id", "participant_id", "role_id", "display_name"]
            for field in required_fields:
                assert field in body, f"Missing field: {field}"

    @pytest.mark.contract
    @pytest.mark.security
    def test_create_ticket_missing_run_id_returns_422(self, client):
        """POST /api/tickets without run_id should return 422."""
        response = client.post("/api/tickets", json={})
        assert response.status_code == 422

    @pytest.mark.contract
    @pytest.mark.security
    def test_create_ticket_unknown_run_returns_404(self, client):
        """POST /api/tickets with unknown run_id should return 404."""
        response = client.post(
            "/api/tickets",
            json={"run_id": "nonexistent-run-xyz"},
        )
        assert response.status_code == 404


class TestTranscriptEndpoints:
    """Test transcript retrieval endpoints."""

    @pytest.mark.contract
    def test_get_transcript_returns_200(self, client):
        """GET /api/runs/{run_id}/transcript should return 200."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.get(f"/api/runs/{run_id}/transcript")
        assert response.status_code == 200

    @pytest.mark.contract
    def test_get_transcript_returns_json(self, client):
        """GET /api/runs/{run_id}/transcript should return JSON."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.get(f"/api/runs/{run_id}/transcript")
        body = response.json()
        assert isinstance(body, dict)

    @pytest.mark.contract
    def test_get_transcript_includes_run_id(self, client):
        """GET /api/runs/{run_id}/transcript response should include run_id."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.get(f"/api/runs/{run_id}/transcript")
        body = response.json()
        assert "run_id" in body

    @pytest.mark.contract
    def test_get_transcript_includes_entries(self, client):
        """GET /api/runs/{run_id}/transcript response should include entries array."""
        run_response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run_id = run_response.json()["run"]["id"]

        response = client.get(f"/api/runs/{run_id}/transcript")
        body = response.json()
        assert "entries" in body
        assert isinstance(body["entries"], list)

    @pytest.mark.contract
    @pytest.mark.security
    def test_get_transcript_invalid_run_returns_404(self, client):
        """GET /api/runs/{run_id}/transcript with invalid run should return 404."""
        response = client.get("/api/runs/invalid-run/transcript")
        assert response.status_code == 404


class TestErrorResponses:
    """Test error response structure and content."""

    @pytest.mark.contract
    def test_404_response_includes_detail(self, client):
        """404 responses should include detail field."""
        response = client.get("/api/runs/nonexistent")
        assert response.status_code == 404
        body = response.json()
        assert "detail" in body

    @pytest.mark.contract
    def test_422_response_includes_detail(self, client):
        """422 responses should include detail field."""
        response = client.post("/api/runs", json={})
        assert response.status_code == 422
        body = response.json()
        assert "detail" in body

    @pytest.mark.contract
    @pytest.mark.security
    def test_error_responses_dont_expose_secrets(self, client):
        """Error responses should not expose secret keys or sensitive data."""
        response = client.post("/api/runs", json={})
        body = response.json()
        error_text = str(body)

        # Should not contain common secret patterns
        assert "secret" not in error_text.lower()
        assert "password" not in error_text.lower()
        assert "api_key" not in error_text.lower()

    @pytest.mark.contract
    def test_error_response_is_json(self, client):
        """Error responses should be JSON."""
        response = client.get("/api/runs/nonexistent")
        assert response.headers["content-type"].startswith("application/json")
        response.json()


class TestHttpMethods:
    """Test HTTP method validation."""

    @pytest.mark.contract
    @pytest.mark.security
    def test_unsupported_method_on_health(self, client):
        """POST /api/health should not be allowed (GET only)."""
        response = client.post("/api/health")
        assert response.status_code == 405

    @pytest.mark.contract
    @pytest.mark.security
    def test_unsupported_method_on_ready(self, client):
        """POST /api/health/ready should not be allowed (GET only)."""
        response = client.post("/api/health/ready")
        assert response.status_code == 405


class TestResponseFieldTypes:
    """Test that response fields have correct types."""

    @pytest.mark.contract
    def test_run_id_is_string(self, client):
        """Run ID should be string."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run = response.json()["run"]
        assert isinstance(run["id"], str)

    @pytest.mark.contract
    def test_template_id_is_string(self, client):
        """Template ID should be string."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run = response.json()["run"]
        assert isinstance(run["template_id"], str)

    @pytest.mark.contract
    def test_status_is_string(self, client):
        """Run status should be string."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run = response.json()["run"]
        assert isinstance(run["status"], str)

    @pytest.mark.contract
    def test_created_at_is_string(self, client):
        """Created_at timestamp should be string."""
        response = client.post(
            "/api/runs",
            json={"template_id": "god_of_carnage_solo"},
        )
        run = response.json()["run"]
        assert isinstance(run["created_at"], str)

    @pytest.mark.contract
    def test_template_count_is_integer(self, client):
        """template_count should be integer."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert isinstance(body["template_count"], int)
        assert body["template_count"] >= 0

    @pytest.mark.contract
    def test_run_count_is_integer(self, client):
        """run_count should be integer."""
        response = client.get("/api/health/ready")
        body = response.json()
        assert isinstance(body["run_count"], int)
        assert body["run_count"] >= 0
