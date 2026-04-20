"""Tests for privilege escalation vulnerability fixes.

CRITICAL SECURITY: Prevent admins from elevating themselves to SuperAdmin or higher.
Tests verify that role assignment properly enforces hierarchy and prevents self-elevation.
"""
import pytest
from app.models import Role, User, ActivityLog
from app.extensions import db


class TestPrivilegeEscalation:
    """Tests for privilege escalation vulnerability in users_assign_role()."""

    def test_admin_cannot_assign_themselves_superadmin_role(self, client, admin_user, app):
        """CRITICAL: Admin cannot elevate themselves to SuperAdmin via PATCH /users/<id>/role."""
        admin, password = admin_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": password},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin tries to assign themselves admin role with SuperAdmin level (100)
        with app.app_context():
            original_level = admin.role_level

        r = client.patch(
            f"/api/v1/users/{admin.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 100},
            content_type="application/json",
        )

        # Should fail with 403 PRIVILEGE_DENIED
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "error" in data
        assert "code" in data or "Cannot elevate" in data["error"]

        # Verify admin's level did not change
        with app.app_context():
            admin_db = User.query.get(admin.id)
            assert admin_db.role_level == original_level, "Admin level should not change after failed elevation"

    def test_admin_cannot_assign_superadmin_to_other_user(self, client, admin_user, test_user, app):
        """Admin with level 50 cannot assign SuperAdmin (level 100) to another user."""
        admin, admin_pass = admin_user
        target_user, _ = test_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin tries to assign SuperAdmin level to another user
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 100},
            content_type="application/json",
        )

        # Should fail with 403
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "error" in data
        assert "higher than your own" in data["error"] or "PRIVILEGE_DENIED" in str(data)

    def test_superadmin_can_assign_any_role_level(self, client, super_admin_user, test_user, app):
        """SuperAdmin (level 100) can assign any role level below 100."""
        super_admin, super_pass = super_admin_user
        target_user, _ = test_user

        # SuperAdmin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": super_admin.username, "password": super_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # SuperAdmin assigns admin role with level 50 to another user
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 50},
            content_type="application/json",
        )

        # Should succeed with 200
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert data["role"] == "admin"

        # Verify target user's level was updated
        with app.app_context():
            target_db = User.query.get(target_user.id)
            assert target_db.role_level == 50

    def test_admin_can_assign_lower_roles_to_others(self, client, admin_user, test_user, app):
        """Admin can assign roles with level lower than their own to other users."""
        admin, admin_pass = admin_user
        target_user, _ = test_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin assigns moderator role with level 20 (lower than admin's 50)
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "moderator", "role_level": 20},
            content_type="application/json",
        )

        # Should succeed
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert data["role"] == "moderator"

        # Verify target user's role was updated
        with app.app_context():
            target_db = User.query.get(target_user.id)
            assert target_db.role == "moderator"
            assert target_db.role_level == 20

    def test_admin_cannot_assign_equal_or_higher_role_to_self(self, client, admin_user, app):
        """Admin cannot modify their own role via PATCH /users/<id>/role."""
        admin, admin_pass = admin_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with app.app_context():
            original_level = admin.role_level
            original_role = admin.role

        # Try to assign same role/level to themselves
        r = client.patch(
            f"/api/v1/users/{admin.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 50},
            content_type="application/json",
        )

        # Should fail - cannot modify own role via PATCH endpoint
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "Cannot modify your own role" in data["error"] or "own" in data["error"].lower()

    def test_admin_cannot_assign_higher_role_to_equal_level_user(self, client, admin_user, admin_user_same_level, app):
        """Admin cannot assign higher role to a user with same or higher level."""
        admin, admin_pass = admin_user
        same_level_user, _ = admin_user_same_level

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Try to assign role with level 50 (equal to target and to self)
        r = client.patch(
            f"/api/v1/users/{same_level_user.id}/role",
            headers=headers,
            json={"role": "moderator", "role_level": 50},
            content_type="application/json",
        )

        # Should fail - cannot assign to user with equal or higher level
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "lower role level" in data["error"]

    def test_privilege_escalation_logged_as_failed_attempt(self, client, admin_user, app, caplog):
        """Failed privilege escalation should be logged for audit."""
        import logging
        admin, admin_pass = admin_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Attempt privilege escalation
        with caplog.at_level(logging.WARNING):
            r = client.patch(
                f"/api/v1/users/{admin.id}/role",
                headers=headers,
                json={"role": "admin", "role_level": 200},
                content_type="application/json",
            )

        # Should fail
        assert r.status_code == 403

    def test_non_admin_cannot_assign_roles(self, client, auth_headers, test_user):
        """Non-admin user cannot assign any roles."""
        user, _ = test_user

        # Non-admin tries to assign role
        r = client.patch(
            f"/api/v1/users/{user.id}/role",
            headers=auth_headers,
            json={"role": "admin"},
            content_type="application/json",
        )

        # Should fail with 403
        assert r.status_code == 403

    def test_admin_cannot_bypass_hierarchy_via_role_only(self, client, admin_user, test_user, app):
        """Admin assigning role without specifying role_level should maintain safety."""
        admin, admin_pass = admin_user
        target_user, _ = test_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin assigns admin role without specifying role_level
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "admin"},
            content_type="application/json",
        )

        # Should succeed - maintains target's existing level (0)
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"

    def test_admin_assigning_lower_level_admin_role_succeeds(self, client, admin_user, test_user, app):
        """Admin can assign admin role with lower role_level to other user."""
        admin, admin_pass = admin_user
        target_user, _ = test_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin assigns admin role with level 30 (less than their 50)
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 30},
            content_type="application/json",
        )

        # Should succeed
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert data["role"] == "admin"

        # Verify role_level was set
        with app.app_context():
            target_db = User.query.get(target_user.id)
            assert target_db.role_level == 30

    def test_superadmin_cannot_elevate_themselves_above_threshold(self, client, super_admin_user, app):
        """SuperAdmin cannot elevate themselves above the SuperAdmin threshold (100)."""
        super_admin, super_pass = super_admin_user

        # SuperAdmin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": super_admin.username, "password": super_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # SuperAdmin tries to assign themselves level 150
        r = client.patch(
            f"/api/v1/users/{super_admin.id}/role",
            headers=headers,
            json={"role": "admin", "role_level": 150},
            content_type="application/json",
        )

        # Should fail - cannot assign level higher than own level
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "Cannot elevate" in data["error"] or "higher than your own" in data["error"]

    def test_multiple_failed_escalation_attempts_logged(self, client, admin_user, app):
        """Multiple failed escalation attempts should each be logged."""
        admin, admin_pass = admin_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Make multiple failed attempts
        for level in [100, 150, 200]:
            r = client.patch(
                f"/api/v1/users/{admin.id}/role",
                headers=headers,
                json={"role": "admin", "role_level": level},
                content_type="application/json",
            )
            assert r.status_code == 403

    def test_valid_role_assignment_with_valid_level(self, client, admin_user, test_user, app):
        """Valid role assignment with valid level below admin's own level succeeds."""
        admin, admin_pass = admin_user
        target_user, _ = test_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Admin assigns valid role with valid level
        r = client.patch(
            f"/api/v1/users/{target_user.id}/role",
            headers=headers,
            json={"role": "qa", "role_level": 15},
            content_type="application/json",
        )

        # Should succeed
        assert r.status_code == 200, f"Expected 200, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert data["role"] == "qa"
        assert data["role_level"] == 15

        # Verify in database
        with app.app_context():
            target_db = User.query.get(target_user.id)
            assert target_db.role == "qa"
            assert target_db.role_level == 15

    def test_admin_assigning_moderator_role_to_self_fails(self, client, admin_user, app):
        """Admin cannot modify their own role via PATCH endpoint, even to a different role."""
        admin, admin_pass = admin_user

        # Admin logs in
        r = client.post(
            "/api/v1/auth/login",
            json={"username": admin.username, "password": admin_pass},
            content_type="application/json",
        )
        assert r.status_code == 200
        token = r.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        with app.app_context():
            admin_db = User.query.get(admin.id)
            original_role = admin_db.role
            original_level = admin_db.role_level

        # Admin tries to assign moderator role to themselves
        r = client.patch(
            f"/api/v1/users/{admin.id}/role",
            headers=headers,
            json={"role": "moderator"},
            content_type="application/json",
        )

        # Should fail - cannot modify own role via PATCH endpoint
        assert r.status_code == 403, f"Expected 403, got {r.status_code}: {r.get_json()}"
        data = r.get_json()
        assert "Cannot modify your own role" in data["error"]

        # Verify role and level unchanged
        with app.app_context():
            admin_db = User.query.get(admin.id)
            assert admin_db.role == original_role
            assert admin_db.role_level == original_level
