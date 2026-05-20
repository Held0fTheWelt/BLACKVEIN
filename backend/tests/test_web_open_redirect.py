"""Test removed web login route cannot redirect."""


def test_login_post_removed_not_evil_next(client, test_user, app):
    """POST /login?next=https://evil.com is removed and cannot redirect."""
    app.config["FRONTEND_URL"] = "https://frontend.example.com"
    user, password = test_user
    response = client.post(
        "/login?next=https://evil.com",
        data={"username": user.username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 404
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
    assert location == ""
