"""Email verification token for new user activation (0.0.7)."""
from datetime import datetime, timezone

from app.extensions import db

PURPOSE_ACTIVATION = "activation"


class EmailVerificationToken(db.Model):
    """Time-limited token for email verification; one per purpose per user (e.g. activation)."""

    __tablename__ = "email_verification_tokens"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    invalidated_at = db.Column(db.DateTime(timezone=True), nullable=True)
    purpose = db.Column(db.String(32), nullable=False, default=PURPOSE_ACTIVATION)
    sent_to_email = db.Column(db.String(254), nullable=True)

    user = db.relationship("User", backref=db.backref("email_verification_tokens", lazy="dynamic"))

    @property
    def is_expired(self):
        now = datetime.now(timezone.utc)
        exp = self.expires_at
        if exp is None:
            return False
        if exp.tzinfo is None:
            exp = exp.replace(tzinfo=timezone.utc)
        return now > exp

    @property
    def is_usable(self):
        return (
            self.used_at is None
            and self.invalidated_at is None
            and not self.is_expired
        )
