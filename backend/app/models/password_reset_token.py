from datetime import datetime, timezone, timedelta

from app.extensions import db

TOKEN_EXPIRY_MINUTES = 60


class PasswordResetToken(db.Model):
    __tablename__ = "password_reset_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    token_hash = db.Column(db.String(128), unique=True, nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    used = db.Column(db.Boolean, default=False, nullable=False)

    user = db.relationship("User", backref="reset_tokens")

    @property
    def is_expired(self):
        now = datetime.now(timezone.utc)
        created = self.created_at
        if created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        return now > created + timedelta(minutes=TOKEN_EXPIRY_MINUTES)
