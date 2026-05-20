"""Evaluation runs for previews and baselines."""

from __future__ import annotations

from app.extensions import db
from app.utils.time_utils import utc_now as _utc_now


class NarrativeEvaluationRun(db.Model):
    """Persistent evaluation metadata and score summaries."""

    __tablename__ = "narrative_evaluation_runs"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    run_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    module_id = db.Column(db.String(128), nullable=False, index=True)
    preview_id = db.Column(db.String(64), nullable=True, index=True)
    package_version = db.Column(db.String(64), nullable=True)
    run_type = db.Column(db.String(64), nullable=False)
    status = db.Column(db.String(32), nullable=False, index=True)
    scores_json = db.Column(db.JSON, nullable=False, default=dict)
    promotion_readiness_json = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=_utc_now, index=True)
    completed_at = db.Column(db.DateTime(timezone=True), nullable=True)

    def to_dict(self) -> dict[str, str | dict[str, object] | None]:
        """Serialize evaluation run row."""
        return {
            "run_id": self.run_id,
            "module_id": self.module_id,
            "preview_id": self.preview_id,
            "package_version": self.package_version,
            "run_type": self.run_type,
            "status": self.status,
            "scores": self.scores_json or {},
            "promotion_readiness": self.promotion_readiness_json or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
