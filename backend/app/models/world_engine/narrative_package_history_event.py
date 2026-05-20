"""Append-only narrative package lifecycle history events."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativePackageHistoryEvent(db.Model):
    """Immutable event log for package lifecycle changes."""

    __tablename__ = "narrative_package_history_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    package_version = db.Column(db.String(64), nullable=True)
    from_version = db.Column(db.String(64), nullable=True)
    to_version = db.Column(db.String(64), nullable=True)
    preview_id = db.Column(db.String(64), nullable=True, index=True)
    actor_id = db.Column(db.String(128), nullable=True)
    reason = db.Column(db.Text, nullable=True)
    metadata_json = db.Column(db.JSON, nullable=False, default=dict)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)

    def to_dict(self) -> dict[str, str | int | dict[str, object] | None]:
        """Serialize history event."""
        return {
            "id": self.id,
            "module_id": self.module_id,
            "event_type": self.event_type,
            "package_version": self.package_version,
            "from_version": self.from_version,
            "to_version": self.to_version,
            "preview_id": self.preview_id,
            "actor_id": self.actor_id,
            "reason": self.reason,
            "metadata": self.metadata_json or {},
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
