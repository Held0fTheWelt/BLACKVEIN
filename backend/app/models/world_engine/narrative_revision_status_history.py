"""Append-only transition history for revision state machine."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeRevisionStatusHistory(db.Model):
    """Immutable transition records for revision workflow auditing."""

    __tablename__ = "narrative_revision_status_history"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    revision_id = db.Column(db.String(64), nullable=False, index=True)
    from_status = db.Column(db.String(32), nullable=True)
    to_status = db.Column(db.String(32), nullable=False, index=True)
    actor_id = db.Column(db.String(128), nullable=True)
    actor_role = db.Column(db.String(64), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)

    def to_dict(self) -> dict[str, str | None]:
        """Serialize transition history row."""
        return {
            "revision_id": self.revision_id,
            "from_status": self.from_status,
            "to_status": self.to_status,
            "actor_id": self.actor_id,
            "actor_role": self.actor_role,
            "notes": self.notes,
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
