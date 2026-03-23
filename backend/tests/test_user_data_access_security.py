"""
Security tests for user data access control.
Verifies that private user endpoint restricts cross-user access and prevents
sensitive data leaks (HIGH severity vulnerability fix).
"""
import pytest
from werkzeug.security import generate_password_hash
from app.extensions import db
from app.models.user import User
from app.models.role import Role


@pytest.fixture
def setup_test_users(app, client):
    """Create test users: regular user, another regular user, and admin."""
    with app.app_context():
        # Get roles (should exist from seeding in conftest)
        admin_role = Role.query.filter_by(name="admin").first()
        user_role = Role.query.filter_by(name="user").first()

        # Create regular user 1
        user1 = User(
            username="user1",
            email="user1@example.com",
            password_hash=generate_password_hash("TestPassword123"),
            role_id=user_role.id,
            role_level=0
        )
        db.session.add(user1)
        db.session.commit()

        # Create regular user 2
        user2 = User(
            username="user2",
            email="user2@example.com",
            password_hash=generate_password_hash("TestPassword123"),
            role_id=user_role.id,
            role_level=0
        )
        db.session.add(user2)
        db.session.commit()

        # Create admin user
        admin_user = User(
            username="admin",
            email="admin@example.com",
            password_hash=generate_password_hash("TestPassword123"),
            role_id=admin_role.id,
            role_level=100
        )
        db.session.add(admin_user)
        db.session.commit()

        return {
            "user1_id": user1.id,
            "user2_id": user2.id,
            "admin_id": admin_user.id,
        }


def login_user(client, username):
    """Helper to login a user and return JWT token."""
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": "TestPassword123"},
        content_type="application/json",
    )
    if response.status_code == 200:
        return response.get_json()["access_token"]
    return None


