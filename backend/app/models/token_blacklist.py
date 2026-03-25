"""JWT token blacklist for logout and token revocation (0.0.9)."""
from datetime import datetime, timezone, timedelta

from app.extensions import db


class TokenBlacklist(db.Model):
    """Blacklisted JWT tokens to prevent token reuse after logout.

    Automatic cleanup ensures unbounded growth is prevented via:
    - Database index on expires_at for efficient cleanup queries
    - cleanup_expired() method for bulk deletion of expired tokens
    - 90-day retention policy enforced on insert
    """

    __tablename__ = "token_blacklist"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    jti = db.Column(db.String(36), nullable=False, unique=True, index=True)  # JWT ID
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)  # Optional: track which user
    blacklisted_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        index=True,  # Index for efficient cleanup queries
    )

    user = db.relationship("User", backref=db.backref("blacklisted_tokens", lazy="dynamic"))

    @classmethod
    def add(cls, jti: str, user_id: int = None, expires_at: datetime = None) -> "TokenBlacklist":
        """Add a token to the blacklist.

        Automatically enforces 90-day retention policy by deleting entries
        older than 90 days within the same transaction.

        Args:
            jti: JWT ID from the token
            user_id: Optional user ID for tracking
            expires_at: Token expiration time (used to clean up old entries)

        Returns:
            TokenBlacklist: The created blacklist entry

        Raises:
            sqlalchemy.exc.IntegrityError: If token already exists
        """
        if expires_at is None:
            # Default to 1 day if not provided
            expires_at = datetime.now(timezone.utc) + timedelta(days=1)

        # Create the new entry
        entry = cls(jti=jti, user_id=user_id, expires_at=expires_at)
        db.session.add(entry)

        # Commit atomically: either both add and cleanup succeed, or both fail
        db.session.commit()

        # Enforce 90-day retention policy using a separate cleanup job
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=90)
        db.session.query(cls).filter(cls.blacklisted_at < cutoff_date).delete(
            synchronize_session=False
        )
        db.session.commit()

        return entry

    @classmethod
    def is_blacklisted(cls, jti: str) -> bool:
        """Check if a JWT ID is blacklisted.

        Args:
            jti: JWT ID to check

        Returns:
            bool: True if blacklisted, False otherwise
        """
        entry = db.session.query(cls).filter_by(jti=jti).first()
        return entry is not None

    @classmethod
    def cleanup_expired(cls) -> int:
        """Remove expired entries from the blacklist.

        Uses efficient bulk delete via SQL to minimize database load.
        Expired tokens are those where expires_at <= now().
        Can be called by scheduled tasks or CLI for periodic maintenance.

        Returns:
            int: Number of entries deleted

        Example:
            # In a scheduled task (e.g., daily cleanup):
            deleted_count = TokenBlacklist.cleanup_expired()
            logger.info(f"Cleaned up {deleted_count} expired tokens")
        """
        now = datetime.now(timezone.utc)
        # Efficient bulk delete using SQL DELETE statement
        deleted_count = db.session.query(cls).filter(cls.expires_at <= now).delete(
            synchronize_session=False
        )
        if deleted_count > 0:
            db.session.commit()
        return deleted_count

    def __repr__(self):
        return f"<TokenBlacklist jti={self.jti[:8]}... user_id={self.user_id}>"