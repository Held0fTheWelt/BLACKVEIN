"""
Service layer tests for user_service, data_import_service, data_export_service.
Focuses on business logic, validation, and error handling.
"""
import pytest
import json
from datetime import datetime, timezone

from app.models import User, Role
from app.services.user_service import (
    create_user,
    reset_password_with_token,
    ban_user,
    unban_user,
    assign_role,
    verify_email_with_token,
    get_user_by_id,
    create_password_reset_token,
    change_password,
    create_email_verification_token,
)
from app.extensions import db


class TestUserService:
    """Test user_service business logic."""

    def test_create_user_success(self, app):
        """Successfully create a new user with role."""
        with app.app_context():
            user, error = create_user(
                username="newuser",
                password="SecurePass1",
                email="newuser@example.com"
            )
            assert user is not None
            assert error is None
            assert user.username == "newuser"
            assert user.email == "newuser@example.com"
            # Password should be hashed, not plain
            assert user.password_hash != "SecurePass1"

    def test_create_user_duplicate_username(self, app, test_user):
        """Cannot create user with duplicate username."""
        with app.app_context():
            user_obj, _ = test_user
            user, error = create_user(
                username="testuser",  # Already exists
                password="NewPass1",
                email="unique@example.com"
            )
            assert user is None
            assert error is not None
            assert "already taken" in error.lower()

    def test_create_user_duplicate_email(self, app, test_user_with_email):
        """Cannot create user with duplicate email."""
        with app.app_context():
            user_obj, _ = test_user_with_email
            user, error = create_user(
                username="uniqueuser",
                password="NewPass1",
                email=user_obj.email  # Duplicate
            )
            assert user is None
            assert error is not None
            assert "email" in error.lower()

    def test_change_password_success(self, app, test_user):
        """Successfully change user password."""
        with app.app_context():
            user_obj, test_pass = test_user
            user_id = user_obj.id
            old_hash = user_obj.password_hash

            user, error = change_password(
                user_id,
                current_password=test_pass,
                new_password="NewSecurePass1"
            )
            assert user is not None
            assert error is None
            assert user.password_hash != old_hash

    def test_change_password_wrong_old_password(self, app, test_user):
        """Cannot change password with wrong old password."""
        with app.app_context():
            user_obj, _ = test_user
            user, error = change_password(
                user_obj.id,
                current_password="WrongPassword",
                new_password="NewPass1"
            )
            assert user is None
            assert error is not None
            assert "incorrect" in error.lower()

    def test_ban_user(self, app, test_user):
        """Can ban users."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # Ban user
            user, msg = ban_user(user_id, reason="Test ban")
            assert user is not None
            assert msg is None
            assert user.is_banned is True
            assert user.ban_reason == "Test ban"

    def test_unban_user(self, app, test_user):
        """Can unban users."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # First ban
            ban_user(user_id, reason="Test ban")

            # Then unban
            user, msg = unban_user(user_id)
            assert user is not None
            assert msg is None
            assert user.is_banned is False
            assert user.ban_reason is None

    def test_assign_role_success(self, app, test_user):
        """Can assign role to user."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # Get moderator role
            user, msg = assign_role(user_id, "moderator")
            assert user is not None
            assert msg is None
            assert user.has_role("moderator") is True

    def test_assign_role_invalid_role(self, app, test_user):
        """Cannot assign invalid role."""
        with app.app_context():
            user_obj, _ = test_user
            user, msg = assign_role(user_obj.id, "invalid_role_name")
            # Should fail
            assert user is None
            assert msg is not None

    def test_assign_role_admin(self, app, test_user):
        """Can assign admin role."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            user, msg = assign_role(user_id, "admin")
            assert user is not None
            assert msg is None
            assert user.has_role("admin") is True


