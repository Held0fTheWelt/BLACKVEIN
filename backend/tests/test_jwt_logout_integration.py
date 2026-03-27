#!/usr/bin/env python
"""Integration test for JWT token blacklist and logout functionality."""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from datetime import datetime, timezone, timedelta
from flask_jwt_extended import create_access_token, decode_token
from app import create_app
from app.config import TestingConfig
from app.extensions import db
from app.models import User, Role, TokenBlacklist


def test_jwt_logout_integration():
    """Test complete JWT logout/revocation workflow."""
    app = create_app(TestingConfig)

    with app.app_context():
        db.create_all()

        # Setup: Create role and user
        default_role = Role.query.filter_by(name="user").first()
        if not default_role:
            default_role = Role(name="user", description="Regular user")
            db.session.add(default_role)
            db.session.commit()

        user = User(
            username="testuser",
            email="test@example.com",
            password_hash="test_hash",
            role_id=default_role.id,
        )
        db.session.add(user)
        db.session.commit()

        print("\n" + "=" * 70)
        print("JWT TOKEN BLACKLIST & LOGOUT INTEGRATION TEST")
        print("=" * 70)

        # Test 1: Create valid JWT token
        print("\n[TEST 1] Create JWT token")
        access_token = create_access_token(identity=str(user.id))
        print(f"✓ Token created: {access_token[:20]}...")

        # Decode token to verify structure
        decoded = decode_token(access_token)
        jti = decoded.get("jti")
        exp = decoded.get("exp")
        print(f"  - JTI: {jti}")
        print(f"  - Exp (timestamp): {exp}")
        print(f"  - Exp (datetime): {datetime.fromtimestamp(exp, tz=timezone.utc)}")

        # Test 2: Access protected endpoint with valid token
        print("\n[TEST 2] Access protected endpoint with valid token")
        with app.test_client() as client:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.get_json()
            print(f"✓ /api/v1/auth/me returned {response.status_code}")
            print(f"  - User ID: {data.get('id')}")
            print(f"  - Username: {data.get('username')}")

        # Test 3: Call logout endpoint
        print("\n[TEST 3] Call logout endpoint")
        with app.test_client() as client:
            response = client.post(
                "/api/v1/auth/logout",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            data = response.get_json()
            print(f"✓ /api/v1/auth/logout returned {response.status_code}")
            print(f"  - Message: {data.get('message')}")

        # Test 4: Verify token is in blacklist
        print("\n[TEST 4] Verify token is blacklisted in database")
        blacklist_entry = db.session.query(TokenBlacklist).filter_by(jti=jti).first()
        assert blacklist_entry is not None, "Token should be in blacklist"
        print(f"✓ Token found in blacklist")
        print(f"  - JTI: {blacklist_entry.jti}")
        print(f"  - User ID: {blacklist_entry.user_id}")
        print(f"  - Blacklisted at: {blacklist_entry.blacklisted_at}")
        print(f"  - Expires at: {blacklist_entry.expires_at}")

        # Test 5: Verify token is considered blacklisted by checker
        print("\n[TEST 5] Verify token is blacklisted by TokenBlacklist.is_blacklisted()")
        is_blacklisted = TokenBlacklist.is_blacklisted(jti)
        assert is_blacklisted is True, "Token should be reported as blacklisted"
        print(f"✓ TokenBlacklist.is_blacklisted('{jti[:8]}...') = {is_blacklisted}")

        # Test 6: Try to use token after logout (should fail)
        print("\n[TEST 6] Try to use token after logout (should get 401)")
        with app.test_client() as client:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {access_token}"}
            )
            assert response.status_code == 401, f"Expected 401, got {response.status_code}"
            print(f"✓ /api/v1/auth/me returned {response.status_code} (unauthorized)")
            data = response.get_json()
            if data.get("error"):
                print(f"  - Error: {data.get('error')}")

        # Test 7: Non-blacklisted token should still work
        print("\n[TEST 7] Create and verify new token works")
        new_token = create_access_token(identity=str(user.id))
        new_decoded = decode_token(new_token)
        new_jti = new_decoded.get("jti")

        with app.test_client() as client:
            response = client.get(
                "/api/v1/auth/me",
                headers={"Authorization": f"Bearer {new_token}"}
            )
            assert response.status_code == 200, f"Expected 200, got {response.status_code}"
            print(f"✓ New token works: {response.status_code}")
            print(f"  - New JTI: {new_jti[:8]}...")

        # Test 8: Cleanup expired tokens
        print("\n[TEST 8] Test cleanup_expired() functionality")
        # Add an old token that's expired
        old_jti = "old-token-expired-jti"
        old_expires = datetime.now(timezone.utc) - timedelta(hours=1)
        old_entry = TokenBlacklist.add(jti=old_jti, user_id=user.id, expires_at=old_expires)
        print(f"✓ Added old expired token: {old_jti}")

        # Verify it's in the database
        before_cleanup = db.session.query(TokenBlacklist).count()
        print(f"  - Total blacklist entries before cleanup: {before_cleanup}")

        # Run cleanup
        deleted = TokenBlacklist.cleanup_expired()
        print(f"✓ cleanup_expired() deleted {deleted} expired entries")

        # Verify expired token is gone
        after_cleanup = db.session.query(TokenBlacklist).count()
        print(f"  - Total blacklist entries after cleanup: {after_cleanup}")

        is_old_blacklisted = TokenBlacklist.is_blacklisted(old_jti)
        assert is_old_blacklisted is False, "Old token should be cleaned up"
        print(f"  - Old token is_blacklisted: {is_old_blacklisted}")

        # Current token should still be blacklisted
        is_current_blacklisted = TokenBlacklist.is_blacklisted(jti)
        assert is_current_blacklisted is True, "Current token should still be blacklisted"
        print(f"  - Current token is_blacklisted: {is_current_blacklisted}")

        print("\n" + "=" * 70)
        print("ALL INTEGRATION TESTS PASSED!")
        print("=" * 70)
        print("\nSummary:")
        print("  ✓ JWT tokens with 'jti' claim are generated correctly")
        print("  ✓ Protected endpoints work with valid tokens")
        print("  ✓ Logout endpoint adds token to blacklist")
        print("  ✓ Blacklisted tokens are stored in database with proper timezone")
        print("  ✓ TokenBlacklist.is_blacklisted() correctly identifies blacklisted tokens")
        print("  ✓ Blacklisted tokens receive 401 Unauthorized on protected endpoints")
        print("  ✓ New tokens continue to work independently")
        print("  ✓ Cleanup of expired blacklist entries works correctly")
        print()


if __name__ == "__main__":
    test_jwt_logout_integration()
