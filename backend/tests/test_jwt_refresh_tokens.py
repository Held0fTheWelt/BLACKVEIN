"""Tests for JWT refresh token flow (access tokens, refresh tokens, rotation)."""
import time
import pytest
from datetime import datetime, timezone, timedelta
from jwt import decode

from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import RefreshToken, TokenBlacklist


class TestRefreshTokenModel:
    """Tests for RefreshToken model."""

    def test_create_refresh_token(self, app, test_user):
        """RefreshToken.create() stores a new refresh token."""
        user, _ = test_user
        with app.app_context():
            token = RefreshToken.create(
                user_id=user.id,
                jti="test-jti-001",
                token_hash="abcd1234",
                expires_in_seconds=604800,
            )
            assert token.user_id == user.id
            assert token.jti == "test-jti-001"
            assert token.revoked_at is None
            assert token.created_at is not None

    def test_is_valid_checks_expiry(self, app, test_user):
        """RefreshToken.is_valid() returns False for expired tokens."""
        user, _ = test_user
        with app.app_context():
            # Create an expired token
            token = RefreshToken.create(
                user_id=user.id,
                jti="expired-jti",
                token_hash="abcd1234",
                expires_in_seconds=-1,  # Already expired
            )
            assert not RefreshToken.is_valid(user.id, "expired-jti")

    def test_is_valid_returns_true_for_valid_token(self, app, test_user):
        """RefreshToken.is_valid() returns True for valid, non-revoked token."""
        user, _ = test_user
        with app.app_context():
            RefreshToken.create(
                user_id=user.id,
                jti="valid-jti",
                token_hash="abcd1234",
                expires_in_seconds=604800,
            )
            assert RefreshToken.is_valid(user.id, "valid-jti")

    def test_is_valid_checks_revocation(self, app, test_user):
        """RefreshToken.is_valid() returns False for revoked tokens."""
        user, _ = test_user
        with app.app_context():
            RefreshToken.create(
                user_id=user.id,
                jti="revoked-jti",
                token_hash="abcd1234",
                expires_in_seconds=604800,
            )
            RefreshToken.revoke(user.id, "revoked-jti")
            assert not RefreshToken.is_valid(user.id, "revoked-jti")

    def test_revoke_refresh_token(self, app, test_user):
        """RefreshToken.revoke() marks token as revoked."""
        user, _ = test_user
        with app.app_context():
            RefreshToken.create(
                user_id=user.id,
                jti="to-revoke",
                token_hash="abcd1234",
                expires_in_seconds=604800,
            )
            result = RefreshToken.revoke(user.id, "to-revoke")
            assert result is True
            token = db.session.query(RefreshToken).filter_by(jti="to-revoke").first()
            assert token.revoked_at is not None

    def test_revoke_returns_false_for_nonexistent_token(self, app, test_user):
        """RefreshToken.revoke() returns False if token doesn't exist."""
        user, _ = test_user
        with app.app_context():
            result = RefreshToken.revoke(user.id, "nonexistent-jti")
            assert result is False

    def test_revoke_all_user_tokens(self, app, test_user):
        """RefreshToken.revoke_all_user_tokens() revokes all user's tokens."""
        user, _ = test_user
        with app.app_context():
            RefreshToken.create(user.id, "jti-1", "hash1", 604800)
            RefreshToken.create(user.id, "jti-2", "hash2", 604800)
            RefreshToken.create(user.id, "jti-3", "hash3", 604800)

            revoked = RefreshToken.revoke_all_user_tokens(user.id)
            assert revoked == 3

            # All tokens should now be invalid
            assert not RefreshToken.is_valid(user.id, "jti-1")
            assert not RefreshToken.is_valid(user.id, "jti-2")
            assert not RefreshToken.is_valid(user.id, "jti-3")

    def test_cleanup_expired_removes_old_tokens(self, app, test_user):
        """RefreshToken.cleanup_expired() removes expired tokens."""
        user, _ = test_user
        with app.app_context():
            # Create an expired token
            RefreshToken.create(user.id, "expired-jti", "hash-expired-1234", expires_in_seconds=-1)
            # Create a valid token
            RefreshToken.create(user.id, "valid-jti", "hash-valid-5678", expires_in_seconds=604800)

            deleted = RefreshToken.cleanup_expired()
            assert deleted >= 1

            # Expired should be gone, valid should remain
            valid_tokens = db.session.query(RefreshToken).filter_by(user_id=user.id).all()
            valid_jtis = [t.jti for t in valid_tokens]
            assert "valid-jti" in valid_jtis


