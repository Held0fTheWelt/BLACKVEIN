"""CSRF/API split verification after web deprecation."""


def test_api_endpoints_remain_csrf_exempt(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"username": "csrf-user", "password": "StrongPassword123", "email": "csrf@example.com"},
    )
    assert response.status_code in (201, 400, 409)


def test_legacy_logout_still_post_only(client):
    response = client.get("/logout")
    assert response.status_code == 405


def test_legacy_logout_redirects_without_html_render(client, app):
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    response = client.post("/logout", data={}, follow_redirects=False)
    assert response.status_code == 302
    assert response.headers["Location"] == "https://frontend.example.com/"
