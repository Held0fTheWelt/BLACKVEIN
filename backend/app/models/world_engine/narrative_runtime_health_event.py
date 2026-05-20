"""Raw runtime health events used for degradation visibility."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeRuntimeHealthEvent(db.Model):
    """High-granularity runtime health event row."""

    __tablename__ = "narrative_runtime_health_events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    scene_id = db.Column(db.String(128), nullable=True, index=True)
    turn_number = db.Column(db.Integer, nullable=True)
    event_type = db.Column(db.String(64), nullable=False, index=True)
    severity = db.Column(db.String(16), nullable=False)
    failure_types_json = db.Column(db.JSON, nullable=True)
    payload_json = db.Column(db.JSON, nullable=False, default=dict)
    occurred_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)

    __table_args__ = (
        db.Index(
            "ix_narrative_runtime_health_events_module_scene_time",
            "module_id",
            "scene_id",
            "occurred_at",
        ),
    )

    def to_dict(self) -> dict[str, str | int | dict[str, object] | list[str] | None]:
        """Serialize runtime health event row."""
        return {
            "event_id": self.event_id,
            "module_id": self.module_id,
            "scene_id": self.scene_id,
            "turn_number": self.turn_number,
            "event_type": self.event_type,
            "severity": self.severity,
            "failure_types": [str(item) for item in (self.failure_types_json or [])],
            "payload": self.payload_json or {},
            "occurred_at": self.occurred_at.isoformat() if self.occurred_at else None,
        }