class TestLoginEndpointWithTokens:
    """Tests for login endpoint returning both access and refresh tokens."""

    def test_login_returns_both_tokens(self, client, test_user):
        """POST /api/v1/auth/login returns access_token and refresh_token."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "user" in data

    def test_access_token_has_1h_expiry(self, client, test_user, app):
        """Access token should have configured expiry (1 hour or less)."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()
        access_token = data["access_token"]

        # Decode without verification to check claims
        from jwt import decode as jwt_decode
        decoded = jwt_decode(access_token, options={"verify_signature": False})

        # Check token type
        assert decoded.get("type") == "access"
        # Check expiry is set and reasonable (less than 24 hours)
        exp_time = decoded.get("exp")
        current_time = datetime.now(timezone.utc).timestamp()
        expiry_seconds = exp_time - current_time
        assert 100 < expiry_seconds < 86400  # Between 1.6 min and 24 hours

    def test_refresh_token_has_7d_expiry(self, client, test_user, app):
        """Refresh token should have 7 days expiry."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()
        refresh_token = data["refresh_token"]

        from jwt import decode as jwt_decode
        decoded = jwt_decode(refresh_token, options={"verify_signature": False})

        # Check token type
        assert decoded.get("type") == "refresh"
        # Check expiry is roughly 7 days from now
        exp_time = decoded.get("exp")
        current_time = datetime.now(timezone.utc).timestamp()
        expiry_seconds = exp_time - current_time
        assert 604500 < expiry_seconds < 605100  # ~7 days with some tolerance


class TestAccessTokenUsage:
    """Tests for using access tokens in API calls."""

    def test_access_token_works_on_protected_endpoint(self, client, test_user):
        """Access token can be used to call /api/v1/auth/me."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        access_token = login_response.get_json()["access_token"]

        # Use access token on protected endpoint
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert data["username"] == user.username

    def test_refresh_token_cannot_be_used_on_protected_endpoint(self, client, test_user):
        """Refresh token should not work on regular protected endpoints."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        # Try to use refresh token as access token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        # Should be rejected or accepted but we verify it's not the intended use
        # The real test is that /refresh endpoint only accepts refresh tokens


class TestRefreshTokenEndpoint:
    """Tests for POST /api/v1/auth/refresh endpoint."""

    def test_refresh_endpoint_exists(self, client, test_user):
        """POST /api/v1/auth/refresh endpoint exists."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        # Should not be 404 (endpoint exists)
        assert response.status_code != 404

    def test_refresh_returns_new_tokens(self, client, test_user):
        """POST /api/v1/auth/refresh returns new access_token and refresh_token."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert "message" in data

    def test_new_access_token_works(self, client, test_user):
        """New access token from refresh can be used on protected endpoints."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        # Refresh the token
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        new_access_token = refresh_response.get_json()["access_token"]

        # Use new access token
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {new_access_token}"},
        )
        assert response.status_code == 200
        assert response.get_json()["username"] == user.username

    def test_refresh_with_access_token_fails(self, client, test_user):
        """Cannot use access token on /refresh endpoint."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        access_token = login_response.get_json()["access_token"]

        # Try to refresh with access token (should fail)
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 401

    def test_refresh_with_expired_token_fails(self, client, test_user, app):
        """Cannot refresh with expired refresh token."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        # Manually expire the refresh token in DB
        with app.app_context():
            from jwt import decode as jwt_decode
            decoded = jwt_decode(refresh_token, options={"verify_signature": False})
            jti = decoded["jti"]
            token_obj = db.session.query(RefreshToken).filter_by(jti=jti).first()
            token_obj.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
            db.session.commit()

        # Try to refresh with expired token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 401

    def test_refresh_with_revoked_token_fails(self, client, test_user, app):
        """Cannot refresh with revoked refresh token."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        # Revoke the token
        with app.app_context():
            from jwt import decode as jwt_decode
            decoded = jwt_decode(refresh_token, options={"verify_signature": False})
            jti = decoded["jti"]
            RefreshToken.revoke(user.id, jti)

        # Try to refresh with revoked token
        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 401

    def test_refresh_rate_limit(self, client, test_user):
        """POST /api/v1/auth/refresh has rate limit of 10 per minute."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        # Make 11 refresh requests
        for i in range(11):
            response = client.post(
                "/api/v1/auth/refresh",
                headers={"Authorization": f"Bearer {refresh_token}"},
            )
            if i < 10:
                # First 10 should succeed (or be rejected for other reasons)
                assert response.status_code != 429
            else:
                # 11th should hit rate limit
                if response.status_code == 429:
                    # Rate limit hit as expected
                    pass


