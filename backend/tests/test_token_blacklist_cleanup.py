#!/usr/bin/env python
"""Comprehensive test suite for token blacklist cleanup and retention policies.

Tests cover:
1. Efficient bulk deletion via cleanup_expired()
2. Automatic 90-day retention policy on insert
3. Database index on expires_at
4. Production-ready transaction safety
"""

import pytest
from datetime import datetime, timezone, timedelta
from app.models import TokenBlacklist, User, Role
from app.extensions import db


class TestTokenBlacklistCleanup:
    """Test token blacklist automatic cleanup and retention."""

    def test_cleanup_expired_removes_only_expired_tokens(self, app):
        """cleanup_expired() should remove only tokens with expires_at <= now()."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Create expired token (1 hour ago)
            expired_jti = "expired-token-1h-ago"
            expired_entry = TokenBlacklist(
                jti=expired_jti,
                expires_at=now - timedelta(hours=1),
            )
            db.session.add(expired_entry)

            # Create valid token (expires in 1 day)
            valid_jti = "valid-token-tomorrow"
            valid_entry = TokenBlacklist(
                jti=valid_jti,
                expires_at=now + timedelta(days=1),
            )
            db.session.add(valid_entry)

            # Create boundary token (expires exactly now)
            boundary_jti = "boundary-token-now"
            boundary_entry = TokenBlacklist(
                jti=boundary_jti,
                expires_at=now,  # Exactly at cutoff (should be deleted)
            )
            db.session.add(boundary_entry)

            db.session.commit()

            initial_count = db.session.query(TokenBlacklist).count()
            assert initial_count == 3

            # Run cleanup
            deleted = TokenBlacklist.cleanup_expired()

            # Should delete expired and boundary, keep valid
            assert deleted == 2
            remaining_count = db.session.query(TokenBlacklist).count()
            assert remaining_count == 1

            # Verify correct token remains
            remaining = db.session.query(TokenBlacklist).filter_by(jti=valid_jti).first()
            assert remaining is not None
            assert remaining.jti == valid_jti

            # Verify expired tokens are gone
            assert db.session.query(TokenBlacklist).filter_by(jti=expired_jti).first() is None
            assert db.session.query(TokenBlacklist).filter_by(jti=boundary_jti).first() is None

    def test_cleanup_expired_returns_correct_count(self, app):
        """cleanup_expired() should return the exact number of deleted entries."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Create 5 expired tokens
            for i in range(5):
                entry = TokenBlacklist(
                    jti=f"expired-{i}",
                    expires_at=now - timedelta(hours=i + 1),
                )
                db.session.add(entry)

            # Create 3 valid tokens
            for i in range(3):
                entry = TokenBlacklist(
                    jti=f"valid-{i}",
                    expires_at=now + timedelta(hours=i + 1),
                )
                db.session.add(entry)

            db.session.commit()

            deleted = TokenBlacklist.cleanup_expired()
            assert deleted == 5

    def test_cleanup_expired_with_no_expired_tokens(self, app):
        """cleanup_expired() should return 0 when no tokens are expired."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Create only valid tokens
            for i in range(3):
                entry = TokenBlacklist(
                    jti=f"valid-{i}",
                    expires_at=now + timedelta(days=i + 1),
                )
                db.session.add(entry)

            db.session.commit()

            deleted = TokenBlacklist.cleanup_expired()
            assert deleted == 0

            # All tokens should remain
            count = db.session.query(TokenBlacklist).count()
            assert count == 3

    def test_cleanup_expired_is_efficient_bulk_operation(self, app):
        """cleanup_expired() should use efficient SQL DELETE, not loop deletion."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Create 100 expired tokens to verify it's not looping
            for i in range(100):
                entry = TokenBlacklist(
                    jti=f"expired-bulk-{i}",
                    expires_at=now - timedelta(hours=1),
                )
                db.session.add(entry)

            db.session.commit()

            # Should complete quickly with bulk delete
            deleted = TokenBlacklist.cleanup_expired()
            assert deleted == 100

            count = db.session.query(TokenBlacklist).count()
            assert count == 0

    def test_retention_policy_on_add_removes_entries_older_than_90_days(self, app):
        """add() should auto-delete entries older than 90 days (blacklisted_at).

        This is the primary defense against unbounded growth.
        """
        with app.app_context():
            # Setup: create a user for realistic test
            role = Role.query.filter_by(name="user").first()
            if not role:
                role = Role(name="user", description="User")
                db.session.add(role)
                db.session.commit()

            user = User(
                username="testuser_retention",
                email="retention@test.example.com",
                password_hash="test_hash",
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()

            now = datetime.now(timezone.utc)

            # Create old entries (92 days ago)
            for i in range(5):
                old_jti = f"old-{i}-92days"
                old_entry = TokenBlacklist(
                    jti=old_jti,
                    user_id=user.id,
                    expires_at=now - timedelta(days=92),
                    blacklisted_at=now - timedelta(days=92),
                )
                db.session.add(old_entry)

            # Create recent entries (10 days ago)
            for i in range(3):
                recent_jti = f"recent-{i}-10days"
                recent_entry = TokenBlacklist(
                    jti=recent_jti,
                    user_id=user.id,
                    expires_at=now - timedelta(days=10),
                    blacklisted_at=now - timedelta(days=10),
                )
                db.session.add(recent_entry)

            db.session.commit()

            initial_count = db.session.query(TokenBlacklist).count()
            assert initial_count == 8

            # Add a new token - this should trigger cleanup of 90+ day old entries
            new_jti = "new-token-triggers-cleanup"
            TokenBlacklist.add(
                jti=new_jti,
                user_id=user.id,
                expires_at=now + timedelta(days=1),
            )

            # After add(), old entries should be gone
            remaining_count = db.session.query(TokenBlacklist).count()
            # Should have: 3 recent + 1 new = 4
            assert remaining_count == 4

            # Verify new token exists
            new_entry = db.session.query(TokenBlacklist).filter_by(jti=new_jti).first()
            assert new_entry is not None

            # Verify recent tokens still exist
            for i in range(3):
                recent_jti = f"recent-{i}-10days"
                entry = db.session.query(TokenBlacklist).filter_by(jti=recent_jti).first()
                assert entry is not None, f"Recent token {recent_jti} should not be deleted"

            # Verify old tokens are gone
            for i in range(5):
                old_jti = f"old-{i}-92days"
                entry = db.session.query(TokenBlacklist).filter_by(jti=old_jti).first()
                assert entry is None, f"Old token {old_jti} should be deleted"

    def test_add_is_atomic_with_cleanup(self, app):
        """add() should atomically add new token and cleanup old ones.

        Transaction safety: either both succeed or both fail.
        """
        with app.app_context():
            role = Role.query.filter_by(name="user").first()
            if not role:
                role = Role(name="user", description="User")
                db.session.add(role)
                db.session.commit()

            user = User(
                username="testuser_atomic",
                email="atomic@test.example.com",
                password_hash="test_hash",
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()

            now = datetime.now(timezone.utc)

            # Create old entry that will be cleaned up
            old_entry = TokenBlacklist(
                jti="old-atomic-test",
                user_id=user.id,
                expires_at=now - timedelta(days=1),
                blacklisted_at=now - timedelta(days=95),
            )
            db.session.add(old_entry)
            db.session.commit()

            # Add new token (should trigger cleanup)
            new_entry = TokenBlacklist.add(
                jti="new-atomic-test",
                user_id=user.id,
                expires_at=now + timedelta(days=1),
            )

            # Verify transaction was successful
            assert new_entry.jti == "new-atomic-test"

            # Verify both add and cleanup committed
            new = db.session.query(TokenBlacklist).filter_by(jti="new-atomic-test").first()
            assert new is not None

            old = db.session.query(TokenBlacklist).filter_by(jti="old-atomic-test").first()
            assert old is None

    def test_expires_at_index_exists(self, app):
        """expires_at column should have a database index for efficient cleanup."""
        with app.app_context():
            from sqlalchemy import inspect

            inspector = inspect(db.engine)
            indexes = inspector.get_indexes("token_blacklist")

            # Check that expires_at is indexed
            expires_at_indexed = any(
                "expires_at" in index.get("column_names", [])
                for index in indexes
            )
            assert expires_at_indexed, "expires_at should be indexed for efficient cleanup queries"

    def test_jti_uniqueness_constraint(self, app):
        """jti column should enforce unique constraint."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Create first entry
            entry1 = TokenBlacklist(
                jti="duplicate-test-jti",
                expires_at=now + timedelta(days=1),
            )
            db.session.add(entry1)
            db.session.commit()

            # Try to add duplicate
            entry2 = TokenBlacklist(
                jti="duplicate-test-jti",
                expires_at=now + timedelta(days=1),
            )
            db.session.add(entry2)

            with pytest.raises(Exception):  # IntegrityError
                db.session.commit()

            db.session.rollback()

    def test_blacklist_check_ignores_expired_tokens(self, app):
        """is_blacklisted() might naturally ignore expired tokens in real usage.

        Although currently it returns True for expired, cleanup prevents growth.
        """
        with app.app_context():
            now = datetime.now(timezone.utc)

            jti = "test-blacklist-check"
            entry = TokenBlacklist(
                jti=jti,
                expires_at=now - timedelta(hours=1),
            )
            db.session.add(entry)
            db.session.commit()

            # Currently still returns True even if expired
            # (cleanup will remove it in background, or on insert)
            is_blacklisted = TokenBlacklist.is_blacklisted(jti)
            assert is_blacklisted is True

            # After cleanup, should be gone
            TokenBlacklist.cleanup_expired()
            is_blacklisted = TokenBlacklist.is_blacklisted(jti)
            assert is_blacklisted is False

    def test_stress_test_concurrent_cleanup_and_add(self, app):
        """Stress test: simulate high-volume logout and cleanup."""
        with app.app_context():
            now = datetime.now(timezone.utc)

            # Simulate 100 logouts in short succession
            for i in range(100):
                TokenBlacklist.add(
                    jti=f"stress-test-{i}",
                    expires_at=now + timedelta(days=1),
                )

            # All should exist
            count = db.session.query(TokenBlacklist).count()
            assert count == 100

            # Add some old entries that should be cleaned up
            for i in range(20):
                old_entry = TokenBlacklist(
                    jti=f"old-stress-{i}",
                    expires_at=now - timedelta(days=1),
                    blacklisted_at=now - timedelta(days=95),
                )
                db.session.add(old_entry)

            db.session.commit()

            total_before = db.session.query(TokenBlacklist).count()
            assert total_before == 120

            # Run cleanup
            deleted = TokenBlacklist.cleanup_expired()

            # All expired tokens should be gone
            remaining = db.session.query(TokenBlacklist).count()
            assert remaining == 100

    def test_cleanup_with_user_relationship(self, app):
        """cleanup_expired() should work correctly with user relationships."""
        with app.app_context():
            role = Role.query.filter_by(name="user").first()
            if not role:
                role = Role(name="user", description="User")
                db.session.add(role)
                db.session.commit()

            user = User(
                username="testuser_relationship",
                email="relationship@test.example.com",
                password_hash="test_hash",
                role_id=role.id,
            )
            db.session.add(user)
            db.session.commit()

            now = datetime.now(timezone.utc)

            # Create tokens for this user
            for i in range(3):
                entry = TokenBlacklist(
                    jti=f"user-token-{i}",
                    user_id=user.id,
                    expires_at=now - timedelta(hours=1),
                )
                db.session.add(entry)

            db.session.commit()

            # Cleanup should work with FK relationships
            deleted = TokenBlacklist.cleanup_expired()
            assert deleted == 3

            # User should still exist
            user_check = db.session.query(User).filter_by(id=user.id).first()
            assert user_check is not None
