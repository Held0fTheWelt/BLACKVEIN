"""Tests for MCP service token authentication decorator."""

import os
import pytest
from flask import Flask
from backend.app.api.v1.auth import require_mcp_service_token


def test_require_mcp_service_token_missing_env_returns_503():
    """When MCP_SERVICE_TOKEN not set, decorator should return 503."""
    # Ensure env var is not set
    if "MCP_SERVICE_TOKEN" in os.environ:
        del os.environ["MCP_SERVICE_TOKEN"]

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer sometoken"})
        assert response.status_code == 503
        data = response.get_json()
        assert data["error"]["code"] == "MISCONFIGURED"
        assert "MCP_SERVICE_TOKEN" in data["error"]["message"]


def test_require_mcp_service_token_valid_token_allows_request(monkeypatch):
    """When token is valid, request proceeds to handler."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer secret-token-123"})
        assert response.status_code == 200
        data = response.get_json()
        assert data["data"] == "ok"


def test_require_mcp_service_token_missing_header_returns_401(monkeypatch):
    """When Authorization header missing, return 401."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test")  # No Authorization header
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"


def test_require_mcp_service_token_invalid_token_returns_401(monkeypatch):
    """When token doesn't match, return 401."""
    monkeypatch.setenv("MCP_SERVICE_TOKEN", "secret-token-123")

    app = Flask(__name__)

    @app.route("/test")
    @require_mcp_service_token
    def test_route():
        return {"data": "ok"}, 200

    with app.test_client() as client:
        response = client.get("/test", headers={"Authorization": "Bearer wrong-token"})
        assert response.status_code == 401
        data = response.get_json()
        assert data["error"]["code"] == "UNAUTHORIZED"
