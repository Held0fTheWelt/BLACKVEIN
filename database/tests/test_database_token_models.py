from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from app.models import EmailVerificationToken, PasswordResetToken, RefreshToken, TokenBlacklist


class TestPasswordResetTokenModel:
    def test_password_reset_token_expires_after_configured_window(self, db, user_factory):
        user = user_factory(email="reset@example.com")
        token = PasswordResetToken(user_id=user.id, token_hash="reset-token")
        db.session.add(token)
        db.session.commit()

        assert token.is_expired is False

        token.created_at = datetime.now(timezone.utc) - timedelta(minutes=61)
        db.session.commit()
        assert token.is_expired is True

    def test_password_reset_token_hash_must_be_unique(self, db, user_factory):
        user = user_factory(email="reset2@example.com")
        db.session.add(PasswordResetToken(user_id=user.id, token_hash="duplicate-reset-hash"))
        db.session.commit()

        db.session.add(PasswordResetToken(user_id=user.id, token_hash="duplicate-reset-hash"))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


class TestEmailVerificationTokenModel:
    def test_email_verification_token_usable_state_changes_with_flags_and_expiry(self, db, user_factory):
        user = user_factory(email="verify@example.com")
        token = EmailVerificationToken(
            user_id=user.id,
            token_hash="verification-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            sent_to_email=user.email,
        )
        db.session.add(token)
        db.session.commit()

        assert token.is_expired is False
        assert token.is_usable is True

        token.used_at = datetime.now(timezone.utc)
        db.session.commit()
        assert token.is_usable is False

        token.used_at = None
        token.invalidated_at = datetime.now(timezone.utc)
        db.session.commit()
        assert token.is_usable is False

        token.invalidated_at = None
        token.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        db.session.commit()
        assert token.is_expired is True
        assert token.is_usable is False

    def test_email_verification_token_hash_must_be_unique(self, db, user_factory):
        user = user_factory(email="verify2@example.com")
        db.session.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash="dup-verify-hash",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        db.session.commit()

        db.session.add(
            EmailVerificationToken(
                user_id=user.id,
                token_hash="dup-verify-hash",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


class TestRefreshTokenModel:
    def test_refresh_token_create_and_is_valid_roundtrip(self, db, user_factory):
        user = user_factory()
        entry = RefreshToken.create(user_id=user.id, jti="jti-valid-1", token_hash="hashed-refresh-1", expires_in_seconds=3600)

        assert entry.id is not None
        assert RefreshToken.is_valid(user.id, "jti-valid-1") is True
        assert RefreshToken.is_valid(user.id, "missing") is False

    def test_refresh_token_revoke_marks_token_invalid(self, db, user_factory):
        user = user_factory()
        RefreshToken.create(user_id=user.id, jti="jti-revoke-1", token_hash="hashed-refresh-2", expires_in_seconds=3600)

        assert RefreshToken.revoke(user.id, "jti-revoke-1") is True
        assert RefreshToken.is_valid(user.id, "jti-revoke-1") is False
        assert RefreshToken.revoke(user.id, "unknown") is False

    def test_refresh_token_revoke_all_user_tokens_only_affects_open_tokens(self, db, user_factory):
        user = user_factory()
        other_user = user_factory()
        RefreshToken.create(user_id=user.id, jti="bulk-1", token_hash="hash-bulk-1", expires_in_seconds=3600)
        RefreshToken.create(user_id=user.id, jti="bulk-2", token_hash="hash-bulk-2", expires_in_seconds=3600)
        RefreshToken.create(user_id=other_user.id, jti="bulk-3", token_hash="hash-bulk-3", expires_in_seconds=3600)

        updated = RefreshToken.revoke_all_user_tokens(user.id)
        assert updated == 2
        assert RefreshToken.is_valid(user.id, "bulk-1") is False
        assert RefreshToken.is_valid(user.id, "bulk-2") is False
        assert RefreshToken.is_valid(other_user.id, "bulk-3") is True

    def test_refresh_token_cleanup_expired_removes_expired_and_old_revoked(self, db, user_factory):
        user = user_factory()
        fresh = RefreshToken(user_id=user.id, jti="fresh-jti", refresh_token="fresh-hash", expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
        expired = RefreshToken(user_id=user.id, jti="expired-jti", refresh_token="expired-hash", expires_at=datetime.now(timezone.utc) - timedelta(seconds=1))
        old_revoked = RefreshToken(
            user_id=user.id,
            jti="old-revoked-jti",
            refresh_token="old-revoked-hash",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            revoked_at=datetime.now(timezone.utc) - timedelta(days=31),
        )
        db.session.add_all([fresh, expired, old_revoked])
        db.session.commit()

        deleted = RefreshToken.cleanup_expired()
        assert deleted == 2
        assert RefreshToken.query.filter_by(jti="fresh-jti").first() is not None
        assert RefreshToken.query.filter_by(jti="expired-jti").first() is None
        assert RefreshToken.query.filter_by(jti="old-revoked-jti").first() is None

    def test_refresh_token_unique_constraints_reject_duplicates(self, db, user_factory):
        user = user_factory()
        RefreshToken.create(user_id=user.id, jti="dup-jti", token_hash="dup-hash", expires_in_seconds=3600)

        db.session.add(
            RefreshToken(
                user_id=user.id,
                jti="dup-jti",
                refresh_token="other-hash",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()

        db.session.add(
            RefreshToken(
                user_id=user.id,
                jti="other-jti",
                refresh_token="dup-hash",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
        )
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()


class TestTokenBlacklistModel:
    def test_token_blacklist_add_and_lookup_roundtrip(self, db, user_factory):
        user = user_factory()
        entry = TokenBlacklist.add(jti="blacklisted-1", user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))

        assert entry.id is not None
        assert TokenBlacklist.is_blacklisted("blacklisted-1") is True
        assert TokenBlacklist.is_blacklisted("unknown") is False

    def test_token_blacklist_cleanup_expired_removes_only_expired_entries(self, db, user_factory):
        user = user_factory()
        db.session.add_all(
            [
                TokenBlacklist(jti="tb-live", user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=2)),
                TokenBlacklist(jti="tb-expired", user_id=user.id, expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)),
            ]
        )
        db.session.commit()

        deleted = TokenBlacklist.cleanup_expired()
        assert deleted == 1
        assert TokenBlacklist.query.filter_by(jti="tb-expired").first() is None
        assert TokenBlacklist.query.filter_by(jti="tb-live").first() is not None

    def test_token_blacklist_jti_must_be_unique(self, db, user_factory):
        user = user_factory()
        TokenBlacklist.add(jti="dup-blacklist", user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=1))

        db.session.add(TokenBlacklist(jti="dup-blacklist", user_id=user.id, expires_at=datetime.now(timezone.utc) + timedelta(hours=2)))
        with pytest.raises(IntegrityError):
            db.session.commit()
        db.session.rollback()
