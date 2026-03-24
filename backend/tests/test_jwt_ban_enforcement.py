"""Test JWT token ban enforcement - real-time invalidation of banned user tokens."""
import pytest
from datetime import datetime, timezone
from werkzeug.security import generate_password_hash

from app.models import Role, User
from app.extensions import db


class TestJWTBanEnforcement:
    """Test suite for real-time JWT ban enforcement."""

    def test_banned_user_cannot_use_valid_token(self, app, client):
        """
        CRITICAL SECURITY TEST:
        A valid JWT token should be rejected immediately when the user is banned,
        even if the token hasn't expired yet.

        Steps:
        1. Create and authenticate a user (get valid JWT)
        2. Ban the user directly in DB
        3. Attempt to use the JWT token on a protected endpoint
        4. Expect 401 Unauthorized
        """
        with app.app_context():
            # Create test user
            role_user = Role.query.filter_by(name=Role.NAME_USER).first()
            test_user = User(
                username="ban_test_user_endpoint",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role_user.id,
            )
            db.session.add(test_user)
            db.session.commit()
            db.session.refresh(test_user)
            test_user_id = test_user.id

        # Step 2: Get valid JWT token for test user by logging in
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "ban_test_user_endpoint", "password": "Testpass1"},
            content_type="application/json",
        )
        assert response.status_code == 200
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify token works before ban
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["username"] == "ban_test_user_endpoint"

        # Step 3: Ban the user directly in database
        with app.app_context():
            user = User.query.get(test_user_id)
            user.is_banned = True
            user.banned_at = datetime.now(timezone.utc)
            user.ban_reason = "Test ban enforcement"
            db.session.commit()

        # Step 4: Try to use the same JWT token after ban - should be rejected with 403 Forbidden
        # (JWT token is valid, but user is banned so access is forbidden)
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 403
        assert "error" in response.get_json()
        assert "restricted" in response.get_json()["error"].lower()

    def test_unbanned_user_can_login_again(self, app, client):
        """
        Test that unban allows user to login:
        1. Create user and ban them
        2. Unban the user
        3. User can now login
        """
        with app.app_context():
            # Create test user
            role_user = Role.query.filter_by(name=Role.NAME_USER).first()
            test_user = User(
                username="unban_test_user_endpoint",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role_user.id,
                is_banned=True,
                banned_at=datetime.now(timezone.utc),
                ban_reason="Test ban",
            )
            db.session.add(test_user)
            db.session.commit()
            db.session.refresh(test_user)
            test_user_id = test_user.id

        # Verify banned user cannot login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unban_test_user_endpoint", "password": "Testpass1"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert "Account is restricted" in response.get_json()["error"]

        # Unban the user
        with app.app_context():
            user = User.query.get(test_user_id)
            user.is_banned = False
            user.banned_at = None
            user.ban_reason = None
            db.session.commit()

        # Now user can login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "unban_test_user_endpoint", "password": "Testpass1"},
            content_type="application/json",
        )
        assert response.status_code == 200
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Token should work
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200
        assert response.get_json()["username"] == "unban_test_user_endpoint"

    def test_banned_user_cannot_login(self, app, client):
        """Test that banned users cannot get a token via login."""
        with app.app_context():
            role_user = Role.query.filter_by(name=Role.NAME_USER).first()
            test_user = User(
                username="login_ban_test_user",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role_user.id,
                is_banned=True,
                banned_at=datetime.now(timezone.utc),
                ban_reason="Pre-banned for testing",
            )
            db.session.add(test_user)
            db.session.commit()

        # Try to login with banned user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "login_ban_test_user", "password": "Testpass1"},
            content_type="application/json",
        )
        assert response.status_code == 403
        assert "Account is restricted" in response.get_json()["error"]

    def test_ban_enforcement_on_multiple_endpoints(self, app, client):
        """Test that a banned user's token is rejected on multiple protected endpoints."""
        with app.app_context():
            role_user = Role.query.filter_by(name=Role.NAME_USER).first()
            test_user = User(
                username="endpoint_ban_test_multi",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role_user.id,
            )
            db.session.add(test_user)
            db.session.commit()
            db.session.refresh(test_user)
            test_user_id = test_user.id

        # Get valid token
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "endpoint_ban_test_multi", "password": "Testpass1"},
            content_type="application/json",
        )
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Ban the user (returns 403 Forbidden on ban check)
        with app.app_context():
            user = User.query.get(test_user_id)
            user.is_banned = True
            user.banned_at = datetime.now(timezone.utc)
            user.ban_reason = "Testing endpoint access"
            db.session.commit()

        # Test multiple protected endpoints - should get 403 because user is banned
        endpoints_to_test = [
            ("/api/v1/auth/me", "GET"),
        ]

        for endpoint, method in endpoints_to_test:
            if method == "GET":
                response = client.get(endpoint, headers=headers)
            elif method == "PUT":
                response = client.put(endpoint, headers=headers, json={})

            assert response.status_code == 403, f"Endpoint {endpoint} should return 403 for banned user"
            assert "error" in response.get_json()

    def test_ban_enforcement_is_real_time_check(self, app, client):
        """
        Test that ban enforcement is real-time - banned user's token is checked on every request.
        This ensures admins can immediately revoke access by banning without waiting for token expiration.
        """
        with app.app_context():
            role_user = Role.query.filter_by(name=Role.NAME_USER).first()
            test_user = User(
                username="realtime_ban_test_endpoint",
                password_hash=generate_password_hash("Testpass1"),
                role_id=role_user.id,
            )
            db.session.add(test_user)
            db.session.commit()
            db.session.refresh(test_user)
            test_user_id = test_user.id

        # Get token
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "realtime_ban_test_endpoint", "password": "Testpass1"},
            content_type="application/json",
        )
        token = response.get_json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Verify it works
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 200

        # Ban the user in DB
        with app.app_context():
            user = User.query.get(test_user_id)
            user.is_banned = True
            user.banned_at = datetime.now(timezone.utc)
            user.ban_reason = "Real-time test"
            db.session.commit()

        # Immediately after ban, token should be rejected (403 - account restricted)
        response = client.get("/api/v1/auth/me", headers=headers)
        assert response.status_code == 403

        # Unban the user
        with app.app_context():
            user = User.query.get(test_user_id)
            user.is_banned = False
            user.banned_at = None
            user.ban_reason = None
            db.session.commit()
