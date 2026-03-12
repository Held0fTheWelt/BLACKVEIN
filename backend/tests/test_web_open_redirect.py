"""Test open-redirect protection on login."""
import pytest


def test_login_success_with_evil_next_redirects_to_dashboard(client, test_user):
    """POST /login?next=https://evil.com with valid credentials redirects to dashboard, not to external URL."""
    user, password = test_user
    response = client.post(
        "/login?next=https://evil.com",
        data={"username": user.username, "password": password},
        follow_redirects=False,
    )
    assert response.status_code == 302
    location = response.headers.get("Location", "")
    assert "evil.com" not in location
    assert "dashboard" in location or location.endswith("/dashboard")
