"""
Comprehensive test suite for account lockout mechanism.
Tests: failed login tracking, account locking after 5 attempts, 429 response,
and successful login resetting the counter.
"""

import pytest
from datetime import datetime, timedelta, timezone
from werkzeug.security import generate_password_hash

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Role


@pytest.fixture
def app():
    """Create and configure a test app."""
    application = create_app(TestingConfig)
    with application.app_context():
        db.create_all()
        from app.models.role import ensure_roles_seeded
        from app.models.area import ensure_areas_seeded
        ensure_roles_seeded()
        ensure_areas_seeded()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """Test client."""
    return app.test_client()


@pytest.fixture
def test_user(app):
    """Create a test user."""
    with app.app_context():
        user_role = Role.query.filter_by(name=Role.NAME_USER).first()
        user = User(
            username="testuser",
            email="testuser@example.com",
            password_hash=generate_password_hash("ValidPassword1"),
            role_id=user_role.id,
            email_verified_at=datetime.now(timezone.utc),
        )
        db.session.add(user)
        db.session.commit()
        return user


class TestAccountLockoutMechanism:
    """Test suite for account lockout."""

    def test_initial_failed_login_attempts_zero(self, app, test_user):
        """User starts with failed_login_attempts = 0."""
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None

    def test_failed_login_increments_counter(self, client, test_user):
        """Each failed login increments failed_login_attempts."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPassword1"},
        )
        assert response.status_code == 401

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 1

    def test_failed_login_increments_to_5(self, client, test_user):
        """5 failed logins increment counter to 5."""
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )
            assert response.status_code == 401

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 5

    def test_account_locked_after_5_failures(self, client, test_user):
        """After 5 failed logins, locked_until is set to now + 15 minutes."""
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )
            assert response.status_code == 401

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.locked_until is not None
            now = datetime.now(timezone.utc)
            # locked_until should be approximately 15 minutes from now
            locked_until = user.locked_until
            if locked_until.tzinfo is None:
                locked_until = locked_until.replace(tzinfo=timezone.utc)
            delta = (locked_until - now).total_seconds()
            assert 14 * 60 < delta < 16 * 60  # Allow 1 minute variance

    def test_6th_login_attempt_returns_429_locked(self, client, test_user):
        """6th login attempt on locked account returns 429."""
        # Lock the account with 5 failed attempts
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )
            assert response.status_code == 401

        # 6th attempt should return 429
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPassword1"},
        )
        assert response.status_code == 429
        data = response.get_json()
        assert "temporarily locked" in data["error"].lower()

    def test_successful_login_resets_counter(self, client, test_user):
        """Successful login resets failed_login_attempts to 0 and clears locked_until."""
        # Make 2 failed attempts
        for i in range(2):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )
            assert response.status_code == 401

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 2

        # Login successfully
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "ValidPassword1"},
        )
        assert response.status_code == 200

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None

    def test_successful_login_after_unlock_timeout(self, app, client, test_user):
        """Login succeeds after 15+ minutes have passed since lock."""
        # Lock the account
        for i in range(5):
            response = client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )
            assert response.status_code == 401

        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            # Manually move locked_until to the past
            user.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
            db.session.commit()

        # Now login should succeed
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "ValidPassword1"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data

    def test_locked_account_blocked_before_password_check(self, app, client, test_user):
        """Locked account is rejected even before password validation."""
        # Lock the account
        with app.app_context():
            user = User.query.filter_by(username="testuser").first()
            user.failed_login_attempts = 5
            user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
            db.session.commit()

        # Try login with correct password - should still be 429
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "ValidPassword1"},
        )
        assert response.status_code == 429
        data = response.get_json()
        assert "temporarily locked" in data["error"].lower()

    def test_unknown_username_no_counter_increment(self, client):
        """Login with non-existent username doesn't increment any counter."""
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "nonexistent", "password": "SomePassword1"},
        )
        assert response.status_code == 401

        # Since user doesn't exist, no counter should be incremented
        # (We can't test this directly, but we can verify no errors occur)

    def test_multiple_consecutive_locks(self, client, test_user):
        """Account can be locked, unlocked, and locked again."""
        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()

        # First lock
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            first_lock_time = user.locked_until
            if first_lock_time and first_lock_time.tzinfo is None:
                first_lock_time = first_lock_time.replace(tzinfo=timezone.utc)
            assert user.failed_login_attempts == 5

        # Simulate unlock by clearing lock timestamp
        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            user.locked_until = None
            user.failed_login_attempts = 0
            db.session.commit()

        # Successful login
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "ValidPassword1"},
        )
        assert response.status_code == 200

        # Counter is reset
        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 0
            assert user.locked_until is None

        # Second lock
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )

        with client.application.app_context():
            user = User.query.filter_by(username="testuser").first()
            assert user.failed_login_attempts == 5
            assert user.locked_until is not None
            second_lock_time = user.locked_until
            if second_lock_time and second_lock_time.tzinfo is None:
                second_lock_time = second_lock_time.replace(tzinfo=timezone.utc)
            assert second_lock_time > first_lock_time

    def test_lockout_activity_logging(self, client, test_user):
        """Lock-related activity is logged."""
        from app.models.activity_log import ActivityLog

        with client.application.app_context():
            initial_log_count = ActivityLog.query.count()

        # Make 5 failed attempts
        for i in range(5):
            client.post(
                "/api/v1/auth/login",
                json={"username": "testuser", "password": "WrongPassword1"},
            )

        with client.application.app_context():
            logs = ActivityLog.query.filter_by(action="login_failed").all()
            assert len(logs) >= 5  # At least 5 failed login logs

        # Try 6th attempt on locked account
        response = client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "WrongPassword1"},
        )
        assert response.status_code == 429

        with client.application.app_context():
            logs = ActivityLog.query.filter_by(action="login_blocked_locked").all()
            assert len(logs) >= 1  # At least 1 blocked login log
