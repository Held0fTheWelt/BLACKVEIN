"""CSRF/API split verification after backend web route removal."""

from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
CSRF_MATRIX = REPO_ROOT / "docs" / "security" / "csrf-matrix.md"


def test_csrf_matrix_documents_backend_cookie_and_api_boundaries():
    matrix = CSRF_MATRIX.read_text(encoding="utf-8")

    assert "Backend web routes removed" in matrix
    assert "Backend JSON API `/api/v1/*`" in matrix
    assert "`/logout`" in matrix
    assert "`/api/v1/auth/register`" in matrix
    assert "CSRF-exempt by design" in matrix


def test_api_endpoints_remain_csrf_exempt(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "csrf-user", "password": "StrongPassword123", "email": "csrf@example.com"},
    )
    assert response.status_code in (201, 400, 409)


@pytest.mark.security
@pytest.mark.parametrize(
    "path",
    [
        "/logout",
        "/login",
        "/register",
        "/resend-verification",
        "/forgot-password",
        "/reset-password/reset-token",
        "/play/start",
        "/play/run-1/execute",
    ],
)
def test_removed_backend_web_posts_are_not_registered(client_csrf, path):
    response = client_csrf.post(path, data={"field": "value"}, follow_redirects=False)

    assert response.status_code == 404


@pytest.mark.security
def test_cookie_flow_matrix_api_v1_mutation_stays_bearer_not_csrf(client_csrf):
    register_response = client_csrf.post(
        "/api/v1/auth/register",
        json={"username": "csrf-matrix-user", "password": "StrongPassword123"},
    )
    assert register_response.status_code == 201

    login_response = client_csrf.post(
        "/api/v1/auth/login",
        json={"username": "csrf-matrix-user", "password": "StrongPassword123"},
    )
    assert login_response.status_code == 200
    token = login_response.get_json()["access_token"]

    logout_response = client_csrf.post(
        "/api/v1/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_response.status_code == 200


def test_old_logout_route_removed(client):
    response = client.get("/logout")
    assert response.status_code == 404


def test_old_logout_post_route_removed(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 404