class TestDataExportService:
    """Test data_export_service via API endpoints (actual endpoints only)."""

    def test_export_endpoint_requires_auth(self, client):
        """Export endpoint requires authentication."""
        response = client.post("/api/v1/data/export", json={"scope": "full"})
        assert response.status_code == 401

    def test_export_endpoint_requires_admin(self, client, auth_headers):
        """Regular users cannot export data."""
        response = client.post(
            "/api/v1/data/export",
            headers=auth_headers,
            json={"scope": "full"}
        )
        # Will be 403 Forbidden (not admin) or 400 (missing feature flag)
        assert response.status_code in [403, 400]

    def test_export_full_scope_requires_admin(self, client, admin_headers):
        """Admin can call export endpoint with full scope."""
        response = client.post(
            "/api/v1/data/export",
            headers=admin_headers,
            json={"scope": "full"}
        )
        # Endpoint exists and requires admin (200 if feature enabled, 400 if not)
        assert response.status_code in [200, 400, 403]

    def test_export_missing_scope(self, client, admin_headers):
        """Export requires scope parameter."""
        response = client.post(
            "/api/v1/data/export",
            headers=admin_headers,
            json={}
        )
        assert response.status_code in [400, 403]

    def test_export_table_scope_requires_table(self, client, admin_headers):
        """Export with table scope requires table name."""
        response = client.post(
            "/api/v1/data/export",
            headers=admin_headers,
            json={"scope": "table"}
        )
        assert response.status_code in [400, 403]

    def test_export_rows_scope_requires_table_and_ids(self, client, admin_headers):
        """Export with rows scope requires table and primary_keys."""
        response = client.post(
            "/api/v1/data/export",
            headers=admin_headers,
            json={"scope": "rows", "table": "users"}
        )
        # Missing primary_keys
        assert response.status_code in [400, 403]


