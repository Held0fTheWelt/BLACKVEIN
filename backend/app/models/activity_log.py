"""Structured activity/audit log for admin dashboard visibility."""
from datetime import datetime, timezone

from app.extensions import db


def _utc_now():
    return datetime.now(timezone.utc)


class ActivityLog(db.Model):
    """
    Structured activity log entry for admin visibility.
    Not for raw exception dumps; use categories/actions for filtering.
    """

    __tablename__ = "activity_logs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=_utc_now,
    )

    actor_user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    actor_username_snapshot = db.Column(db.String(80), nullable=True)
    actor_role_snapshot = db.Column(db.String(20), nullable=True)

    category = db.Column(db.String(32), nullable=False, index=True)
    action = db.Column(db.String(64), nullable=False, index=True)
    status = db.Column(db.String(20), nullable=False, default="info")
    message = db.Column(db.String(512), nullable=True)

    route = db.Column(db.String(256), nullable=True)
    method = db.Column(db.String(10), nullable=True)

    tags = db.Column(db.JSON, nullable=True)
    meta = db.Column(db.JSON, nullable=True)

    target_type = db.Column(db.String(64), nullable=True)
    target_id = db.Column(db.String(64), nullable=True)

    def to_dict(self):
        return {
            "id": self.id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "actor_user_id": self.actor_user_id,
            "actor_username_snapshot": self.actor_username_snapshot,
            "actor_role_snapshot": self.actor_role_snapshot,
            "category": self.category,
            "action": self.action,
            "status": self.status,
            "message": self.message,
            "route": self.route,
            "method": self.method,
            "tags": self.tags or [],
            "metadata": self.meta or {},
            "target_type": self.target_type,
            "target_id": self.target_id,
        }

    def __repr__(self):
        return f"<ActivityLog id={self.id} category={self.category!r} action={self.action!r}>"
