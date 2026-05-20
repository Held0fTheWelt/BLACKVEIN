"""Notification rules for narrative governance events."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeNotificationRule(db.Model):
    """Event routing rules for operator alerts."""

    __tablename__ = "narrative_notification_rules"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    rule_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    condition_json = db.Column(db.JSON, nullable=False, default=dict)
    channels_json = db.Column(db.JSON, nullable=False, default=list)
    recipients_json = db.Column(db.JSON, nullable=False, default=list)
    enabled = db.Column(db.Boolean, nullable=False, default=True, index=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)
    updated_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, onupdate=_utc_now)

    def to_dict(self) -> dict[str, str | bool | dict[str, object] | list[str] | None]:
        """Serialize rule row."""
        return {
            "rule_id": self.rule_id,
            "event_type": self.event_type,
            "condition": self.condition_json or {},
            "channels": [str(item) for item in (self.channels_json or [])],
            "recipients": [str(item) for item in (self.recipients_json or [])],
            "enabled": bool(self.enabled),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
