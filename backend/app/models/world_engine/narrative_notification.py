"""Operator-visible notification feed for narrative governance."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeNotification(db.Model):
    """Stored alert/feed item emitted from governance events."""

    __tablename__ = "narrative_notifications"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    notification_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(16), nullable=False, index=True)
    title = db.Column(db.String(255), nullable=False)
    body = db.Column(db.Text, nullable=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    acknowledged = db.Column(db.Boolean, nullable=False, default=False, index=True)
    acknowledged_by = db.Column(db.String(128), nullable=True)
    acknowledged_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)

    def to_dict(self) -> dict[str, str | bool | dict[str, object] | None]:
        """Serialize notification row."""
        return {
            "notification_id": self.notification_id,
            "event_type": self.event_type,
            "severity": self.severity,
            "title": self.title,
            "body": self.body,
            "payload": self.payload_json or {},
            "acknowledged": bool(self.acknowledged),
            "acknowledged_by": self.acknowledged_by,
            "acknowledged_at": self.acknowledged_at.isoformat() if self.acknowledged_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