class TestUserDataAccessSecurity:
    """Tests for cross-user data access vulnerability (HIGH severity)."""

    def test_user_can_view_own_profile_with_email(self, client, setup_test_users):
        """User viewing own profile should get email and full data."""
        user_id = setup_test_users["user1_id"]
        token = login_user(client, "user1")

        response = client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == user_id
        assert data["username"] == "user1"
        assert "email" in data  # Self can see email
        assert data["email"] == "user1@example.com"

    def test_user_cannot_view_other_user_profile(self, client, setup_test_users):
        """CRITICAL FIX: Non-admin user viewing other user's profile must get 403."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        token = login_user(client, "user1")

        response = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # SECURITY: Must return 403 Forbidden, not 200 with limited data
        assert response.status_code == 403
        data = response.get_json()
        assert "error" in data
        assert "Forbidden" in data["error"]

    def test_user_cannot_leak_other_user_email(self, client, setup_test_users):
        """VULNERABILITY FIX: User endpoint should NOT leak email of other users."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        token = login_user(client, "user1")

        response = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        # Should be 403 before even getting user data
        assert response.status_code == 403
        # Email should not be present in error response
        assert "user2@example.com" not in str(response.data)

    def test_admin_can_view_any_user_with_full_data(self, client, setup_test_users):
        """Admin viewing other user should get email, ban status, and areas."""
        user1_id = setup_test_users["user1_id"]
        token = login_user(client, "admin")

        response = client.get(
            f"/api/v1/users/{user1_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == user1_id
        assert data["username"] == "user1"
        assert "email" in data  # Admin can see email
        assert data["email"] == "user1@example.com"
        # Admin should see ban-related fields
        assert "is_banned" in data
        assert "banned_at" in data
        assert "ban_reason" in data

    def test_unauthorized_user_cannot_access_endpoint(self, client, setup_test_users):
        """Request without JWT token should be rejected."""
        user_id = setup_test_users["user1_id"]

        response = client.get(f"/api/v1/users/{user_id}")

        assert response.status_code == 401

    def test_admin_can_view_own_profile(self, client, setup_test_users):
        """Admin viewing own profile should get all data."""
        admin_id = setup_test_users["admin_id"]
        token = login_user(client, "admin")

        response = client.get(
            f"/api/v1/users/{admin_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == admin_id
        assert "email" in data
        assert "is_banned" in data

    def test_nonexistent_user_returns_404(self, client, setup_test_users):
        """Accessing non-existent user returns 404 if you're authorized to try."""
        token = login_user(client, "admin")  # Admin can try to access any user

        response = client.get(
            "/api/v1/users/99999",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 404

    def test_public_profile_endpoint_available_to_all(self, client, setup_test_users):
        """Public /profile endpoint should be accessible without authentication."""
        user1_id = setup_test_users["user1_id"]

        # Access without token (public endpoint)
        response = client.get(f"/api/v1/users/{user1_id}/profile")

        assert response.status_code == 200
        data = response.get_json()
        assert data["id"] == user1_id
        # Public profile should NOT include email
        assert "email" not in data or data.get("email") is None

    def test_private_endpoint_vs_public_endpoint_distinction(self, client, setup_test_users):
        """Verify that /users/<id> is private and /users/<id>/profile is public."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        user_token = login_user(client, "user1")

        # Private endpoint: User viewing other user should be 403
        private_response = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert private_response.status_code == 403

        # Public endpoint: Viewing other user's public profile is OK
        public_response = client.get(f"/api/v1/users/{user2_id}/profile")
        assert public_response.status_code == 200
        # Public profile has restricted data
        public_data = public_response.get_json()
        assert "id" in public_data
        assert "username" in public_data

    def test_cross_user_access_attempts_blocked(self, client, setup_test_users):
        """SECURITY: Multiple cross-user access attempts should all be blocked."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        admin_id = setup_test_users["admin_id"]
        user_token = login_user(client, "user1")

        # Attempt to access user2
        response1 = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response1.status_code == 403

        # Attempt to access admin
        response2 = client.get(
            f"/api/v1/users/{admin_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response2.status_code == 403

    def test_email_field_conditional_on_permission(self, client, setup_test_users):
        """Email field should only be present when viewer has permission."""
        user_id = setup_test_users["user1_id"]
        user_token = login_user(client, "user1")

        # User viewing self: email included
        response_self = client.get(
            f"/api/v1/users/{user_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response_self.status_code == 200
        data = response_self.get_json()
        assert "email" in data
        assert data["email"] == "user1@example.com"


class TestDataLeakagePrevention:
    """Tests to ensure sensitive data is not leaked through any vector."""

    def test_error_response_does_not_leak_user_data(self, client, setup_test_users):
        """403 error response should not contain any user's sensitive data."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        token = login_user(client, "user1")

        response = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {token}"}
        )

        assert response.status_code == 403
        error_text = str(response.data)

        # Verify no sensitive data leakage in error response
        assert "user2@example.com" not in error_text
        assert "password" not in error_text.lower()

    def test_ban_information_restricted_to_admin(self, client, setup_test_users):
        """Ban status should only be visible to admins and in their own profile if banned."""
        user1_id = setup_test_users["user1_id"]
        user_token = login_user(client, "user1")

        # User viewing self: basic data shown, ban info not included unless banned
        response_self = client.get(
            f"/api/v1/users/{user1_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response_self.status_code == 200
        # When viewing self, basic data is shown (email, preferences, etc.)
        data = response_self.get_json()
        assert "email" in data  # Users can see their own email
        assert "is_banned" not in data  # Ban info not shown unless actually banned

    def test_role_level_visible_but_areas_restricted(self, client, setup_test_users):
        """Role level is public, but areas (with moderation features) are admin-only."""
        user1_id = setup_test_users["user1_id"]
        user2_id = setup_test_users["user2_id"]
        user_token = login_user(client, "user1")

        # User cannot access other user data at all
        response = client.get(
            f"/api/v1/users/{user2_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response.status_code == 403

        # User viewing self: should see role_level
        response_self = client.get(
            f"/api/v1/users/{user1_id}",
            headers={"Authorization": f"Bearer {user_token}"}
        )
        assert response_self.status_code == 200
        data = response_self.get_json()
        # Users can see their own role and role_level
        assert "role" in data
        assert "role_level" in data
        assert "area_ids" in data  # area_ids always included