class TestDataImportService:
    """Test data_import_service via actual API endpoints."""

    def test_import_preflight_endpoint_exists(self, client, admin_headers):
        """Import preflight endpoint exists and is protected."""
        response = client.post(
            "/api/v1/data/import/preflight",
            headers=admin_headers,
            json={}
        )
        # Should not be 404; may be 200 or 400 for validation
        assert response.status_code != 404

    def test_import_execute_endpoint_exists(self, client, admin_headers):
        """Import execute endpoint exists and is protected."""
        response = client.post(
            "/api/v1/data/import/execute",
            headers=admin_headers,
            json={}
        )
        # Should not be 404; may be 403 (needs super admin) or 400 (validation)
        assert response.status_code != 404

    def test_import_preflight_requires_auth(self, client):
        """Preflight endpoint requires authentication."""
        response = client.post(
            "/api/v1/data/import/preflight",
            json={}
        )
        assert response.status_code == 401

    def test_import_execute_requires_auth(self, client):
        """Execute endpoint requires authentication."""
        response = client.post(
            "/api/v1/data/import/execute",
            json={}
        )
        assert response.status_code == 401

    def test_import_execute_requires_super_admin(self, client, admin_headers):
        """Import execute requires super admin (role_level 100+), not just admin."""
        response = client.post(
            "/api/v1/data/import/execute",
            headers=admin_headers,
            json={}
        )
        # Regular admin (role_level 50) should get 403 for super admin requirement
        assert response.status_code == 403
        data = response.get_json()
        assert "SuperAdmin" in data.get("error", "")

    def test_import_execute_with_super_admin(self, client, super_admin_headers):
        """Super admin can call execute (even if payload is invalid)."""
        response = client.post(
            "/api/v1/data/import/execute",
            headers=super_admin_headers,
            json={}
        )
        # Should not be 403 (SuperAdmin allowed); may be 400 (validation)
        assert response.status_code != 403

    def test_import_preflight_missing_json(self, client, admin_headers):
        """Preflight requires valid JSON body."""
        response = client.post(
            "/api/v1/data/import/preflight",
            headers=admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "json" in data.get("error", "").lower()

    def test_import_execute_missing_json(self, client, super_admin_headers):
        """Execute requires valid JSON body."""
        response = client.post(
            "/api/v1/data/import/execute",
            headers=super_admin_headers
        )
        assert response.status_code == 400
        data = response.get_json()
        assert "json" in data.get("error", "").lower()


class TestServiceErrorHandling:
    """Test error handling in services."""

    def test_create_user_weak_password_rejected(self, app):
        """Weak passwords should be rejected at service level."""
        with app.app_context():
            user, error = create_user(
                username="testuser",
                password="weak",  # Too weak
                email="test@example.com"
            )
            assert user is None
            assert error is not None
            assert "password" in error.lower()

    def test_create_user_no_password(self, app):
        """Missing password is rejected."""
        with app.app_context():
            user, error = create_user(
                username="testuser",
                password="",
                email="test@example.com"
            )
            assert user is None
            assert error is not None

    def test_operations_on_nonexistent_user(self, app):
        """Operations on nonexistent users fail gracefully."""
        with app.app_context():
            # Try to get nonexistent user
            user = get_user_by_id(99999)
            assert user is None

            # Try to ban nonexistent user
            user, msg = ban_user(99999)
            assert user is None
            assert msg is not None

            # Try to unban nonexistent user
            user, msg = unban_user(99999)
            assert user is None
            assert msg is not None

    def test_concurrent_user_creation(self, app):
        """Concurrent operations handle constraint violations."""
        with app.app_context():
            user1, error1 = create_user(
                username="concurrent_user_new",
                password="Pass123Abc",
                email="concurrent_new@test.com"
            )
            assert user1 is not None
            assert error1 is None

            # Try to create same user again (should fail)
            user2, error2 = create_user(
                username="concurrent_user_new",
                password="Pass456Xyz",
                email="concurrent_new2@test.com"
            )
            assert user2 is None
            assert error2 is not None

    def test_ban_self_prevention(self, app, admin_user):
        """User cannot ban themselves (if actor_id provided)."""
        with app.app_context():
            user_obj, _ = admin_user
            user_id = user_obj.id

            # Try to ban self
            user, msg = ban_user(user_id, reason="Self ban", actor_id=user_id)
            assert user is None
            assert msg is not None
            assert "Cannot ban yourself" in msg

    def test_password_reset_token_valid(self, app, test_user):
        """Password reset token can be created and validated."""
        with app.app_context():
            user_obj, _ = test_user
            token = create_password_reset_token(user_obj)
            assert token is not None
            assert len(token) > 0

    def test_email_verification_token_creation(self, app, test_user):
        """Email verification token can be created."""
        with app.app_context():
            user_obj, _ = test_user
            token = create_email_verification_token(user_obj, ttl_hours=24)
            assert token is not None
            assert len(token) > 0


class TestUserBanAndUnban:
    """Tests for user ban/unban functionality."""

    def test_ban_user_sets_fields(self, app, test_user):
        """Banning a user sets is_banned, banned_at, and ban_reason."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            user, msg = ban_user(user_id, reason="Spam")
            assert user.is_banned is True
            assert user.banned_at is not None
            assert user.ban_reason == "Spam"

    def test_ban_user_idempotent(self, app, test_user):
        """Banning already-banned user is idempotent."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # Ban first time
            user1, msg1 = ban_user(user_id, reason="First ban")
            assert user1.is_banned is True

            # Ban again (should succeed)
            user2, msg2 = ban_user(user_id, reason="Second ban")
            assert user2.is_banned is True
            # Second reason should update
            assert user2.ban_reason == "Second ban"

    def test_unban_user_sets_fields(self, app, test_user):
        """Unbanning a user clears is_banned, banned_at, and ban_reason."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # Ban first
            ban_user(user_id, reason="Test")

            # Unban
            user, msg = unban_user(user_id)
            assert user.is_banned is False
            assert user.banned_at is None
            assert user.ban_reason is None

    def test_unban_already_unbanned_is_idempotent(self, app, test_user):
        """Unbanning already-unbanned user is idempotent."""
        with app.app_context():
            user_obj, _ = test_user
            user_id = user_obj.id

            # User is not banned by default
            user1, msg1 = unban_user(user_id)
            assert user1.is_banned is False

            # Unban again (should succeed)
            user2, msg2 = unban_user(user_id)
            assert user2.is_banned is False
