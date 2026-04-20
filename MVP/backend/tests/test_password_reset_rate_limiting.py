"""
Integration tests for password reset endpoint brute force protection.
Tests rate limiting (5 per hour per email), token one-time use, and expiration.
"""
import pytest
import time
from unittest.mock import patch
from datetime import datetime, timedelta, timezone

from app.extensions import db
from app.models import User
from app.models.password_reset_token import PasswordResetToken


class TestPasswordResetRateLimiting:
    """Test brute force protection on password reset endpoints."""

    def test_forgot_password_rate_limit_5_per_hour(self, app, client):
        """Test that forgot-password endpoint is rate limited to 5 per hour per email."""
        with app.app_context():
            from app.services.user_service import create_user
            user, err = create_user("testuser", "InitPass123!", email="bruteforce@example.com")
            assert err is None

            # First 5 requests should succeed
            for i in range(5):
                response = client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "bruteforce@example.com"},
                    content_type="application/json",
                )
                assert response.status_code == 200, f"Request {i+1} should succeed"
                assert "password reset link has been sent" in response.get_json()["message"]

            # 6th request should be rate limited (429 Too Many Requests)
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "bruteforce@example.com"},
                content_type="application/json",
            )
            assert response.status_code == 429, "6th request should hit rate limit"

    def test_forgot_password_rate_limit_per_email(self, app, client):
        """Test that rate limit is per email, not per IP."""
        with app.app_context():
            from app.services.user_service import create_user
            user1, err = create_user("user1", "InitPass123!", email="user1@example.com")
            assert err is None
            user2, err = create_user("user2", "InitPass123!", email="user2@example.com")
            assert err is None

            # Use up 5 requests on user1's email
            for i in range(5):
                response = client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "user1@example.com"},
                    content_type="application/json",
                )
                assert response.status_code == 200

            # 6th request on user1's email should fail
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "user1@example.com"},
                content_type="application/json",
            )
            assert response.status_code == 429

            # But user2's email should still work (fresh limit)
            for i in range(5):
                response = client.post(
                    "/api/v1/auth/forgot-password",
                    json={"email": "user2@example.com"},
                    content_type="application/json",
                )
                assert response.status_code == 200, f"User2 request {i+1} should succeed"

            # 6th request on user2's email should also fail
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "user2@example.com"},
                content_type="application/json",
            )
            assert response.status_code == 429

    def test_reset_password_rate_limit_5_per_hour(self, app, client):
        """Test that reset-password endpoint is rate limited to 5 per hour per IP."""
        with app.app_context():
            from app.services.user_service import create_user, create_password_reset_token
            user, err = create_user("resetuser", "InitPass123!", email="reset@example.com")
            assert err is None

            # Generate 6 reset tokens (for 6 attempts)
            tokens = []
            for _ in range(6):
                token = create_password_reset_token(user)
                tokens.append(token)

            # First 5 requests should succeed
            for i in range(5):
                response = client.post(
                    "/api/v1/auth/reset-password",
                    json={"token": tokens[i], "new_password": f"NewPass123456!"},
                    content_type="application/json",
                )
                # Note: First attempt will succeed and mark token as used
                # Subsequent attempts with same token will fail with 400 (invalid/expired token)
                # which still counts against rate limit
                assert response.status_code in (200, 400), f"Request {i+1} should be allowed"

            # 6th request should be rate limited (429 Too Many Requests)
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": tokens[5], "new_password": "NewPass123456!"},
                content_type="application/json",
            )
            assert response.status_code == 429, "6th request should hit rate limit (429)"

    def test_password_reset_token_one_time_use(self, app, client):
        """Test that password reset tokens can only be used once."""
        with app.app_context():
            from app.services.user_service import create_user, create_password_reset_token
            user, err = create_user("onetime", "InitPass123!", email="onetime@example.com")
            assert err is None

            # Create a reset token
            token = create_password_reset_token(user)

            # First use should succeed
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "NewPass123456!"},
                content_type="application/json",
            )
            assert response.status_code == 200, "First use should succeed"
            assert "successfully" in response.get_json()["message"]

            # Second use with same token should fail
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "AnotherPass123456!"},
                content_type="application/json",
            )
            assert response.status_code == 400, "Second use should fail with 400"
            error = response.get_json().get("error", "")
            assert "invalid" in error.lower() or "expired" in error.lower()

    def test_password_reset_token_expires_after_60_minutes(self, app, client):
        """Test that password reset tokens expire after 60 minutes."""
        with app.app_context():
            from app.services.user_service import create_user, create_password_reset_token
            user, err = create_user("expiredtoken", "InitPass123!", email="expired@example.com")
            assert err is None

            # Create a reset token
            token = create_password_reset_token(user)

            # Manually set created_at to 61 minutes ago to simulate expiration
            reset_record = PasswordResetToken.query.filter_by(user_id=user.id).first()
            assert reset_record is not None
            reset_record.created_at = datetime.now(timezone.utc) - timedelta(minutes=61)
            db.session.commit()

            # Attempt to use expired token should fail
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "NewPass123456!"},
                content_type="application/json",
            )
            assert response.status_code == 400, "Expired token should fail with 400"
            error = response.get_json().get("error", "")
            assert "invalid" in error.lower() or "expired" in error.lower()

    def test_password_reset_constant_time_delay(self, app, client):
        """Test that password reset endpoint applies constant-time delay for non-existent emails."""
        with app.app_context():
            from app.services.user_service import create_user
            user, err = create_user("exists", "InitPass123!", email="exists@example.com")
            assert err is None

            # Measure time for valid email
            start = time.time()
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "exists@example.com"},
                content_type="application/json",
            )
            valid_time = time.time() - start
            assert response.status_code == 200

            # Measure time for non-existent email
            start = time.time()
            response = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "nonexistent@example.com"},
                content_type="application/json",
            )
            nonexistent_time = time.time() - start
            assert response.status_code == 200

            # Times should be similar (within 100ms) due to constant-time delay
            # This prevents timing-based email enumeration attacks
            time_diff = abs(valid_time - nonexistent_time)
            assert time_diff < 0.1, f"Time difference {time_diff:.3f}s exceeds 100ms threshold"

    def test_reset_password_invalid_token_format(self, app, client):
        """Test that invalid token format is properly handled."""
        with app.app_context():
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": "invalid_token_format", "new_password": "NewPass123456!"},
                content_type="application/json",
            )
            assert response.status_code == 400
            error = response.get_json().get("error", "")
            assert "invalid" in error.lower() or "expired" in error.lower()

    def test_reset_password_missing_token(self, app, client):
        """Test that missing token returns 400."""
        response = client.post(
            "/api/v1/auth/reset-password",
            json={"new_password": "NewPass123456!"},
            content_type="application/json",
        )
        assert response.status_code == 400
        assert "token" in response.get_json()["error"].lower()

    def test_reset_password_weak_password_rejected(self, app, client):
        """Test that weak passwords are rejected during reset."""
        with app.app_context():
            from app.services.user_service import create_user, create_password_reset_token
            user, err = create_user("weakpass", "InitPass123!", email="weak@example.com")
            assert err is None

            token = create_password_reset_token(user)

            # Try with weak password (too short)
            response = client.post(
                "/api/v1/auth/reset-password",
                json={"token": token, "new_password": "short"},
                content_type="application/json",
            )
            assert response.status_code == 400
            assert "password" in response.get_json()["error"].lower()

    def test_forgot_password_nonexistent_email_no_enumeration(self, app, client):
        """Test that forgot-password doesn't reveal if email exists."""
        with app.app_context():
            from app.services.user_service import create_user
            user, err = create_user("exists", "InitPass123!", email="existing@example.com")
            assert err is None

            # Request for existing email
            response1 = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "existing@example.com"},
                content_type="application/json",
            )

            # Request for non-existing email
            response2 = client.post(
                "/api/v1/auth/forgot-password",
                json={"email": "notexisting@example.com"},
                content_type="application/json",
            )

            # Both should return the same message to prevent enumeration
            assert response1.status_code == 200
            assert response2.status_code == 200
            msg1 = response1.get_json()["message"]
            msg2 = response2.get_json()["message"]
            assert msg1 == msg2, "Existing and non-existing emails should return same message"

    def test_resend_verification_still_has_previous_limits(self, app, client):
        """Test that resend-verification endpoint has its own rate limiting."""
        with app.app_context():
            from app.services.user_service import create_user
            user, err = create_user("verifyuser", "InitPass123!", email="verify@example.com")
            assert err is None

            # resend-verification has "5 per minute" limit (separate from password reset)
            # This test verifies the endpoints have independent rate limiting
            for i in range(5):
                response = client.post(
                    "/api/v1/auth/resend-verification",
                    json={"email": "verify@example.com"},
                    content_type="application/json",
                )
                assert response.status_code == 200, f"Resend request {i+1} should succeed"

            # 6th request to resend-verification should hit its own limit
            response = client.post(
                "/api/v1/auth/resend-verification",
                json={"email": "verify@example.com"},
                content_type="application/json",
            )
            assert response.status_code == 429, "6th resend should hit its own rate limit"
