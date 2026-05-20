"""Windowed runtime health aggregates for governance dashboards."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeRuntimeHealthRollup(db.Model):
    """Aggregated runtime quality counters by module and time window."""

    __tablename__ = "narrative_runtime_health_rollups"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    window_key = db.Column(db.String(64), nullable=False, index=True)
    window_start = db.Column(db.DateTime(timezone=True), nullable=False, index=True)
    window_end = db.Column(db.DateTime(timezone=True), nullable=False)
    total_turns = db.Column(db.Integer, nullable=False, default=0)
    first_pass_success_rate = db.Column(db.Float, nullable=False, default=0.0)
    corrective_retry_rate = db.Column(db.Float, nullable=False, default=0.0)
    safe_fallback_rate = db.Column(db.Float, nullable=False, default=0.0)
    top_failure_types_json = db.Column(db.JSON, nullable=False, default=list)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now)

    __table_args__ = (
        db.Index(
            "ix_narrative_runtime_health_rollups_module_window_start",
            "module_id",
            "window_start",
        ),
        db.Index(
            "ix_narrative_runtime_health_rollups_module_windowkey_window_start",
            "module_id",
            "window_key",
            "window_start",
        ),
    )

    def to_dict(self) -> dict[str, str | int | float | list[str] | None]:
        """Serialize rollup row."""
        return {
            "module_id": self.module_id,
            "window_key": self.window_key,
            "window_start": self.window_start.isoformat() if self.window_start else None,
            "window_end": self.window_end.isoformat() if self.window_end else None,
            "total_turns": self.total_turns,
            "first_pass_success_rate": self.first_pass_success_rate,
            "corrective_retry_rate": self.corrective_retry_rate,
            "safe_fallback_rate": self.safe_fallback_rate,
            "top_failure_types": [str(item) for item in (self.top_failure_types_json or [])],
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
