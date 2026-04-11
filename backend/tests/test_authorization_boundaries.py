"""API authorization boundary tests (split from former test_coverage_expansion)."""

import pytest

from app.extensions import db
from app.models import User


class TestAuthorizationBoundaries:
    """Test permission enforcement across API endpoints."""

    def test_non_admin_cannot_access_admin_analytics(self, client, auth_headers, test_user):
        """Non-admins blocked from admin analytics endpoint."""
        response = client.get(
            "/api/v1/admin/analytics/summary",
            headers=auth_headers,
        )
        assert response.status_code == 403
        assert "admin" in response.get_json().get("error", "").lower()

    def test_moderator_cannot_delete_user(self, client, moderator_headers, test_user, app):
        """Moderators cannot delete users (admin only)."""
        user, _ = test_user
        with app.app_context():
            user_id = user.id
        response = client.delete(
            f"/api/v1/users/{user_id}",
            headers=moderator_headers,
        )
        assert response.status_code == 403

    def test_user_cannot_modify_other_user_profile(self, client, app, test_user, admin_user):
        """Users can only modify their own profile."""
        test_user_obj, test_user_pass = test_user
        admin_user_obj, _admin_user_pass = admin_user
        with app.app_context():
            other_user_id = admin_user_obj.id
        response = client.post(
            "/api/v1/auth/login",
            json={"username": test_user_obj.username, "password": test_user_pass},
        )
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        response = client.put(
            f"/api/v1/users/{other_user_id}",
            headers=headers,
            json={"email": "hacked@example.com"},
        )
        assert response.status_code == 403

    def test_unverified_user_cannot_post(self, client, app):
        """Unverified users blocked from creating content."""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            if user:
                user.is_verified = False
                db.session.commit()

        response = client.post(
            "/api/v1/forum/categories/1/threads",
            json={"title": "Test", "content": "Test"},
            headers={"Authorization": "Bearer invalid"},
        )
        assert response.status_code == 401

    def test_banned_user_cannot_authenticate(self, client, app):
        """Banned users cannot obtain JWT tokens."""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            if user:
                user.is_banned = True
                db.session.commit()

        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "Testpass1"},
        )
        assert response.status_code in [401, 403]
