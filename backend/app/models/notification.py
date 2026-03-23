"""Notification foundation: basic notifications for user subscriptions."""
from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class Notification(db.Model):
    """Basic notification for thread subscriptions and other events."""

    __tablename__ = "notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)  # e.g., "thread_reply", "mention"
    target_type = db.Column(db.String(32), nullable=False)  # e.g., "forum_thread", "forum_post"
    target_id = db.Column(db.Integer, nullable=False)
    message = db.Column(db.String(512), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    read_at = db.Column(db.DateTime(timezone=True), nullable=True)

    user = db.relationship("User", backref="notifications")

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "event_type": self.event_type,
            "target_type": self.target_type,
            "target_id": self.target_id,
            "message": self.message,
            "is_read": self.is_read,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "read_at": self.read_at.isoformat() if self.read_at else None,
        }