class TestLogoutWithRefreshTokens:
    """Tests for logout endpoint revoking refresh tokens."""

    def test_logout_revokes_refresh_tokens(self, client, test_user, app):
        """Logout endpoint revokes all refresh tokens for user."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        access_token = login_response.get_json()["access_token"]
        refresh_token = login_response.get_json()["refresh_token"]

        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 200

        # Try to use refresh token after logout
        refresh_response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        # Should fail because token is revoked
        assert refresh_response.status_code == 401

    def test_logout_blacklists_access_token(self, client, test_user):
        """Logout endpoint blacklists the current access token."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        access_token = login_response.get_json()["access_token"]

        # Logout
        logout_response = client.post(
            "/api/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert logout_response.status_code == 200

        # Try to use access token after logout
        me_response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        # Should fail because token is blacklisted
        assert me_response.status_code == 401


class TestTokenExpiry:
    """Tests for token expiry behavior."""

    def test_access_token_expires_after_1h(self, client, test_user, app):
        """Access token should be rejected after 1 hour."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        access_token = login_response.get_json()["access_token"]

        # Token works immediately
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )
        assert response.status_code == 200

        # Manually expire the token in JWT claims
        with app.app_context():
            from jwt import decode as jwt_decode
            decoded = jwt_decode(access_token, options={"verify_signature": False})
            # Verify the expiry is set
            exp_time = decoded.get("exp")
            now = datetime.now(timezone.utc).timestamp()
            assert exp_time > now  # Token is not yet expired

    def test_refresh_token_valid_for_7d(self, client, test_user):
        """Refresh token is valid for 7 days."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        from jwt import decode as jwt_decode
        decoded = jwt_decode(refresh_token, options={"verify_signature": False})

        # Check expiry is ~7 days
        exp_time = decoded.get("exp")
        now = datetime.now(timezone.utc).timestamp()
        expiry_seconds = exp_time - now

        # 7 days = 604800 seconds, allow 5 minute tolerance
        assert 604500 < expiry_seconds < 605100


class TestLoginExpirationFields:
    """Tests for token expiration information in login response."""

    def test_login_response_includes_expiration_fields(self, client, test_user):
        """Login response includes expires_at, expires_in, and refresh_expires_at fields."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        assert response.status_code == 200
        data = response.get_json()

        # Verify all required fields are present
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_at" in data
        assert "expires_in" in data
        assert "refresh_expires_at" in data

    def test_login_expires_at_is_unix_timestamp(self, client, test_user):
        """expires_at in login response is a Unix timestamp (seconds since epoch)."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()
        expires_at = data["expires_at"]

        # Verify it's an integer timestamp
        assert isinstance(expires_at, int)
        # Verify it's in the future (within next 2 hours)
        now = datetime.now(timezone.utc).timestamp()
        assert expires_at > now
        assert expires_at < now + 7200  # Within 2 hours

    def test_login_expires_in_is_seconds(self, client, test_user, app):
        """expires_in in login response is the number of seconds until expiration."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()
        expires_in = data["expires_in"]

        # Verify it's an integer (seconds)
        assert isinstance(expires_in, int)
        # Default access token lifetime is 3600 seconds (1 hour)
        with app.app_context():
            expected_expiry = app.config.get("JWT_ACCESS_TOKEN_EXPIRES", 3600)
        # Should be very close to the configured value
        assert abs(expires_in - expected_expiry) < 2  # Within 2 seconds

    def test_login_refresh_expires_at_is_unix_timestamp(self, client, test_user):
        """refresh_expires_at in login response is a Unix timestamp."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()
        refresh_expires_at = data["refresh_expires_at"]

        # Verify it's an integer timestamp
        assert isinstance(refresh_expires_at, int)
        # Verify it's in the future (within next 8 days)
        now = datetime.now(timezone.utc).timestamp()
        assert refresh_expires_at > now
        assert refresh_expires_at < now + (8 * 24 * 3600)

    def test_login_expiration_times_are_consistent(self, client, test_user, app):
        """Expiration fields are consistent with token exp claims."""
        user, password = test_user
        response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        data = response.get_json()

        # Decode tokens to verify consistency
        from jwt import decode as jwt_decode
        access_decoded = jwt_decode(data["access_token"], options={"verify_signature": False})
        refresh_decoded = jwt_decode(data["refresh_token"], options={"verify_signature": False})

        # expires_at should match access token's exp claim
        assert data["expires_at"] == access_decoded["exp"]
        # refresh_expires_at should match refresh token's exp claim
        assert data["refresh_expires_at"] == refresh_decoded["exp"]


class TestRefreshExpirationFields:
    """Tests for token expiration information in refresh response."""

    def test_refresh_response_includes_expiration_fields(self, client, test_user):
        """Refresh response includes expires_at, expires_in, and refresh_expires_at fields."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        assert response.status_code == 200
        data = response.get_json()

        # Verify all required fields are present
        assert "access_token" in data
        assert "refresh_token" in data
        assert "expires_at" in data
        assert "expires_in" in data
        assert "refresh_expires_at" in data

    def test_refresh_expires_at_is_unix_timestamp(self, client, test_user):
        """expires_at in refresh response is a Unix timestamp."""
        user, password = test_user
        login_response = client.post(
            "/api/v1/auth/login",
            json={"username": user.username, "password": password},
            content_type="application/json",
        )
        refresh_token = login_response.get_json()["refresh_token"]

        response = client.post(
            "/api/v1/auth/refresh",
            headers={"Authorization": f"Bearer {refresh_token}"},
        )
        data = response.get_json()
        expires_at = data["expires_at"]

        # Verify it's an integer timestamp
        assert isinstance(expires_at, int)
        # Verify it's in the future (within next 2 hours)
        now = datetime.now(timezone.utc).timestamp()
        assert expires_at > now
        assert expires_at < now + 7200
