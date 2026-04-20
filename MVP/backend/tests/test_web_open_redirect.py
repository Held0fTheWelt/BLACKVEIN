"""Test open-redirect protection on legacy web login compatibility route."""


def test_login_post_redirects_to_frontend_login_not_evil_next(client, test_user, app):
    """POST /login?next=https://evil.com redirects to FRONTEND_URL/login, never to evil.com."""
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    user, password = test_user
    response = client.post(
        "/login?next=https://evil.com",
        data={"username": user.username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
    assert location == "https://frontend.example.com/login"
