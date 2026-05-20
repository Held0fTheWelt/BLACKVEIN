"""RefreshToken model for JWT refresh token flow (v0.1.0)."""
from datetime import datetime, timezone, timedelta
from uuid import uuid4

from app.extensions import db


class RefreshToken(db.Model):
    """Long-lived refresh tokens for obtaining new access tokens.

    Implements secure refresh token rotation with automatic cleanup:
    - Database indices on user_id and jti for efficient lookups
    - Revocation tracking to prevent token reuse
    - Automatic cleanup of expired tokens via cleanup_expired()
    - 7-day default expiration with configurable TTL
    """

    __tablename__ = "refresh_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)  # JWT ID (UUID)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    refresh_token = db.Column(db.String(500), nullable=False, unique=True)  # Hashed token value
    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,  # Index for efficient cleanup queries
    )
    revoked_at = db.Column(
        db.DateTime(timezone=True),
        nullable=True,
        index=True,  # Track revocation for explicit token termination
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    user = db.relationship("User", backref=db.backref("refresh_tokens", lazy="dynamic"))

    @classmethod
    def create(
        cls,
        user_id: int,
        jti: str,
        token_hash: str,
        expires_in_seconds: int = 604800,  # 7 days default
    ) -> "RefreshToken":
        """Create a new refresh token.

        Args:
            user_id: User ID
            jti: JWT ID (unique identifier for this token)
            token_hash: Hashed token value (store hash, not plaintext)
            expires_in_seconds: Token lifetime in seconds (default: 7 days = 604800)

        Returns:
            RefreshToken: The created refresh token instance
        """
        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in_seconds)
        entry = cls(
            jti=jti,
            user_id=user_id,
            refresh_token=token_hash,
            expires_at=expires_at,
        )
        db.session.add(entry)
        db.session.commit()
        return entry

    @classmethod
    def is_valid(cls, user_id: int, jti: str) -> bool:
        """Check if a refresh token is valid (exists, not expired, not revoked).

        Args:
            user_id: User ID to verify ownership
            jti: JWT ID to check

        Returns:
            bool: True if token is valid and usable
        """
        now = datetime.now(timezone.utc)
        entry = (
            db.session.query(cls)
            .filter(
                cls.user_id == user_id,
                cls.jti == jti,
                cls.expires_at > now,
                cls.revoked_at.is_(None),
            )
            .first()
        )
        return entry is not None

    @classmethod
    def revoke(cls, user_id: int, jti: str) -> bool:
        """Revoke a refresh token to prevent further use.

        Args:
            user_id: User ID for verification
            jti: JWT ID to revoke

        Returns:
            bool: True if revocation succeeded, False if token not found
        """
        entry = (
            db.session.query(cls)
            .filter(cls.user_id == user_id, cls.jti == jti)
            .first()
        )
        if entry:
            entry.revoked_at = datetime.now(timezone.utc)
            db.session.commit()
            return True
        return False

    @classmethod
    def revoke_all_user_tokens(cls, user_id: int) -> int:
        """Revoke all refresh tokens for a user (e.g., during logout).

        Args:
            user_id: User ID

        Returns:
            int: Number of tokens revoked
        """
        now = datetime.now(timezone.utc)
        updated = (
            db.session.query(cls)
            .filter(cls.user_id == user_id, cls.revoked_at.is_(None))
            .update({"revoked_at": now}, synchronize_session=False)
        )
        if updated > 0:
            db.session.commit()
        return updated

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove expired and revoked tokens.

        Uses efficient bulk delete to minimize database load.
        Expired tokens are those where expires_at <= now().
        Revoked tokens older than 30 days are also cleaned up.
        Can be called by scheduled tasks or CLI for periodic maintenance.

        Returns:
            int: Number of entries deleted
        """
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(days=30)

        # Delete expired tokens
        deleted = (
            db.session.query(cls)
            .filter(cls.expires_at <= now)
            .delete(synchronize_session=False)
        )

        # Delete revoked tokens older than 30 days
        deleted += (
            db.session.query(cls)
            .filter(cls.revoked_at <= cutoff)
            .delete(synchronize_session=False)
        )

        if deleted > 0:
            db.session.commit()

        return deleted

    def __repr__(self):
        return f"<RefreshToken jti={self.jti[:8]}... user_id={self.user_id} expires_at={self.expires_at}>"
